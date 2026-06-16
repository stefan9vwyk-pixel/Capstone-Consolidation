"""REST API views and custom permissions for the news app.

This module defines viewsets for articles, newsletters, and publishers,
plus a webhook endpoint for approved article notifications.
"""

import logging

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import (
    BasePermission, AllowAny
)
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count

from .models import Article, Newsletter, Publisher
from .serializers import (
    ArticleListSerializer, ArticleDetailSerializer,
    NewsletterListSerializer, NewsletterDetailSerializer,
    PublisherDetailSerializer,
)

logger = logging.getLogger(__name__)


# ── Custom permissions ──────────────────────────────────────────────────────

class IsEditorOrReadOnly(BasePermission):
    """Allow read-only access for authenticated users; editors may modify."""

    def has_permission(self, request, view):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user and request.user.is_authenticated
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_editor
        )

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.is_editor


class CanCreateContent(BasePermission):
    """
    Permission rules for content creation, updates, deletion, and reading.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Global Route Access Controls
        if view.action == 'create':
            return request.user.can_create_content

        if view.action in ('update', 'partial_update', 'destroy'):
            return request.user.is_journalist or request.user.is_editor

        # Allow reading endpoints (list, retrieve, subscribed) to pass,
        # through to object checks.
        return True

    def has_object_permission(self, request, view, obj):
        # Readers may only access approved records.
        if request.user.is_reader:
            return (
                request.method in ('GET', 'HEAD', 'OPTIONS') and obj.approved
            )

        # Editors have full access.
        if request.user.is_editor:
            return True

        # Journalists may read everything,
        # But may only modify/delete their own work.
        if request.user.is_journalist:
            if request.method in ('GET', 'HEAD', 'OPTIONS'):
                return True
            return obj.author == request.user

        return False


class IsEditorPermission(BasePermission):
    """Allow access only to authenticated users with editor privileges."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_editor
        )


# ── Article ViewSet ─────────────────────────────────────────────────────────

class ArticleViewSet(viewsets.ModelViewSet):
    """
    CRUD API for articles with filtering, searching,
    ordering, and approval actions.
    """

    permission_classes = [CanCreateContent]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['approved', 'publisher']
    search_fields = [
        'title',
        'content',
        'author__username',
        'author__first_name',
        'author__last_name'
    ]
    ordering_fields = ['created_at', 'title', 'approved']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Return articles visible to the current user,
        optionally filtered by author.
        """
        qs = Article.objects.select_related(
            'author', 'publisher'
        ).order_by('-created_at')

        if self.request.user.is_reader:
            qs = qs.filter(approved=True)
        author_id = self.request.query_params.get('author')
        if author_id:
            qs = qs.filter(author__id=author_id)
        return qs

    def get_serializer_class(self):
        """
        Use the list serializer for list views,
        otherwise use the detail serializer.
        """
        if self.action == 'list':
            return ArticleListSerializer
        return ArticleDetailSerializer

    def perform_create(self, serializer):
        """Attach the currently authenticated user as the article author."""
        serializer.save(author=self.request.user)

    @action(detail=False, methods=['get'], url_path='subscribed')
    def subscribed(self, request):
        """Return the authenticated reader's subscribed article feed."""
        if not request.user.is_reader:
            return Response(
                {"detail": "Only readers can access subscribed feeds."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Build a personalized approved-article feed from subscriptions.
        followed_journalists = request.user.subscribed_journalists.all()
        followed_publishers = request.user.subscribed_publishers.all()

        queryset = Article.objects.filter(
            approved=True
        ).filter(
            Q(author__in=followed_journalists) |
            Q(publisher__in=followed_publishers)
        ).distinct().select_related(
            'author', 'publisher'
        ).order_by('-created_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'],
            permission_classes=[IsEditorPermission],
            url_path='approve')
    def approve(self, request, pk=None):
        """Toggle approval status for the specified article."""
        article = self.get_object()
        was_approved = article.approved
        article.approved = not article.approved
        if article.approved and not was_approved:
            article._approval_just_toggled = True
        article.save()

        article_status = "approved" if article.approved else "unapproved"

        return Response({
            'id': article.pk,
            'approved': article.approved,
            'status': article.get_status_label(),
            'message': f"Article has been {article_status}.",
        })


# ── Newsletter ViewSet ──────────────────────────────────────────────────────

class NewsletterViewSet(viewsets.ModelViewSet):
    """
    CRUD API for newsletters with search,
    ordering, and article count annotation.
    """

    permission_classes = [CanCreateContent]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['author']
    search_fields = [
        'title',
        'description',
        'author__username',
        'author__first_name',
        'author__last_name'
    ]
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Return newsletters with related author and article count annotation.
        """
        return Newsletter.objects.select_related(
            'author'
        ).prefetch_related('articles').annotate(
            article_count=Count('articles')
        ).order_by('-created_at')

    def get_serializer_class(self):
        """
        Select a list or detail serializer depending on the current action.
        """
        if self.action == 'list':
            return NewsletterListSerializer
        return NewsletterDetailSerializer

    def perform_create(self, serializer):
        """Attach the authenticated user as the newsletter author."""
        serializer.save(author=self.request.user)


# ── Publisher ViewSet (read-only) ───────────────────────────────────────────

class PublisherViewSet(viewsets.ModelViewSet):
    """
    Read-only publisher API with related editors, journalists,
    and articles preloaded.
    """

    permission_classes = [IsEditorOrReadOnly]
    serializer_class = PublisherDetailSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """
        Return publishers with related editorial
        profiles and articles prefetched.
        """
        return Publisher.objects.prefetch_related(
            'editors',
            'journalists',
            'articles'
        ).order_by('name')


# ── /api/approved/ — Internal webhook endpoint ──────────────────────────────

class ApprovedArticleWebhookView(APIView):
    """Internal webhook endpoint for approved article notifications."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        """Handle POST notifications from the approval signal integration."""

        data = request.data
        article_id = data.get('article_id')
        title = data.get('title', 'Unknown')

        logger.info(
            '[/api/approved/] Received approved article — '
            'id=%s title="%s" author="%s" publisher="%s"',
            article_id,
            title,
            data.get('author'),
            data.get('publisher'),
        )

        # In a real integration, this would push the article to an external
        # CMS, CDN, or notification service.
        return Response(
            {
                'received': True,
                'article_id': article_id,
                'title': title,
                'message': (
                    f'Article "{title}" has been registered as published.'
                ),
            },
            status=status.HTTP_200_OK,
        )
