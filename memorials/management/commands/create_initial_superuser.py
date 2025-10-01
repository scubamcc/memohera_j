from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Creates an initial superuser'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@memohera.com')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Ayy>2U;DgW!Bm4HB4F|$')
        
        if not password:
            self.stdout.write(self.style.ERROR('DJANGO_SUPERUSER_PASSWORD environment variable is required'))
            return
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'Superuser "{username}" already exists'))
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" created successfully'))