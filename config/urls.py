from django.contrib import admin
from django.urls import path
from catalog.views import blogger_list, blogger_detail, create_proposal

urlpatterns = [
    path('admin/', admin.site.urls),
    # Главная страница (каталог)
    path('', blogger_list, name='blogger_list'),
    # Страница конкретного блогера
    path('blogger/<int:pk>/', blogger_detail, name='blogger_detail'),
    # Обработка формы отправки предложения
    path('blogger/<int:pk>/propose/', create_proposal, name='create_proposal'),
]