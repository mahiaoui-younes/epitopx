#!/usr/bin/env python
"""Script to create test users"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create admin user
admin, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'email': 'admin@example.com',
        'is_staff': True,
        'is_superuser': True,
        'is_admin': True,
    }
)
if created:
    admin.set_password('admin123')
    admin.save()
    print("✅ Admin user created: username=admin, password=admin123")
else:
    print("✓ Admin user already exists")

# Create test user
user, created = User.objects.get_or_create(
    username='testuser',
    defaults={
        'email': 'testuser@example.com',
        'is_admin': False,
    }
)
if created:
    user.set_password('test123')
    user.save()
    print("✅ Test user created: username=testuser, password=test123")
else:
    print("✓ Test user already exists")

# Create another admin for testing
admin2, created = User.objects.get_or_create(
    username='admin_user',
    defaults={
        'email': 'admin2@example.com',
        'is_admin': True,
    }
)
if created:
    admin2.set_password('admin456')
    admin2.save()
    print("✅ Admin user created: username=admin_user, password=admin456")
else:
    print("✓ Admin user already exists")

print("\n🎯 Users created successfully!")
