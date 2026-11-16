from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import BloggerProfile, Proposal
from users.models import User


def blogger_list(request):
    # Получаем всех блогеров для главной страницы
    bloggers = BloggerProfile.objects.all()
    return render(request, 'catalog/blogger_list.html', {'bloggers': bloggers})


def blogger_detail(request, pk):
    # Находим конкретного блогера по ID. Если нет — страница 404.
    blogger = get_object_or_404(BloggerProfile, pk=pk)
    return render(request, 'catalog/blogger_detail.html', {'blogger': blogger})


def create_proposal(request, pk):
    # Обрабатываем только POST-запросы (нажатие на кнопку формы)
    if request.method == 'POST':
        blogger = get_object_or_404(BloggerProfile, pk=pk)
        price = request.POST.get('price')
        message = request.POST.get('message')

        # ВРЕМЕННО: берем первого пользователя из базы как рекламодателя,
        # так как у нас пока нет системы авторизации. Позже заменим на request.user
        temp_advertiser = User.objects.first()

        if temp_advertiser:
            Proposal.objects.create(
                blogger=blogger,
                advertiser=temp_advertiser,
                price=price,
                message=message
            )

    # После отправки формы возвращаем пользователя на страницу этого же блогера
    return redirect('blogger_detail', pk=pk)