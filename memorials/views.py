from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login as auth_login
from django.utils.translation import gettext as _
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from .forms import MemorialForm, SuggestRelationshipForm
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
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import get_object_or_404
from .models import Memorial, FamilyRelationship, Notification, SmartMatchSuggestion
from memorials.matching_algorithm import find_potential_matches
from .forms import UserNotificationSettingsForm, MemorialReminderSettingsForm
from .models import UserProfile, MemorialReminderSettings
from difflib import SequenceMatcher
from django.db import models
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import stripe
import json
import os
from memorials.models import (
    Memorial, 
    FamilyRelationship, 
    Notification,
    PremiumPackage,  # ADD THIS
    UserSubscription,  # ADD THIS
    PaymentTransaction,  # ADD THIS
    SmartMatchSuggestion,  # ADD THIS if not already there
    # ... your other imports
)





stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_YOUR_SECRET_KEY_HERE')

@login_required
def subscription_dashboard(request):
    """User's subscription dashboard"""
    subscription = UserSubscription.objects.filter(user=request.user).first()
    transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')[:10]
    all_packages = PremiumPackage.objects.filter(is_active=True)  # Add this line
    
    context = {
        'subscription': subscription,
        'transactions': transactions,
        'all_packages': all_packages,  # Add this line
    }
    
    return render(request, 'premium/my_subscription.html', context)


@login_required
def pricing_page(request):
    """Show pricing and package options"""
    packages = PremiumPackage.objects.filter(is_active=True)
    
    # Get user's current subscription
    user_subscription = UserSubscription.objects.filter(user=request.user).first()
    
    context = {
        'packages': packages,
        'user_subscription': user_subscription,
    }
    
    return render(request, 'premium/pricing.html', context)


@login_required
def create_checkout_session(request, package_id):
    """Create Stripe checkout session"""
    package = get_object_or_404(PremiumPackage, id=package_id)
    
    try:
        # Get or create customer
        user_sub = UserSubscription.objects.filter(user=request.user).first()
        
        if user_sub and user_sub.stripe_customer_id:
            customer_id = user_sub.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name() or request.user.username,
                metadata={'user_id': request.user.id}
            )
            customer_id = customer.id
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            mode='subscription',
            customer=customer_id,
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': package.name,
                        'description': package.description,
                    },
                    'unit_amount': int(package.price * 100),  # Convert to cents
                    'recurring': {
                        'interval': 'month',
                        'interval_count': 1,
                    },
                },
                'quantity': 1,
            }],
            success_url=request.build_absolute_uri('/premium/success/'),
            cancel_url=request.build_absolute_uri('/pricing/'),
            metadata={
                'user_id': request.user.id,
                'package_id': package.id,
            }
        )
        
        return redirect(session.url)
        
    except Exception as e:
        messages.error(request, f"Error creating checkout: {str(e)}")
        return redirect('pricing_page')


@login_required
def payment_success(request):
    """Handle successful payment"""
    messages.success(request, "Payment successful! Your premium subscription is now active.")
    return render(request, 'premium/success.html')




@login_required
def cancel_subscription(request):
    """Cancel user's subscription"""
    if request.method == 'POST':
        subscription = UserSubscription.objects.filter(user=request.user).first()
        
        if subscription and subscription.stripe_subscription_id:
            try:
                stripe.Subscription.delete(subscription.stripe_subscription_id)
                subscription.status = 'cancelled'
                subscription.save()
                messages.success(request, "Subscription cancelled successfully.")
            except Exception as e:
                messages.error(request, f"Error cancelling subscription: {str(e)}")
    
    return redirect('subscription_dashboard')


@login_required
def smart_match_suggestions(request):
    """Show AI-powered memorial match suggestions for user's memorials"""
    
    # Get all user's memorials
    user_memorials = Memorial.objects.filter(
        created_by=request.user,
        approved=True
    )
    
    # Get all smart match suggestions for user's memorials
    suggestions = SmartMatchSuggestion.objects.filter(
        my_memorial__in=user_memorials,
        status='pending'
    ).select_related('my_memorial', 'suggested_memorial')
    
    # Group by memorial for easier template rendering
    grouped_suggestions = {}
    for suggestion in suggestions:
        memorial_id = suggestion.my_memorial.id
        if memorial_id not in grouped_suggestions:
            grouped_suggestions[memorial_id] = {
                'memorial': suggestion.my_memorial,
                'matches': []
            }
        grouped_suggestions[memorial_id]['matches'].append(suggestion)
    
    all_suggestions = list(grouped_suggestions.values())
    
    context = {
        'suggestions': all_suggestions,
        'total_pending': suggestions.count(),
    }
    
    return render(request, 'memorials/smart_matches.html', context)

@login_required
@require_http_methods(["POST"])
def accept_smart_match(request, my_memorial_id, suggested_memorial_id):
    """Accept a smart match and redirect to suggest relationship page"""
    my_memorial = get_object_or_404(
        Memorial,
        id=my_memorial_id,
        created_by=request.user
    )
    suggested_memorial = get_object_or_404(Memorial, id=suggested_memorial_id)
    
    # Update suggestion status to 'accepted'
    SmartMatchSuggestion.objects.filter(
        my_memorial=my_memorial,
        suggested_memorial=suggested_memorial
    ).update(status='accepted')
    
    # Redirect to suggest relationship page with pre-filled data
    return redirect(
        f'/memorial/{suggested_memorial_id}/suggest-relationship/?my_memorial={my_memorial_id}'
    )

@login_required
@require_http_methods(["POST"])
def dismiss_smart_match(request, my_memorial_id, suggested_memorial_id):
    """Dismiss a smart match suggestion"""
    my_memorial = get_object_or_404(
        Memorial,
        id=my_memorial_id,
        created_by=request.user
    )
    suggested_memorial = get_object_or_404(Memorial, id=suggested_memorial_id)
    
    # Update suggestion status to 'dismissed'
    SmartMatchSuggestion.objects.filter(
        my_memorial=my_memorial,
        suggested_memorial=suggested_memorial
    ).update(status='dismissed')
    
    messages.success(request, "Suggestion dismissed.")
    return redirect('smart_match_suggestions')

@login_required
def archive_all_smart_matches(request):
    """Archive all pending smart matches for a memorial"""
    if request.method == 'POST':
        memorial_id = request.POST.get('memorial_id')
        memorial = get_object_or_404(
            Memorial,
            id=memorial_id,
            created_by=request.user
        )
        
        count, _ = SmartMatchSuggestion.objects.filter(
            my_memorial=memorial,
            status='pending'
        ).update(status='archived')
        
        messages.success(request, f"Archived {count} suggestions.")
        return redirect('smart_match_suggestions')
    
    return redirect('smart_match_suggestions')

def get_smart_matches_context(request):
    """Helper function to get smart matches count for navbar"""
    if request.user.is_authenticated:
        user_memorials = Memorial.objects.filter(
            created_by=request.user,
            approved=True
        ).count()
        
        if user_memorials > 0:
            # Count unreviewed matches
            unreviewed = SmartMatchSuggestion.objects.filter(
                my_memorial__created_by=request.user,
                status='pending'
            ).count()
            return {'unreviewed_matches': unreviewed}
    
    return {'unreviewed_matches': 0}




def find_potential_matches(memorial, limit=5):
    """
    Find potential family connections for a memorial using AI-like matching
    Returns list of (memorial, confidence_score, reasons) tuples
    """
    potential_matches = []
    
    # Get all other approved memorials (exclude current one and same creator's memorials initially)
    other_memorials = Memorial.objects.filter(
        approved=True
    ).exclude(
        id=memorial.id
    ).exclude(
        created_by=memorial.created_by  # Exclude own memorials for now
    )
    
    # Check if already connected
    existing_relationships = set()
    for rel in FamilyRelationship.objects.filter(
        models.Q(person_a=memorial) | models.Q(person_b=memorial)
    ).values_list('person_a_id', 'person_b_id'):
        existing_relationships.add(rel[0])
        existing_relationships.add(rel[1])
    
    # Filter out already connected memorials
    other_memorials = other_memorials.exclude(id__in=existing_relationships)
    
    for other in other_memorials:
        score = 0
        reasons = []
        
        # 1. Name similarity (40 points max)
        name_similarity = calculate_name_similarity(memorial.full_name, other.full_name)
        if name_similarity > 0.5:
            score += int(name_similarity * 40)
            if name_similarity > 0.8:
                reasons.append(f"Very similar names ({int(name_similarity * 100)}% match)")
            else:
                reasons.append(f"Similar names ({int(name_similarity * 100)}% match)")
        
        # 2. Same last name (20 points)
        if has_same_last_name(memorial.full_name, other.full_name):
            score += 20
            reasons.append("Same last name")
        
        # 3. Same country (15 points)
        if memorial.country == other.country:
            score += 15
            reasons.append(f"Both from {memorial.country.name}")
        
        # 4. Similar birth years (15 points)
        if memorial.dob and other.dob:
            year_diff = abs(memorial.dob.year - other.dob.year)
            if year_diff <= 5:
                score += 15 - year_diff
                reasons.append(f"Born within {year_diff} years of each other")
            elif year_diff <= 30:
                score += max(5 - (year_diff - 5) // 5, 0)
                reasons.append(f"Similar generation (born {year_diff} years apart)")
        
        # 5. Overlapping lifetimes (10 points)
        if memorial.dob and memorial.dod and other.dob and other.dod:
            if lifetimes_overlap(memorial.dob, memorial.dod, other.dob, other.dod):
                score += 10
                reasons.append("Lived during the same time period")
        
        # Only include matches with score > 30 (threshold)
        if score >= 30:
            potential_matches.append({
                'memorial': other,
                'score': score,
                'reasons': reasons
            })
    
    # Sort by score (highest first) and return top matches
    potential_matches.sort(key=lambda x: x['score'], reverse=True)
    return potential_matches[:limit]


def calculate_name_similarity(name1, name2):
    """Calculate similarity between two names using sequence matching"""
    name1 = name1.lower().strip()
    name2 = name2.lower().strip()
    return SequenceMatcher(None, name1, name2).ratio()


def has_same_last_name(name1, name2):
    """Check if two names have the same last name"""
    last1 = name1.strip().split()[-1].lower()
    last2 = name2.strip().split()[-1].lower()
    return last1 == last2


def lifetimes_overlap(dob1, dod1, dob2, dod2):
    """Check if two people's lifetimes overlapped"""
    # They overlap if person1 was alive when person2 was born or vice versa
    return (dob1 <= dod2 and dob2 <= dod1)

@login_required
def upgrade_to_premium(request):
    """Temporary upgrade page - redirect to settings for now"""
    messages.info(request, 'Premium upgrade feature coming soon!')
    return redirect('notification_settings')


@login_required
def notification_settings(request):
    """User notification preferences page"""
    # Get or create user profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = UserNotificationSettingsForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Notification settings updated successfully!')
            return redirect('notification_settings')
    else:
        form = UserNotificationSettingsForm(instance=profile)
    
    # Get user's memorials for per-memorial settings
    user_memorials = Memorial.objects.filter(created_by=request.user, approved=True).order_by('full_name')
    
    context = {
        'form': form,
        'profile': profile,
        'user_memorials': user_memorials,
    }
    
    return render(request, 'memorials/notification_settings.html', context)


@login_required
def memorial_reminder_settings(request, memorial_id):
    """Per-memorial notification settings"""
    memorial = get_object_or_404(Memorial, id=memorial_id, created_by=request.user)
    
    # Get or create reminder settings
    settings_obj, created = MemorialReminderSettings.objects.get_or_create(
        memorial=memorial,
        defaults={'created_by': request.user}
    )
    
    if request.method == 'POST':
        form = MemorialReminderSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Reminder settings for {memorial.full_name} updated successfully!')
            return redirect('notification_settings')
    else:
        form = MemorialReminderSettingsForm(instance=settings_obj)
    
    context = {
        'form': form,
        'memorial': memorial,
        'settings': settings_obj,
    }
    
    return render(request, 'memorials/memorial_reminder_settings.html', context)



def create_notification(user, notification_type, title, message, action_url='', **kwargs):
    """Helper function to create notifications"""
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        related_memorial=kwargs.get('related_memorial'),
        related_relationship=kwargs.get('related_relationship'),
        related_user=kwargs.get('related_user'),
    )

def notify_relationship_suggested(relationship):
    """Notify memorial owners when a relationship is suggested"""
    # Notify owner of person_a
    if relationship.person_a.created_by != relationship.suggested_by:
        create_notification(
            user=relationship.person_a.created_by,
            notification_type='relationship_suggested',
            title='New Family Connection Suggestion',
            message=f'{relationship.suggested_by.username} suggested that {relationship.person_a.full_name} is {relationship.get_relationship_type_display()} of {relationship.person_b.full_name}',
            action_url='/relationship-suggestions/',
            related_relationship=relationship,
            related_user=relationship.suggested_by
        )
    
    # Notify owner of person_b
    if relationship.person_b.created_by != relationship.suggested_by:
        create_notification(
            user=relationship.person_b.created_by,
            notification_type='relationship_suggested',
            title='New Family Connection Suggestion',
            message=f'{relationship.suggested_by.username} suggested a family connection with {relationship.person_b.full_name}',
            action_url='/relationship-suggestions/',
            related_relationship=relationship,
            related_user=relationship.suggested_by
        )

def notify_relationship_approved(relationship, approved_by):
    """Notify suggester when their relationship is approved"""
    if relationship.suggested_by and relationship.suggested_by != approved_by:
        create_notification(
            user=relationship.suggested_by,
            notification_type='relationship_approved',
            title='Family Connection Approved!',
            message=f'Your suggested connection between {relationship.person_a.full_name} and {relationship.person_b.full_name} has been approved!',
            action_url=f'/memorial/{relationship.person_a.id}/family-tree/',
            related_relationship=relationship,
            related_user=approved_by
        )

def notify_relationship_rejected(relationship, rejected_by):
    """Notify suggester when their relationship is rejected"""
    if relationship.suggested_by and relationship.suggested_by != rejected_by:
        create_notification(
            user=relationship.suggested_by,
            notification_type='relationship_rejected',
            title='Family Connection Not Approved',
            message=f'The suggested connection between {relationship.person_a.full_name} and {relationship.person_b.full_name} was not approved.',
            action_url='/browse/',
            related_relationship=relationship,
            related_user=rejected_by
        )











@login_required
def family_tree_view(request, memorial_id):
    """Display interactive family tree for a memorial"""
    memorial = get_object_or_404(Memorial, id=memorial_id, approved=True)
    
    # Build tree data structure
    tree_data = build_tree_data(memorial)
    
    context = {
        'memorial': memorial,
        'tree_data': tree_data,
    }
    
    return render(request, 'memorials/family_tree.html', context)

def build_tree_data(root_memorial):
    """Build hierarchical tree data for D3.js - shows all relationships"""
    visited = set()
    
    def get_node_data(memorial, depth=0, max_depth=3):
        """Get data for a single memorial node"""
        if memorial.id in visited or depth > max_depth:
            return None
        
        visited.add(memorial.id)
        
        node = {
            'id': memorial.id,
            'name': memorial.full_name,
            'birth_year': memorial.dob.year if memorial.dob else '',
            'death_year': memorial.dod.year if memorial.dod else '',
            'image': memorial.image_url.url if memorial.image_url else '',
            'country': memorial.country.name,
            'children': []
        }
        
        # Get ALL approved relationships (not just parent-child)
        # Relationships where this memorial is person_a
        relationships_from = FamilyRelationship.objects.filter(
            person_a=memorial,
            status='approved'
        ).select_related('person_b')
        
        for rel in relationships_from:
            child_node = get_node_data(rel.person_b, depth + 1, max_depth)
            if child_node:
                # Add relationship type to the node
                child_node['relationship'] = rel.get_relationship_type_display()
                node['children'].append(child_node)
        
        # Relationships where this memorial is person_b (reverse)
        relationships_to = FamilyRelationship.objects.filter(
            person_b=memorial,
            status='approved'
        ).select_related('person_a')
        
        for rel in relationships_to:
            child_node = get_node_data(rel.person_a, depth + 1, max_depth)
            if child_node:
                # Add reverse relationship type
                reverse_map = {
                    'parent': 'Child',
                    'child': 'Parent',
                    'spouse': 'Spouse',
                    'sibling': 'Sibling',
                    'grandparent': 'Grandchild',
                    'grandchild': 'Grandparent',
                    'aunt_uncle': 'Niece/Nephew',
                    'niece_nephew': 'Aunt/Uncle',
                    'cousin': 'Cousin',
                }
                child_node['relationship'] = reverse_map.get(rel.relationship_type, rel.get_relationship_type_display())
                node['children'].append(child_node)
        
        return node
    
    tree = get_node_data(root_memorial)
    
    # Convert to JSON
    import json
    return json.dumps(tree) if tree else json.dumps({'id': root_memorial.id, 'name': root_memorial.full_name, 'children': []})

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
    # messages.success(request, _('Memorial created successfully!'))
    return render(request, 'memorials/create.html', context)



def edit_memorial(request, memorial_id):
    """Edit an existing memorial"""
    memorial = get_object_or_404(Memorial, id=memorial_id, created_by=request.user)
    
    if request.method == 'POST':
        form = MemorialForm(request.POST, request.FILES, instance=memorial, user=request.user)
        if form.is_valid():
            memorial = form.save(commit=False)
            memorial.created_by = request.user
            memorial.save()
            
            # Handle family relationship updates if needed
            related_memorial = form.cleaned_data.get('related_memorial')
            relationship_type = form.cleaned_data.get('relationship_type')
            
            if related_memorial and relationship_type and getattr(settings, 'ENABLE_FAMILY_RELATIONSHIPS', False):
                # Check if relationship already exists
                existing = FamilyRelationship.objects.filter(
                    person_a=memorial,
                    person_b=related_memorial,
                    relationship_type=relationship_type
                ).first()
                
                if not existing:
                    FamilyRelationship.objects.create(
                        person_a=memorial,
                        person_b=related_memorial,
                        relationship_type=relationship_type,
                        created_by=request.user,
                        status='approved'
                    )
            
            messages.success(request, _('Memorial updated successfully!'))
            return redirect('my_memorials')
    else:
        form = MemorialForm(instance=memorial, user=request.user)
    
    context = {
        'form': form,
        'memorial': memorial,
        'is_edit': True,
    }
    return render(request, 'memorials/edit_memorial.html', context)



def privacy_policy(request):
    return render(request, 'memorials/privacy_policy.html')


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
            'type': rel.get_relationship_type_display(),
            'memorial': rel.person_b,
            'relationship_obj': rel,
            'verification_status': rel.verification_status,
            'verification_badge': get_verification_badge(rel.verification_status),
            'suggested_by': rel.suggested_by,
        })

    # Get relationships where this memorial is person_b (reverse the relationship)
    for rel in memorial.family_relationships_to.filter(status='approved'):
        reverse_type = reverse_map.get(rel.relationship_type, rel.relationship_type.replace('_', '/').title())
        relationships.append({
            'type': reverse_type,
            'memorial': rel.person_a,
            'relationship_obj': rel,
            'verification_status': rel.verification_status,
            'verification_badge': get_verification_badge(rel.verification_status),
            'suggested_by': rel.suggested_by,
        })


    return relationships

def get_verification_badge(verification_status):
    """Return badge HTML for verification status"""
    badges = {
        'creator_verified': {
            'icon': 'fa-check-circle',
            'color': 'success',
            'text': 'Verified',
            'title': 'Verified by memorial creator'
        },
        'user_suggested': {
            'icon': 'fa-users',
            'color': 'info',
            'text': 'User-suggested',
            'title': 'Suggested by community member'
        },
        'auto_approved': {
            'icon': 'fa-check-double',
            'color': 'primary',
            'text': 'Auto-verified',
            'title': 'Automatically verified (same creator)'
        },
    }
    
    return badges.get(verification_status, badges['user_suggested'])


def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in after password change
            messages.success(request, 'Your password was successfully updated!')
            return redirect('my_memorials')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'registration/change_password.html', {'form': form})

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


@login_required
def suggest_relationship(request, memorial_id):
    """Suggest a family relationship to someone else's memorial"""
    target_memorial = get_object_or_404(Memorial, id=memorial_id, approved=True)
    
    # Check if user has any approved memorials to connect
    user_memorials = Memorial.objects.filter(created_by=request.user, approved=True)
    
    if not user_memorials.exists():
        messages.error(request, "You need to create at least one approved memorial before suggesting relationships.")
        return redirect('create_memorial')
    
    if request.method == 'POST':
        form = SuggestRelationshipForm(request.POST, user=request.user, target_memorial=target_memorial)
        if form.is_valid():
            my_memorial = form.cleaned_data['my_memorial']
            relationship_type = form.cleaned_data['relationship_type']
            suggestion_note = form.cleaned_data.get('suggestion_note', '')
            
            # Check if relationship already exists
            existing = FamilyRelationship.objects.filter(
                person_a=my_memorial,
                person_b=target_memorial,
                relationship_type=relationship_type
            ).first()
            
            if existing:
                messages.warning(request, "This relationship has already been suggested.")
                return redirect('browse')
            
            # Check if user owns both memorials (auto-approve)
            if my_memorial.created_by == target_memorial.created_by:
                verification_status = 'auto_approved'
                status = 'approved'
                messages.success(request, "Relationship added successfully (both memorials are yours)!")
            else:
                verification_status = 'user_suggested'
                status = 'pending'
                messages.success(request, "Relationship suggestion sent! The memorial owner will be notified.")
            
            # Create the relationship
            relationship = FamilyRelationship.objects.create(
                person_a=my_memorial,
                person_b=target_memorial,
                relationship_type=relationship_type,
                created_by=request.user,
                suggested_by=request.user,
                status=status,
                verification_status=verification_status,
                suggestion_note=suggestion_note
            )

            # Send notification if not auto-approved
            if status == 'pending':
                notify_relationship_suggested(relationship)
            
            return redirect('memorial_detail', pk=target_memorial.id)
    else:
        form = SuggestRelationshipForm(user=request.user, target_memorial=target_memorial)
    
    context = {
        'form': form,
        'target_memorial': target_memorial,
        'user_memorials': user_memorials,
    }
    
    return render(request, 'memorials/suggest_relationship.html', context)


@login_required
def manage_relationship_suggestions(request):
    """View pending relationship suggestions for user's memorials"""
    # Get all pending suggestions for memorials owned by this user
    pending_suggestions = FamilyRelationship.objects.filter(
        status='pending'
    ).filter(
        Q(person_a__created_by=request.user) | Q(person_b__created_by=request.user)
    ).select_related('person_a', 'person_b', 'suggested_by')
    
    context = {
        'pending_suggestions': pending_suggestions,
    }
    
    return render(request, 'memorials/manage_suggestions.html', context)


@login_required
def approve_relationship_suggestion(request, relationship_id):
    """Approve a relationship suggestion"""
    relationship = get_object_or_404(FamilyRelationship, id=relationship_id)
    
    if not relationship.can_approve(request.user):
        messages.error(request, "You don't have permission to approve this relationship.")
        return redirect('manage_relationship_suggestions')
    
    if request.method == 'POST':
        relationship.approve(request.user)
        
        # Send notification
        notify_relationship_approved(relationship, request.user)
        
        messages.success(request, f"Relationship approved: {relationship.person_a.full_name} - {relationship.get_relationship_type_display()} - {relationship.person_b.full_name}")
    
    return redirect('manage_relationship_suggestions')


@login_required
def reject_relationship_suggestion(request, relationship_id):
    """Reject a relationship suggestion"""
    relationship = get_object_or_404(FamilyRelationship, id=relationship_id)
    
    if not relationship.can_approve(request.user):
        messages.error(request, "You don't have permission to reject this relationship.")
        return redirect('manage_relationship_suggestions')
    
    if request.method == 'POST':
        # Send notification before deleting
        notify_relationship_rejected(relationship, request.user)
        
        relationship.reject(request.user)
        messages.info(request, "Relationship suggestion rejected.")
    
    return redirect('manage_relationship_suggestions')

@login_required
def notifications_list(request):
    """Display all notifications for the user"""
    notifications = Notification.objects.filter(user=request.user)
    
    # Separate unread and read
    unread_notifications = notifications.filter(is_read=False)
    read_notifications = notifications.filter(is_read=True)[:20]  # Last 20 read
    
    context = {
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
    }
    
    return render(request, 'memorials/notifications.html', context)


@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    # Redirect to action URL if exists
    if notification.action_url:
        return redirect(notification.action_url)
    
    return redirect('notifications_list')


@login_required
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications_list')

