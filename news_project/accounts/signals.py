from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.conf import settings
from rest_framework.authtoken.models import Token

from news.models import Article, Newsletter


def _setup_groups():
    """Helper function to create roles and assign permissions."""
    try:
        article_ct = ContentType.objects.get_for_model(Article)
        newsletter_ct = ContentType.objects.get_for_model(Newsletter)

        # Readers group
        readers_group, _ = Group.objects.get_or_create(name='Readers')
        reader_perms = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__startswith='view_'
        )
        readers_group.permissions.set(reader_perms)

        # Editors group
        editors_group, _ = Group.objects.get_or_create(name='Editors')
        editor_perms = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
            codename__in=[
                'view_article', 'change_article', 'delete_article',
                'view_newsletter', 'change_newsletter', 'delete_newsletter',
            ]
        )
        editors_group.permissions.set(editor_perms)

        # Journalists group
        journalists_group, _ = Group.objects.get_or_create(name='Journalists')
        journalist_perms = Permission.objects.filter(
            content_type__in=[article_ct, newsletter_ct],
        )
        journalists_group.permissions.set(journalist_perms)

        print("Groups have been created and permissions have been granted.")

    except Exception:
        # Prevents migrations from breaking if tables don't exist yet
        pass


@receiver(post_migrate)
def create_groups(sender, **kwargs):
    """Triggers the group setup after migrations finish."""
    if sender.name == 'accounts':
        _setup_groups()


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """Automatically generates a DRF Token whenever a new user is saved."""
    if created:
        Token.objects.create(user=instance)
