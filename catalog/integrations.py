"""External API adapters. No fabricated successes when credentials are absent."""
import os
from datetime import timedelta
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException


class ProviderUnavailable(APIException):
    status_code = 503
    default_detail = 'Внешний сервис временно недоступен. Данные сохранены, попробуйте позже.'


def provider_json(method, url, **kwargs):
    if settings.EDUCATIONAL_MODE:
        raise ProviderUnavailable('В учебной версии внешние подключения отключены.')
    try:
        r = requests.request(method, url, timeout=15, **kwargs)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise ValueError('Expected object')
        return data
    except (requests.RequestException, ValueError) as exc:
        # Do not include response bodies or tokens in user-facing errors/logs.
        raise ProviderUnavailable() from exc


def youtube_statistics(token):
    headers = {'Authorization': 'Bearer '+token}
    channel = provider_json('GET', 'https://www.googleapis.com/youtube/v3/channels', headers=headers, params={'part': 'statistics,snippet', 'mine': 'true'})
    items = channel.get('items', [])
    if not items:
        raise ProviderUnavailable('Канал YouTube не найден. Заполните профиль вручную.')
    c = items[0]
    result = {'platform': 'YouTube', 'subscribers': int(c['statistics'].get('subscriberCount', 0)), 'channel_url': 'https://www.youtube.com/channel/'+c['id'], 'stats_updated_at': timezone.now()}
    end = timezone.localdate()-timedelta(days=2)
    try:
        report = provider_json('GET', 'https://youtubeanalytics.googleapis.com/v2/reports', headers=headers, params={'ids':'channel==MINE','startDate':str(end-timedelta(days=30)),'endDate':str(end),'metrics':'views,likes,comments,shares','dimensions':'video','maxResults':50,'sort':'-views'})
        rows = report.get('rows', [])
        if rows:
            views = sum(int(r[1]) for r in rows)
            result['views'] = round(views/len(rows))
            result['engagement_rate'] = min(100, round(sum(sum(int(v) for v in r[2:5]) for r in rows)/views*100, 2)) if views else 0
    except (ProviderUnavailable, ValueError, IndexError):
        pass
    # Total lifetime channel views are not average publication views.
    try:
        end = timezone.localdate()-timedelta(days=2)
        report = provider_json('GET', 'https://youtubeanalytics.googleapis.com/v2/reports', headers=headers, params={'ids':'channel==MINE','startDate':str(end-timedelta(days=30)),'endDate':str(end),'metrics':'viewerPercentage','dimensions':'ageGroup,gender'})
        rows = report.get('rows', [])
        if rows:
            result['female_percent'] = min(100, round(sum(float(r[2]) for r in rows if r[1] == 'female')))
            bands = [r[0].removeprefix('age').split('-') for r in rows if float(r[2]) > 0]
            result['age_min'] = min(int(b[0].removesuffix('-')) for b in bands)
            result['age_max'] = max(int(b[1]) if len(b) > 1 else 100 for b in bands)
    except (ProviderUnavailable, ValueError, IndexError):
        pass  # Partial channel statistics are still useful and must not be lost.
    return result


def check_inn_registry(inn):
    key = os.getenv('DADATA_API_TOKEN')
    if not key:
        raise ProviderUnavailable('Проверка по реестру не подключена. Нужен DADATA_API_TOKEN.')
    data = provider_json('POST', 'https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party', headers={'Authorization':'Token '+key}, json={'query':inn})
    return any(s.get('data', {}).get('inn') == inn for s in data.get('suggestions', []))
