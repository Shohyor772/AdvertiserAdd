from pathlib import Path
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction, IntegrityError
from django.db.models import Q, Avg, Count
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import api_view, permission_classes, action, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, extend_schema_view, inline_serializer, OpenApiTypes, OpenApiParameter
from .models import *
from .serializers import *
from .search import search_bloggers, SearchParams
from .services import participant, require_role, notify, agreement, confirm_test_payment, complete, resolve_dispute


class LoginThrottle(AnonRateThrottle):
    scope = 'login'


@extend_schema(request=RegisterSerializer, responses={201: OpenApiTypes.OBJECT})
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def register(request):
    s = RegisterSerializer(data=request.data)
    s.is_valid(raise_exception=True)
    with transaction.atomic():
        user = s.save()
        token = signing.dumps({'uid': user.pk, 'email': user.email}, salt='email-confirm')
        link = settings.PUBLIC_URL+'/#/verify?token='+token
        send_mail('Подтвердите email — Blogger Marketplace', 'Для завершения регистрации откройте: '+link, settings.DEFAULT_FROM_EMAIL, [user.email])
    return Response({'detail': 'Письмо отправлено. Подтвердите email для входа.'}, status=201)


@extend_schema(request=inline_serializer('EmailToken', fields={'token': serializers.CharField()}), responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    try:
        data = signing.loads(request.data.get('token', ''), salt='email-confirm', max_age=86400)
    except signing.BadSignature:
        raise ValidationError('Ссылка недействительна или устарела.')
    user = get_object_or_404(User, pk=data['uid'], email=data['email'])
    # Do not reactivate an account blocked after an earlier confirmation.
    if not user.email_verified:
        user.email_verified = True
        user.is_active = True
        user.save(update_fields=['email_verified', 'is_active'])
    return Response({'detail': 'Email подтверждён. Теперь можно войти.'})


@extend_schema(request=inline_serializer('ResendEmail', fields={'email': serializers.EmailField()}), responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def resend_email(request):
    email = serializers.EmailField().run_validation(request.data.get('email'))
    user = User.objects.filter(email__iexact=email).first()
    if user and not user.email_verified:
        token = signing.dumps({'uid': user.pk, 'email': user.email}, salt='email-confirm')
        send_mail('Подтвердите email — Blogger Marketplace', 'Откройте: '+settings.PUBLIC_URL+'/#/verify?token='+token, settings.DEFAULT_FROM_EMAIL, [user.email])
    return Response({'detail': 'Если адрес зарегистрирован, письмо подтверждения отправлено.'})


@extend_schema(request=UserSerializer, responses=UserSerializer)
@api_view(['GET', 'PATCH'])
def me(request):
    if request.method == 'PATCH':
        s = UserSerializer(request.user, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
    return Response(UserSerializer(request.user).data)


@extend_schema(request=ProfileSerializer, responses=ProfileSerializer)
@api_view(['GET', 'PATCH'])
def profile(request):
    require_role(request.user, 'blogger')
    obj, _ = BloggerProfile.objects.get_or_create(user=request.user)
    s = ProfileSerializer(obj, data=request.data, partial=True) if request.method == 'PATCH' else ProfileSerializer(obj)
    if request.method == 'PATCH':
        s.is_valid(raise_exception=True)
        s.save(is_verified=False, fraud_status='unverified')
    return Response(s.data)


@extend_schema(request=inline_serializer('Logout', fields={'refresh': serializers.CharField()}), responses={204: None})
@api_view(['POST'])
def logout(request):
    try:
        token = RefreshToken(request.data.get('refresh', ''))
        if int(token['user_id']) != request.user.pk:
            raise PermissionDenied()
        token.blacklist()
    except PermissionDenied:
        raise
    except Exception:
        raise ValidationError('Недействительный refresh token.')
    from django.contrib.auth import logout as session_logout
    session_logout(request._request)
    return Response(status=204)


@extend_schema(responses=OpenApiTypes.OBJECT)
@api_view(['GET'])
@permission_classes([AllowAny])
def options(request):
    import os
    return Response({
        'categories': list(BloggerProfile.objects.filter(user__is_active=True).order_by('category').values_list('category', flat=True).distinct()),
        'cities': list(BloggerProfile.objects.filter(user__is_active=True).exclude(city='').order_by('city').values_list('city', flat=True).distinct()),
        'platforms': ['Telegram', 'YouTube', 'TikTok'],
        'payment_mode': settings.PAYMENT_MODE, 'commission_percent': settings.COMMISSION_PERCENT,
        'social_providers': {'google':bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET')), 'telegram':bool(os.getenv('TELEGRAM_BOT_NAME') and os.getenv('TELEGRAM_BOT_TOKEN'))},
    })


@extend_schema_view(list=extend_schema(parameters=[SearchParams]))
class BloggerViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = BloggerSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        return search_bloggers(self.request.query_params if self.action == 'list' else {})
    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        if request.user.is_authenticated and request.user.pk != obj.user_id:
            from django.core.cache import cache
            if cache.add(f'view:{request.user.pk}:{obj.pk}', True, timeout=86400):
                notify(obj.user_id, f'{request.user.username} просмотрел ваш профиль.', f'#/bloggers/{obj.pk}')
        data = self.get_serializer(obj).data
        data['reviews'] = ReviewSerializer(obj.user.received_reviews.select_related('author').order_by('-created_at')[:30], many=True).data
        return Response(data)
    @extend_schema(parameters=[OpenApiParameter('q', str)], responses=OpenApiTypes.OBJECT)
    @action(detail=False)
    def suggest(self, request):
        return Response(list(search_bloggers({'q': request.query_params.get('q', '')}).values('id', 'user__username')[:8]))


class ProposalViewSet(viewsets.ModelViewSet):
    serializer_class = ProposalSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    def create(self, request, *args, **kwargs):
        require_role(request.user, 'advertiser')
        return super().create(request, *args, **kwargs)
    def get_queryset(self):
        qs = Proposal.objects.select_related('blogger__user', 'advertiser', 'deal__payment')
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(advertiser=self.request.user) | Q(blogger__user=self.request.user))
    @transaction.atomic
    def perform_create(self, serializer):
        require_role(self.request.user, 'advertiser')
        p = serializer.save(advertiser=self.request.user, last_offer_by=self.request.user)
        ChatMessage.objects.create(proposal=p, sender=self.request.user, text=p.message or 'Прикреплено ТЗ.')
        notify(p.blogger.user_id, f'Новое предложение от {self.request.user.username}', f'#/chats/{p.pk}')
        if p.blogger.reply_template.strip():
            ChatMessage.objects.create(proposal=p, sender=p.blogger.user, text='Автоответ: '+p.blogger.reply_template)
    def retrieve(self, request, *args, **kwargs):
        p = self.get_object()
        data = self.get_serializer(p).data
        data['messages'] = MessageSerializer(p.messages.select_related('sender'), many=True).data
        data['deal'] = DealSerializer(p.deal).data if hasattr(p, 'deal') else None
        data['dispute'] = DisputeSerializer(p.deal.dispute).data if hasattr(p, 'deal') and hasattr(p.deal, 'dispute') else None
        data['reviews'] = ReviewSerializer(p.deal.reviews.all(), many=True).data if hasattr(p, 'deal') else []
        return Response(data)
    @extend_schema(request=MessageSerializer, responses={201: MessageSerializer})
    @action(detail=True, methods=['post'])
    def message(self, request, pk=None):
        p = self.get_object()
        participant(p, request.user, staff=True)
        s = MessageSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        s.save(proposal=p, sender=request.user)
        recipients = {p.advertiser_id, p.blogger.user_id}-{request.user.pk}
        for uid in recipients:
            notify(uid, 'Новое сообщение в чате', f'#/chats/{p.pk}')
        return Response(s.data, status=201)
    @extend_schema(request=inline_serializer('Negotiation', fields={'action': serializers.ChoiceField(choices=['accept','reject','counter']), 'price': serializers.IntegerField(required=False, min_value=1)}), responses=ProposalSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def negotiate(self, request, pk=None):
        p = self.get_queryset().select_for_update(of=('self',)).get(pk=self.get_object().pk)
        participant(p, request.user)
        if p.status != 'sent':
            raise ValidationError('Переговоры уже закрыты.')
        op = request.data.get('action')
        if op == 'accept':
            agreement(p, request.user)
        elif op == 'reject':
            p.status = 'rejected'
            p.save(update_fields=['status'])
        elif op == 'counter':
            f = serializers.IntegerField(min_value=1, max_value=1_000_000_000)
            p.counter_price = f.run_validation(request.data.get('price'))
            p.last_offer_by = request.user
            p.save(update_fields=['counter_price', 'last_offer_by'])
        else:
            raise ValidationError('Неизвестное действие.')
        other = p.blogger.user_id if request.user.pk == p.advertiser_id else p.advertiser_id
        notify(other, 'Условия предложения обновлены.', f'#/chats/{p.pk}')
        return Response(self.get_serializer(p).data)


class DealViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DealSerializer
    def get_queryset(self):
        qs = Deal.objects.select_related('proposal__blogger', 'payment')
        if getattr(self, 'swagger_fake_view', False):
            return qs.none()
        if self.request.user.is_staff:
            return qs
        return qs.filter(Q(proposal__advertiser=self.request.user) | Q(proposal__blogger__user=self.request.user))
    @extend_schema(request=None, responses=DealSerializer)
    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        d = self.get_object()
        d = confirm_test_payment(d.pk, request.user)
        return Response(self.get_serializer(d).data)
    @extend_schema(request=inline_serializer('Publication', fields={'publication_url':serializers.URLField()}), responses=DealSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def submit(self, request, pk=None):
        d = self.get_queryset().select_for_update(of=('self',)).get(pk=self.get_object().pk)
        if request.user.pk != d.proposal.blogger.user_id:
            raise PermissionDenied()
        if d.status not in ['in_progress', 'revision']:
            raise ValidationError('Сдать можно работу в исполнении или на доработке.')
        d.publication_url = serializers.URLField(max_length=200).run_validation(request.data.get('publication_url'))
        if not d.publication_url.startswith('https://'):
            raise ValidationError('Используйте HTTPS-ссылку на публикацию.')
        d.submitted_at = timezone.now()
        d.status = 'submitted'
        d.save()
        notify(d.proposal.advertiser_id, 'Работа сдана на приёмку. Автоприёмка через 3 дня.', f'#/chats/{d.proposal_id}')
        return Response(self.get_serializer(d).data)
    @extend_schema(request=None, responses=DealSerializer)
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        return Response(self.get_serializer(complete(self.get_object().pk, request.user)).data)
    @extend_schema(request=inline_serializer('Revision', fields={'reason':serializers.CharField()}), responses=DealSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def revise(self, request, pk=None):
        d = self.get_queryset().select_for_update(of=('self',)).get(pk=self.get_object().pk)
        if request.user.pk != d.proposal.advertiser_id:
            raise PermissionDenied()
        if d.status != 'submitted':
            raise ValidationError('На доработку можно отправить сданную работу.')
        d.revision_reason = serializers.CharField(max_length=10000).run_validation(request.data.get('reason'))
        d.status = 'revision'
        d.save()
        notify(d.proposal.blogger.user_id, 'Требуется доработка: '+d.revision_reason[:300], f'#/chats/{d.proposal_id}')
        return Response(self.get_serializer(d).data)
    @extend_schema(request=DisputeSerializer, responses={201: DisputeSerializer})
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def dispute(self, request, pk=None):
        d = self.get_queryset().select_for_update(of=('self',)).get(pk=self.get_object().pk)
        if request.user.pk != d.proposal.advertiser_id:
            raise PermissionDenied()
        if d.status not in ['submitted', 'revision', 'in_progress'] or hasattr(d, 'dispute'):
            raise ValidationError('Спор недоступен для текущего состояния.')
        s = DisputeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        dispute = s.save(deal=d)
        d.status = 'disputed'
        d.save(update_fields=['status', 'updated_at'])
        for admin in User.objects.filter(is_staff=True, is_active=True):
            notify(admin.pk, 'Открыт спор №'+str(dispute.pk), f'#/chats/{d.proposal_id}')
        notify(d.proposal.blogger.user_id, 'Открыт спор. Резерв заблокирован до решения.', f'#/chats/{d.proposal_id}')
        return Response(s.data, status=201)


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    def get_queryset(self):
        return Review.objects.select_related('author').order_by('-created_at')
    @transaction.atomic
    def perform_create(self, serializer):
        d = Deal.objects.select_for_update(of=('self',)).select_related('proposal__blogger').get(pk=serializer.validated_data['deal'].pk)
        participant(d.proposal, self.request.user)
        if d.status != 'completed':
            raise ValidationError('Отзыв доступен после завершения сделки.')
        if d.reviews.filter(author=self.request.user).exists():
            raise ValidationError('Вы уже оценили эту сделку.')
        target = d.proposal.blogger.user_id if d.proposal.advertiser_id == self.request.user.pk else d.proposal.advertiser_id
        serializer.save(author=self.request.user, target_id=target)
        rating = User.objects.get(pk=target).received_reviews.aggregate(v=Avg('rating'))['v']
        notify(target, 'Получен отзыв.'+(' Внимание: рейтинг ниже 4.' if rating < 4 else ''), '#/profile')


class CampaignViewSet(viewsets.ModelViewSet):
    serializer_class = CampaignSerializer
    http_method_names = ['get', 'post', 'head', 'options']
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Campaign.objects.none()
        if self.request.user.user_type == 'blogger':
            return Campaign.objects.filter(matched_bloggers__user=self.request.user)
        return Campaign.objects.filter(advertiser=self.request.user)
    @transaction.atomic
    def perform_create(self, serializer):
        require_role(self.request.user, 'advertiser')
        if not self.request.user.email_verified:
            raise ValidationError('Подтвердите email.')
        c = serializer.save(advertiser=self.request.user)
        from .tasks import match_campaign
        transaction.on_commit(lambda: match_campaign.delay(c.pk))
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        require_role(request.user, 'blogger')
        c = self.get_object()
        from django.core.cache import cache
        if cache.add(f'campaign-interest:{c.pk}:{request.user.pk}', True, timeout=86400):
            profile = get_object_or_404(BloggerProfile, user=request.user)
            notify(c.advertiser_id, f'{request.user.username} откликнулся на «{c.title}»', f'#/bloggers/{profile.pk}')
        return Response({'detail': 'Отклик отправлен рекламодателю.'})


class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    http_method_names = ['get', 'patch', 'post', 'head', 'options']
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user) if self.request.user.is_authenticated else Notification.objects.none()
    def create(self, request, *args, **kwargs):
        raise PermissionDenied()
    @extend_schema(request=None, responses={204: None})
    @action(detail=False, methods=['post'])
    def read_all(self, request):
        self.get_queryset().update(is_read=True)
        return Response(status=204)


class SavedSearchViewSet(viewsets.ModelViewSet):
    serializer_class = SavedSearchSerializer
    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user) if self.request.user.is_authenticated else SavedSearch.objects.none()
    def perform_create(self, serializer):
        require_role(self.request.user, 'advertiser')
        params = SearchParams(data=serializer.validated_data['filters'])
        params.is_valid(raise_exception=True)
        serializer.save(user=self.request.user, filters=params.validated_data, last_result_ids=list(search_bloggers(params.validated_data).values_list('id', flat=True)))
    def perform_update(self, serializer):
        params = SearchParams(data=serializer.validated_data.get('filters', serializer.instance.filters))
        params.is_valid(raise_exception=True)
        serializer.save(filters=params.validated_data)


@extend_schema(request=inline_serializer('DisputeDecision', fields={'decision': serializers.ChoiceField(choices=['blogger', 'advertiser']), 'resolution': serializers.CharField()}), responses=DisputeSerializer)
@api_view(['POST'])
def resolve(request, pk):
    d = get_object_or_404(Dispute, pk=pk)
    result = resolve_dispute(d.pk, request.user, request.data.get('decision'), str(request.data.get('resolution', '')))
    return Response(DisputeSerializer(result).data)


@extend_schema(responses=OpenApiTypes.BINARY)
@api_view(['GET'])
def download(request, kind, pk):
    if kind == 'brief':
        obj = get_object_or_404(Proposal.objects.select_related('blogger'), pk=pk)
        p, f = obj, obj.attachment
    elif kind == 'message':
        obj = get_object_or_404(ChatMessage.objects.select_related('proposal__blogger'), pk=pk)
        p, f = obj.proposal, obj.attachment
    elif kind == 'evidence':
        obj = get_object_or_404(Dispute.objects.select_related('deal__proposal__blogger'), pk=pk)
        p, f = obj.deal.proposal, obj.evidence
    else:
        raise ValidationError('Неизвестный вид файла.')
    participant(p, request.user, staff=True)
    if not f:
        raise ValidationError('Файл не приложен.')
    return FileResponse(f.open('rb'), as_attachment=True, filename=Path(f.name).name, content_type='application/octet-stream')


@extend_schema(responses=inline_serializer('CategoryAnalytics', fields={'category': serializers.CharField(), 'count': serializers.IntegerField(), 'average_cpm': serializers.FloatField(), 'average_price': serializers.FloatField()}, many=True))
@api_view(['GET'])
def analytics(request):
    if not request.user.is_premium and not request.user.is_staff:
        raise PermissionDenied('Аналитика доступна с премиум-доступом. Обратитесь к администратору.')
    from django.db.models import F, FloatField, ExpressionWrapper
    rows = BloggerProfile.objects.filter(user__is_active=True, views__gt=0).values('category').annotate(count=Count('id'), average_cpm=Avg(ExpressionWrapper(F('price')*1000.0/F('views'), output_field=FloatField())), average_price=Avg('price'))
    return Response(list(rows))


@extend_schema(parameters=[SearchParams], responses=OpenApiTypes.BINARY)
@api_view(['GET'])
def export_catalog(request):
    import csv
    import io
    from django.http import HttpResponse
    require_role(request.user, 'advertiser')
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['Блогер', 'Площадка', 'Тематика', 'Город', 'Подписчики', 'Просмотры', 'Цена, ₽', 'Рейтинг', 'Канал'])
    for b in search_bloggers(request.query_params).iterator(chunk_size=1000):
        row = [b.user.username, b.platform, b.category, b.city, b.subscribers, b.views, b.price, b.rating_value or '', b.channel_url]
        writer.writerow([("'"+str(v)) if str(v).lstrip().startswith(('=', '+', '-', '@')) else v for v in row])
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="bloggers.csv"'
    return response
