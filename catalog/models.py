from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class BloggerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blogger_profile')
    platform = models.CharField(max_length=50, default='Telegram')
    subscribers = models.IntegerField(default=0)
    price = models.IntegerField(default=0)
    category = models.CharField(max_length=100, default='Разное')
    is_verified = models.BooleanField(default=False)
    city = models.CharField(max_length=120, blank=True, db_index=True)
    bio = models.TextField(blank=True)
    avatar_url = models.URLField(blank=True)
    channel_url = models.URLField(blank=True)
    views = models.PositiveIntegerField(default=0)
    engagement_rate = models.FloatField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    female_percent = models.PositiveSmallIntegerField(default=50, validators=[MaxValueValidator(100)])
    age_min = models.PositiveSmallIntegerField(default=18, validators=[MaxValueValidator(100)])
    age_max = models.PositiveSmallIntegerField(default=65, validators=[MaxValueValidator(100)])
    forbidden_topics = models.TextField(blank=True)
    reply_template = models.TextField(blank=True)
    fraud_status = models.CharField(max_length=20, default='unverified')
    fraud_notes = models.TextField(blank=True)
    stats_updated_at = models.DateTimeField(null=True, blank=True)
    quality_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['category', 'price']), models.Index(fields=['platform', 'subscribers'])]

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
    attachment = models.FileField(upload_to='briefs/%Y/%m/', blank=True)
    counter_price = models.PositiveIntegerField(null=True, blank=True)
    last_offer_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    campaign = models.ForeignKey('Campaign', null=True, blank=True, on_delete=models.SET_NULL, related_name='proposals')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Предложение для {self.blogger.user.username} от {self.advertiser.username}"


class Campaign(models.Model):
    advertiser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=160)
    description = models.TextField()
    category = models.CharField(max_length=100)
    city = models.CharField(max_length=120, blank=True)
    budget = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    starts_at = models.DateField()
    ends_at = models.DateField()
    min_subscribers = models.PositiveIntegerField(default=0)
    female_percent = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    age_min = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(100)])
    age_max = models.PositiveSmallIntegerField(default=100, validators=[MaxValueValidator(100)])
    matched_bloggers = models.ManyToManyField(BloggerProfile, blank=True, related_name='matched_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class ChatMessage(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    attachment = models.FileField(upload_to='messages/%Y/%m/', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class Deal(models.Model):
    STATUSES = [('awaiting_payment', 'Ожидает оплаты'), ('in_progress', 'В работе'), ('submitted', 'На приёмке'), ('revision', 'Доработка'), ('disputed', 'Спор'), ('completed', 'Завершена'), ('refunded', 'Возврат')]
    proposal = models.OneToOneField(Proposal, on_delete=models.PROTECT, related_name='deal')
    amount = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    commission = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=24, choices=STATUSES, default='awaiting_payment', db_index=True)
    publication_url = models.URLField(blank=True)
    revision_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Payment(models.Model):
    deal = models.OneToOneField(Deal, on_delete=models.PROTECT, related_name='payment')
    key = models.UUIDField(unique=True, default=uuid.uuid4, editable=False)
    provider_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    status = models.CharField(max_length=24, default='pending')
    confirmation_url = models.URLField(blank=True)
    is_test = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LedgerEntry(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.PROTECT, related_name='ledger')
    kind = models.CharField(max_length=20, choices=[('hold', 'Резерв'), ('payout', 'Выплата'), ('refund', 'Возврат'), ('commission', 'Комиссия')])
    amount = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'kind'], name='unique_deal_ledger_kind')]


class Dispute(models.Model):
    deal = models.OneToOneField(Deal, on_delete=models.PROTECT, related_name='dispute')
    reason = models.TextField()
    evidence = models.FileField(upload_to='evidence/%Y/%m/', blank=True)
    decision = models.CharField(max_length=12, blank=True, choices=[('blogger', 'В пользу блогера'), ('advertiser', 'В пользу рекламодателя')])
    resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)


class Review(models.Model):
    deal = models.ForeignKey(Deal, on_delete=models.PROTECT, related_name='reviews')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='written_reviews')
    target = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['deal', 'author'], name='one_review_per_partner')]


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    text = models.CharField(max_length=500)
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_searches')
    title = models.CharField(max_length=120)
    filters = models.JSONField(default=dict)
    last_result_ids = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)


class SocialIdentity(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='social_identities')
    provider = models.CharField(max_length=20)
    subject = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['provider', 'subject'], name='unique_social_identity')]


class CampaignResponse(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='responses')
    blogger = models.ForeignKey(BloggerProfile, on_delete=models.CASCADE, related_name='campaign_responses')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['campaign', 'blogger'], name='one_campaign_response_per_blogger')]
        ordering = ['created_at']
