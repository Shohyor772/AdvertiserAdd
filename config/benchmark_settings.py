from .e2e_settings import *

DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'tmp'/'benchmark.sqlite3'}}
