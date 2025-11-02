# -*- coding: utf-8 -*-
from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import Memorial, FamilyRelationship, UserProfile, MemorialReminderSettings, RELATIONSHIP_CHOICES
import datetime
from django.forms import modelformset_factory, inlineformset_factory
from .models import MemorialPhoto, Memorial
from django.core.exceptions import ValidationError
from PIL import Image
from io import BytesIO


class MemorialPhotoForm(forms.ModelForm):
    """
    Form for uploading a single memorial photo
    """
    class Meta:
        model = MemorialPhoto
        fields = ['photo', 'caption', 'alt_text', 'is_primary']
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
                'data-max-file-size': '10485760',  # 10MB in bytes
            }),
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Add a caption for this photo (optional)',
                'maxlength': '500',
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Describe the image for accessibility (optional)',
                'maxlength': '200',
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'photo': 'Photo',
            'caption': 'Photo Caption',
            'alt_text': 'Alternative Text (for accessibility)',
            'is_primary': 'Set as primary memorial photo',
        }
    
    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        
        if photo:
            # Check file size (max 10MB)
            if photo.size > 10 * 1024 * 1024:
                raise ValidationError('Photo size must not exceed 10MB')
            
            # Check file type
            allowed_formats = ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']
            try:
                img = Image.open(photo)
                if img.format and img.format.upper() not in allowed_formats:
                    raise ValidationError(f'File format must be one of: {", ".join(allowed_formats)}')
            except Exception as e:
                raise ValidationError('Invalid image file')
        
        return photo


class MultipleMemorialPhotosForm(forms.Form):
    """
    Form for uploading multiple photos at once
    """
    photos = forms.FileField(
        label='Select Photos',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*',
        }),
        help_text='Select one or more images. Max 10MB each, formats: JPEG, PNG, GIF, WebP'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add multiple attribute to the widget after initialization
        self.fields['photos'].widget.attrs['multiple'] = True
    
    def clean_photos(self):
        photos = self.files.getlist('photos')
        
        if not photos:
            raise ValidationError('Please select at least one photo')
        
        allowed_formats = ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']
        
        for photo in photos:
            # Check file size
            if photo.size > 10 * 1024 * 1024:
                raise ValidationError(f'File "{photo.name}" exceeds 10MB limit')
            
            # Check file type
            try:
                img = Image.open(photo)
                if img.format and img.format.upper() not in allowed_formats:
                    raise ValidationError(
                        f'File "{photo.name}" has unsupported format. '
                        f'Allowed: {", ".join(allowed_formats)}'
                    )
            except ValidationError:
                raise
            except Exception:
                raise ValidationError(f'File "{photo.name}" is not a valid image')
        
        return photos


# Formset for managing multiple photos
MemorialPhotoFormSet = inlineformset_factory(
    Memorial,
    MemorialPhoto,
    form=MemorialPhotoForm,
    extra=3,  # Show 3 empty forms for new photos
    max_num=100,  # Max 100 photos per memorial
    can_delete=True,
)


class MemorialPhotoUpdateForm(forms.ModelForm):
    """
    Form for updating photo details (caption, alt text, primary status)
    """
    class Meta:
        model = MemorialPhoto
        fields = ['caption', 'alt_text', 'is_primary', 'order']
        widgets = {
            'caption': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': '500',
            }),
            'alt_text': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '200',
            }),
            'is_primary': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
            }),
        }


class MemorialEditWithPhotosForm(forms.ModelForm):
    """
    Extended memorial form that includes photo management
    Use this when editing a memorial with photo gallery
    """
    class Meta:
        model = Memorial
        fields = [
            'full_name', 'dob', 'dod', 'story', 'country'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full name'
            }),
            'dob': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Date of Birth'
            }),
            'dod': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'placeholder': 'Date of Death'
            }),
            'story': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share their story...'
            }),
            'country': forms.Select(attrs={
                'class': 'form-control',
            }),
        }











##################################################################


class MemorialForm(forms.ModelForm):
    country = CountryField().formfield(widget=CountrySelectWidget())
    
    related_memorial = forms.ModelChoiceField(
        queryset=Memorial.objects.none(),
        required=False,
        empty_label="No family relation",
        help_text="Select a family member if this person is related to someone you've already added",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    relationship_type = forms.ChoiceField(
        choices=[('', 'Select relationship')] + list(RELATIONSHIP_CHOICES),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Memorial
        fields = ['full_name', 'dob', 'dod', 'country', 'story', 'image_url']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'dod': forms.DateInput(attrs={'type': 'date'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'story': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share memories, stories, or a tribute...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        self.fields['image_url'].widget.attrs.update({'type': 'file', 'accept': 'image/jpeg,image/jpg,image/png,image/webp'})
        
        if user and user.is_authenticated:
            self.fields['related_memorial'].queryset = Memorial.objects.filter(created_by=user, approved=True).order_by('full_name')
        else:
            self.fields['related_memorial'].widget = forms.HiddenInput()
            self.fields['relationship_type'].widget = forms.HiddenInput()

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        if not full_name or not full_name.strip():
            raise forms.ValidationError("Full name is required and cannot be empty.")
        return full_name.strip()

    def clean_image_url(self):
        image = self.cleaned_data.get('image_url')
        if image and hasattr(image, 'content_type'):
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
            if image.content_type not in allowed_types:
                raise forms.ValidationError('Only JPEG, PNG, and WebP images are allowed. GIFs, PDFs, and videos are not permitted.')
            if image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Image file size must be under 5MB.')
        return image

    def clean_dod(self):
        dod = self.cleaned_data.get('dod')
        if dod and dod > datetime.date.today():
            raise forms.ValidationError("Date of death cannot be in the future.")
        return dod
    
    def clean_dob(self):
        dob = self.cleaned_data.get('dob')
        if dob and dob > datetime.date.today():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return dob
    
    def clean(self):
        cleaned_data = super().clean()
        dob = cleaned_data.get('dob')
        dod = cleaned_data.get('dod')
        related_memorial = cleaned_data.get('related_memorial')
        relationship_type = cleaned_data.get('relationship_type')
        
        if related_memorial and not relationship_type:
            raise forms.ValidationError("Please select the relationship type.")
        if relationship_type and not related_memorial:
            raise forms.ValidationError("Please select a family member.")
        if dob and dod and dod < dob:
            raise forms.ValidationError('Date of death cannot be before date of birth.')
        return cleaned_data


class SuggestRelationshipForm(forms.Form):
    my_memorial = forms.ModelChoiceField(
        queryset=Memorial.objects.none(),
        required=True,
        label="Select Your Memorial",
        help_text="Which of your memorials is related to this person?",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    relationship_type = forms.ChoiceField(
        choices=[('', 'Select relationship')] + list(RELATIONSHIP_CHOICES),
        required=True,
        label="Relationship Type",
        help_text="How is your memorial related to this person?",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    suggestion_note = forms.CharField(
        required=False,
        label="Additional Information (Optional)",
        help_text="Provide any context or explanation for this relationship",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'E.g., "John and George were brothers, both born in Chicago in the 1920s"'})
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        target_memorial = kwargs.pop('target_memorial', None)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            queryset = Memorial.objects.filter(created_by=user, approved=True).order_by('full_name')
            if target_memorial:
                queryset = queryset.exclude(id=target_memorial.id)
            self.fields['my_memorial'].queryset = queryset
    
    def clean(self):
        cleaned_data = super().clean()
        my_memorial = cleaned_data.get('my_memorial')
        relationship_type = cleaned_data.get('relationship_type')
        
        if not my_memorial:
            raise forms.ValidationError("Please select one of your memorials.")
        if not relationship_type:
            raise forms.ValidationError("Please select a relationship type.")
        return cleaned_data


class UserNotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'enable_anniversary_notifications',
            'notify_death_anniversaries',
            'notify_birthdays',
            'notify_milestones',
            'notify_week_before',
            'notify_day_before',
            'notify_on_day',
        ]
        widgets = {
            'enable_anniversary_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_death_anniversaries': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_birthdays': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_milestones': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_week_before': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_day_before': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'enable_anniversary_notifications': 'Enable Anniversary Notifications',
            'notify_death_anniversaries': 'Death Anniversaries',
            'notify_birthdays': 'Birthdays',
            'notify_milestones': 'Major Milestones (1, 5, 10, 25, 50 years)',
            'notify_week_before': '1 Week Before',
            'notify_day_before': '1 Day Before',
            'notify_on_day': 'On the Day',
        }
        help_texts = {
            'enable_anniversary_notifications': 'Receive automatic reminders for memorial anniversaries',
            'notify_week_before': 'Get notified 7 days in advance',
            'notify_day_before': 'Get notified 1 day in advance',
            'notify_on_day': 'Get notified on the anniversary day',
        }


class MemorialReminderSettingsForm(forms.ModelForm):
    class Meta:
        model = MemorialReminderSettings
        fields = [
            'custom_settings_enabled',
            'notify_death_anniversary',
            'notify_birthday',
            'notify_creator_only',
            'notify_all_family',
        ]
        widgets = {
            'custom_settings_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_death_anniversary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_birthday': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_creator_only': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_all_family': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'custom_settings_enabled': 'Use custom settings for this memorial',
            'notify_death_anniversary': 'Death Anniversary',
            'notify_birthday': 'Birthday',
            'notify_creator_only': 'Notify only me',
            'notify_all_family': 'Notify all connected family members',
        }