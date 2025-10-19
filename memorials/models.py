from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from cloudinary.models import CloudinaryField
from django_countries.fields import CountryField
import uuid




class Memorial(models.Model):
    full_name = models.CharField(max_length=200, blank=False)
    dob = models.DateField("Date of Birth")
    dod = models.DateField("Date of Death")
    story = models.TextField()
    image_url = CloudinaryField('image', blank=True, null=True)
    country = CountryField()
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memorials')  # New field

    # share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    # is_shareable = models.BooleanField(default=True, help_text="Allow this memorial to be shared publicly")
    # share_count = models.PositiveIntegerField(default=0, help_text="Number of times this memorial has been shared")
   
    # def get_share_url(self):
    #     """Get the shareable URL for this memorial"""
    #     return reverse('memorial_share', kwargs={'share_token': self.share_token})
    # def increment_share_count(self):
    #     """Increment the share counter"""
    #     self.share_count += 1
    #     self.save(update_fields=['share_count'])
    
    def get_absolute_url(self):
        """Get the regular URL for this memorial (if you don't have this already)"""
        return reverse('memorial_detail', kwargs={'pk': self.pk})
    

   
    def clean(self):
        """Validate that death date is not before birth date"""
        super().clean()
        # Validate full_name
        if not self.full_name or not self.full_name.strip():
            raise ValidationError({
                'full_name': 'Full name is required and cannot be empty.'
            })

        if self.dob and self.dod:
            if self.dod < self.dob:
                raise ValidationError({
                    'dod': 'Date of death cannot be before date of birth.'
                })
    def save(self, *args, **kwargs):
        """Clean whitespace and call clean before saving"""
        # Strip whitespace from full_name
        if self.full_name:
            self.full_name = self.full_name.strip()
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approved']),
            models.Index(fields=['created_at']),
            models.Index(fields=['full_name']),
            models.Index(fields=['country']),
            models.Index(fields=['approved', '-created_at']),  # Compound index
        ]

    def __str__(self):
        return f"{self.full_name} (by {self.created_by.username})"
    
# Add this BEFORE the FamilyRelationship class in your models.py

RELATIONSHIP_CHOICES = [
    ('parent', 'Parent'),
    ('child', 'Child'),
    ('spouse', 'Spouse'),
    ('sibling', 'Sibling'),
    ('grandparent', 'Grandparent'),
    ('grandchild', 'Grandchild'),
    ('aunt_uncle', 'Aunt/Uncle'),
    ('niece_nephew', 'Niece/Nephew'),
    ('cousin', 'Cousin'),
]

VERIFICATION_STATUS_CHOICES = [
    ('user_suggested', 'User Suggested'),
    ('creator_verified', 'Creator Verified'),
    ('auto_approved', 'Auto Approved'),
]

class FamilyRelationship(models.Model):
    person_a = models.ForeignKey(Memorial, on_delete=models.CASCADE, related_name='family_relationships_from')
    person_b = models.ForeignKey(Memorial, on_delete=models.CASCADE, related_name='family_relationships_to')
    relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    
    # Who created/suggested this relationship
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_relationships')
    
    # NEW: Who suggested this relationship (might be different from created_by for user suggestions)
    suggested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='suggested_relationships', null=True, blank=True)
    
    # Status for approval workflow
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    
    # NEW: Verification status for trust badges
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='user_suggested')
    
    # Optional note/explanation from suggester
    suggestion_note = models.TextField(blank=True, help_text="Optional explanation for this relationship")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['person_a', 'person_b', 'relationship_type']
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.person_a.full_name} - {self.get_relationship_type_display()} - {self.person_b.full_name}"
    
    def get_reverse_relationship_type(self):
        """Get the reverse relationship type for bidirectional display"""
        reverse_map = {
            'parent': 'child',
            'child': 'parent',
            'spouse': 'spouse',
            'sibling': 'sibling',
            'grandparent': 'grandchild',
            'grandchild': 'grandparent',
            'aunt_uncle': 'niece_nephew',
            'niece_nephew': 'aunt_uncle',
            'cousin': 'cousin',
        }
        return reverse_map.get(self.relationship_type, self.relationship_type)
    
    def can_approve(self, user):
        """Check if user can approve this relationship"""
        # User can approve if they own either memorial
        return (self.person_a.created_by == user or self.person_b.created_by == user)
    
    def approve(self, user):
        """Approve the relationship"""
        if self.can_approve(user):
            self.status = 'approved'
            # If owner approves, mark as creator verified
            if user in [self.person_a.created_by, self.person_b.created_by]:
                self.verification_status = 'creator_verified'
            self.save()
            return True
        return False
    
    def reject(self, user):
        """Reject the relationship"""
        if self.can_approve(user):
            self.status = 'rejected'
            self.save()
            return True
        return False

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    is_premium = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    
    # Anniversary notification settings
    enable_anniversary_notifications = models.BooleanField(default=True)
    notify_death_anniversaries = models.BooleanField(default=True)
    notify_birthdays = models.BooleanField(default=True)
    notify_milestones = models.BooleanField(default=True)
    
    # Timing preferences
    notify_week_before = models.BooleanField(default=True)
    notify_day_before = models.BooleanField(default=True)
    notify_on_day = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} - {'Premium' if self.is_premium else 'Free'}"
    
    @property
    def is_premium_active(self):
        """Check if premium is currently active"""
        if not self.is_premium:
            return False
        if self.premium_until and self.premium_until < timezone.now():
            return False
        return True

class MemorialReminderSettings(models.Model):
    memorial = models.OneToOneField('Memorial', on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # Override global settings
    custom_settings_enabled = models.BooleanField(default=False)
    notify_death_anniversary = models.BooleanField(default=True)
    notify_birthday = models.BooleanField(default=True)
    
    # Who to notify
    notify_creator_only = models.BooleanField(default=True)
    notify_all_family = models.BooleanField(default=False)
    specific_users = models.ManyToManyField(User, blank=True, related_name='memorial_reminders')
    
    # Custom dates
    custom_reminder_date = models.DateField(null=True, blank=True)
    custom_reminder_label = models.CharField(max_length=100, blank=True)

class ScheduledNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    memorial = models.ForeignKey('Memorial', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50)  # 'death_anniversary', 'birthday', etc.
    scheduled_date = models.DateField()
    year_count = models.IntegerField()  # e.g., "5th anniversary"
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('relationship_suggested', 'Relationship Suggested'),
        ('relationship_approved', 'Relationship Approved'),
        ('relationship_rejected', 'Relationship Rejected'),
        ('new_family_member', 'New Family Member'),
        ('death_anniversary', 'Death Anniversary'),  # ADD
        ('birthday_anniversary', 'Birthday Anniversary'),  # ADD        
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Optional: Link to related objects
    related_memorial = models.ForeignKey('Memorial', on_delete=models.CASCADE, null=True, blank=True)
    related_relationship = models.ForeignKey('FamilyRelationship', on_delete=models.CASCADE, null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications_from')
    
    # URL to navigate to when clicked
    action_url = models.CharField(max_length=500, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

class SmartMatchSuggestion(models.Model):
    """Tracks AI-generated family relationship suggestions"""
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('dismissed', 'Dismissed'),
        ('archived', 'Archived'),
    ]
    
    my_memorial = models.ForeignKey(
        Memorial,
        on_delete=models.CASCADE,
        related_name='smart_suggestions_for'
    )
    suggested_memorial = models.ForeignKey(
        Memorial,
        on_delete=models.CASCADE,
        related_name='smart_suggestions_by'
    )
    confidence_score = models.IntegerField(default=0)  # 0-100
    match_reasons = models.JSONField(default=list)  # Store reasons for match
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    user_notified = models.BooleanField(default=False)
    notification_sent_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('my_memorial', 'suggested_memorial')
        ordering = ['-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['my_memorial', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Match: {self.my_memorial.full_name} ↔ {self.suggested_memorial.full_name} ({self.confidence_score}%)"



