#!/bin/sh
set -eu
python manage.py backup_database
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if python -c "import os,sys;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings');from django.conf import settings;sys.exit(0 if settings.EDUCATIONAL_MODE else 1)"; then
    exec python manage.py runserver 0.0.0.0:8000 --noreload
fi
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 45 --access-logfile -
