from django.contrib import admin, messages
from django.utils.html import format_html
from rest_framework.exceptions import APIException
from .models import BloggerProfile, Proposal, Campaign, ChatMessage, Deal, Dispute, Payment, LedgerEntry, Review, Notification, SavedSearch
from .services import resolve_dispute

admin.site.site_header = 'Blogger Marketplace'
admin.site.site_title = 'Управление платформой'
admin.site.index_title = 'Модерация и поддержка'

@admin.register(BloggerProfile)
class BloggerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'platform', 'subscribers', 'price', 'city', 'is_verified', 'fraud_status')
    search_fields = ('user__username', 'category', 'city')
    list_filter = ('platform', 'is_verified', 'fraud_status')

class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Proposal)
class ProposalAdmin(ReadOnlyAdmin):
    list_display = ('blogger', 'advertiser', 'price', 'status', 'created_at')

@admin.register(Deal)
class DealAdmin(ReadOnlyAdmin):
    list_display = ('id', 'proposal', 'amount', 'commission', 'status')
    list_filter = ('status',)

@admin.register(Dispute)
class DisputeAdmin(ReadOnlyAdmin):
    list_display = ('id', 'deal', 'decision', 'created_at', 'resolved_at')
    fields = ('deal', 'reason', 'materials', 'decision', 'resolution', 'resolved_by', 'created_at', 'resolved_at')
    def get_readonly_fields(self, request, obj=None):
        return ['deal', 'reason', 'materials', 'decision', 'resolved_by', 'created_at', 'resolved_at'] + (['resolution'] if obj and obj.resolved_at else [])
    @admin.display(description='Materials / chat')
    def materials(self, obj):
        return format_html('<a href="/#/chats/{}" target="_blank">Open brief, conversation and evidence</a>', obj.deal.proposal_id)
    actions = ['award_blogger', 'refund_advertiser']
    def apply_decision(self, request, queryset, decision):
        for dispute in queryset:
            try:
                resolve_dispute(dispute.pk, request.user, decision, dispute.resolution)
                self.message_user(request, f'Dispute #{dispute.pk} resolved')
            except APIException as exc:
                self.message_user(request, str(exc.detail), level=messages.ERROR)
    @admin.action(description='Resolve in favor of blogger (save resolution first)')
    def award_blogger(self, request, queryset):
        self.apply_decision(request, queryset, 'blogger')
    @admin.action(description='Refund advertiser (save resolution first)')
    def refund_advertiser(self, request, queryset):
        self.apply_decision(request, queryset, 'advertiser')

for model in [Payment, LedgerEntry, Review, ChatMessage, Notification, SavedSearch, Campaign]:
    admin.site.register(model, ReadOnlyAdmin)
