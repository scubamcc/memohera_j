# memorials/context_processors.py

from django.conf import settings
from django.utils.translation import get_language
from .models import FamilyRelationship, Notification
from django.db.models import Q
from memorials.models import SmartMatchSuggestion


def pending_suggestions_count(request):
    """Add pending suggestions count to all templates"""
    if request.user.is_authenticated:
        count = FamilyRelationship.objects.filter(
            status='pending'
        ).filter(
            Q(person_a__created_by=request.user) | Q(person_b__created_by=request.user)
        ).count()
        return {'pending_suggestions_count': count}
    return {'pending_suggestions_count': 0}

def language_context(request):
    """
    Context processor to provide language information to all templates
    """
    current_language = get_language()
    
    # Custom language code display mapping (remove country references)
    LANGUAGE_CODE_DISPLAY = {
        'en': 'EN',
        'zh-cn': 'CN', 
        'es': 'ES',
        'ar': 'AR',
        'fr': 'FR',
        'de': 'DE',
        'pt': 'BR',  # Keep BR for Brazilian Portuguese to distinguish from European Portuguese
        'ru': 'RU',
        'ja': 'JA',
        'hi': 'HI',
        'el': 'EL',  # Greek
    }
    
    # Get language display info
    languages_with_flags = []
    for code, name in settings.LANGUAGES:
        languages_with_flags.append({
            'code': code,
            'name': name,
            'display_code': LANGUAGE_CODE_DISPLAY.get(code, code.upper()),
            'flag': settings.LANGUAGE_FLAGS.get(code, '🏳️'),
            'is_current': code == current_language,
        })
    
    return {
        'LANGUAGES_WITH_FLAGS': languages_with_flags,
        'CURRENT_LANGUAGE': current_language,
        'CURRENT_LANGUAGE_CODE': LANGUAGE_CODE_DISPLAY.get(current_language, current_language.upper()),
        'CURRENT_LANGUAGE_FLAG': settings.LANGUAGE_FLAGS.get(current_language, '🏳️'),
    }


def pending_suggestions_count(request):
    """Add pending suggestions and notifications count to all templates"""
    if request.user.is_authenticated:
        # Pending relationship suggestions
        suggestions_count = FamilyRelationship.objects.filter(
            status='pending'
        ).filter(
            Q(person_a__created_by=request.user) | Q(person_b__created_by=request.user)
        ).count()
        
        # Unread notifications
        notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return {
            'pending_suggestions_count': suggestions_count,
            'unread_notifications_count': notifications_count
        }
    
    return {
        'pending_suggestions_count': 0,
        'unread_notifications_count': 0
    }

def smart_matches(request):
    """Make smart matches available in all templates"""
    return get_smart_matches_context(request)

def smart_matches_context(request):
    """Make smart matches available in all templates"""
    if request.user.is_authenticated:
        unreviewed = SmartMatchSuggestion.objects.filter(
            my_memorial__created_by=request.user,
            status='pending'
        ).count()
        return {'unreviewed_matches': unreviewed}
    return {'unreviewed_matches': 0}
