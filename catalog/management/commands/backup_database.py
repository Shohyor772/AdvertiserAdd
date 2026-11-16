from pathlib import Path
import sqlite3
import subprocess
import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = 'Online SQLite backup or PostgreSQL pg_dump; never overwrites a previous backup.'
    def handle(self, *args, **options):
        folder = Path(settings.BASE_DIR) / 'backups'
        folder.mkdir(exist_ok=True)
        name = timezone.now().strftime('%Y%m%d-%H%M%S-%f')
        db = settings.DATABASES['default']
        if db['ENGINE'].endswith('sqlite3'):
            target = folder / (name+'.sqlite3')
            with sqlite3.connect(str(db['NAME'])) as src, sqlite3.connect(target) as dst:
                src.backup(dst)
                if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('Backup integrity check failed')
        else:
            target = folder / (name+'.dump')
            env = dict(os.environ, PGPASSWORD=db['PASSWORD'])
            subprocess.run(['pg_dump', '-h', db['HOST'], '-p', str(db.get('PORT', 5432)), '-U', db['USER'], '-Fc', '-f', str(target), db['NAME']], env=env, check=True)
        self.stdout.write(str(target))
