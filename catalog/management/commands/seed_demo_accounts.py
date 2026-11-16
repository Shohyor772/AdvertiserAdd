"""Create an additive demo dataset; never reset or modify existing accounts."""
import secrets
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import User
from catalog.models import BloggerProfile


BLOGGERS = [
    ('Анна · Красота', 'Telegram', 'Красота', 'Москва', 18000, 6800, 7000, 4.2, 88, 18, 34),
    ('Максим · Технологии', 'YouTube', 'Технологии', 'Санкт-Петербург', 95000, 42000, 35000, 5.1, 32, 18, 44),
    ('Елена · Фитнес', 'TikTok', 'Фитнес', 'Казань', 56000, 23000, 16000, 6.4, 76, 18, 34),
    ('Дмитрий · Игры', 'YouTube', 'Игры', 'Москва', 210000, 87000, 65000, 4.8, 24, 16, 30),
    ('Ольга · Путешествия', 'Telegram', 'Путешествия', 'Екатеринбург', 32000, 11000, 12000, 3.9, 65, 25, 44),
    ('Илья · Образование', 'Telegram', 'Образование', 'Новосибирск', 8500, 3200, 3000, 5.5, 58, 18, 35),
]


class Command(BaseCommand):
    help = 'Create 3 advertisers, 6 bloggers and a support moderator for local manual testing.'

    def handle(self, *args, **options):
        if not settings.DEBUG or settings.PAYMENT_MODE != 'test':
            raise CommandError('Demo accounts require DEBUG=true and PAYMENT_MODE=test.')
        accounts = [(f'demo_brand{i}', 'advertiser', name) for i, name in enumerate(
            ['Демо · Косметический бренд', 'Демо · Магазин техники', 'Демо · Спортивный клуб'], 1)]
        accounts += [(f'demo_blogger{i}', 'blogger', row[0]) for i, row in enumerate(BLOGGERS, 1)]
        accounts += [('demo_support', 'admin', 'Демо · Поддержка')]
        existing = list(User.objects.filter(username__in=[a[0] for a in accounts]).values_list('username', flat=True))
        if existing:
            raise CommandError('Accounts already exist; nothing changed: '+', '.join(existing))
        password = 'Demo-'+secrets.token_urlsafe(12)+'!'
        target = Path(settings.BASE_DIR) / 'tmp' / 'demo-accounts.md'
        target.parent.mkdir(exist_ok=True)
        if target.exists():
            raise CommandError('Existing credential file retained: '+str(target))
        with transaction.atomic():
            for username, role, name in accounts:
                user = User.objects.create_user(
                    username=username, password=password,
                    email=username+'@demo.example.test', first_name=name,
                    user_type=role, email_verified=True, is_active=True,
                    is_staff=role == 'admin', is_premium=role == 'advertiser',
                )
                if role == 'blogger':
                    row = BLOGGERS[int(username.removeprefix('demo_blogger'))-1]
                    _, platform, category, city, subscribers, views, price, er, female, age_min, age_max = row
                    BloggerProfile.objects.create(
                        user=user, platform=platform, category=category, city=city,
                        subscribers=subscribers, views=views, price=price,
                        engagement_rate=er, female_percent=female,
                        age_min=age_min, age_max=age_max,
                        bio='Демонстрационный профиль для проверки приложения. Все показатели вымышлены.',
                        forbidden_topics='казино, алкоголь',
                        reply_template='Спасибо за предложение! Готов обсудить формат, сроки и стоимость.',
                        is_verified=False, fraud_status='unverified',
                    )
            lines = ['# Локальные демонстрационные аккаунты', '',
                     'Только для тестирования. Все профили и показатели вымышлены.', '',
                     'Адрес: http://127.0.0.1:8000/#/login', '',
                     'Общий пароль: `'+password+'`', '',
                     '| Логин | Роль | Имя |', '|---|---|---|']
            lines += [f'| {username} | {role} | {name} |' for username, role, name in accounts]
            target.write_text('\n'.join(lines)+'\n', encoding='utf-8')
        self.stdout.write(self.style.SUCCESS(f'Created {len(accounts)} accounts and {len(BLOGGERS)} profiles. Existing data unchanged.'))
        self.stdout.write('Credentials: '+str(target))
