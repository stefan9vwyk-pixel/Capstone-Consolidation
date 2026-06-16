"""Management views for user administration.

These views are protected by the `editor_required` decorator and are
intended for editors to list, inspect, create, edit and deactivate
user accounts. Small docstrings and inline comments clarify behavior
for maintainers and template authors.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count
from .models import CustomUser
from .decorators import editor_required
from .management_forms import UserCreateForm, UserEditForm
from news.models import Article, Newsletter


@editor_required
def user_list_view(request):
    """List users for administrative purposes.

    Supports optional filtering by search query, role and active status.
    Annotates each user with counts of related `Article` and
    `Newsletter` objects for convenient display in the template.
    """

    users = CustomUser.objects.annotate(
        article_count=Count('articles', distinct=True),
        newsletter_count=Count('newsletters', distinct=True),
    ).order_by('last_name', 'first_name')

    # Free-text search across common user fields
    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    role_filter = request.GET.get('role', '').strip()
    if role_filter in ('reader', 'journalist', 'editor'):
        users = users.filter(role=role_filter)

    active_filter = request.GET.get('active', '').strip()
    if active_filter == 'active':
        users = users.filter(is_active=True)
    elif active_filter == 'inactive':
        users = users.filter(is_active=False)

    all_users = CustomUser.objects.all()
    stats = {
        'total':       all_users.count(),
        'editors':     all_users.filter(role='editor').count(),
        'journalists': all_users.filter(role='journalist').count(),
        'readers':     all_users.filter(role='reader').count(),
        'inactive':    all_users.filter(is_active=False).count(),
    }

    return render(request, 'accounts/user_list.html', {
        'users':        users,
        'stats':        stats,
        'query':        query,
        'role_filter':  role_filter,
        'active_filter': active_filter,
        'total_count':  users.count(),
    })


@editor_required
def user_detail_view(request, pk):
    """Show detailed information about a single user.

    Returns the most recent articles and newsletters authored by the
    target user, basic approval stats, and role-specific context used by
    the admin templates.
    """

    target = get_object_or_404(CustomUser, pk=pk)
    # Recent authored content for quick preview
    articles = Article.objects.filter(
        author=target
    ).order_by('-created_at')[:10]
    newsletters = Newsletter.objects.filter(
        author=target
        ).order_by('-created_at')[:5]

    stats = {
        'total_articles':    Article.objects.filter(author=target).count(),
        'approved_articles': Article.objects.filter(
            author=target, approved=True
        ).count(),
        'pending_articles':  Article.objects.filter(
            author=target, approved=False
        ).count(),
        'total_newsletters': Newsletter.objects.filter(author=target).count(),
    }

    # Role-specific context
    reader_context = journalist_context = None

    if target.role == 'reader':
        reader_context = {
            'subscribed_publishers': target.reader_subscribed_publishers,
            'subscribed_journalists': target.reader_subscribed_journalists,
            'publisher_count': target.subscribed_publishers.count(),
            'journalist_count': target.subscribed_journalists.count(),
        }

    if target.role in ('journalist', 'editor'):
        ind_articles = target.journalist_independent_articles
        ind_newsletters = target.journalist_independent_newsletters
        journalist_context = {
            'independent_articles': (
                ind_articles[:5] if ind_articles is not None else []
            ),
            'independent_newsletters': (
                ind_newsletters[:5] if ind_newsletters is not None else []
            ),
            'independent_article_count': (
                ind_articles.count() if ind_articles is not None else 0
            ),
            'independent_newsletter_count': (
                ind_newsletters.count() if ind_newsletters is not None else 0
            ),
        }

    return render(request, 'accounts/user_detail.html', {
        'target':             target,
        'articles':           articles,
        'newsletters':        newsletters,
        'stats':              stats,
        'reader_context':     reader_context,
        'journalist_context': journalist_context,
    })


@editor_required
def user_create_view(request):
    """Create a new user from the management interface.

    On success redirects to the newly created user's detail page and
    flashes a message confirming account creation.
    """

    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(
                request,
                f"Account created for {user.get_full_name() or user.username}."
            )
            return redirect('accounts:user_detail', pk=user.pk)
    else:
        form = UserCreateForm()
    return render(request, 'accounts/user_create.html', {'form': form})


@editor_required
def user_edit_view(request, pk):
    """Edit an existing user's account.

    If the form is valid the changes are saved and the admin is
    redirected to the user's detail page with a success message.
    """

    target = get_object_or_404(CustomUser, pk=pk)
    is_self = (target == request.user)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            user = form.save()
            # Use a single-line f-string to avoid multi-line formatting issues
            messages.success(
                request,
                f"Account updated for {user.get_full_name() or user.username}."
            )
            return redirect('accounts:user_detail', pk=user.pk)
    else:
        form = UserEditForm(instance=target)

    return render(request, 'accounts/user_edit.html', {
        'form':    form,
        'target':  target,
        'is_self': is_self,
    })


@editor_required
def user_deactivate_view(request, pk):
    """Toggle the `is_active` flag for a user.

    Editors cannot deactivate their own account. The endpoint expects a
    POST request to perform the state toggle and provides feedback via
    Django messages.
    """

    target = get_object_or_404(CustomUser, pk=pk)
    if target == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:user_detail', pk=pk)
    if request.method == 'POST':
        target.is_active = not target.is_active
        target.save()
        action = 'activated' if target.is_active else 'deactivated'
        user = target.get_full_name() or target.username
        messages.success(
            request, f"Account {action} for {user}."
        )
    return redirect('accounts:user_detail', pk=pk)
