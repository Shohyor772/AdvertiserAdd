import re
import tempfile
from datetime import timedelta
from django.core import mail
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from users.models import User
from .models import BloggerProfile, Proposal, Deal, LedgerEntry, Notification, Review, Campaign
from .tasks import auto_accept, match_campaign, check_fraud


@override_settings(PAYMENT_MODE='test', DEBUG=True, EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', MEDIA_ROOT=tempfile.mkdtemp())
class WorkflowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ad = User.objects.create_user('advertiser', 'ad@example.com', 'test-Strong-54321', user_type='advertiser', email_verified=True)
        cls.b = User.objects.create_user('blogger', 'b@example.com', 'test-Strong-54321', user_type='blogger', email_verified=True)
        cls.other = User.objects.create_user('stranger', 'other@example.com', 'test-Strong-54321', user_type='advertiser', email_verified=True)
        cls.admin = User.objects.create_user('moderator', 'm@example.com', 'test-Strong-54321', is_staff=True, user_type='admin')
        cls.profile = BloggerProfile.objects.create(user=cls.b, price=10000, subscribers=20000, category='Фитнес', city='Москва', views=10000, female_percent=85, age_min=18, age_max=25)

    def as_user(self, user):
        self.client.force_authenticate(user)

    def proposal(self):
        self.as_user(self.ad)
        r = self.client.post('/api/proposals/', {'blogger': self.profile.pk, 'price': 10000, 'message': 'Интеграция спортивного питания'})
        self.assertEqual(r.status_code, 201, r.data)
        return r.data['id']

    def agreed(self):
        pid = self.proposal()
        self.as_user(self.b)
        r = self.client.post(f'/api/proposals/{pid}/negotiate/', {'action': 'accept'})
        self.assertEqual(r.status_code, 200, r.data)
        return Deal.objects.get(proposal_id=pid)

    def paid(self):
        d = self.agreed()
        self.as_user(self.ad)
        r = self.client.post(f'/api/deals/{d.pk}/pay/')
        self.assertEqual(r.status_code, 200, r.data)
        return d

    def submitted(self):
        d = self.paid()
        self.as_user(self.b)
        r = self.client.post(f'/api/deals/{d.pk}/submit/', {'publication_url': 'https://t.me/blogger/123'})
        self.assertEqual(r.status_code, 200, r.data)
        return d

    def test_registration_email_confirmation_and_jwt(self):
        r = self.client.post('/api/register/', {'username': 'newperson', 'email': 'new@example.com', 'password': 'Password-54321-strong', 'user_type': 'advertiser'})
        self.assertEqual(r.status_code, 201, r.data)
        u = User.objects.get(username='newperson')
        self.assertFalse(u.is_active)
        self.assertTrue(u.check_password('Password-54321-strong'))
        token = mail.outbox[-1].body.split('token=')[-1]
        r = self.client.post('/api/verify-email/', {'token': token})
        self.assertEqual(r.status_code, 200)
        r = self.client.post('/api/login/', {'username': 'newperson', 'password': 'Password-54321-strong'})
        self.assertIn('access', r.data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer '+r.data['access'])
        self.assertEqual(self.client.get('/api/me/').status_code, 200)

    def test_registration_cannot_escalate_role_or_use_bad_inn(self):
        data = {'username': 'newperson', 'email': 'new@example.com', 'password': 'Password-54321-strong', 'user_type': 'admin'}
        self.assertEqual(self.client.post('/api/register/', data).status_code, 400)
        data.update(user_type='advertiser', account_type='company', inn='1234567890')
        self.assertEqual(self.client.post('/api/register/', data).status_code, 400)
        self.assertFalse(User.objects.filter(username='newperson').exists())

    def test_blocked_account_is_not_reactivated_by_old_email(self):
        from django.core import signing
        self.ad.is_active = False
        self.ad.save()
        token = signing.dumps({'uid': self.ad.pk, 'email': self.ad.email}, salt='email-confirm')
        self.client.post('/api/verify-email/', {'token': token})
        self.ad.refresh_from_db()
        self.assertFalse(self.ad.is_active)

    def test_catalog_filters_and_empty_results(self):
        r = self.client.get('/api/bloggers/', {'city': 'Москва', 'female_percent': 80, 'price_max': 10000, 'age_min': 16, 'age_max': 25, 'platform': 'Telegram'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(self.client.get('/api/bloggers/', {'price_max': 9999}).data['count'], 0)
        self.assertEqual(self.client.get('/api/bloggers/', {'price_max': 'abc'}).status_code, 400)
        self.assertEqual(self.client.get('/api/bloggers/', {'price_min': 20, 'price_max': 10}).status_code, 400)

    def test_proposal_auth_validation_and_chat(self):
        self.assertEqual(self.client.post('/api/proposals/', {}).status_code, 401)
        self.as_user(self.ad)
        for price, message in [(-1, 'ТЗ'), ('oops', 'ТЗ'), (100, '')]:
            self.assertEqual(self.client.post('/api/proposals/', {'blogger': self.profile.pk, 'price': price, 'message': message}).status_code, 400)
        pid = self.proposal()
        p = Proposal.objects.get(pk=pid)
        self.assertEqual(p.advertiser_id, self.ad.pk)
        self.assertEqual(p.messages.count(), 1)
        self.assertTrue(Notification.objects.filter(user=self.b).exists())
        self.as_user(self.b)
        self.assertEqual(self.client.post('/api/proposals/', {'blogger': self.profile.pk, 'price': 100, 'message': 'test'}).status_code, 403)

    def test_private_objects_and_files(self):
        pid = self.proposal()
        self.as_user(self.other)
        self.assertEqual(self.client.get(f'/api/proposals/{pid}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/proposals/{pid}/message/', {'text': 'x'}).status_code, 404)
        self.assertEqual(self.client.get(f'/api/files/brief/{pid}/').status_code, 403)

    def test_counter_offer_and_acceptance_by_other_party(self):
        pid = self.proposal()
        self.assertEqual(self.client.post(f'/api/proposals/{pid}/negotiate/', {'action': 'accept'}).status_code, 400)
        self.as_user(self.b)
        self.assertEqual(self.client.post(f'/api/proposals/{pid}/negotiate/', {'action': 'counter', 'price': 12000}).status_code, 200)
        self.assertEqual(self.client.post(f'/api/proposals/{pid}/negotiate/', {'action': 'accept'}).status_code, 400)
        self.as_user(self.ad)
        self.assertEqual(self.client.post(f'/api/proposals/{pid}/negotiate/', {'action': 'accept'}).status_code, 200)
        self.assertEqual(Deal.objects.get(proposal_id=pid).amount, 12000)
        self.assertEqual(self.client.post(f'/api/proposals/{pid}/negotiate/', {'action': 'accept'}).status_code, 400)

    def test_payment_only_owner_and_only_once(self):
        d = self.agreed()
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/pay/').status_code, 403)
        self.as_user(self.ad)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/pay/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/pay/').status_code, 400)
        self.assertEqual(LedgerEntry.objects.filter(deal=d, kind='hold').count(), 1)

    @override_settings(PAYMENT_MODE='disabled')
    def test_disabled_payment_does_not_create_reserve(self):
        d = self.agreed()
        self.as_user(self.ad)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/pay/').status_code, 400)
        self.assertFalse(d.ledger.exists())

    def test_complete_workflow_and_review(self):
        d = self.submitted()
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/accept/').status_code, 403)
        self.as_user(self.ad)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/accept/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/accept/').status_code, 400)
        self.assertEqual(d.ledger.get(kind='payout').amount, 9000)
        self.assertEqual(d.ledger.get(kind='commission').amount, 1000)
        r = self.client.post('/api/reviews/', {'deal': d.pk, 'rating': 3, 'text': 'Была задержка'})
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(self.client.post('/api/reviews/', {'deal': d.pk, 'rating': 5}).status_code, 400)
        self.assertEqual(self.client.get(f'/api/bloggers/{self.profile.pk}/').data['rating'], 3)
        self.as_user(self.b)
        self.assertEqual(self.client.post('/api/reviews/', {'deal': d.pk, 'rating': 5}).status_code, 201)

    def test_revision_requires_reason_and_resubmission(self):
        d = self.submitted()
        self.as_user(self.ad)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/revise/', {'reason': ''}).status_code, 400)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/revise/', {'reason': 'Добавить ссылку на магазин'}).status_code, 200)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/accept/').status_code, 400)
        self.as_user(self.b)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/submit/', {'publication_url': 'javascript:alert(1)'}).status_code, 400)
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/submit/', {'publication_url': 'https://t.me/blogger/124'}).status_code, 200)

    def test_arbitration_blocks_acceptance_and_refunds_once(self):
        d = self.submitted()
        self.as_user(self.ad)
        r = self.client.post(f'/api/deals/{d.pk}/dispute/', {'reason': 'Не соответствует ТЗ'})
        self.assertEqual(r.status_code, 201, r.data)
        sid = r.data['id']
        self.assertEqual(self.client.post(f'/api/deals/{d.pk}/accept/').status_code, 400)
        self.assertEqual(self.client.post(f'/api/disputes/{sid}/resolve/', {'decision': 'advertiser', 'resolution': 'Возврат'}).status_code, 403)
        self.as_user(self.admin)
        self.assertEqual(self.client.post(f'/api/disputes/{sid}/resolve/', {'decision': 'advertiser', 'resolution': 'Требования ТЗ не выполнены'}).status_code, 200)
        self.assertEqual(self.client.post(f'/api/disputes/{sid}/resolve/', {'decision': 'blogger', 'resolution': 'Повтор'}).status_code, 400)
        self.assertEqual(d.ledger.get(kind='refund').amount, 10000)
        self.assertFalse(d.ledger.filter(kind='payout').exists())

    def test_auto_accept_after_three_days_only(self):
        d = self.submitted()
        self.assertEqual(auto_accept(), 0)
        Deal.objects.filter(pk=d.pk).update(submitted_at=timezone.now()-timedelta(days=3, minutes=1))
        self.assertEqual(auto_accept(), 1)
        self.assertEqual(auto_accept(), 0)

    def test_campaign_matching_budget_and_deduplication(self):
        c = Campaign.objects.create(advertiser=self.ad, title='Спортивное питание', description='Кампания', category='Спорт', budget=12000, starts_at=timezone.localdate(), ends_at=timezone.localdate()+timedelta(days=10))
        self.assertEqual(match_campaign(c.pk), [self.profile.pk])
        self.assertEqual(match_campaign(c.pk), [])
        self.assertEqual(c.matched_bloggers.count(), 1)

    def test_antifraud_does_not_verify_manual_data(self):
        self.profile.views = 5
        self.profile.save()
        self.assertEqual(check_fraud(self.profile.pk), 'suspicious')
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_verified)

    def test_profile_readonly_privileges_and_range_validation(self):
        self.as_user(self.b)
        self.assertEqual(self.client.patch('/api/profile/', {'age_min': 50, 'age_max': 20}).status_code, 400)
        self.assertEqual(self.client.patch('/api/profile/', {'is_verified': True, 'price': 12000}).status_code, 200)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.is_verified)
        self.client.patch('/api/me/', {'is_staff': True, 'is_premium': True})
        self.b.refresh_from_db()
        self.assertFalse(self.b.is_staff)
        self.assertFalse(self.b.is_premium)
