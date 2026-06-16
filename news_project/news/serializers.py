"""Serializers for the news application.

This module exposes concise and detailed serializers for `Article`,
`Newsletter`, `Publisher`, and user profile summaries. Serializers include
read-only summary representations for nested related objects and
validation logic that enforces role-based constraints (e.g. only editors
may approve articles).
"""

from rest_framework import serializers
from .models import Article, Newsletter, Publisher
from accounts.models import CustomUser


class UserSummarySerializer(serializers.ModelSerializer):
    """Lightweight serializer for user references.

    Used when embedding a user inside other serializers (e.g. article
    author). Provides a `full_name` field that falls back to `username`.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'full_name', 'role')
        read_only_fields = fields

    def get_full_name(self, obj):
        """Return a display name for the user, preferring full name."""
        return obj.get_full_name() or obj.username


class PublisherSummarySerializer(serializers.ModelSerializer):
    """Compact publisher representation used in nested contexts."""

    class Meta:
        model = Publisher
        fields = ('id', 'name', 'website')
        read_only_fields = fields


# ── Article ────────────────────────────────────────────────────────────────

class ArticleListSerializer(serializers.ModelSerializer):
    """Summary serializer for article lists and feeds.

    Includes a short `excerpt` and a human-readable `status` label.
    """

    author = UserSummarySerializer(read_only=True)
    publisher = PublisherSummarySerializer(read_only=True)
    status = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'excerpt', 'author',
            'publisher', 'approved', 'status', 'created_at',
        )
        read_only_fields = fields

    def get_status(self, obj):
        """Return the article's human-readable status label."""
        return obj.get_status_label()

    def get_excerpt(self, obj):
        """Return a short excerpt derived from article content.

        Grabs the first 25 words (or fewer) and appends an ellipsis when
        the content is longer.
        """
        if obj.content:
            words = obj.content.split()
            return " ".join(words[:25]) + ("..." if len(words) > 25 else "")
        return ""


class ArticleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Article create/retrieve/update actions.

    Provides both the editable `publisher` primary key field and a
    read-only `publisher_detail` nested representation. Includes
    custom validation to enforce that only editors can set `approved`.
    """

    author = UserSummarySerializer(read_only=True)
    publisher_detail = PublisherSummarySerializer(
        source='publisher',
        read_only=True
    )
    publisher = serializers.PrimaryKeyRelatedField(
        queryset=Publisher.objects.all(),
        allow_null=True,
        required=False,
    )
    status = serializers.SerializerMethodField()
    source_label = serializers.SerializerMethodField()
    newsletter_count = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = (
            'id', 'title', 'content', 'author',
            'publisher', 'publisher_detail',
            'approved', 'status', 'source_label',
            'newsletter_count',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'author', 'status', 'source_label',
            'newsletter_count', 'created_at', 'updated_at',
        )

    def get_status(self, obj):
        """Return the article's current status label."""
        return obj.get_status_label()

    def get_newsletter_count(self, obj):
        """Return the number of newsletters that include this article."""
        return obj.newsletters.count()

    def validate(self, data):
        """Enforce role-based validation rules on article data.

        - Only users with the editor role may set `approved=True`.
        - Non-editors who update an existing article will have `approved`
          forced to False to ensure changes enter the review queue.
        """
        request = self.context.get('request')
        if request and request.user:
            # If a non-editor attempts to change the approval status to True
            if data.get('approved', False) and not request.user.is_editor:
                raise serializers.ValidationError(
                    {'approved': 'Only editors can approve articles.'}
                )

            # Security guard: If a journalist edits their own article,
            # force status back to pending review (approved=False).
            if not request.user.is_editor and self.instance:
                data['approved'] = False

        return data

    def get_source_label(self, obj):
        """
        Return the name of the publisher or 'Independent' when none exists.
        """
        return obj.publisher.name if obj.publisher else "Independent"


# ── Newsletter ─────────────────────────────────────────────────────────────

class NewsletterListSerializer(serializers.ModelSerializer):
    """Serializer for displaying newsletter lists with article counts."""

    author = UserSummarySerializer(read_only=True)
    article_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Newsletter
        fields = (
            'id',
            'title',
            'description',
            'author',
            'article_count',
            'created_at'
        )
        read_only_fields = fields


class NewsletterDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for creating and updating newsletters.

    Accepts `article_ids` (write-only) to set the newsletter's articles,
    and exposes a read-only `articles` list for retrieval.
    """

    author = UserSummarySerializer(read_only=True)
    articles = ArticleListSerializer(many=True, read_only=True)
    article_ids = serializers.PrimaryKeyRelatedField(
        source='articles',
        queryset=Article.objects.filter(approved=True),
        many=True,
        required=False,
        write_only=True,
    )
    article_count = serializers.SerializerMethodField()

    class Meta:
        model = Newsletter
        fields = (
            'id', 'title', 'description', 'author',
            'articles', 'article_ids', 'article_count',
            'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'author', 'articles', 'article_count',
            'created_at', 'updated_at',
        )

    def get_article_count(self, obj):
        """Return the number of articles included in this newsletter."""
        return obj.articles.count()

    def create(self, validated_data):
        """Create a newsletter and attach any provided articles.

        The `article_ids` are provided under the `articles` key in
        `validated_data` because of the `source='articles'` mapping.
        """
        articles = validated_data.pop('articles', [])
        newsletter = Newsletter.objects.create(**validated_data)
        newsletter.articles.set(articles)
        return newsletter

    def update(self, instance, validated_data):
        """Update newsletter fields and optionally replace article M2M list."""
        articles = validated_data.pop('articles', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if articles is not None:
            instance.articles.set(articles)
        return instance


# ── Publisher ──────────────────────────────────────────────────────────────

class PublisherDetailSerializer(serializers.ModelSerializer):
    """Detailed publisher serializer with editorial relationships."""

    editors = UserSummarySerializer(many=True, read_only=True)
    journalists = UserSummarySerializer(many=True, read_only=True)
    article_count = serializers.SerializerMethodField()

    class Meta:
        model = Publisher
        fields = (
            'id', 'name', 'description', 'website',
            'editors', 'journalists', 'article_count', 'created_at',
        )
        read_only_fields = fields

    def get_article_count(self, obj):
        """Return how many articles are associated with this publisher."""
        return obj.articles.count()


# ── User Profile (role-aware) ──────────────────────────────────────────────

class UserProfileSerializer(serializers.ModelSerializer):
    """Exposes role-specific profile fields for different user roles.

    Readers expose `subscribed_publishers` and `subscribed_journalists`.
    Journalists and editors additionally expose article/newsletter counts
    and independent counts. Fields that are not applicable for a role are
    returned as `None` to make API responses explicit.
    """

    full_name = serializers.SerializerMethodField()

    # Reader fields — will be None when role != reader
    subscribed_publishers = serializers.SerializerMethodField()
    subscribed_journalists = serializers.SerializerMethodField()

    # Journalist/Editor fields — will be None when role == reader
    article_count = serializers.SerializerMethodField()
    newsletter_count = serializers.SerializerMethodField()
    independent_article_count = serializers.SerializerMethodField()
    independent_newsletter_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'id', 'username', 'full_name', 'role',
            'bio', 'avatar_url', 'is_active', 'date_joined',
            # reader
            'subscribed_publishers', 'subscribed_journalists',
            # journalist/editor
            'article_count', 'newsletter_count',
            'independent_article_count', 'independent_newsletter_count',
        )
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    # ── Reader fields ──────────────────────────────────────────────────────

    def get_subscribed_publishers(self, obj):
        # If the precomputed related set is not present for this user role,
        # return None so the client knows the property is not applicable.
        if obj.reader_subscribed_publishers is None:
            return None
        return PublisherSummarySerializer(
            obj.reader_subscribed_publishers, many=True
        ).data

    def get_subscribed_journalists(self, obj):
        if obj.reader_subscribed_journalists is None:
            return None
        return UserSummarySerializer(
            obj.reader_subscribed_journalists, many=True
        ).data

    # ── Journalist / Editor fields ─────────────────────────────────────────

    def get_article_count(self, obj):
        # For non-journalist/editor roles the property may be omitted.
        if obj.journalist_articles is None:
            return None
        return obj.journalist_articles.count()

    def get_newsletter_count(self, obj):
        if obj.journalist_newsletters is None:
            return None
        return obj.journalist_newsletters.count()

    def get_independent_article_count(self, obj):
        if obj.journalist_independent_articles is None:
            return None
        return obj.journalist_independent_articles.count()

    def get_independent_newsletter_count(self, obj):
        if obj.journalist_independent_newsletters is None:
            return None
        return obj.journalist_independent_newsletters.count()
