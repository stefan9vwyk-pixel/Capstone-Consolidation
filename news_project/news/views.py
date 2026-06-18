from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count, Q

from .models import Article, Newsletter, Publisher
from .forms import ArticleForm, NewsletterForm, PublisherForm
from .filters import apply_article_filters
from accounts.models import CustomUser
from accounts.decorators import editor_required


# ── Dashboard ───────────────────────────────────────────────────────────────

def dashboard_view(request):
    """
    Render the news dashboard with recent content and user-specific metrics.
    """
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    recent_articles = Article.objects.select_related(
        'author',
        'publisher'
    ).order_by('-created_at')[:5]

    recent_newsletters = Newsletter.objects.select_related(
        'author'
    ).order_by('-created_at')[:3]

    stats = {
        'total_articles': Article.objects.count(),
        'approved_articles': Article.objects.filter(approved=True).count(),
        'pending_articles': Article.objects.filter(approved=False).count(),
        'total_newsletters': Newsletter.objects.count(),
        'total_publishers': Publisher.objects.count(),
    }
    if request.user.is_journalist:
        stats['my_articles'] = Article.objects.filter(
            author=request.user
        ).count()

        stats['my_newsletters'] = Newsletter.objects.filter(
            author=request.user
        ).count()

    return render(request, 'news/dashboard.html', {
        'recent_articles': recent_articles,
        'recent_newsletters': recent_newsletters,
        'stats': stats,
    })


# ── Articles ────────────────────────────────────────────────────────────────

@login_required
def article_list_view(request):
    """
    Display a paginated, filterable list of articles for authorized users.
    """
    base_qs = Article.objects.select_related(
        'author',
        'publisher'
    ).order_by('-created_at')

    queryset, active_filters = apply_article_filters(
        base_qs,
        request.GET,
        user=request.user
    )

    total_count = queryset.count()
    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    def remove_filter_url(key):
        params = request.GET.copy()
        params.pop(key, None)
        params['page'] = 1
        return '?' + params.urlencode()

    filter_chips = []
    label_map = {
        'q': 'Search', 'status': 'Status', 'publisher': 'Publisher',
        'author': 'Author', 'date_from': 'From', 'date_to': 'To',
    }
    for key, value in active_filters.items():
        filter_chips.append({
            'key': key, 'label': label_map.get(key, key.title()),
            'value': value, 'remove_url': remove_filter_url(key),
        })

    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    filter_query_string = filter_params.urlencode()
    authors = CustomUser.objects.filter(
        role__in=['journalist', 'editor']
    ).order_by('last_name', 'first_name')

    publishers = Publisher.objects.order_by('name')
    page_range = paginator.get_elided_page_range(
        page_obj.number,
        on_each_side=2,
        on_ends=1
    )

    return render(request, 'news/article_list.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'active_filters': active_filters,
        'filter_chips': filter_chips,
        'filter_query_string': filter_query_string,
        'page_range': page_range,
        'authors': authors,
        'publishers': publishers,
        'current_q': request.GET.get('q', ''),
        'current_status': request.GET.get('status', ''),
        'current_publisher': request.GET.get('publisher', ''),
        'current_author': request.GET.get('author', ''),
        'current_date_from': request.GET.get('date_from', ''),
        'current_date_to': request.GET.get('date_to', ''),
        'current_sort': request.GET.get('sort', 'date'),
        'current_order': request.GET.get('order', 'desc'),
    })


@login_required
def article_detail_view(request, pk):
    """Render a single article detail page, enforcing reader access rules."""
    article = get_object_or_404(Article, pk=pk)
    if request.user.is_reader and not article.approved:
        messages.error(request, 'This article is not yet available.')
        return redirect('news:article_list')
    return render(request, 'news/article_detail.html', {
        'article': article,
        'can_edit': request.user.can_create_content and (
            request.user == article.author or request.user.is_editor),
        'can_approve': request.user.is_editor,
        'can_delete': request.user == article.author or request.user.is_editor,
    })


@login_required
def article_create_view(request):
    """Handle article creation and redirect to the new article detail view."""
    if not request.user.can_create_content:
        messages.error(
            request,
            'You do not have permission to create articles.'
        )
        return redirect('news:article_list')
    if request.method == 'POST':
        form = ArticleForm(request.POST, user=request.user)
        if form.is_valid():
            article = form.save()
            messages.success(
                request,
                f'Article "{article.title}" created successfully.'
            )
            return redirect('news:article_detail', pk=article.pk)
    else:
        form = ArticleForm(user=request.user)
    return render(
        request,
        'news/article_form.html',
        {'form': form, 'action': 'Create'}
    )


@login_required
def article_edit_view(request, pk):
    """Handle editing an existing article when the user has permission."""
    article = get_object_or_404(Article, pk=pk)
    if not (request.user.can_create_content and (
            request.user == article.author or request.user.is_editor)):
        messages.error(
            request,
            'You do not have permission to edit this article.'
        )
        return redirect('news:article_detail', pk=pk)
    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article, user=request.user)
        if form.is_valid():
            article = form.save()
            messages.success(request, 'Article updated successfully.')
            return redirect('news:article_detail', pk=article.pk)
    else:
        form = ArticleForm(instance=article, user=request.user)
    return render(
        request,
        'news/article_form.html',
        {'form': form, 'article': article, 'action': 'Update'}
    )


@login_required
def article_delete_view(request, pk):
    """Confirm and delete an article if the current user is authorized."""
    article = get_object_or_404(Article, pk=pk)
    if not (request.user == article.author or request.user.is_editor):
        messages.error(
            request,
            'You do not have permission to delete this article.'
        )

        return redirect('news:article_detail', pk=pk)
    if request.method == 'POST':
        title = article.title
        article.delete()
        messages.success(request, f'Article "{title}" deleted.')
        return redirect('news:article_list')
    return render(
        request,
        'news/article_confirm_delete.html', {'article': article}
    )


@login_required
def article_approve_view(request, pk):
    """Toggle approval on a single article. Editors only."""
    if not request.user.is_editor:
        messages.error(request, 'Only editors can approve articles.')
        return redirect('news:article_detail', pk=pk)

    article = get_object_or_404(Article, pk=pk)

    if request.method == 'POST':
        was_approved = article.approved
        article.approved = not article.approved

        # Set sentinel flag so the signal handler
        # Knows this was an intentional approval
        if article.approved and not was_approved:
            article._approval_just_toggled = True

        article.save()
        action_label = 'approved' if article.approved else 'unapproved'
        messages.success(
            request,
            f'Article "{article.title}" has been {action_label}.'
        )

        # Redirect back to the queue if coming from there
        next_url = request.POST.get('next', '')
        if next_url == 'queue':
            return redirect('news:article_approval_queue')
        return redirect('news:article_detail', pk=pk)

    return redirect('news:article_detail', pk=pk)


# ── Approval Queue (Editor only) ────────────────────────────────────────────

@editor_required
def article_approval_queue_view(request):
    """
    Displays all pending (unapproved) articles for editorial review.
    Restricted to users with the Editor role or Editor group membership.
    """
    sort = request.GET.get('sort', 'oldest')
    order = '-created_at' if sort == 'newest' else 'created_at'

    pending_qs = (
        Article.objects
        .filter(approved=False)
        .select_related('author', 'publisher')
        .order_by(order)
    )

    # Optional search within the queue
    q = request.GET.get('q', '').strip()
    if q:
        from django.db.models import Q
        pending_qs = pending_qs.filter(
            Q(title__icontains=q) |
            Q(author__first_name__icontains=q) |
            Q(author__last_name__icontains=q) |
            Q(publisher__name__icontains=q)
        )

    total_pending = pending_qs.count()
    paginator = Paginator(pending_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    page_range = paginator.get_elided_page_range(
        page_obj.number,
        on_each_side=2,
        on_ends=1
    )

    # Count of articles approved today for the stats strip
    today = timezone.now().date()
    approved_today = Article.objects.filter(
        approved=True,
        updated_at__date=today
    ).count()

    return render(request, 'news/article_approval_queue.html', {
        'page_obj': page_obj,
        'total_pending': total_pending,
        'approved_today': approved_today,
        'sort': sort,
        'q': q,
        'page_range': page_range,
    })


@editor_required
def article_approve_confirm_view(request, pk):
    """
    Confirmation page before approving an article.
    Shows article metadata and a content preview.
    """
    article = get_object_or_404(Article, pk=pk)

    if article.approved:
        messages.info(request, f'"{article.title}" is already approved.')
        return redirect('news:article_approval_queue')

    return render(request, 'news/article_approve_confirm.html', {
        'article': article,
    })


# ── Newsletters ─────────────────────────────────────────────────────────────

@login_required
def newsletter_list_view(request):
    """Render a searchable, paginated list of newsletters."""
    from django.db.models import Q
    newsletters = Newsletter.objects.select_related(
        'author'
    ).prefetch_related('articles').order_by('-created_at')
    query = request.GET.get('q', '').strip()
    if query:
        newsletters = newsletters.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(author__first_name__icontains=query) |
            Q(author__last_name__icontains=query)
        )
    total_count = newsletters.count()
    paginator = Paginator(newsletters, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    filter_params = request.GET.copy()
    filter_params.pop('page', None)
    return render(request, 'news/newsletter_list.html', {
        'page_obj': page_obj,
        'total_count': total_count,
        'query': query,
        'filter_query_string': filter_params.urlencode(),
        'page_range': paginator.get_elided_page_range(
            page_obj.number,
            on_each_side=2,
            on_ends=1
        ),
    })


@login_required
def newsletter_detail_view(request, pk):
    """Show details for a newsletter and whether the user may edit it."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    return render(request, 'news/newsletter_detail.html', {
        'newsletter': newsletter,
        'can_edit': request.user.can_create_content and (
            request.user == newsletter.author or request.user.is_editor
        ),
        'can_delete': (
            request.user == newsletter.author or request.user.is_editor
        ),
    })


@login_required
def newsletter_create_view(request):
    """
    Handle newsletter creation and redirect to the new newsletter detail view.
    """
    if not request.user.can_create_content:
        messages.error(
            request,
            'You do not have permission to create newsletters.'
        )
        return redirect('news:newsletter_list')
    if request.method == 'POST':
        form = NewsletterForm(request.POST, user=request.user)
        if form.is_valid():
            newsletter = form.save()
            messages.success(
                request,
                f'Newsletter "{newsletter.title}" created.'
            )
            return redirect('news:newsletter_detail', pk=newsletter.pk)
    else:
        form = NewsletterForm(user=request.user)
    return render(
        request,
        'news/newsletter_form.html',
        {'form': form, 'action': 'Create'}
    )


@login_required
def newsletter_edit_view(request, pk):
    """Handle editing an existing newsletter when the user is authorized."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    if not (request.user.can_create_content and (
            request.user == newsletter.author or request.user.is_editor)):
        messages.error(
            request,
            'You do not have permission to edit this newsletter.'
        )
        return redirect('news:newsletter_detail', pk=pk)
    if request.method == 'POST':
        form = NewsletterForm(
            request.POST,
            instance=newsletter,
            user=request.user,
            is_edit=True
        )
        if form.is_valid():
            newsletter = form.save()
            messages.success(request, 'Newsletter updated.')
            return redirect('news:newsletter_detail', pk=newsletter.pk)
    else:
        form = NewsletterForm(instance=newsletter, user=request.user)
    return render(request, 'news/newsletter_form.html', {
        'form': form, 'newsletter': newsletter, 'action': 'Update',
    })


@login_required
def newsletter_delete_view(request, pk):
    """Confirm and delete a newsletter when the current user may do so."""
    newsletter = get_object_or_404(Newsletter, pk=pk)
    if not (request.user == newsletter.author or request.user.is_editor):
        messages.error(
            request,
            'You do not have permission to delete this newsletter.'
        )
        return redirect('news:newsletter_detail', pk=pk)
    if request.method == 'POST':
        title = newsletter.title
        newsletter.delete()
        messages.success(request, f'Newsletter "{title}" deleted.')
        return redirect('news:newsletter_list')
    return render(
        request,
        'news/newsletter_confirm_delete.html',
        {'newsletter': newsletter}
    )


# ── Publishers ──────────────────────────────────────────────────────────────

@editor_required  # Reuses your clean decorator!
def publisher_create_view(request):
    """Handles creating a brand new publisher profile."""
    if request.method == 'POST':
        form = PublisherForm(request.POST)
        if form.is_valid():
            publisher = form.save()
            messages.success(
                request,
                f"Publisher '{publisher.name}' created successfully!"
            )
            return redirect('news:publisher_detail', pk=publisher.pk)

    else:
        form = PublisherForm()

    return render(request, 'news/publisher_form.html', {'form': form})


@editor_required
def publisher_update_view(request, pk):
    """Handles editing an existing publisher profile."""
    publisher = get_object_or_404(Publisher, pk=pk)
    if request.method == 'POST':
        form = PublisherForm(request.POST, instance=publisher)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                f"Publisher '{publisher.name}' updated successfully!"
            )
            return redirect('news:publisher_detail', pk=publisher.pk)

    else:
        form = PublisherForm(instance=publisher)

    return render(
        request,
        'news/publisher_form.html',
        {'form': form, 'instance': publisher, 'action': 'Update'}
    )


@editor_required
def publisher_delete_view(request, pk):
    """Handles the safe deletion of a publisher network node."""
    publisher = get_object_or_404(Publisher, pk=pk)

    if request.method == 'POST':
        publisher_name = publisher.name
        publisher.delete()
        messages.success(
            request,
            f"Publisher Network '{publisher_name}' was permanently deleted."
        )
        return redirect('news:publisher_list')

    # If it's a GET request, show a nice confirmation page
    return render(
        request,
        'news/publisher_confirm_delete.html',
        {'publisher': publisher}
    )


@login_required
def publisher_list_view(request):
    """Render a list of publishers including approved article counts."""
    publishers = Publisher.objects.prefetch_related(
        'editors',
        'journalists',
        'articles'
    ).annotate(
        total_articles_count=Count(
            'articles',
            filter=Q(articles__approved=True)
        )
    ).order_by('name')

    return render(
        request,
        'news/publisher_list.html',
        {'publishers': publishers}
    )


@login_required
def publisher_detail_view(request, pk):
    """Show a publisher with its articles, hiding drafts from readers."""
    publisher = get_object_or_404(Publisher, pk=pk)
    articles = publisher.articles.select_related(
        'author'
    ).order_by('-created_at')
    if request.user.is_reader:
        articles = articles.filter(approved=True)
    return render(request, 'news/publisher_detail.html', {
        'publisher': publisher,
        'articles': articles,
    })


# ── API Docs ────────────────────────────────────────────────────────────────

@login_required
def api_docs_view(request):
    """Render the API documentation page for authenticated users."""
    return render(request, 'news/api_docs.html')
