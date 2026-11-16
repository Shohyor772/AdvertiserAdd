"""Isolated browser-test database. Never points at the user's db.sqlite3."""
from .settings import *

DEBUG = True
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'tmp' / 'e2e.sqlite3'}}
MEDIA_ROOT = BASE_DIR / 'tmp' / 'e2e-media'
PAYMENT_MODE = 'test'
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = BASE_DIR / 'tmp' / 'e2e-emails'
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}}
CELERY_TASK_ALWAYS_EAGER = True
LOCAL_MAINTENANCE = False
