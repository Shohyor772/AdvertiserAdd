"""Repeatable in-process catalog measurement; not a concurrent-user load test."""
import os
import sys
import json
import statistics
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
os.environ['DJANGO_SETTINGS_MODULE']='config.benchmark_settings'
import django
django.setup()
from django.conf import settings
from django.core.management import call_command
from django.test import Client
from users.models import User
from catalog.models import BloggerProfile

assert Path(settings.DATABASES['default']['NAME']).resolve()==(settings.BASE_DIR/'tmp'/'benchmark.sqlite3').resolve()
(settings.BASE_DIR/'tmp').mkdir(exist_ok=True)
call_command('migrate',verbosity=0)
if not User.objects.exists():
    User.objects.bulk_create([User(username=f'benchmark_{i}',password='!',user_type='blogger') for i in range(5000)],batch_size=500)
    BloggerProfile.objects.bulk_create([BloggerProfile(user_id=pk,subscribers=pk*100,price=pk*10,category='Technology',city='Moscow',views=pk*20) for pk in User.objects.values_list('id',flat=True)],batch_size=500)
client=Client(HTTP_HOST='localhost')
path='/api/bloggers/?city=Moscow&price_max=30000&subscribers_min=1000&ordering=-rating'
for _ in range(3):
    assert client.get(path).status_code==200
times=[]
for _ in range(30):
    start=time.perf_counter();r=client.get(path);times.append((time.perf_counter()-start)*1000)
    assert r.status_code==200
report={'kind':'in-process Django test client; SQLite; sequential warm requests','profile_count':BloggerProfile.objects.count(),'requests':len(times),'mean_ms':round(statistics.mean(times),2),'p95_ms':round(sorted(times)[28],2),'max_ms':round(max(times),2),'sla_or_50000_concurrent_users_proven':False}
target=settings.BASE_DIR/'docs'/'catalog-benchmark.json'
target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,indent=2))
