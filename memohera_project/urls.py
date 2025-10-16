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
    suggest_relationship,manage_relationship_suggestions,approve_relationship_suggestion,reject_relationship_suggestion
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
    # path('memorial/<int:memorial_id>/add-family/', add_family_relationship, name='add_family_relationship'),
    # path('approve-relationship/<int:relationship_id>/', approve_family_relationship, name='approve_family_relationship'),     

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


    # # Sharing URLs
    # path('share/<uuid:share_token>/', memorial_share, name='memorial_share'),
    # path('api/memorial/<int:memorial_id>/share-links/', get_social_sharing_links, name='get_social_sharing_links'),
    
    # # Premium sharing features
    # path('create-invitation/', create_sharing_invitation, name='create_sharing_invitation'),
    # path('invitation/<uuid:invitation_id>/', memorial_create_via_invitation, name='memorial_create_via_invitation'),
    # path('manage-invitations/', manage_invitations, name='manage_invitations'),    
    path('api/memorial/<int:memorial_id>/share-links/', get_social_sharing_links, name='get_social_sharing_links'),

    path('change-password/', change_password, name='change_password'),
    prefix_default_language=False,  # Don't add /en/ for English URLs
)

