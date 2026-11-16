from django.core.management.base import BaseCommand
from catalog.tasks import auto_accept, refresh_catalog


class Command(BaseCommand):
    help = 'Run auto-acceptance, matching and heuristic checks synchronously (local fallback without Celery).'
    def handle(self, *args, **options):
        count = auto_accept()
        refresh_catalog()
        self.stdout.write(f'Accepted: {count}; catalog maintenance complete.')
