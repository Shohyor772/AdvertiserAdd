from pathlib import Path
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.http import require_GET
from django.db import connection
from django.http import JsonResponse

@require_GET
def app(request, **kwargs):
    index = Path(settings.BASE_DIR) / 'frontend' / 'dist' / 'index.html'
    if not index.exists():
        return HttpResponse('Build frontend first: cd frontend && npm ci && npm run build', status=503, content_type='text/plain; charset=utf-8')
    return HttpResponse(index.read_text(encoding='utf-8'))

@require_GET
def blogger_detail(request, pk):
    return HttpResponseRedirect('/#/bloggers/'+str(pk))


@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        return JsonResponse({'status':'ok'})
    except Exception:
        return JsonResponse({'status':'unavailable'}, status=503)
