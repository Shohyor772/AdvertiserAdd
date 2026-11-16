import os
import tempfile
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from django.core import signing
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from users.models import User
from .models import BloggerProfile, Campaign, CampaignResponse, Notification
from .tasks import check_fraud, match_campaign


@override_settings(EDUCATIONAL_MODE=True, PAYMENT_MODE='test', DEBUG=True)
class EducationalTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff=User.objects.create_user('edu_staff',user_type='admin',is_staff=True,email_verified=True)
        cls.ad=User.objects.create_user('edu_ad',user_type='advertiser',email_verified=True)
        cls.b=User.objects.create_user('edu_b',user_type='blogger',email_verified=True)
        cls.profile=BloggerProfile.objects.create(user=cls.b,price=1000,category='Фитнес',subscribers=10000,views=2000,age_min=18,age_max=25)

    @patch('catalog.api.send_mail')
    @patch('catalog.integrations.requests.request')
    @patch.dict(os.environ, {'DADATA_API_TOKEN':'ignored','GOOGLE_CLIENT_ID':'ignored','GOOGLE_CLIENT_SECRET':'ignored','TELEGRAM_BOT_TOKEN':'ignored','TELEGRAM_BOT_NAME':'ignored'})
    def test_registration_and_providers_are_offline(self, network, mail):
        r=self.client.post('/api/register/',{'username':'edu_new','email':'new@example.test','password':'Offline-Strong-54321','user_type':'advertiser','account_type':'company','inn':'7707083893'})
        self.assertEqual(r.status_code,201,r.data)
        self.assertTrue(r.data['verification_url'].startswith('/#/verify?token='))
        u=User.objects.get(username='edu_new')
        self.assertFalse(u.inn_verified)
        token=r.data['verification_url'].split('token=')[1]
        self.assertEqual(self.client.post('/api/verify-email/',{'token':token}).status_code,200)
        opts=self.client.get('/api/options/').data
        self.assertTrue(opts['educational_mode'])
        self.assertFalse(any(opts['social_providers'].values()))
        self.assertEqual(self.client.post('/api/auth/google/start/',{}).status_code,503)
        self.assertEqual(self.client.post('/api/auth/telegram/start/',{}).status_code,503)
        self.client.get('/auth/google/callback/?code=ignored&state=ignored')
        mail.assert_not_called();network.assert_not_called()

    def test_moderation_permissions_blocking_and_email_cannot_unblock(self):
        self.client.force_authenticate(self.ad)
        self.assertEqual(self.client.get('/api/moderation/').status_code,403)
        self.client.force_authenticate(self.staff)
        r=self.client.post(f'/api/moderation/{self.b.pk}/moderate/',{'action':'block'})
        self.assertEqual(r.status_code,200,r.data)
        self.b.refresh_from_db();self.assertTrue(self.b.is_suspended);self.assertFalse(self.b.is_active)
        self.assertEqual(self.client.get('/api/bloggers/').data['count'],0)
        token=signing.dumps({'uid':self.b.pk,'email':self.b.email},salt='email-confirm')
        self.assertEqual(self.client.post('/api/verify-email/',{'token':token}).status_code,403)
        self.assertEqual(self.client.post(f'/api/moderation/{self.b.pk}/moderate/',{'action':'unblock'}).status_code,200)
        self.assertEqual(self.client.post(f'/api/moderation/{self.staff.pk}/moderate/',{'action':'block'}).status_code,403)

    def test_local_quality_report_and_moderator_verification(self):
        self.assertEqual(check_fraud(self.profile.pk),'clear')
        self.profile.refresh_from_db();self.assertIsNotNone(self.profile.quality_checked_at)
        self.assertFalse(self.profile.is_verified)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(f'/api/moderation/{self.b.pk}/moderate/',{'action':'verify'}).status_code,200)
        self.profile.refresh_from_db();self.assertTrue(self.profile.is_verified)
        self.profile.views=1;self.profile.save(update_fields=['views'])
        check_fraud(self.profile.pk);check_fraud(self.profile.pk)
        self.profile.refresh_from_db();self.assertFalse(self.profile.is_verified)
        self.assertEqual(Notification.objects.filter(user=self.b,text__startswith='Локальная проверка').count(),1)
        self.assertEqual(self.client.post(f'/api/moderation/{self.b.pk}/moderate/',{'action':'verify'}).status_code,400)

    def test_premium_access_is_managed_by_moderator(self):
        self.client.force_authenticate(self.ad)
        self.assertEqual(self.client.get('/api/analytics/').status_code,403)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post(f'/api/moderation/{self.ad.pk}/moderate/',{'action':'grant_premium'}).status_code,200)
        self.ad.refresh_from_db()
        self.client.force_authenticate(self.ad)
        self.assertEqual(self.client.get('/api/analytics/').status_code,200)

    def test_campaign_response_is_persistent_unique_and_visible_to_owner(self):
        c=Campaign.objects.create(advertiser=self.ad,title='Фитнес',description='Спорт',category='Фитнес',budget=5000,starts_at=timezone.localdate(),ends_at=timezone.localdate()+timedelta(days=5))
        match_campaign(c.pk)
        self.client.force_authenticate(self.b)
        for _ in range(2):
            self.assertEqual(self.client.post(f'/api/campaigns/{c.pk}/respond/').status_code,200)
        self.assertEqual(CampaignResponse.objects.count(),1)
        self.client.force_authenticate(self.ad)
        self.assertEqual(self.client.get(f'/api/campaigns/{c.pk}/').data['responses'][0]['blogger'],self.profile.pk)

    def test_campaign_age_requirements_and_saved_search_notifications(self):
        from .models import SavedSearch
        from .tasks import refresh_catalog
        c=Campaign.objects.create(advertiser=self.ad,title='Фитнес',description='Спорт',category='Фитнес',budget=5000,age_min=30,age_max=45,starts_at=timezone.localdate(),ends_at=timezone.localdate()+timedelta(days=5))
        self.assertEqual(match_campaign(c.pk),[])
        s=SavedSearch.objects.create(user=self.ad,title='Фитнес',filters={'category':'Фитнес'})
        refresh_catalog();refresh_catalog()
        self.assertEqual(Notification.objects.filter(user=self.ad,text__startswith='Новые блогеры').count(),1)
        s.refresh_from_db();self.assertEqual(s.last_result_ids,[self.profile.pk])

    def test_local_scheduler_runs_jobs_and_only_one_backup_per_day(self):
        from .maintenance import run_cycle
        with tempfile.TemporaryDirectory() as directory, override_settings(BASE_DIR=Path(directory)), patch('catalog.tasks.auto_accept') as accept, patch('catalog.tasks.refresh_catalog') as refresh, patch('django.core.management.call_command') as backup:
            (Path(directory)/'backups').mkdir()
            run_cycle();run_cycle()
            self.assertEqual(accept.call_count,2);self.assertEqual(refresh.call_count,2)
            backup.assert_called_once_with('backup_database',verbosity=0)
