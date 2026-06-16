"""
Filter helpers for news article querysets.

This module provides shared filtering logic used by article list views,
search pages, and admin filtering. It returns both the filtered queryset and
a dictionary of active filters for display in templates and UI summaries.
"""

from django.db.models import Q
from accounts.models import CustomUser


def apply_article_filters(queryset, params, user=None):
    """Apply user-facing filters to an Article queryset.

    Args:
        queryset: Initial Article queryset to filter.
        params: Query parameters dict, typically request.GET.
        user: Optional user instance for permission-aware filtering.

    Returns:
        tuple: (filtered_queryset, active_filters_dict)
    """

    active_filters = {}

    # Restrict readers to approved articles only.
    if user and user.is_reader:
        queryset = queryset.filter(approved=True)

    # Full-text search across title, content, and author fields.
    query = params.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query) |
            Q(author__username__icontains=query)
        )
        active_filters['q'] = query

    # Status filter: approved or pending review.
    status = params.get('status', '').strip()
    if status == 'approved':
        queryset = queryset.filter(approved=True)
        active_filters['status'] = 'Approved'
    elif status == 'pending':
        queryset = queryset.filter(approved=False)
        active_filters['status'] = 'Pending Review'

    # Publisher filter: independent publishers or a specific publisher.
    publisher = params.get('publisher', '').strip()
    if publisher == 'independent':
        queryset = queryset.filter(publisher__isnull=True)
        active_filters['publisher'] = 'Independent'
    elif publisher:
        try:
            publisher_id = int(publisher)
            queryset = queryset.filter(publisher__id=publisher_id)
            from news.models import Publisher as Pub
            try:
                pub_name = Pub.objects.get(id=publisher_id).name
                active_filters['publisher'] = pub_name
            except Pub.DoesNotExist:
                pass
        except (ValueError, TypeError):
            pass

    # Author filter by id, also capture display name if available.
    author_id = params.get('author', '').strip()
    if author_id:
        try:
            author_pk = int(author_id)
            queryset = queryset.filter(author__id=author_pk)
            try:
                author = CustomUser.objects.get(id=author_pk)
                active_filters['author'] = (
                    author.get_full_name() or author.username
                )
            except CustomUser.DoesNotExist:
                pass
        except (ValueError, TypeError):
            pass

    # Date range filtering.
    date_from = params.get('date_from', '').strip()
    date_to = params.get('date_to', '').strip()
    if date_from:
        queryset = queryset.filter(created_at__date__gte=date_from)
        active_filters['date_from'] = date_from
    if date_to:
        queryset = queryset.filter(created_at__date__lte=date_to)
        active_filters['date_to'] = date_to

    # Sorting options with default ordering by date.
    sort = params.get('sort', 'date').strip()
    order = params.get('order', 'desc').strip()

    sort_map = {
        'date':   'created_at',
        'title':  'title',
        'author': 'author__last_name',
        'status': 'approved',
    }
    sort_field = sort_map.get(sort, 'created_at')
    if order == 'asc':
        queryset = queryset.order_by(sort_field)
    else:
        queryset = queryset.order_by(f'-{sort_field}')

    return queryset, active_filters
