import os
import sys
import django

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create admin
try:
    admin = User.objects.get(username='admin')
    admin.set_password('admin123')
    admin.is_admin = True
    admin.is_staff = True
    admin.is_superuser = True
    admin.save()
    print("✓ Admin updated")
except User.DoesNotExist:
    admin = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123',
    )
    admin.is_admin = True
    admin.save()
    print("✅ Admin created")

# Create test user
try:
    user = User.objects.get(username='testuser')
    user.set_password('test123')
    user.is_admin = False
    user.save()
    print("✓ Testuser updated")
except User.DoesNotExist:
    user = User.objects.create_user(
        username='testuser',
        email='testuser@example.com',
        password='test123',
    )
    user.is_admin = False
    user.save()
    print("✅ Testuser created")

print("\n✨ Accounts ready!")
print("Admin: admin / admin123")
print("User: testuser / test123")
