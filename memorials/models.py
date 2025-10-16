from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
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
#####################################################################################
# class FamilyRelationship(models.Model):
#     person_a = models.ForeignKey(Memorial, on_delete=models.CASCADE, related_name='family_relationships_from')
#     person_b = models.ForeignKey(Memorial, on_delete=models.CASCADE, related_name='family_relationships_to')
#     relationship_type = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
#     created_by = models.ForeignKey(User, on_delete=models.CASCADE)
#     status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved')], default='pending')
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         unique_together = ['person_a', 'person_b', 'relationship_type']
        
#     def __str__(self):
#         return f"{self.person_a.full_name} - {self.get_relationship_type_display()} - {self.person_b.full_name}"

#####################################################################################
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
#####################################################################################


# # Add these fields to your Memorial model
# class Memorial(models.Model):
#     # ... your existing fields ...
    
#     # New sharing fields
#     share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
#     is_shareable = models.BooleanField(default=True, help_text="Allow this memorial to be shared publicly")
#     share_count = models.PositiveIntegerField(default=0, help_text="Number of times this memorial has been shared")
    
#     # ... rest of your existing fields ...
    
#     def get_share_url(self):
#         """Get the shareable URL for this memorial"""
#         return reverse('memorial_share', kwargs={'share_token': self.share_token})
    
#     def get_absolute_url(self):
#         """Get the regular URL for this memorial (if you don't have this already)"""
#         return reverse('memorial_detail', kwargs={'pk': self.pk})
    
#     def increment_share_count(self):
#         """Increment the share counter"""
#         self.share_count += 1
#         self.save(update_fields=['share_count'])

#     def __str__(self):
#         return self.full_name    

# New model for premium sharing invitations
# class SharingInvitation(models.Model):
#     INVITATION_TYPES = [
#         ('create', 'Create Memorial'),
#         ('collaborate', 'Collaborate on Memorial'),
#     ]
    
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     created_by = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='sent_invitations')
#     invitation_type = models.CharField(max_length=20, choices=INVITATION_TYPES, default='create')
#     email = models.EmailField(blank=True, help_text="Email of person being invited")
#     message = models.TextField(blank=True, help_text="Personal message from inviter")
#     memorial = models.ForeignKey(Memorial, on_delete=models.CASCADE, null=True, blank=True, 
#                                 help_text="Memorial to collaborate on (if applicable)")
    
#     # Usage tracking
#     is_used = models.BooleanField(default=False)
#     used_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True,
#                                related_name='used_invitations')
#     used_at = models.DateTimeField(null=True, blank=True)
    
#     # Expiry
#     expires_at = models.DateTimeField()
#     is_active = models.BooleanField(default=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         ordering = ['-created_at']
    
#     def __str__(self):
#         return f"Invitation {self.id} - {self.invitation_type} - {self.email or 'No email'}"
    
#     def get_invitation_url(self):
#         """Get the invitation URL"""
#         if self.invitation_type == 'create':
#             return reverse('memorial_create_via_invitation', kwargs={'invitation_id': self.id})
#         else:
#             return reverse('memorial_collaborate', kwargs={'invitation_id': self.id})
    
#     def is_valid(self):
#         """Check if invitation is still valid"""
#         from django.utils import timezone
#         return (
#             self.is_active and 
#             not self.is_used and 
#             self.expires_at > timezone.now()
#         )
    
#     def mark_as_used(self, user):
#         """Mark invitation as used"""
#         from django.utils import timezone
#         self.is_used = True
#         self.used_by = user
#         self.used_at = timezone.now()
#         self.save()
