from django.contrib import admin
from .models import BloggerProfile

@admin.register(BloggerProfile)
class BloggerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'subscribers', 'price', 'is_verified')