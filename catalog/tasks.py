from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from .models import BloggerProfile, Campaign, Deal, SavedSearch
from .services import complete, notify

RELATED_CATEGORIES = {'Фитнес': ['Спорт', 'ЗОЖ', 'Здоровье'], 'Спорт': ['Фитнес', 'ЗОЖ'], 'Красота': ['Мода', 'Здоровье'], 'Технологии': ['Игры', 'Образование']}


@shared_task
def match_campaign(campaign_id):
    with transaction.atomic():
        c = Campaign.objects.select_for_update().get(pk=campaign_id)
        candidates = BloggerProfile.objects.filter(user__is_active=True, price__lte=c.budget, subscribers__gte=c.min_subscribers, female_percent__gte=c.female_percent)
        if c.city:
            candidates = candidates.filter(city__iexact=c.city)
        matched = candidates.filter(category__iexact=c.category)
        if not matched.exists():
            matched = candidates.filter(category__in=RELATED_CATEGORIES.get(c.category, []))
        existing = set(c.matched_bloggers.values_list('id', flat=True))
        new = []
        for b in matched:
            forbidden = [s.strip().casefold() for s in b.forbidden_topics.replace(',', '\n').splitlines() if s.strip()]
            if b.pk not in existing and not any(t in (c.title+' '+c.description+' '+c.category).casefold() for t in forbidden):
                c.matched_bloggers.add(b)
                new.append(b.pk)
                notify(b.user_id, 'Новая кампания: '+c.title, '#/campaigns')
        if new:
            notify(c.advertiser_id, f'К кампании «{c.title}» подобрано новых блогеров: {len(new)}', '#/campaigns')
        return new


@shared_task
def auto_accept():
    from rest_framework.exceptions import ValidationError
    ids = Deal.objects.filter(status='submitted', submitted_at__lte=timezone.now()-timedelta(days=3)).values_list('id', flat=True)
    count = 0
    for did in list(ids):
        try:
            complete(did, automatic=True)
            count += 1
        except ValidationError:
            continue
    return count


@shared_task
def check_fraud(profile_id):
    """Heuristics identify suspicious self-reported data; never claim verification."""
    b = BloggerProfile.objects.get(pk=profile_id)
    notes = []
    if b.subscribers >= 5000 and b.views < b.subscribers * .01:
        notes.append('Мало просмотров относительно подписчиков')
    if b.engagement_rate > 30:
        notes.append('Аномально высокий ER')
    b.fraud_status = 'suspicious' if notes else 'unverified'
    b.fraud_notes = '; '.join(notes) or 'Нет подтверждённых данных API для полноценной проверки.'
    b.save(update_fields=['fraud_status', 'fraud_notes'])
    return b.fraud_status


@shared_task
def refresh_catalog():
    from .search import search_bloggers
    from urllib.parse import urlencode
    for pk in BloggerProfile.objects.values_list('pk', flat=True).iterator():
        check_fraud(pk)
    for pk in Campaign.objects.filter(ends_at__gte=timezone.localdate()).values_list('pk', flat=True).iterator():
        match_campaign(pk)
    for s in SavedSearch.objects.all().iterator():
        ids = list(search_bloggers(s.filters).values_list('id', flat=True))
        if set(ids)-set(s.last_result_ids):
            notify(s.user_id, 'Новые блогеры по поиску «'+s.title+'»', '#/?'+urlencode(s.filters))
        s.last_result_ids = ids
        s.save(update_fields=['last_result_ids'])


@shared_task
def daily_backup():
    from django.core.management import call_command
    call_command('backup_database')
