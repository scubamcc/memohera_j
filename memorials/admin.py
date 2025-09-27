# memorials/admin.py
from django.contrib import admin
from .models import Memorial
from .models import Memorial, FamilyRelationship


@admin.register(Memorial)
# @admin.register(FamilyRelationship)
class MemorialAdmin(admin.ModelAdmin):
    # What columns to show in the list view
    list_display = ['full_name', 'country', 'dob', 'dod', 'approved', 'created_at']
    
    # Add filters on the right side
    list_filter = ['approved', 'country', 'created_at']
    
    # Make certain fields clickable to edit
    list_display_links = ['full_name']
    
    # Add search functionality
    search_fields = ['full_name', 'story', 'country']
    
    # Make approval status editable directly from the list
    list_editable = ['approved']
    
    # Order by newest first
    ordering = ['-created_at']
    
    # How many items per page
    list_per_page = 25
    
    # Organize the edit form into sections
    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'dob', 'dod', 'country')
        }),
        ('Memorial Content', {
            'fields': ('story', 'image_url')
        }),
        ('Administration', {
            'fields': ('approved',),
            'description': 'Check this box to make the memorial visible to the public.'
        }),
    )
    
    # Make created_at read-only since it's auto-generated
    readonly_fields = ['created_at']
    
    # Add actions for bulk operations
    actions = ['approve_memorials', 'unapprove_memorials']
    
    def approve_memorials(self, request, queryset):
        updated = queryset.update(approved=True)
        self.message_user(request, f'{updated} memorial(s) were approved.')
    approve_memorials.short_description = "Approve selected memorials"
    
    def unapprove_memorials(self, request, queryset):
        updated = queryset.update(approved=False)
        self.message_user(request, f'{updated} memorial(s) were unapproved.')
    unapprove_memorials.short_description = "Unapprove selected memorials"
    
    # Show a summary of approved vs pending
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # Get counts for dashboard
        total_memorials = Memorial.objects.count()
        approved_memorials = Memorial.objects.filter(approved=True).count()
        pending_memorials = Memorial.objects.filter(approved=False).count()
        
        extra_context['total_memorials'] = total_memorials
        extra_context['approved_memorials'] = approved_memorials
        extra_context['pending_memorials'] = pending_memorials
        
        return super().changelist_view(request, extra_context)