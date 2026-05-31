"""Management command: create demo/admin users for production seeding (idempotent)."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create demo and admin users if they do not already exist (idempotent).'

    def handle(self, *args, **options):
        from rest_framework.authtoken.models import Token
        from api.models import Subscription

        users_to_create = [
            dict(
                username='admin',
                email='admin@epitopx.ai',
                password='admin123',
                is_staff=True,
                is_superuser=True,
                is_admin=True,
            ),
            dict(
                username='demo',
                email='demo@epitopx.ai',
                password='demo123',
                is_staff=False,
                is_superuser=False,
                is_admin=False,
            ),
        ]

        for data in users_to_create:
            username = data['username']
            if User.objects.filter(username=username).exists():
                self.stdout.write(f'  User "{username}" already exists — skipping.')
                continue

            user = User.objects.create_user(
                username=username,
                email=data['email'],
                password=data['password'],
                is_staff=data['is_staff'],
                is_superuser=data['is_superuser'],
                is_admin=data['is_admin'],
                is_email_verified=True,
            )

            # Ensure auth token exists
            Token.objects.get_or_create(user=user)

            # Ensure free subscription exists
            Subscription.objects.get_or_create(user=user, defaults={'plan': 'free', 'status': 'active'})

            self.stdout.write(self.style.SUCCESS(f'  Created user "{username}" ({data["email"]})'))

        self.stdout.write(self.style.SUCCESS('seed_demo_users done.'))
