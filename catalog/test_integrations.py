import hashlib
import hmac
import os
import time
from unittest.mock import patch
from django.test import override_settings
from rest_framework.test import APITestCase, APIClient
from users.models import User
from .models import BloggerProfile, SocialIdentity
from .integrations import ProviderUnavailable, youtube_statistics


@override_settings(DEBUG=True, EDUCATIONAL_MODE=False)
class IntegrationTests(APITestCase):
    def test_unconfigured_oauth_is_not_a_fake_login(self):
        with patch.dict(os.environ, {'GOOGLE_CLIENT_ID':'','GOOGLE_CLIENT_SECRET':''}):
            self.assertEqual(self.client.post('/api/auth/google/start/', {}).status_code, 503)
        self.assertEqual(User.objects.count(), 0)

    def test_invalid_oauth_state_is_rejected(self):
        r = self.client.get('/auth/google/callback/?state=forged&code=forged')
        self.assertIn('oauth_error=state', r.url)
        self.assertEqual(User.objects.count(), 0)

    @patch.dict(os.environ, {'GOOGLE_CLIENT_ID':'test-client','GOOGLE_CLIENT_SECRET':'test-secret'})
    @patch('catalog.social.provider_json')
    def test_google_oauth_pkce_csrf_and_one_time_exchange(self, provider):
        self.client = APIClient(enforce_csrf_checks=True)
        r = self.client.post('/api/auth/google/start/', {'provider':'google'})
        self.assertIn('code_challenge_method=S256', r.data['authorization_url'])
        attempt = self.client.session['oauth_attempt']
        provider.side_effect = [{'access_token':'provider-token'}, {'sub':'google-subject','email':'social@example.test','email_verified':True,'name':'Social user'}]
        r = self.client.get('/auth/google/callback/', {'state':attempt['state'],'code':'provider-code'})
        self.assertEqual(r.url, '/#/oauth')
        user = User.objects.get(email='social@example.test')
        self.assertFalse(user.has_usable_password())
        self.assertTrue(user.email_verified)
        self.assertTrue(BloggerProfile.objects.filter(user=user).exists())
        self.assertEqual(self.client.post('/api/auth/exchange/').status_code, 403)
        csrf = self.client.cookies['csrftoken'].value
        r = self.client.post('/api/auth/exchange/', HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(r.status_code, 200, r.data)
        self.assertIn('access', r.data)
        self.assertEqual(self.client.post('/api/auth/exchange/', HTTP_X_CSRFTOKEN=csrf).status_code, 403)

    @patch.dict(os.environ, {'GOOGLE_CLIENT_ID':'test-client','GOOGLE_CLIENT_SECRET':'test-secret'})
    @patch('catalog.social.provider_json')
    def test_email_collision_does_not_link_an_existing_account(self, provider):
        User.objects.create_user('existing','same@example.test','Local-Password-456')
        self.client.post('/api/auth/google/start/', {})
        attempt = self.client.session['oauth_attempt']
        provider.side_effect = [{'access_token':'provider-token'}, {'sub':'external','email':'same@example.test','email_verified':True}]
        r = self.client.get('/auth/google/callback/', {'state':attempt['state'],'code':'code'})
        self.assertIn('oauth_error=unavailable', r.url)
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(SocialIdentity.objects.exists())

    @patch.dict(os.environ, {'GOOGLE_CLIENT_ID':'test-client','GOOGLE_CLIENT_SECRET':'test-secret'})
    @patch('catalog.social.youtube_statistics', side_effect=ProviderUnavailable())
    @patch('catalog.social.provider_json')
    def test_youtube_api_failure_preserves_account(self, provider, stats):
        self.client.post('/api/auth/google/start/', {'provider':'youtube'})
        attempt = self.client.session['oauth_attempt']
        provider.side_effect = [{'access_token':'provider-token'}, {'sub':'youtube-sub','email':'yt@example.test','email_verified':True}]
        r = self.client.get('/auth/google/callback/', {'state':attempt['state'],'code':'code'})
        self.assertIn('stats=partial', r.url)
        self.assertTrue(BloggerProfile.objects.filter(user__email='yt@example.test', is_verified=False).exists())

    @patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN':'test-bot-token','TELEGRAM_BOT_NAME':'test_bot'})
    def test_telegram_signature_and_nonce_replay(self):
        r = self.client.post('/api/auth/telegram/start/')
        nonce = r.data['nonce']
        data = {'id':12345,'first_name':'Telegram user','auth_date':int(time.time())}
        content = '\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
        data['hash'] = hmac.new(hashlib.sha256(b'test-bot-token').digest(), content.encode(), hashlib.sha256).hexdigest()
        r = self.client.post('/api/auth/telegram/login/', {'nonce':nonce,'auth':data}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.client.post('/api/auth/telegram/login/', {'nonce':nonce,'auth':data}, format='json').status_code, 403)
        self.assertEqual(SocialIdentity.objects.get().provider, 'telegram')

    @patch('catalog.integrations.provider_json')
    def test_youtube_partial_data_does_not_use_total_views_as_average(self, provider):
        provider.side_effect = [{'items':[{'id':'channel123','statistics':{'subscriberCount':'12345','viewCount':'999999999'}}]}, ProviderUnavailable(), ProviderUnavailable()]
        result = youtube_statistics('token')
        self.assertEqual(result['subscribers'], 12345)
        self.assertNotIn('views', result)

    def test_csv_export_preserves_filter_and_escapes_spreadsheet_formulas(self):
        ad = User.objects.create_user('ad','ad@example.test',user_type='advertiser')
        user = User.objects.create_user('blogger','b@example.test')
        BloggerProfile.objects.create(user=user, category='=FORMULA()', city='Москва', price=2000)
        self.client.force_authenticate(ad)
        r = self.client.get('/api/export/?city=Москва')
        self.assertEqual(r.status_code, 200)
        self.assertIn("'=FORMULA()", r.content.decode('utf-8'))
        self.assertNotIn('example.test', r.content.decode('utf-8'))
