#!/usr/bin/env python3
"""
Create or update a Django admin user from environment variables.

This helper is safe to run multiple times. It reads the following env vars:
  - DJANGO_ADMIN_USERNAME (default: 'xxx')
  - DJANGO_ADMIN_PASSWORD (default: 'Y12345678')
  - DJANGO_ADMIN_EMAIL (default: 'admin@example.com')
  - DJANGO_ADMIN_FORCE (if truthy, will reset password when user exists)

Usage:
  python scripts/create_admin_from_env.py

This script is intended to be called from deployment/startup scripts
to ensure an administrative account exists without interactive prompts.
"""
import os
import sys

try:
    import django
except Exception as e:
    print('Error: Django not available in this environment:', e)
    sys.exit(2)

# Ensure project root is on path when called from backend/ or repo root
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

username = os.environ.get('DJANGO_ADMIN_USERNAME', 'xxx')
password = os.environ.get('DJANGO_ADMIN_PASSWORD', 'Y12345678')
email = os.environ.get('DJANGO_ADMIN_EMAIL', 'admin@example.com')
force = os.environ.get('DJANGO_ADMIN_FORCE', '1').lower() in ('1', 'true', 'yes')

def main():
    try:
        user = User.objects.filter(username=username).first()
        if user:
            changed = False
            if force:
                user.set_password(password)
                changed = True
            if not user.is_staff:
                user.is_staff = True
                changed = True
            if not user.is_superuser:
                user.is_superuser = True
                changed = True
            # Optional custom flags
            if hasattr(user, 'is_admin') and not getattr(user, 'is_admin'):
                try:
                    user.is_admin = True
                except Exception:
                    pass
                changed = True
            if hasattr(user, 'is_email_verified') and not getattr(user, 'is_email_verified'):
                try:
                    user.is_email_verified = True
                except Exception:
                    pass
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if changed:
                user.save()
                print(f"✓ Admin updated: {username}")
            else:
                print(f"✓ Admin already configured: {username}")
        else:
            # create_superuser uses REQUIRED_FIELDS (email may be required)
            User.objects.create_superuser(username=username, email=email, password=password)
            u = User.objects.get(username=username)
            try:
                if hasattr(u, 'is_admin'):
                    u.is_admin = True
                if hasattr(u, 'is_email_verified'):
                    u.is_email_verified = True
            except Exception:
                pass
            u.save()
            print(f"✅ Admin created: {username}")
        return 0
    except Exception as exc:
        print('Error creating/updating admin:', exc)
        return 1

if __name__ == '__main__':
    sys.exit(main())
