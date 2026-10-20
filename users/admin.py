from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # Добавляем наши поля в форму редактирования
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('user_type', 'phone')}),
    )
    # Добавляем наши поля в форму создания нового пользователя
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('user_type', 'phone')}),
    )
    # Выводим колонку с типом в общий список
    list_display = ('username', 'email', 'user_type', 'is_staff')

admin.site.register(User, CustomUserAdmin)