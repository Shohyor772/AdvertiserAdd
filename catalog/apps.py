from django.apps import AppConfig


class CatalogConfig(AppConfig):
    name = 'catalog'
    def ready(self):
        import os
        import sys
        from django.conf import settings
        if settings.LOCAL_MAINTENANCE and 'runserver' in sys.argv and ('--noreload' in sys.argv or os.getenv('RUN_MAIN') == 'true'):
            from .maintenance import start
            start()
