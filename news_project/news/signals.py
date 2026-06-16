"""Signal handlers and helpers for post-approval workflows.

This module performs post-approval tasks for `Article` instances, including:
- Gathering subscriber email addresses (journalist- and publisher-subscribers),
- Sending notification emails to subscribers, and
- Posting a lightweight notification to an internal endpoint for further
  integration (runs in a background thread to avoid blocking requests).

Signal handlers are intentionally tolerant of missing related data and
network failures — logging warnings instead of raising errors so that the
main application flow is unaffected by non-critical post-save actions.
"""

import logging
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Article

logger = logging.getLogger(__name__)


def _collect_subscriber_emails(article):
    """
    Gather email addresses of users who have subscribed to:
      - the article's journalist (author), or
      - the article's publisher.
    Returns a deduplicated list of email strings.
    """
    emails = set()

    # Readers subscribed to this journalist (direct M2M on the author)
    try:
        journalist_subscribers = article.author.journalist_subscribers.all()
        for user in journalist_subscribers:
            # Only collect valid email addresses
            if user.email:
                emails.add(user.email)
    except Exception as exc:
        # Defensive logging — failures here should not prevent the main flow
        logger.warning('Could not fetch journalist subscribers: %s', exc)

    # Readers subscribed to this publisher (publisher may be None)
    if article.publisher:
        try:
            # Primary attempt: use the publisher's related subscriber set
            publisher_subscribers = article.publisher.subscriber_set.all()
            for user in publisher_subscribers:
                if user.email:
                    emails.add(user.email)
        except Exception:
            # Fallback: query the CustomUser M2M relationship if the reverse
            # accessor isn't available (defensive compatibility handling).
            try:
                from accounts.models import CustomUser
                publisher_subscribers = CustomUser.objects.filter(
                    subscribed_publishers=article.publisher
                )
                for user in publisher_subscribers:
                    if user.email:
                        emails.add(user.email)
            except Exception as exc2:
                logger.warning(
                    'Could not fetch publisher subscribers: %s', exc2
                )

    return list(emails)


def _send_approval_emails(article, subscriber_emails):
    """Send notification emails to all subscribers.

       This uses Django's `send_mail` which will obey the configured email
       backend; in development this may be the console backend.
    """
    if not subscriber_emails:
        logger.info(
            'No subscribers to notify for article "%s".', article.title
        )
        return

    subject = f'New Article Published: {article.title}'
    publisher_name = (
        article.publisher.name if article.publisher else 'Independent'
    )
    author_name = article.author.get_full_name() or article.author.username
    # Short content snippet for the email body
    snippet = article.content[:300] + (
        '…' if len(article.content) > 300 else ''
    )

    # Compose a simple plain-text notification message
    message = (
        f'Hello,\n\n'
        f'A new article has been published that you may be interested in.\n\n'
        f'Title:     {article.title}\n'
        f'Author:    {author_name}\n'
        f'Publisher: {publisher_name}\n\n'
        f'{snippet}\n\n'
        f'Log in to the Newsroom to read the full article.\n\n'
        f'— The Newsroom Team'
    )

    from_email = getattr(
        settings, 'DEFAULT_FROM_EMAIL', 'newsroom@example.com'
    )

    try:
        # `fail_silently=False` ensures exceptions bubble here for logging.
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=subscriber_emails,
            fail_silently=False,
        )
        logger.info(
            'Approval email sent to %d subscriber(s) for article "%s".',
            len(subscriber_emails), article.title
        )
    except Exception as exc:
        # Log failure; email sending is non-critical for the main flow.
        logger.error('Failed to send approval emails: %s', exc)


def _post_to_approved_endpoint(article):
    """POST article data to the internal /api/approved/ endpoint.

       Runs in a background thread so it doesn't block the request cycle. This
       function is tolerant of missing `requests` library or network failures
       — it will log warnings but not raise errors.
    """
    try:
        import requests as req_lib
    except ImportError:
        # The integration is optional; do not treat missing requests as fatal.
        logger.warning(
            'requests library not installed — skipping internal API POST.'
        )
        return

    author_name = article.author.get_full_name() or article.author.username
    publisher_name = article.publisher.name if article.publisher else None

    payload = {
        'article_id': article.pk,
        'title': article.title,
        'author': author_name,
        'publisher': publisher_name,
        'approved': article.approved,
        'word_count': article.word_count,
        'created_at': article.created_at.isoformat(),
    }

    # Use the development server port if provided in settings; default 8000.
    port = getattr(settings, 'DEV_SERVER_PORT', 8000)
    url = f'http://127.0.0.1:{port}/api/approved/'

    try:
        # Perform a short, synchronous POST with a timeout so the thread exits
        # quickly if the internal service is unavailable.
        response = req_lib.post(
            url,
            json=payload,
            timeout=5,
            headers={'Content-Type': 'application/json'},
        )
        logger.info(
            'Internal API POST to %s — status %d — body: %s',
            url, response.status_code, response.text[:200]
        )
    except Exception as exc:
        # Non-critical: network failures should not affect application flow.
        logger.warning('Internal API POST failed (non-critical): %s', exc)


@receiver(post_save, sender=Article)
def on_article_save(sender, instance, created, **kwargs):
    """Signal handler triggered after an Article is saved.

       The handler performs post-approval actions only when the article has
       just been approved. To avoid triggering on unrelated saves, the view
       or model code sets a `_approval_just_toggled` sentinel on the instance
       around the save() call; this handler checks that flag to decide.
    """
    # Ignore if the article is not approved after save.
    if not instance.approved:
        return

    # The `_approval_just_toggled` sentinel is expected to be set by the
    # code path that flips approval (e.g., an admin view or action).
    # This distinguishes a genuine transition from other saves.
    if not getattr(instance, '_approval_just_toggled', False):
        return

    logger.info(
        'Article "%s" (pk=%d) approved — running post-approval actions.',
        instance.title,
        instance.pk
    )

    # 1. Collect subscriber emails (may perform multiple DB queries).
    subscriber_emails = _collect_subscriber_emails(instance)

    # 2. Send notification emails to subscribers.
    # In development the email backend may be a console backend; in
    # production this will use the configured SMTP/relay settings.
    _send_approval_emails(instance, subscriber_emails)

    # 3. Notify internal integrations via a background thread so we don't
    # block the request/response cycle. The handler does not wait for this
    # thread; failures are logged non-fatally by the worker.
    thread = threading.Thread(
        target=_post_to_approved_endpoint,
        args=(instance,),
        daemon=True,
    )
    thread.start()
