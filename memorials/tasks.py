# ============================================================================
# tasks.py - Celery tasks for background matching
# ============================================================================

from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task
def generate_smart_matches_for_memorial(memorial_id):
    """Generate smart match suggestions for a memorial"""
    try:
        memorial = Memorial.objects.get(id=memorial_id, approved=True)
        matches = find_potential_matches(memorial, limit=5)
        
        notifications_to_send = []
        
        for match_data in matches:
            suggestion, created = SmartMatchSuggestion.objects.get_or_create(
                my_memorial=memorial,
                suggested_memorial=match_data['memorial'],
                defaults={
                    'confidence_score': match_data['score'],
                    'match_reasons': match_data['reasons']
                }
            )
            
            if created:
                notifications_to_send.append(suggestion)
        
        if notifications_to_send:
            send_match_notifications.delay([s.id for s in notifications_to_send])
        
        logger.info(f"Generated {len(matches)} smart matches for memorial {memorial_id}")
        
    except Memorial.DoesNotExist:
        logger.error(f"Memorial {memorial_id} not found")
    except Exception as e:
        logger.error(f"Error generating smart matches: {str(e)}")


@shared_task
def send_match_notifications(suggestion_ids):
    """Send batched email notifications for new matches"""
    suggestions = SmartMatchSuggestion.objects.filter(
        id__in=suggestion_ids,
        user_notified=False
    ).select_related('my_memorial', 'suggested_memorial', 'my_memorial__created_by')
    
    notifications_by_user = {}
    
    for suggestion in suggestions:
        user = suggestion.my_memorial.created_by
        if user not in notifications_by_user:
            notifications_by_user[user] = []
        notifications_by_user[user].append(suggestion)
    
    for user, user_suggestions in notifications_by_user.items():
        try:
            send_smart_match_email(user, user_suggestions)
            
            for suggestion in user_suggestions:
                suggestion.user_notified = True
                suggestion.notification_sent_at = timezone.now()
                suggestion.save()
                
        except Exception as e:
            logger.error(f"Error sending notification to {user.email}: {str(e)}")


def send_smart_match_email(user, suggestions):
    """Send email notification about smart matches"""
    subject = f"🔍 {len(suggestions)} New Family Connection(s) Found!"
    
    context = {
        'user': user,
        'suggestions': suggestions,
        'total_matches': len(suggestions),
    }
    
    html_message = render_to_string('notifications/smart_match_email.html', context)
    text_message = render_to_string('notifications/smart_match_email.txt', context)
    
    send_mail(
        subject,
        text_message,
        'noreply@memorialheritage.com',
        [user.email],
        html_message=html_message,
        fail_silently=False,
    )
