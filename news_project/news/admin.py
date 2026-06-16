"""Django admin registration for news app models.

This module registers `Publisher`, `Article` and `Newsletter` models to the
admin site and configures list display, search fields, filters, and custom
admin actions for content moderation.
"""

from django.contrib import admin
from django.contrib import messages
from .models import Article, Newsletter, Publisher


@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name', 'website', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('editors', 'journalists')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'publisher', 'approved', 'created_at')
    list_filter = ('approved', 'publisher', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['approve_articles', 'unapprove_articles']

    def approve_articles(self, request, queryset):
        """Mark the selected articles as approved."""
        count = queryset.update(approved=True)
        self.message_user(
            request,
            f'{count} article(s) approved.',
            messages.SUCCESS
        )
    approve_articles.short_description = 'Approve selected articles'

    def unapprove_articles(self, request, queryset):
        """Mark the selected articles as not approved."""
        count = queryset.update(approved=False)
        self.message_user(
            request,
            f'{count} article(s) unapproved.',
            messages.WARNING
        )
    unapprove_articles.short_description = 'Unapprove selected articles'


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at')
    search_fields = ('title', 'description', 'author__username')
    filter_horizontal = ('articles',)
    readonly_fields = ('created_at', 'updated_at')
