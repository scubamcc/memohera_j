# ============================================================================
# memorials/webhook.py - CREATE THIS NEW FILE
# ============================================================================

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import stripe
import os

stripe.api_key = os.getenv('STRIPE_SECRET_KEY', 'sk_test_YOUR_SECRET_KEY_HERE')


@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    elif event['type'] == 'charge.failed':
        charge = event['data']['object']
        handle_charge_failed(charge)
    
    return JsonResponse({'received': True})


def handle_checkout_completed(session):
    """Update subscription when checkout completes"""
    from memorials.models import UserSubscription, PremiumPackage, PaymentTransaction
    
    user_id = session['metadata'].get('user_id')
    package_id = session['metadata'].get('package_id')
    
    if not user_id or not package_id:
        return
    
    try:
        user = User.objects.get(id=user_id)
        package = PremiumPackage.objects.get(id=package_id)
        
        # Get or create subscription
        subscription, created = UserSubscription.objects.get_or_create(user=user)
        
        # Update subscription
        subscription.package = package
        subscription.status = 'active'
        subscription.stripe_customer_id = session['customer']
        subscription.stripe_subscription_id = session['subscription']
        subscription.started_at = timezone.now()
        subscription.expires_at = timezone.now() + timedelta(days=30)
        subscription.save()
        
        # Create payment transaction
        PaymentTransaction.objects.create(
            user=user,
            subscription=subscription,
            amount=package.price,
            status='completed',
            stripe_payment_intent_id=session.get('payment_intent', ''),
            completed_at=timezone.now(),
        )
        
    except Exception as e:
        print(f"Error handling checkout: {str(e)}")


def handle_subscription_updated(subscription):
    """Update subscription status"""
    from memorials.models import UserSubscription
    
    customer_id = subscription['customer']
    status = subscription['status']
    
    try:
        user_sub = UserSubscription.objects.get(stripe_customer_id=customer_id)
        user_sub.stripe_subscription_id = subscription['id']
        user_sub.status = 'active' if status == 'active' else 'cancelled'
        user_sub.save()
    except UserSubscription.DoesNotExist:
        pass


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    from memorials.models import UserSubscription
    
    customer_id = subscription['customer']
    
    try:
        user_sub = UserSubscription.objects.get(stripe_customer_id=customer_id)
        user_sub.status = 'cancelled'
        user_sub.save()
    except UserSubscription.DoesNotExist:
        pass


def handle_charge_failed(charge):
    """Handle failed payments"""
    from memorials.models import UserSubscription, PaymentTransaction
    
    customer_id = charge.get('customer')
    
    if customer_id:
        try:
            user_sub = UserSubscription.objects.get(stripe_customer_id=customer_id)
            # Create failed transaction record
            PaymentTransaction.objects.create(
                user=user_sub.user,
                subscription=user_sub,
                amount=charge['amount'] / 100,
                status='failed',
                stripe_payment_intent_id=charge.get('payment_intent', ''),
            )
        except UserSubscription.DoesNotExist:
            pass