# Update your views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.utils.translation import gettext as _
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from .forms import MemorialForm
from .models import Memorial, FamilyRelationship
from django.db.models import Q

from django.core.paginator import Paginator
from django_countries import countries
from django.utils.translation import gettext as _
from django.contrib.auth import logout
from django.shortcuts import redirect
import uuid
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail





@login_required
def create_memorial(request):
    if request.method == 'POST':
        form = MemorialForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            # Save the memorial
            memorial = form.save(commit=False)
            memorial.created_by = request.user  # Link memorial to user
            memorial.approved = getattr(settings, 'AUTO_APPROVE_MEMORIALS', False)
            memorial.save()
            
            # Create family relationship if specified
            related_memorial = form.cleaned_data.get('related_memorial')
            relationship_type = form.cleaned_data.get('relationship_type')
            
            if related_memorial and relationship_type and getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False):
                FamilyRelationship.objects.create(
                    person_a=memorial,
                    person_b=related_memorial,
                    relationship_type=relationship_type,
                    created_by=request.user,
                    status='approved'  # Auto-approve since it's their own memorial
                )
                
                messages.success(
                    request, 
                    _('Memorial submitted successfully! Family relationship with %(name)s has been added. Your memorial will be reviewed before being published.') % {'name': related_memorial.full_name}
                )
            else:
                messages.success(request, _('Memorial created and published successfully!'))
            
            return render(request, 'memorials/thank_you.html', {'memorial': memorial})
    else:
        form = MemorialForm(user=request.user)
    
    # Get user's existing memorials for context
    user_memorials = Memorial.objects.filter(
        created_by=request.user, 
        approved=True
    ).order_by('full_name') if request.user.is_authenticated else Memorial.objects.none()
    
    context = {
        'form': form,
        'user_memorials': user_memorials,
        'enable_family_relationships': getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False)
    }
    messages.success(request, _('Memorial created successfully!'))
    return render(request, 'memorials/create.html', context)

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, _('Welcome! Your account has been created. You can now create memorials.'))
            # Redirect to create page or wherever they were trying to go
            next_url = request.GET.get('next', 'create_memorial')
            return redirect(next_url)
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

# In your browse_memorials view, update the context preparation:

def browse_memorialsold(request):
    query = request.GET.get('q', '')
    country = request.GET.get('country', '')
    birth_year = request.GET.get('birth_year', '')
    death_year = request.GET.get('death_year', '')
    
    # Start with approved memorials
    memorials = Memorial.objects.filter(approved=True)
    
    # Apply search filters
    if query:
        memorials = memorials.filter(
            Q(full_name__icontains=query) |
            Q(story__icontains=query) |
            Q(country__icontains=query)
        )
    
    if country:
        memorials = memorials.filter(country=country)
    
    if birth_year:
        memorials = memorials.filter(dob__year=birth_year)
    
    if death_year:
        memorials = memorials.filter(dod__year=death_year)
    
    # Order memorials
    sort_by = request.GET.get('sort', '-created_at')
    memorials = memorials.order_by(sort_by)
    
    # Add relationship data for each memorial (if feature is enabled)
    if getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False):
        for memorial in memorials:
            memorial.relationships = get_memorial_relationships(memorial)
    
    # SINGLE context section with everything
    context = {
        'memorials': memorials,
        'query': query,
        'country': country,
        'birth_year': birth_year,
        'death_year': death_year,
        'current_view': request.GET.get('view', 'list'),
        'ENABLE_FAMILY_RELATIONSHIPS': getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False),
    }
    return render(request, 'memorials/browse.html', context)

def browse_memorials(request):
    query = request.GET.get('q', '')
    country = request.GET.get('country', '')
    birth_year = request.GET.get('birth_year', '')
    death_year = request.GET.get('death_year', '')
    
    # Start with approved memorials
    memorials = Memorial.objects.filter(approved=True)
    
    # Apply search filters
    if query:
        memorials = memorials.filter(
            Q(full_name__icontains=query) |
            Q(story__icontains=query) |
            Q(country__icontains=query)
        )
    
    if country:
        memorials = memorials.filter(country=country)
    
    # Fix birth year filter
    if birth_year:
        try:
            birth_year_int = int(birth_year)
            memorials = memorials.filter(dob__year=birth_year_int)
        except (ValueError, TypeError):
            pass  # Ignore invalid birth year input
    
    # Fix death year filter  
    if death_year:
        try:
            death_year_int = int(death_year)
            memorials = memorials.filter(dod__year=death_year_int)
        except (ValueError, TypeError):
            pass  # Ignore invalid death year input
    
    # Order memorials
    sort_by = request.GET.get('sort', '-created_at')
    memorials = memorials.order_by(sort_by)
    
    # Add pagination - show 20 per page
    paginator = Paginator(memorials, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Only process relationships for the current page
    if getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False):
        for memorial in page_obj:
            memorial.relationships = get_memorial_relationships(memorial)
    
    context = {
        'memorials': page_obj,
        'page_obj': page_obj,
        'query': query,
        'country': country,
        'birth_year': birth_year,
        'death_year': death_year,
        'current_view': request.GET.get('view', 'list'),
        'countries': countries,  # Add this
        'ENABLE_FAMILY_RELATIONSHIPS': getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False),
    }
    return render(request, 'memorials/browse.html', context)

def home(request):
    if request.user.is_authenticated:
        return redirect('create_memorial')
    else:
        # Show about page with clear path to create memorial
        return redirect('about')

def about(request):
    return render(request, 'memorials/about.html')


def custom_logout(request):
    logout(request)
    return redirect('about')  # or wherever you want to redirect


def logout_view(request):
    
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, 'You have been logged out successfully.')
 
    return redirect('about')
    
def my_memorials(request):
    """Display all memorials submitted by the current user"""
    # Get memorials created by the current user (both approved and pending)
    memorials = Memorial.objects.filter(created_by=request.user).order_by('-created_at')
    
    # Add relationship data for each memorial (if feature is enabled)
    if getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False):
        for memorial in memorials:
            memorial.relationships = get_memorial_relationships(memorial)
    
    context = {
        'memorials': memorials,
    }
    return render(request, 'memorials/my_memorials.html', context)









def add_family_relationship(request, memorial_id):
    """Add a family relationship between two memorials"""
    memorial = get_object_or_404(Memorial, id=memorial_id)
    
    if request.method == 'POST':
        related_memorial_id = request.POST.get('related_memorial')
        relationship_type = request.POST.get('relationship_type')
        
        try:
            related_memorial = Memorial.objects.get(id=related_memorial_id)
            
            # Create the relationship
            relationship = FamilyRelationship.objects.create(
                person_a=memorial,
                person_b=related_memorial,
                relationship_type=relationship_type,
                created_by=request.user,
                status='pending'  # Needs approval from memorial owners
            )
            
            messages.success(request, f'Family relationship suggested! Awaiting approval from memorial owners.')
            return redirect('memorial_detail', memorial_id=memorial_id)
            
        except Memorial.DoesNotExist:
            messages.error(request, 'Memorial not found.')
    
    # Get available memorials (exclude current one)
    available_memorials = Memorial.objects.filter(approved=True).exclude(id=memorial_id)
    
    context = {
        'memorial': memorial,
        'available_memorials': available_memorials,
        'relationship_choices': FamilyRelationship.RELATIONSHIP_CHOICES,
    }
    
    return render(request, 'memorials/add_family_relationship.html', context)

def approve_family_relationship(request, relationship_id):
    """Approve or reject a family relationship suggestion"""
    relationship = get_object_or_404(FamilyRelationship, id=relationship_id)
    
    # Check if user owns one of the memorials
    if (relationship.person_a.created_by != request.user and 
        relationship.person_b.created_by != request.user):
        messages.error(request, 'You can only approve relationships for your own memorials.')
        return redirect('my_memorials')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'approve':
            relationship.status = 'approved'
            relationship.save()
            messages.success(request, 'Family relationship approved!')
        elif action == 'reject':
            relationship.delete()
            messages.info(request, 'Family relationship suggestion rejected.')
    
    return redirect('my_memorials')

def get_memorial_relationships(memorial):
    """Helper function to get all approved relationships for a memorial"""
    if not getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False):
        return []
    
    relationships = []
    
    # Get relationships where this memorial is person_a
    for rel in memorial.family_relationships_from.filter(status='approved'):
        relationships.append({
            'type': rel.get_relationship_type_display(),
            'memorial': rel.person_b,
            'relationship_obj': rel
        })
    
    # Get relationships where this memorial is person_b (reverse the relationship)
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
    
    for rel in memorial.family_relationships_to.filter(status='approved'):
        reverse_type = reverse_map.get(rel.relationship_type, rel.relationship_type)
        relationships.append({
            'type': reverse_type.replace('_', '/').title(),
            'memorial': rel.person_a,
            'relationship_obj': rel
        })
    
    return relationships
# Add these views to your memorials/views.py file

# Memorial sharing view (public access via share token)
def memorial_share(request, share_token):
    """View a memorial via share token (public access)"""
    try:
        memorial = Memorial.objects.get(share_token=share_token, is_shareable=True)
    except Memorial.DoesNotExist:
        messages.error(request, "Memorial not found or not available for sharing.")
        return redirect('browse')
    
    # Increment share count
    memorial.share_count = getattr(memorial, 'share_count', 0) + 1
    memorial.save(update_fields=['share_count'])
    
    # Build social sharing URLs
    share_url = request.build_absolute_uri()
    share_title = f"Memorial for {memorial.full_name}"
    share_description = f"Remember and honor {memorial.full_name}. {memorial.birth_year or ''} - {memorial.death_year or ''}. {memorial.story[:100] if memorial.story else ''}"
    
    social_links = {
        'facebook': f"https://www.facebook.com/sharer/sharer.php?u={share_url}",
        'twitter': f"https://twitter.com/intent/tweet?url={share_url}&text={share_title}",
        'whatsapp': f"https://wa.me/?text={share_title} - {share_url}",
        'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={share_url}",
        'email': f"mailto:?subject={share_title}&body=I wanted to share this memorial with you: {share_url}",
    }
    
    context = {
        'memorial': memorial,
        'social_links': social_links,
        'share_url': share_url,
        'is_shared_view': True,  # Flag to show this is the shared version
    }
    
    return render(request, 'memorials/memorial_detail.html', context)

# Social sharing AJAX endpoint
@login_required
# def get_social_sharing_links(request, memorial_id):
#     """Get social sharing links for a memorial"""
#     try:
#         memorial = Memorial.objects.get(pk=memorial_id)
#     except Memorial.DoesNotExist:
#         return JsonResponse({'error': 'Memorial not found'}, status=404)
    
#     # Check if user can share this memorial
#     if not getattr(memorial, 'is_shareable', True):
#         return JsonResponse({'error': 'This memorial is not shareable'}, status=403)
    
#     # Generate or get share token
#     if not hasattr(memorial, 'share_token') or not memorial.share_token:
#         memorial.share_token = uuid.uuid4()
#         memorial.save(update_fields=['share_token'])
    
#     share_url = request.build_absolute_uri(reverse('memorial_share', kwargs={'share_token': memorial.share_token}))
#     share_title = f"Memorial for {memorial.full_name}"
#     share_description = f"Remember and honor {memorial.full_name}. {memorial.birth_year or ''} - {memorial.death_year or ''}. {memorial.story[:100] if memorial.story else ''}"
    
#     social_links = {
#         'facebook': f"https://www.facebook.com/sharer/sharer.php?u={share_url}",
#         'twitter': f"https://twitter.com/intent/tweet?url={share_url}&text={share_title}",
#         'whatsapp': f"https://wa.me/?text={share_title} - {share_url}",
#         'linkedin': f"https://www.linkedin.com/sharing/share-offsite/?url={share_url}",
#         'email': f"mailto:?subject={share_title}&body=I wanted to share this memorial with you: {share_url}",
#         'copy': share_url,  # For copy to clipboard
#     }
    
#     return JsonResponse({
#         'social_links': social_links,
#         'share_url': share_url,
#         'title': share_title,
#         'description': share_description
#     })


def get_social_sharing_links(request, memorial_id):
    """Ultra-simple version for testing"""
    return JsonResponse({
        'success': True,
        'share_url': f'http://127.0.0.1:8000/memorial/{memorial_id}/',
        'social_links': {
            'facebook': f'https://www.facebook.com/sharer/sharer.php?u=http://127.0.0.1:8000/memorial/{memorial_id}/',
            'twitter': f'https://twitter.com/intent/tweet?url=http://127.0.0.1:8000/memorial/{memorial_id}/',
            'whatsapp': f'https://wa.me/?text=Memorial - http://127.0.0.1:8000/memorial/{memorial_id}/',
            'copy': f'http://127.0.0.1:8000/memorial/{memorial_id}/'
        }
    })
# Create sharing invitation (Premium feature)
# @login_required
# def create_sharing_invitation(request):
#     """Create a sharing invitation for premium users"""
#     # For now, assume all users have premium access - you can add premium checks later
#     # if not request.user.profile.is_premium:
#     #     messages.error(request, "This feature is only available for premium members.")
#     #     return redirect('browse')
    
#     if request.method == 'POST':
#         invitation_type = request.POST.get('invitation_type', 'create')
#         email = request.POST.get('email', '')
#         message = request.POST.get('message', '')
#         memorial_id = request.POST.get('memorial_id')
        
#         # Set expiry (7 days from now)
#         expires_at = timezone.now() + timedelta(days=7)
        
#         # Create a simple invitation (you'll need to create this model later)
#         invitation_id = uuid.uuid4()
        
#         # For now, just return success with a mock invitation URL
#         invitation_url = request.build_absolute_uri(f'/invitation/{invitation_id}/')
        
#         messages.success(request, f"Invitation created! Share this link: {invitation_url}")
        
#         if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#             return JsonResponse({
#                 'success': True,
#                 'invitation_url': invitation_url,
#                 'invitation_id': str(invitation_id)
#             })
#         else:
#             return redirect('create_sharing_invitation')
    
#     # GET request - show form
#     memorials = Memorial.objects.filter(created_by=request.user)
    
#     context = {
#         'memorials': memorials,
#     }
    
#     return render(request, 'memorials/create_invitation.html', context)

# Use sharing invitation to create memorial
# def memorial_create_via_invitation(request, invitation_id):
#     """Create a memorial using a sharing invitation"""
#     # For now, just redirect to create memorial with a success message
#     # You can implement full invitation logic later
    
#     # If user is not authenticated, redirect to signup with invitation
#     if not request.user.is_authenticated:
#         messages.info(request, "Please create an account to use this invitation.")
#         return redirect(f"{reverse('signup')}?invitation={invitation_id}")
    
#     # Add success message
#     messages.success(request, "Welcome! You've been invited to create a memorial.")
    
#     # Redirect to create memorial page
#     return redirect('create_memorial')
# View to manage sharing invitations
# @login_required
# def manage_invitations(request):
#     """Manage user's sharing invitations"""
#     # For now, just show a placeholder page
#     # You can implement full invitation management later
    
#     context = {
#         'sent_invitations': [],  # Will be populated when you implement the invitation model
#         'used_invitations': [],
#     }
    
#     return render(request, 'memorials/manage_invitations.html', context)