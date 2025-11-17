from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from cloudinary.models import CloudinaryField
from django_countries.fields import CountryField
import uuid
from datetime import timedelta




class MemorialPhoto(models.Model):
    """
    Model for storing multiple photos for a memorial.
    Premium users can upload multiple photos, free users limited to 1.
    """
    memorial = models.ForeignKey(
        'Memorial', 
        on_delete=models.CASCADE, 
        related_name='photos'
    )
    photo = CloudinaryField('image')  # Like your Memorial model
    # photo = models.ImageField(
    #     upload_to='memorial_photos/%Y/%m/%d/',
    #     help_text='Upload high-quality memorial photos'
    # )
    caption = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text='Optional caption for this photo'
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text='Alternative text for accessibility'
    )
    is_primary = models.BooleanField(
        default=False,
        help_text='Display this as the main memorial photo'
    )
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_memorial_photos'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(
        default=0,
        help_text='Display order in gallery (lower numbers first)'
    )
    
    class Meta:
        ordering = ['order', '-uploaded_at']
        verbose_name = 'Memorial Photo'
        verbose_name_plural = 'Memorial Photos'
        
        constraints = [
            models.UniqueConstraint(
                fields=['memorial', 'is_primary'],
                condition=models.Q(is_primary=True),
                name='unique_memorial_primary_photo'
            )
        ]
    
    def __str__(self):
        return f"Photo for {self.memorial.full_name} - {self.uploaded_at.strftime('%Y-%m-%d')}"
    
    def clean(self):
        # Validate file size (max 10MB)
        if self.photo:
            file_size = self.photo.size
            limit_mb = 10
            if file_size > limit_mb * 1024 * 1024:
                raise ValidationError(f'Max file size is {limit_mb}MB')
    
    def save(self, *args, **kwargs):
        self.clean()
        
        # If this is set as primary, remove primary status from other photos
        if self.is_primary:
            MemorialPhoto.objects.filter(
                memorial=self.memorial,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return self.photo.url


class PremiumPackage(models.Model):
    """Premium subscription tiers"""
    TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('premium', 'Premium'),
    ]
    
    name = models.CharField(max_length=50)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Features
    smart_matches_enabled = models.BooleanField(default=False)
    anniversary_notifications = models.BooleanField(default=False)
    family_tree_advanced = models.BooleanField(default=False)
    storage_gb = models.IntegerField(default=1)
    
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['display_order']
    
    def __str__(self):
        return f"{self.name} (${self.price})"


class UserSubscription(models.Model):
    """Track user's premium subscriptions"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
        ('pending', 'Pending'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    package = models.ForeignKey(PremiumPackage, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stripe info
    stripe_customer_id = models.CharField(max_length=255, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, blank=True)
    stripe_payment_method_id = models.CharField(max_length=255, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def is_active_subscription(self):
        """Check if subscription is currently active"""
        if self.status != 'active':
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True
    
    def days_until_expiry(self):
        """Days remaining on subscription"""
        if not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return max(0, delta.days)
    
    class Meta:
        verbose_name_plural = "User Subscriptions"
    
    def __str__(self):
        return f"{self.user.username} - {self.package.name if self.package else 'No Package'}"


class PaymentTransaction(models.Model):
    """Track all payment transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Stripe info
    stripe_payment_intent_id = models.CharField(max_length=255, unique=True)
    stripe_charge_id = models.CharField(max_length=255, blank=True)
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"${self.amount} - {self.user.username} - {self.status}"

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
    
    def get_max_photos(self):
        """
        Get maximum number of photos allowed based on subscription status
        Free users: 1 photo
        Premium users: unlimited (10 for practical purposes)
        """
        try:
            subscription = UserSubscription.objects.filter(
                user=self.created_by,
                status='active'
            ).first()
            
            if subscription:
                return 100  # Premium unlimited
            else:
                return 1  # Free tier: 1 photo
        except:
            return 1

    def get_photo_count(self):
        """Get current number of photos for this memorial"""
        return self.photos.count()

    def can_add_photo(self):
        """Check if user can add more photos"""
        current_count = self.get_photo_count()
        max_allowed = self.get_max_photos()
        return current_count < max_allowed

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
        dob_str = self.dob.strftime('%b %d, %Y') if self.dob else '?'
        dod_str = self.dod.strftime('%b %d, %Y') if self.dod else '?'
        return f"{self.full_name} ({dob_str} – {dod_str})"
    
    def get_primary_photo(self):
        '''Get the primary photo, or first uploaded if none marked as primary'''
        primary = self.photos.filter(is_primary=True).first()
        if primary:
            return primary
        return self.photos.first()
    
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