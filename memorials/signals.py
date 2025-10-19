# ============================================================================
# signals.py - Auto-trigger matching
# ============================================================================

from django.db.models.signals import post_save
from django.dispatch import receiver
from .tasks import generate_smart_matches_for_memorial

@receiver(post_save, sender=Memorial)
def trigger_smart_matching(sender, instance, created, update_fields, **kwargs):
    """Auto-trigger smart matching when memorial is created/approved"""
    if created and instance.approved:
        generate_smart_matches_for_memorial.delay(instance.id)
    
    if update_fields and 'approved' in update_fields and instance.approved:
        generate_smart_matches_for_memorial.delay(instance.id)