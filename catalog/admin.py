from django.contrib import admin
from .models import BloggerProfile

@admin.register(BloggerProfile)
class BloggerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'subscribers', 'price', 'is_verified')

from .models import Proposal

@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('blogger', 'advertiser', 'price', 'status', 'created_at')