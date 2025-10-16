# Add this to your forms.py (create this file if it doesn't exist)

from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import Memorial, FamilyRelationship
import datetime

# Define relationship choices here or import from models
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



class MemorialForm(forms.ModelForm):
    country = CountryField().formfield(widget=CountrySelectWidget())
    
    # Family relationship fields
    related_memorial = forms.ModelChoiceField(
        queryset=Memorial.objects.none(),  # Will be set in __init__
        required=False,
        empty_label="No family relation",
        help_text="Select a family member if this person is related to someone you've already added",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    relationship_type = forms.ChoiceField(
        choices=[('', 'Select relationship')] + [
            ('parent', 'Parent'),
            ('child', 'Child'),
            ('spouse', 'Spouse'),
            ('sibling', 'Sibling'),
            ('grandparent', 'Grandparent'),
            ('grandchild', 'Grandchild'),
            ('aunt_uncle', 'Aunt/Uncle'),
            ('niece_nephew', 'Niece/Nephew'),
            ('cousin', 'Cousin'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = Memorial
        fields = ['full_name', 'dob', 'dod', 'country', 'story', 'image_url']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'dod': forms.DateInput(attrs={'type': 'date'}),
            'full_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Full name',
                'required': True  # Add this
            }),
            'story': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share memories, stories, or a tribute...'}),
        }
        # Add custom error messages
        error_messages = {
            'full_name': {
                'required': 'Please enter the full name of the person.',
            },
        }
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Ensure file input renders correctly with accept attribute for images only
        self.fields['image_url'].widget.attrs.update({
            'type': 'file',
            'accept': 'image/jpeg,image/jpg,image/png,image/webp'  # Only allow these image formats
        })

        
        # Only show approved memorials created by the current user
        if user and user.is_authenticated:
            self.fields['related_memorial'].queryset = Memorial.objects.filter(
                created_by=user, 
                approved=True
            ).order_by('full_name')
        else:
            # Hide the family relationship fields if user is not logged in
            self.fields['related_memorial'].widget = forms.HiddenInput()
            self.fields['relationship_type'].widget = forms.HiddenInput()

    def clean_image_url(self):
            """Validate that uploaded file is an image (not PDF, video, GIF, etc.)"""
            image = self.cleaned_data.get('image_url')
            
            if image:
                # Check if it's a file upload (not just existing Cloudinary URL)
                if hasattr(image, 'content_type'):
                    # Allowed image types
                    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
                    
                    if image.content_type not in allowed_types:
                        raise forms.ValidationError(
                            'Only JPEG, PNG, and WebP images are allowed. '
                            'GIFs, PDFs, and videos are not permitted.'
                        )
                    
                    # Optional: Check file size (e.g., max 5MB)
                    if image.size > 5 * 1024 * 1024:  # 5MB in bytes
                        raise forms.ValidationError(
                            'Image file size must be under 5MB.'
                        )
            
            return image


    def clean_full_name(self):
        """Validate that full name is not empty"""
        full_name = self.cleaned_data.get('full_name')
        
        # Check if empty or only whitespace
        if not full_name or not full_name.strip():
            raise forms.ValidationError("Full name is required and cannot be empty.")
        
        # Return the cleaned value (with whitespace stripped)
        return full_name.strip()

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
        dob = cleaned_data.get('dob')  # Get dob from cleaned_data
        dod = cleaned_data.get('dod')  # Get dod from cleaned_data
        related_memorial = cleaned_data.get('related_memorial')
        relationship_type = cleaned_data.get('relationship_type')
        
        # If one field is filled, both must be filled
        if related_memorial and not relationship_type:
            raise forms.ValidationError("Please select the relationship type.")
        
        if relationship_type and not related_memorial:
            raise forms.ValidationError("Please select a family member.")
        
        if dob and dod:
            if dod < dob:
                raise forms.ValidationError('Date of death cannot be before date of birth.')

        return cleaned_data
    
class SuggestRelationshipForm(forms.Form):
    """Form for suggesting a relationship between two memorials"""
    
    my_memorial = forms.ModelChoiceField(
        queryset=Memorial.objects.none(),
        required=True,
        label="Select Your Memorial",
        help_text="Which of your memorials is related to this person?",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    relationship_type = forms.ChoiceField(
        choices=[('', 'Select relationship')] + RELATIONSHIP_CHOICES,
        required=True,
        label="Relationship Type",
        help_text="How is your memorial related to this person?",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    suggestion_note = forms.CharField(
        required=False,
        label="Additional Information (Optional)",
        help_text="Provide any context or explanation for this relationship",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'E.g., "John and George were brothers, both born in Chicago in the 1920s"'
        })
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        target_memorial = kwargs.pop('target_memorial', None)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            # Show only approved memorials created by the current user
            # Exclude the target memorial from the list
            queryset = Memorial.objects.filter(
                created_by=user,
                approved=True
            ).order_by('full_name')
            
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