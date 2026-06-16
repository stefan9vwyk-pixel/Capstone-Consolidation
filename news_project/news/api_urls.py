from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter
from .api_views import (
    ArticleViewSet,
    NewsletterViewSet,
    PublisherViewSet,
    ApprovedArticleWebhookView
)

router = DefaultRouter()
router.register(r'articles', ArticleViewSet, basename='api-article')
router.register(r'newsletters', NewsletterViewSet, basename='api-newsletter')
router.register(r'publishers', PublisherViewSet, basename='api-publisher')

urlpatterns = [
    path('', include(router.urls)),
    path('token/', obtain_auth_token, name='api-token-auth'),
    path(
        'approved/',
        ApprovedArticleWebhookView.as_view(),
        name='api-approved-webhook'
    ),
]
