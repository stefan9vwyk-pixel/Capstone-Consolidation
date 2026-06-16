from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Articles
    path('articles/', views.article_list_view, name='article_list'),
    path('articles/new/', views.article_create_view, name='article_create'),
    path(
        'articles/approval-queue/',
        views.article_approval_queue_view,
        name='article_approval_queue',
    ),
    path(
        'articles/<int:pk>/',
        views.article_detail_view,
        name='article_detail'
    ),
    path(
        'articles/<int:pk>/edit/',
        views.article_edit_view,
        name='article_edit'
    ),
    path(
        'articles/<int:pk>/delete/',
        views.article_delete_view,
        name='article_delete'
    ),
    path(
        'articles/<int:pk>/approve/',
        views.article_approve_view,
        name='article_approve'
    ),
    path(
        'articles/<int:pk>/approve/confirm/',
        views.article_approve_confirm_view,
        name='article_approve_confirm'
    ),

    # Newsletters
    path('newsletters/', views.newsletter_list_view, name='newsletter_list'),
    path(
        'newsletters/new/',
        views.newsletter_create_view,
        name='newsletter_create'
    ),
    path(
        'newsletters/<int:pk>/',
        views.newsletter_detail_view,
        name='newsletter_detail'
    ),
    path(
        'newsletters/<int:pk>/edit/',
        views.newsletter_edit_view,
        name='newsletter_edit'
    ),
    path(
        'newsletters/<int:pk>/delete/',
        views.newsletter_delete_view,
        name='newsletter_delete'
    ),

    # Publishers
    path('publishers/', views.publisher_list_view, name='publisher_list'),
    path(
        'publishers/<int:pk>/',
        views.publisher_detail_view,
        name='publisher_detail'
    ),
    path(
        'publishers/create/',
        views.publisher_create_view,
        name='publisher_create'
    ),
    path(
        'publishers/<int:pk>/edit/',
        views.publisher_update_view,
        name='publisher_edit'
    ),
    path(
        'publishers/<int:pk>/delete/',
        views.publisher_delete_view,
        name='publisher_delete'
    ),

    # API Docs
    path('api-docs/', views.api_docs_view, name='api_docs'),
]
