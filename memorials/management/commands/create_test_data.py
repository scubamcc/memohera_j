from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from memorials.models import Memorial, FamilyRelationship
from faker import Faker
import random
from django.utils import timezone

class Command(BaseCommand):
    help = 'Create test memorial data'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=1000, help='Number of memorials to create')
        parser.add_argument('--users', type=int, default=100, help='Number of test users to create')

    def handle(self, *args, **options):
        fake = Faker()
        count = options['count']
        user_count = options['users']
        
        self.stdout.write(f'Creating {user_count} test users...')
        
        # Create test users
        users = []
        for i in range(user_count):
            username = f'testuser{i:05d}'
            email = f'test{i:05d}@example.com'
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email, 'first_name': fake.first_name(), 'last_name': fake.last_name()}
            )
            users.append(user)
        
        self.stdout.write(f'Creating {count} test memorials...')
        
        countries = ['US', 'UK', 'CA', 'FR', 'DE', 'IT', 'ES', 'AU', 'NZ', 'JP']
        
        # Create memorials in batches for better performance
        batch_size = 1000
        memorials = []
        
        for i in range(count):
            birth_date = fake.date_between(start_date='-100y', end_date='-20y')
            death_date = fake.date_between(start_date=birth_date, end_date='today')
            
            memorial = Memorial(
                full_name=fake.name(),
                dob=birth_date,
                dod=death_date,
                country=random.choice(countries),
                story=fake.text(max_nb_chars=1000),
                created_by=random.choice(users),
                approved=random.choice([True, True, True, False]),  # 75% approved
                created_at=fake.date_time_between(start_date='-2y', end_date='now', tzinfo=timezone.get_current_timezone())
            )
            memorials.append(memorial)
            
            # Batch create every 1000 records
            if len(memorials) >= batch_size:
                Memorial.objects.bulk_create(memorials)
                memorials = []
                self.stdout.write(f'Created {i+1} memorials...')
        
        # Create remaining memorials
        if memorials:
            Memorial.objects.bulk_create(memorials)
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {count} test memorials and {user_count} test users!')
        )