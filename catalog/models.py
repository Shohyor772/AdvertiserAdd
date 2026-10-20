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