from pathlib import Path

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Avg
from rest_framework import serializers
from users.models import User
from .models import BloggerProfile, Proposal, Campaign, ChatMessage, Deal, Dispute, Review, Notification, SavedSearch


def validate_file(value):
    if value and (value.size > 10 * 1024 * 1024 or Path(value.name).suffix.lower() not in {'.pdf', '.txt', '.docx', '.png', '.jpg', '.jpeg', '.webp'}):
        raise serializers.ValidationError('Разрешены PDF, TXT, DOCX и изображения до 10 МБ.')
    return value


def validate_inn(value):
    if not value.isascii() or not value.isdigit() or len(value) not in (10, 12) or len(set(value)) == 1:
        raise serializers.ValidationError('Введите корректный ИНН из 10 или 12 цифр.')
    digits = list(map(int, value))
    def check(weights, position):
        return sum(a * b for a, b in zip(digits, weights)) % 11 % 10 == digits[position]
    valid = check([2,4,10,3,5,9,4,6,8], 9) if len(value) == 10 else check([7,2,4,10,3,5,9,4,6,8], 10) and check([3,7,2,4,10,3,5,9,4,6,8], 11)
    if not valid:
        raise serializers.ValidationError('Контрольная сумма ИНН не совпадает.')
    return value


class UserSerializer(serializers.ModelSerializer):
    rating = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'user_type', 'account_type', 'inn', 'phone', 'email_verified', 'notifications_enabled', 'is_premium', 'is_staff', 'rating']
        read_only_fields = ['id', 'username', 'email', 'user_type', 'account_type', 'inn', 'email_verified', 'is_premium', 'is_staff']
    def get_rating(self, obj) -> float | None:
        return obj.received_reviews.aggregate(value=Avg('rating'))['value']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    user_type = serializers.ChoiceField(choices=['blogger', 'advertiser'])
    email = serializers.EmailField()
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'user_type', 'account_type', 'inn']
    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Этот email уже зарегистрирован.')
        return value.lower()
    def validate(self, attrs):
        try:
            validate_password(attrs['password'], User(username=attrs['username'], email=attrs['email']))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': exc.messages})
        if attrs.get('account_type') == 'company':
            validate_inn(attrs.get('inn', ''))
        return attrs
    def create(self, data):
        user = User.objects.create_user(**data, is_active=False)
        if user.user_type == 'blogger':
            BloggerProfile.objects.create(user=user)
        return user


class BloggerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    display_name = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    cpm = serializers.SerializerMethodField()
    class Meta:
        model = BloggerProfile
        fields = ['id', 'user_id', 'username', 'display_name', 'platform', 'subscribers', 'price', 'category', 'is_verified', 'city', 'bio', 'channel_url', 'views', 'engagement_rate', 'female_percent', 'age_min', 'age_max', 'forbidden_topics', 'fraud_status', 'stats_updated_at', 'rating', 'review_count', 'cpm']
        read_only_fields = ['user_id', 'is_verified', 'fraud_status', 'stats_updated_at']
    def get_display_name(self, obj) -> str:
        return obj.user.first_name or obj.user.username
    def get_rating(self, obj) -> float | None:
        return getattr(obj, 'rating_value', None) if hasattr(obj, 'rating_value') else obj.user.received_reviews.aggregate(value=Avg('rating'))['value']
    def get_review_count(self, obj) -> int:
        return getattr(obj, 'reviews_count', None) if hasattr(obj, 'reviews_count') else obj.user.received_reviews.count()
    def get_cpm(self, obj) -> float | None:
        return round(obj.price * 1000 / obj.views, 2) if obj.views else None
    def validate(self, data):
        for key in ['price', 'subscribers', 'views']:
            if key in data and not 0 <= data[key] <= 1_000_000_000:
                raise serializers.ValidationError({key: 'Допустимое значение: 0–1 000 000 000.'})
        lo = data.get('age_min', getattr(self.instance, 'age_min', 18))
        hi = data.get('age_max', getattr(self.instance, 'age_max', 65))
        if lo > hi:
            raise serializers.ValidationError('Минимальный возраст не должен превышать максимальный.')
        return data


class ProfileSerializer(BloggerSerializer):
    class Meta(BloggerSerializer.Meta):
        fields = BloggerSerializer.Meta.fields + ['reply_template']


class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = '__all__'
        read_only_fields = ['advertiser', 'matched_bloggers', 'created_at']
    def validate(self, data):
        if data.get('starts_at') and data.get('ends_at') and data['starts_at'] > data['ends_at']:
            raise serializers.ValidationError('Дата окончания должна быть не раньше даты начала.')
        return data


class ProposalSerializer(serializers.ModelSerializer):
    blogger_name = serializers.CharField(source='blogger.user.username', read_only=True)
    advertiser_name = serializers.CharField(source='advertiser.username', read_only=True)
    blogger_user_id = serializers.IntegerField(source='blogger.user_id', read_only=True)
    attachment_name = serializers.SerializerMethodField()
    attachment = serializers.FileField(write_only=True, required=False, validators=[validate_file])
    class Meta:
        model = Proposal
        fields = ['id', 'blogger', 'blogger_name', 'blogger_user_id', 'advertiser', 'advertiser_name', 'price', 'message', 'attachment', 'attachment_name', 'status', 'counter_price', 'last_offer_by', 'campaign', 'created_at']
        read_only_fields = ['advertiser', 'status', 'counter_price', 'last_offer_by', 'created_at']
    def get_attachment_name(self, obj) -> str:
        return Path(obj.attachment.name).name if obj.attachment else ''
    def validate(self, data):
        user = self.context['request'].user
        if not user.email_verified:
            raise serializers.ValidationError('Подтвердите email перед отправкой предложения.')
        if data['blogger'].user_id == user.pk or not data['blogger'].user.is_active:
            raise serializers.ValidationError('Нельзя отправить предложение этому профилю.')
        if not data.get('message', '').strip() and not data.get('attachment'):
            raise serializers.ValidationError('Добавьте сообщение или файл ТЗ.')
        if not 1 <= data['price'] <= 1_000_000_000:
            raise serializers.ValidationError({'price': 'Цена должна быть от 1 до 1 000 000 000 ₽.'})
        if data.get('campaign') and data['campaign'].advertiser_id != user.pk:
            raise serializers.ValidationError('Выберите свою кампанию.')
        return data


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    attachment_name = serializers.SerializerMethodField()
    attachment = serializers.FileField(write_only=True, required=False, validators=[validate_file])
    class Meta:
        model = ChatMessage
        fields = ['id', 'sender', 'sender_name', 'text', 'attachment', 'attachment_name', 'created_at']
        read_only_fields = ['sender', 'created_at']
    def get_attachment_name(self, obj) -> str:
        return Path(obj.attachment.name).name if obj.attachment else ''
    def validate(self, data):
        if not data.get('text', '').strip() and not data.get('attachment'):
            raise serializers.ValidationError('Введите сообщение или прикрепите файл.')
        return data


class DealSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    payment_status = serializers.SerializerMethodField()
    is_test = serializers.SerializerMethodField()
    class Meta:
        model = Deal
        fields = ['id', 'proposal', 'amount', 'commission', 'status', 'status_label', 'publication_url', 'revision_reason', 'submitted_at', 'completed_at', 'payment_status', 'is_test']
        read_only_fields = fields
    def get_payment_status(self, obj) -> str | None:
        return obj.payment.status if hasattr(obj, 'payment') else None
    def get_is_test(self, obj) -> bool | None:
        return obj.payment.is_test if hasattr(obj, 'payment') else None


class DisputeSerializer(serializers.ModelSerializer):
    evidence = serializers.FileField(write_only=True, required=False, validators=[validate_file])
    class Meta:
        model = Dispute
        fields = '__all__'
        read_only_fields = ['deal', 'decision', 'resolution', 'resolved_by', 'created_at', 'resolved_at']


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    class Meta:
        model = Review
        fields = ['id', 'deal', 'author', 'author_name', 'target', 'rating', 'text', 'created_at']
        read_only_fields = ['author', 'target', 'created_at']
        validators = []


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'text', 'link', 'is_read', 'created_at']
        read_only_fields = ['text', 'link', 'created_at']


class SavedSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedSearch
        fields = ['id', 'title', 'filters', 'created_at']
        read_only_fields = ['created_at']
