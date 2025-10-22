from django.core.management.base import BaseCommand
from memorials.models import PremiumPackage

class Command(BaseCommand):
    def handle(self, *args, **options):
        packages = [
            {
                'name': 'Free',
                'tier': 'free',
                'price': 0,
                'smart_matches_enabled': False,
                'anniversary_notifications': False,
                'family_tree_advanced': False,
                'storage_gb': 1,
                'description': 'Basic memorial creation',
                'display_order': 1,
            },
            {
                'name': 'Pro',
                'tier': 'pro',
                'price': 9.99,
                'smart_matches_enabled': True,
                'anniversary_notifications': False,
                'family_tree_advanced': False,
                'storage_gb': 10,
                'description': 'Smart AI matching',
                'display_order': 2,
            },
            {
                'name': 'Premium',
                'tier': 'premium',
                'price': 19.99,
                'smart_matches_enabled': True,
                'anniversary_notifications': True,
                'family_tree_advanced': True,
                'storage_gb': 100,
                'description': 'Full premium experience',
                'display_order': 3,
            },
        ]
        
        for pkg in packages:
            PremiumPackage.objects.get_or_create(
                tier=pkg['tier'],
                defaults=pkg
            )
        
        self.stdout.write(self.style.SUCCESS('Premium packages created!'))