"""Account models for the project.

This module defines `CustomUser`, an extension of Django's
`AbstractUser` that adds role-based behavior (reader, journalist,
editor), subscription relations for readers, and convenience
properties for role checks and related content access.

The model also ensures the user is assigned to an appropriate
Django `Group` on save and keeps reader-only subscription fields
empty for non-readers.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import Group


class CustomUser(AbstractUser):
    """Custom user model with role, subscriptions and helpers.

    Fields added:
    - `role`: determines permissions and group membership.
    - `bio`, `avatar_url`: optional profile fields.
    - `subscribed_publishers`, `subscribed_journalists`: M2M fields
       used by readers to follow publishers and journalists.

    The class exposes properties like `is_reader`, `can_create_content`,
    and related managers (`journalist_articles`, `journalist_newsletters`)
    to simplify view and template logic.
    """
    ROLE_CHOICES = [
        ('reader', 'Reader'),
        ('journalist', 'Journalist'),
        ('editor', 'Editor'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='reader',
        help_text='User role determines permissions and group membership.'
    )
    bio = models.TextField(blank=True, default='')
    avatar_url = models.URLField(blank=True, default='')

    email = models.EmailField(
        unique=True,
        max_length=255,
        error_messages={
            'unique': 'A user with that email address already exists.',
        })

    USERNAME_FIELD = 'username'

    # ── Reader-only fields ──────────────────────────────────────────────────
    subscribed_publishers = models.ManyToManyField(
        'news.Publisher',
        blank=True,
        related_name='subscribed_readers',
        help_text=(
            'Publishers this reader follows. Only relevant for Reader role.'
        ),
        verbose_name='Subscribed publishers',
    )
    subscribed_journalists = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='journalist_subscribers',
        limit_choices_to={'role': 'journalist'},
        help_text=(
            'Journalists this reader follows. Only relevant for Reader role.'
        ),
        verbose_name='Subscribed journalists',
    )

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        # Represent the user as 'Full Name (Role)' falling back to username
        return (
            f'{self.get_full_name() or self.username} '
            f'({self.get_role_display()})'
        )

    # ── Role-guard properties ───────────────────────────────────────────────

    @property
    def reader_subscribed_publishers(self):
        """
        Returns the subscribed_publishers queryset for readers,
        None for other roles.
        """
        if self.role != 'reader':
            return None
        return self.subscribed_publishers.all()

    @property
    def reader_subscribed_journalists(self):
        """
        Returns the subscribed_journalists queryset for readers,
        None for other roles.
        """
        if self.role != 'reader':
            return None
        return self.subscribed_journalists.all()

    @property
    def journalist_articles(self):
        """
        Returns articles authored by this journalist,
        None for non-journalists.
        """
        if self.role not in ('journalist', 'editor'):
            return None
        return self.articles.all()

    @property
    def journalist_independent_articles(self):
        """
        Articles published independently (no publisher).
        None for non-journalists.
        """
        if self.role not in ('journalist', 'editor'):
            return None
        return self.articles.filter(publisher__isnull=True)

    @property
    def journalist_newsletters(self):
        """
        Returns newsletters authored by this journalist,
        None for non-journalists.
        """
        if self.role not in ('journalist', 'editor'):
            return None
        return self.newsletters.all()

    @property
    def journalist_independent_newsletters(self):
        """Newsletters published independently. None for non-journalists."""
        if self.role not in ('journalist', 'editor'):
            return None
        return self.newsletters.filter(publisher__isnull=True)

    # ── Role helpers ────────────────────────────────────────────────────────

    def get_role_display_badge(self):
        colors = {
            'reader': 'badge-neutral',
            'journalist': 'badge-accent',
            'editor': 'badge-success',
        }
        return colors.get(self.role, 'badge-neutral')

    @property
    def is_reader(self):
        return self.role == 'reader'

    @property
    def is_journalist(self):
        return self.role == 'journalist'

    @property
    def is_editor(self):
        return self.role == 'editor'

    @property
    def can_create_content(self):
        return self.role in ('journalist', 'editor')

    @property
    def can_approve(self):
        return self.role == 'editor'

    def save(self, *args, **kwargs):
        """Persist the user and enforce role-related side effects.

        After saving the model fields, ensure the user's Django `Group`
        membership reflects their `role` and clear any reader-only
        subscription relations when the role is not `reader`.
        """
        super().save(*args, **kwargs)
        self._assign_group()
        self._clear_irrelevant_subscriptions()

    def _assign_group(self):
        """Assign the user to a Django Group based on `role`.

        This clears any existing groups and then attempts to add the
        matching Group by name. If the Group does not exist the
        operation is silently skipped to avoid breaking deployments
        that haven't created the groups yet.
        """
        # Reset groups and re-assign according to the current role
        self.groups.clear()
        group_map = {
            'reader': 'Readers',
            'journalist': 'Journalists',
            'editor': 'Editors',
        }
        group_name = group_map.get(self.role)
        if group_name:
            try:
                group = Group.objects.get(name=group_name)
                self.groups.add(group)
            except Group.DoesNotExist:
                # Group not present; safe to continue without assignment
                pass

    def _clear_irrelevant_subscriptions(self):
        """
        Enforce mutual exclusion: if the user is not a reader, clear reader
        subscription M2M fields so they remain semantically None.
        """
        if self.role != 'reader':
            self.subscribed_publishers.clear()
            self.subscribed_journalists.clear()
