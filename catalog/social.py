import base64
import hashlib
import hmac
import os
import secrets
import time
from urllib.parse import urlencode
from django.conf import settings
from django.contrib.auth import login
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from django.middleware.csrf import get_token
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiTypes
from users.models import User
from .models import SocialIdentity, BloggerProfile
from .integrations import provider_json, youtube_statistics, ProviderUnavailable


def social_user(provider, subject, email='', name='', linking_user=None):
    identity = SocialIdentity.objects.filter(provider=provider, subject=subject).select_related('user').first()
    if identity:
        if linking_user and identity.user_id != linking_user.pk:
            raise ValidationError('Этот социальный аккаунт уже привязан к другому пользователю.')
        user = identity.user
    elif linking_user:
        user = linking_user
        SocialIdentity.objects.create(user=user, provider=provider, subject=subject)
    else:
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Аккаунт с этим email уже существует. Войдите паролем и подключите соцсеть в профиле.')
        user = User.objects.create_user(username=provider+'_'+secrets.token_hex(6), email=email, first_name=name[:150], user_type='blogger', email_verified=bool(email))
        user.set_unusable_password()
        user.save(update_fields=['password'])
        SocialIdentity.objects.create(user=user, provider=provider, subject=subject)
        BloggerProfile.objects.create(user=user)
    if not user.is_active:
        raise PermissionDenied('Аккаунт заблокирован.')
    return user


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([AllowAny])
def google_start(request):
    if settings.EDUCATIONAL_MODE:
        raise ProviderUnavailable('В учебной версии используется регистрация по email без внешних платформ.')
    client = os.getenv('GOOGLE_CLIENT_ID')
    if not client or not os.getenv('GOOGLE_CLIENT_SECRET'):
        raise ProviderUnavailable('Google OAuth пока не настроен. Можно зарегистрироваться по email.')
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    provider = request.data.get('provider', 'google')
    if provider not in ['google', 'youtube']:
        raise ValidationError('Неизвестный провайдер.')
    if request.user.is_authenticated and request.user.user_type != 'blogger':
        raise PermissionDenied('Подключение статистики доступно блогерам.')
    request.session['oauth_attempt'] = {'state':state,'verifier':verifier,'provider':provider,'created':time.time(),'uid':request.user.pk if request.user.is_authenticated else None}
    scopes = 'openid email profile'
    if provider == 'youtube':
        scopes += ' https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/yt-analytics.readonly'
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return Response({'authorization_url':'https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':client,'redirect_uri':settings.PUBLIC_URL+'/auth/google/callback/','response_type':'code','scope':scopes,'state':state,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'consent'})})


@require_GET
def google_callback(request):
    if settings.EDUCATIONAL_MODE:
        return HttpResponseRedirect('/#/login')
    attempt = request.session.pop('oauth_attempt', None)
    if not attempt or not secrets.compare_digest(attempt['state'], request.GET.get('state', '')) or time.time()-attempt['created'] > 600:
        return HttpResponseRedirect('/#/login?oauth_error=state')
    if request.GET.get('error') or not request.GET.get('code'):
        return HttpResponseRedirect('/#/register?oauth_error=denied')
    try:
        tokens = provider_json('POST', 'https://oauth2.googleapis.com/token', data={'grant_type':'authorization_code','code':request.GET['code'],'client_id':os.getenv('GOOGLE_CLIENT_ID'),'client_secret':os.getenv('GOOGLE_CLIENT_SECRET'),'redirect_uri':settings.PUBLIC_URL+'/auth/google/callback/','code_verifier':attempt['verifier']})
        token = tokens['access_token']
        info = provider_json('GET', 'https://openidconnect.googleapis.com/v1/userinfo', headers={'Authorization':'Bearer '+token})
        if not info.get('sub') or not info.get('email_verified'):
            raise ValidationError('Google не подтвердил email.')
        with transaction.atomic():
            linked = get_object_or_404(User, pk=attempt['uid']) if attempt.get('uid') else None
            user = social_user('google', info['sub'], info.get('email', ''), info.get('name',''), linked)
            if info.get('picture', '').startswith('https://'):
                BloggerProfile.objects.filter(user=user).update(avatar_url=info['picture'])
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        get_token(request)
        warning = False
        if attempt['provider'] == 'youtube':
            try:
                stats = youtube_statistics(token)
                BloggerProfile.objects.filter(user=user).update(**stats, is_verified=False, fraud_status='unverified')
            except ProviderUnavailable:
                warning = True
        # JWTs never appear in URL/query logs. Exchange requires the login session.
        request.session['social_exchange'] = True
        return HttpResponseRedirect('/#/oauth'+('?stats=partial' if warning else ''))
    except (ProviderUnavailable, ValidationError, PermissionDenied, KeyError):
        return HttpResponseRedirect('/#/login?oauth_error=unavailable')


@extend_schema(request=None, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@authentication_classes([SessionAuthentication])
@permission_classes([AllowAny])
def exchange(request):
    # SessionAuthentication enforces CSRF for this session-authenticated POST.
    if not request.user.is_authenticated or not request.session.pop('social_exchange', False):
        raise PermissionDenied('Социальный вход не подтверждён.')
    token = RefreshToken.for_user(request.user)
    return Response({'access':str(token.access_token),'refresh':str(token)})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([AllowAny])
def telegram_start(request):
    if settings.EDUCATIONAL_MODE:
        raise ProviderUnavailable('В учебной версии Telegram не подключается.')
    if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_BOT_NAME'):
        raise ProviderUnavailable('Вход через Telegram пока не настроен.')
    nonce = secrets.token_urlsafe(32)
    request.session['telegram_nonce'] = nonce
    return Response({'nonce':nonce,'bot_name':os.environ['TELEGRAM_BOT_NAME']})


@extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
@api_view(['POST'])
@permission_classes([AllowAny])
@transaction.atomic
def telegram_login(request):
    if settings.EDUCATIONAL_MODE:
        raise ProviderUnavailable('В учебной версии Telegram не подключается.')
    nonce = request.session.pop('telegram_nonce', None)
    if not nonce or not secrets.compare_digest(nonce, str(request.data.get('nonce', ''))):
        raise PermissionDenied('Повторите вход через Telegram.')
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ProviderUnavailable('Telegram не подключён.')
    data = request.data.get('auth', {})
    if not isinstance(data, dict):
        raise ValidationError('Некорректные данные Telegram.')
    try:
        age = time.time()-int(data['auth_date'])
        if not 0 <= age <= 86400:
            raise ValueError()
        content = '\n'.join(f'{k}={v}' for k,v in sorted(data.items()) if k != 'hash')
        digest = hmac.new(hashlib.sha256(token.encode()).digest(), content.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, str(data.get('hash',''))):
            raise ValueError()
        user = social_user('telegram', str(int(data['id'])), name=str(data.get('first_name','')))
    except (ValueError, KeyError, TypeError):
        raise PermissionDenied('Подпись Telegram недействительна.')
    refresh = RefreshToken.for_user(user)
    return Response({'access':str(refresh.access_token),'refresh':str(refresh)})
