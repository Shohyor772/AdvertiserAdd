"""Create test fixtures only in the explicitly isolated e2e database."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.e2e_settings'
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from users.models import User
from catalog.models import BloggerProfile

assert Path(settings.DATABASES['default']['NAME']).resolve() == (settings.BASE_DIR / 'tmp' / 'e2e.sqlite3').resolve()
(settings.BASE_DIR / 'tmp').mkdir(exist_ok=True)
call_command('migrate', verbosity=0)
for username, role in [('e2e_ad', 'advertiser'), ('e2e_blogger', 'blogger'), ('e2e_admin', 'admin')]:
    u, created = User.objects.get_or_create(username=username, defaults={'email': username+'@example.test', 'user_type': role, 'email_verified': True, 'is_staff': role == 'admin', 'is_premium': True})
    if created:
        u.set_password('E2e-Local-Only-8472')
        u.save()
    if role == 'blogger':
        BloggerProfile.objects.get_or_create(user=u, defaults={'platform': 'Telegram', 'subscribers': 24000, 'views': 9000, 'price': 12000, 'category': 'Технологии', 'city': 'Москва', 'female_percent': 70, 'age_min': 18, 'age_max': 30, 'bio': 'Технологии и повседневная жизнь. Объясняю сложное простыми словами.'})
print('E2E fixtures ready; user database untouched.')
