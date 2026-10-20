from django.contrib import admin
from django.urls import path
from catalog.views import blogger_list

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', blogger_list, name='blogger_list'), 
]