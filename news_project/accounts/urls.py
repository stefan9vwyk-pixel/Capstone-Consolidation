from django.urls import path
from . import views, management_views

app_name = 'accounts'

urlpatterns = [
    # Registration url
    path('register/', views.register_view, name='register'),

    # Login url
    path('login/', views.login_view, name='login'),

    # Logout url
    path('logout/', views.logout_view, name='logout'),

    # Profile url, for users to view and edit their profiles
    path('profile/', views.profile_view, name='profile'),

    # Journalist list url
    path('journalists/', views.journalist_list_view, name='journalist_list'),
    path(
        'journalist/<int:pk>/',
        views.journalist_public_profile,
        name='journalist_public_profile'
    ),
    path(
        'subscribe/<str:target_type>/<int:target_id>/',
        views.toggle_subscription,
        name='toggle_subscription'
    ),

    # Editorial management system
    path(
        'management/users/',
        management_views.user_list_view,
        name='user_list'
    ),

    path(
        'management/users/new/',
        management_views.user_create_view,
        name='user_create'
    ),

    path(
        'management/users/<int:pk>/',
        management_views.user_detail_view,
        name='user_detail'
    ),

    path(
        'management/users/<int:pk>/edit/',
        management_views.user_edit_view,
        name='user_edit'
    ),

    path(
        'management/users/<int:pk>/deactivate/',
        management_views.user_deactivate_view,
        name='user_deactivate'
    ),
]
