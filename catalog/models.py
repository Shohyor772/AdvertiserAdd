from django.db import models
from django.conf import settings

class BloggerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogger_profile')
    platform = models.CharField(max_length=50, default='Telegram')
    subscribers = models.IntegerField(default=0)
    price = models.IntegerField(default=0)
    category = models.CharField(max_length=100, default='Разное')
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.platform}"


class Proposal(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Отправлено'),
        ('agreed', 'Согласовано'),
        ('rejected', 'Отклонено'),
    ]
    # Ссылка на профиль блогера (кому предлагаем)
    blogger = models.ForeignKey(BloggerProfile, on_delete=models.CASCADE, related_name='proposals')
    # Ссылка на пользователя, который отправил (рекламодатель)
    advertiser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_proposals')

    price = models.IntegerField(verbose_name="Предложенная цена")
    message = models.TextField(verbose_name="Сообщение", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Предложение для {self.blogger.user.username} от {self.advertiser.username}"