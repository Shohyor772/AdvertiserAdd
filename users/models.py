from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPE_CHOICES = [
        ('blogger', 'Блогер'),
        ('advertiser', 'Рекламодатель'),
        ('admin', 'Администратор'),
    ]
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='blogger')
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    account_type = models.CharField(max_length=12, choices=[('person', 'Физлицо'), ('company', 'Юрлицо')], default='person')
    inn = models.CharField(max_length=12, blank=True)
    inn_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)
    is_premium = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
