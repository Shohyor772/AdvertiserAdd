"""Local scheduler for the educational runserver; no Redis or external services."""
import logging
import threading
from pathlib import Path
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

logger = logging.getLogger(__name__)
_started = False
_lock = threading.Lock()


def run_cycle(now=None):
    from .tasks import auto_accept, refresh_catalog
    from django.core.management import call_command
    now = now or timezone.now()
    auto_accept()
    refresh_catalog()
    marker = Path(settings.BASE_DIR) / 'backups' / '.local-backup-date'
    today = now.date().isoformat()
    if not marker.exists() or marker.read_text(encoding='utf-8').strip() != today:
        call_command('backup_database', verbosity=0)
        marker.write_text(today, encoding='utf-8')


def start():
    global _started
    with _lock:
        if _started:
            return
        _started = True
    def worker():
        # A grace period allows runserver to finish its migration checks.
        stop = threading.Event()
        stop.wait(5)
        while True:
            close_old_connections()
            try:
                run_cycle()
            except Exception:
                logger.exception('Local educational maintenance failed; retry in 60 seconds')
            finally:
                close_old_connections()
            stop.wait(60)
    threading.Thread(target=worker, name='educational-maintenance', daemon=True).start()
