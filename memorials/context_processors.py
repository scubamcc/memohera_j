# memorials/context_processors.py

from django.conf import settings
from django.utils.translation import get_language

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