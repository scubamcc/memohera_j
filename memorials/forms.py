# Add this to your forms.py (create this file if it doesn't exist)

from django import forms
from django_countries.fields import CountryField
from django_countries.widgets import CountrySelectWidget
from .models import Memorial, FamilyRelationship
import datetime

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
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
            'story': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Share memories, stories, or a tribute...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Ensure file input renders correctly
        self.fields['image_url'].widget.attrs.update({'type': 'file'})
        
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