"""
URL configuration for memohera_project project.
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from memorials.views_old import (
    home, create_memorial, browse_memorials, about, signup, my_memorials, 
    add_family_relationship, approve_family_relationship, logout_view,
    memorial_share, get_social_sharing_links, privacy_policy, change_password, edit_memorial,
    suggest_relationship, manage_relationship_suggestions, approve_relationship_suggestion,
    reject_relationship_suggestion, family_tree_view, notifications_list, mark_notification_read,
    mark_all_notifications_read, notification_settings, memorial_reminder_settings, upgrade_to_premium,
    smart_match_suggestions, accept_smart_match, dismiss_smart_match, archive_all_smart_matches,
    pricing_page, create_checkout_session, payment_success, subscription_dashboard,
    cancel_subscription,memorial_photo_gallery,upload_memorial_photo,upload_multiple_memorial_photos,
    delete_memorial_photo,update_memorial_photo,reorder_memorial_photos,get_memorial_photos_json
)

from memorials import webhook


urlpatterns = []

# Only expose admin in development/DEBUG mode (not in production for security)
if settings.DEBUG:
    urlpatterns += [
        path('admin/', admin.site.urls),
    ]

# Language switching URL
urlpatterns += [
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

    # Sharing URLs
    path('api/memorial/<int:memorial_id>/share-links/', get_social_sharing_links, name='get_social_sharing_links'),

    # Notification settings URLs
    path('settings/notifications/', notification_settings, name='notification_settings'),
    path('memorial/<int:memorial_id>/reminder-settings/', memorial_reminder_settings, name='memorial_reminder_settings'),
    path('upgrade-premium/', upgrade_to_premium, name='upgrade_to_premium'),

    # Smart matching URLs
    path('smart-matches/', smart_match_suggestions, name='smart_match_suggestions'),
    path('smart-match/accept/<int:my_memorial_id>/<int:suggested_memorial_id>/', accept_smart_match, name='accept_smart_match'),
    path('smart-match/dismiss/<int:my_memorial_id>/<int:suggested_memorial_id>/', dismiss_smart_match, name='dismiss_smart_match'),
    path('smart-match/archive/', archive_all_smart_matches, name='archive_smart_matches'),

    # Premium/Pricing URLs
    path('pricing/', pricing_page, name='pricing_page'),
    path('checkout/<int:package_id>/', create_checkout_session, name='create_checkout'),
    path('premium/success/', payment_success, name='payment_success'),
    path('subscription/dashboard/', subscription_dashboard, name='subscription_dashboard'),
    path('subscription/cancel/', cancel_subscription, name='cancel_subscription'),

    path('change-password/', change_password, name='change_password'),
    
    path('memorial/<int:memorial_id>/photos/', memorial_photo_gallery, name='memorial_photo_gallery'),
    path('memorial/<int:memorial_id>/photo/upload/', upload_memorial_photo, name='upload_memorial_photo'),
    path('memorial/<int:memorial_id>/photos/upload-multiple/', upload_multiple_memorial_photos, name='upload_multiple_photos'),
    
    # Photo management
    path('photo/<int:photo_id>/delete/', delete_memorial_photo, name='delete_memorial_photo'),
    path('photo/<int:photo_id>/update/', update_memorial_photo, name='update_memorial_photo'),
    
    # AJAX/API endpoints
    path('memorial/<int:memorial_id>/photos/reorder/', reorder_memorial_photos, name='reorder_memorial_photos'),
    path('api/memorial/<int:memorial_id>/photos/', get_memorial_photos_json, name='get_memorial_photos_json'),
    prefix_default_language=False,
)

# Stripe webhook (outside of language patterns - webhooks shouldn't have /en/ prefix)
urlpatterns += [
    path('webhook/stripe/', webhook.stripe_webhook, name='stripe_webhook'),
]