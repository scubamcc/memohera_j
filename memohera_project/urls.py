"""
URL configuration for memohera_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# Updated memohera_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf.urls.i18n import i18n_patterns
from memorials.views import (
    home, create_memorial, browse_memorials, about, signup, my_memorials, 
    add_family_relationship, approve_family_relationship, logout_view,
    memorial_share, get_social_sharing_links,privacy_policy,change_password,edit_memorial,
    suggest_relationship,manage_relationship_suggestions,approve_relationship_suggestion,
    reject_relationship_suggestion,family_tree_view,notifications_list,mark_notification_read,
    mark_all_notifications_read
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # Language switching URL
    path('i18n/', include('django.conf.urls.i18n')),
]

# URLs that will have language prefixes (like /en/, /es/, /fr/)
urlpatterns += i18n_patterns(
    # Smart home: About for guests, Create for logged-in
    path('', home, name='home'),

    # Core pages
    path('create/', create_memorial, name='create_memorial'),
    path('browse/', browse_memorials, name='browse'),
    path('about/', about, name='about'),
    path('my-memorials/', my_memorials, name='my_memorials'),

    # Auth
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    # path('logout/', auth_views.LogoutView.as_view(next_page='about'), name='logout'),
    path('logout/', logout_view, name='logout'),
    path('signup/', signup, name='signup'),
    path('privacy-policy/', privacy_policy, name='privacy_policy'),
    path('memorial/<int:memorial_id>/edit/', edit_memorial, name='edit_memorial'),
    
    # Relationship suggestion URLs
    path('memorial/<int:memorial_id>/suggest-relationship/', suggest_relationship, name='suggest_relationship'),
    path('relationship-suggestions/', manage_relationship_suggestions, name='manage_relationship_suggestions'),
    path('relationship/<int:relationship_id>/approve/', approve_relationship_suggestion, name='approve_relationship_suggestion'),
    path('relationship/<int:relationship_id>/reject/', reject_relationship_suggestion, name='reject_relationship_suggestion'),
    path('memorial/<int:memorial_id>/family-tree/', family_tree_view, name='family_tree'),

    # Notification URLs
    path('notifications/', notifications_list, name='notifications_list'),
    path('notification/<int:notification_id>/read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='mark_all_notifications_read'),

    # # Sharing URLs
    path('api/memorial/<int:memorial_id>/share-links/', get_social_sharing_links, name='get_social_sharing_links'),

    path('change-password/', change_password, name='change_password'),
    prefix_default_language=False,  # Don't add /en/ for English URLs
)

