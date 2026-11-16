from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from catalog import api, views

router = DefaultRouter()
router.register('bloggers', api.BloggerViewSet, basename='blogger')
router.register('proposals', api.ProposalViewSet, basename='proposal')
router.register('deals', api.DealViewSet, basename='deal')
router.register('campaigns', api.CampaignViewSet, basename='campaign')
router.register('reviews', api.ReviewViewSet, basename='review')
router.register('notifications', api.NotificationViewSet, basename='notification')
router.register('searches', api.SavedSearchViewSet, basename='search')

class LoginView(TokenObtainPairView):
    throttle_classes = [api.LoginThrottle]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/register/', api.register),
    path('api/verify-email/', api.verify_email),
    path('api/resend-email/', api.resend_email),
    path('api/login/', LoginView.as_view()),
    path('api/token/refresh/', TokenRefreshView.as_view()),
    path('api/logout/', api.logout),
    path('api/me/', api.me),
    path('api/profile/', api.profile),
    path('api/options/', api.options),
    path('api/analytics/', api.analytics),
    path('api/disputes/<int:pk>/resolve/', api.resolve),
    path('api/files/<str:kind>/<int:pk>/', api.download),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/', include(router.urls)),
    path('blogger/<int:pk>/', views.blogger_detail, name='blogger_detail'),
    path('', views.app, name='blogger_list'),
]
