from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from memorials.models import Memorial, Notification, UserProfile
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Send anniversary notifications to premium users'
    
    def handle(self, *args, **kwargs):
        today = date.today()
        self.stdout.write(f"Running anniversary check for {today}")
        
        notifications_sent = 0
        
        # Check next 7 days for anniversaries
        for days_ahead in [1, 7]:  # 1 day before and 7 days before
            check_date = today + timedelta(days=days_ahead)
            
            # Find death anniversaries
            death_anniversaries = Memorial.objects.filter(
                dod__month=check_date.month,
                dod__day=check_date.day
            ).select_related('created_by')
            
            for memorial in death_anniversaries:
                years = check_date.year - memorial.dod.year
                
                # Only notify creator if they're premium
                try:
                    profile = memorial.created_by.userprofile
                    if not profile.is_premium or not profile.enable_anniversary_notifications:
                        continue
                    
                    if not profile.notify_death_anniversaries:
                        continue
                    
                    # Check if we should notify based on timing preference
                    if days_ahead == 7 and not profile.notify_week_before:
                        continue
                    if days_ahead == 1 and not profile.notify_day_before:
                        continue
                    
                    # Check if notification already exists
                    existing = Notification.objects.filter(
                        user=memorial.created_by,
                        notification_type='death_anniversary',
                        related_memorial=memorial,
                        created_at__date=today
                    ).exists()
                    
                    if existing:
                        continue
                    
                    # Create notification
                    timing = "tomorrow" if days_ahead == 1 else "in one week"
                    
                    Notification.objects.create(
                        user=memorial.created_by,
                        notification_type='death_anniversary',
                        title=f"Upcoming Anniversary: {memorial.full_name}",
                        message=f"The {years}-year anniversary of {memorial.full_name}'s passing is {timing} ({check_date.strftime('%B %d, %Y')}).",
                        related_memorial=memorial,
                        action_url=f'/memorial/{memorial.id}/family-tree/',
                    )
                    
                    notifications_sent += 1
                    
                except UserProfile.DoesNotExist:
                    continue
            
            # Find birthdays
            birthdays = Memorial.objects.filter(
                dob__month=check_date.month,
                dob__day=check_date.day
            ).select_related('created_by')
            
            for memorial in birthdays:
                age = check_date.year - memorial.dob.year
                
                try:
                    profile = memorial.created_by.userprofile
                    if not profile.is_premium or not profile.enable_anniversary_notifications:
                        continue
                    
                    if not profile.notify_birthdays:
                        continue
                    
                    if days_ahead == 7 and not profile.notify_week_before:
                        continue
                    if days_ahead == 1 and not profile.notify_day_before:
                        continue
                    
                    existing = Notification.objects.filter(
                        user=memorial.created_by,
                        notification_type='birthday_anniversary',
                        related_memorial=memorial,
                        created_at__date=today
                    ).exists()
                    
                    if existing:
                        continue
                    
                    timing = "tomorrow" if days_ahead == 1 else "in one week"
                    
                    Notification.objects.create(
                        user=memorial.created_by,
                        notification_type='birthday_anniversary',
                        title=f"Birthday Coming: {memorial.full_name}",
                        message=f"{memorial.full_name} would have been {age} years old {timing} ({check_date.strftime('%B %d, %Y')}).",
                        related_memorial=memorial,
                        action_url=f'/memorial/{memorial.id}/family-tree/',
                    )
                    
                    notifications_sent += 1
                    
                except UserProfile.DoesNotExist:
                    continue
        
        self.stdout.write(self.style.SUCCESS(f'Successfully sent {notifications_sent} anniversary notifications'))