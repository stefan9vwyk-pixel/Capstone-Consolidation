"""Views for user accounts: registration, authentication, profiles.

This module contains simple Django view functions used by the
`accounts` app. Each view handles request/response logic and uses
Django forms and messages for user feedback.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm, LoginForm, ProfileForm
from .models import CustomUser
from news.models import Publisher


# ------- Register user ----------
def register_view(request):
    """Handle user registration.

    - Redirect authenticated users to the dashboard.
    - On POST, validate `RegisterForm`, create the user, log them in,
      show a success message and redirect to the dashboard.

    Args:
        request: Django HttpRequest

    Returns:
        HttpResponse: render of registration page or redirect on success.
    """
    # Prevent already-authenticated users from re-registering
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the new user in immediately after successful registration
            login(request, user)
            messages.success(
                request,
                f'Welcome, {user.get_full_name() or user.username}! '
                'Your account has been created.'
            )
            return redirect('news:dashboard')
    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {'form': form})


# ------- Login section ---------
def login_view(request):
    """Authenticate and log a user in.

    - Redirect authenticated users to the dashboard.
    - On POST, validate `LoginForm`, log the user in and redirect to
      `next` parameter if provided, otherwise to the dashboard.

    Args:
        request: Django HttpRequest

    Returns:
        HttpResponse: render of login page or redirect on success.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(
                request,
                f'Welcome back, {user.get_full_name() or user.username}!'
            )
            # Honor next parameter for redirects after login
            next_url = request.GET.get('next', 'news:dashboard')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Log the current user out and redirect to the login page.

    Args:
        request: Django HttpRequest

    Returns:
        HttpResponseRedirect: redirect to the login page.
    """
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


# --------- Accounts views -----------
@login_required
def profile_view(request):
    """Display and update the authenticated user's profile.

    Uses `ProfileForm` bound to `request.user`. On successful POST the
    profile is saved and the user is redirected back to the profile page.

    Args:
        request: Django HttpRequest

    Returns:
        HttpResponse: render of profile page.
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


def journalist_list_view(request):
    """List all users that have the `journalist` role.

    The view orders journalists by last name and renders a simple list
    template.

    Args:
        request: Django HttpRequest

    Returns:
        HttpResponse: rendered list of journalists.
    """
    # Fetch only users with the 'journalist' role
    journalists = CustomUser.objects.filter(
        role='journalist'
    ).order_by('last_name')

    return render(request, 'accounts/journalist_list.html', {
        'journalists': journalists,
    })


def journalist_public_profile(request, pk):
    """Show a public profile for a journalist.

    - If the requested profile belongs to the currently authenticated
      journalist, redirect them to their editable `profile` page.
    - Otherwise, show the journalist's public information and a list
      of their approved articles (limited to 10 most recent).

    Args:
        request: Django HttpRequest
        pk: int - primary key of the `CustomUser` with role 'journalist'

    Returns:
        HttpResponse: rendered public profile page.
    """
    journalist = get_object_or_404(CustomUser, pk=pk, role='journalist')

    # Redirect to edit page if the journalist is viewing their own profile
    if request.user.is_authenticated and request.user.pk == journalist.pk:
        return redirect('accounts:profile')

    # Fetch the journalist's approved articles via a related manager
    articles = journalist.journalist_articles.filter(approved=True)[:10]

    return render(request, 'accounts/journalist_public_profile.html', {
        'journalist': journalist,
        'articles': articles,
    })


# ------ Subscriptions -----------
@login_required
def toggle_subscription(request, target_type, target_id):
    """Toggle subscription for the authenticated reader.

    Readers can subscribe/unsubscribe to journalists or publishers.

    Args:
        request: Django HttpRequest
        target_type: str - either 'journalist' or 'publisher'
        target_id: int - primary key of the target object

    Returns:
        HttpResponseRedirect: redirect back to the referring page or
        dashboard if no referrer is present.
    """
    # Only readers should be allowed to subscribe
    if not request.user.is_reader:
        return redirect('news:dashboard')

    if target_type == 'journalist':
        # Ensure target is an actual journalist user
        target = get_object_or_404(CustomUser, id=target_id, role='journalist')
        if target in request.user.subscribed_journalists.all():
            request.user.subscribed_journalists.remove(target)
        else:
            request.user.subscribed_journalists.add(target)

    elif target_type == 'publisher':
        # Target is a Publisher instance
        target = get_object_or_404(Publisher, id=target_id)
        if target in request.user.subscribed_publishers.all():
            request.user.subscribed_publishers.remove(target)
        else:
            request.user.subscribed_publishers.add(target)

    # Redirect back to where the user came from
    return redirect(request.META.get('HTTP_REFERER', 'news:dashboard'))
