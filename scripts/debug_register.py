#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()

# Check tables
print("=== CHECKING TABLES ===")
cursor = connection.cursor()
cursor.execute("SHOW TABLES LIKE '%user%'")
tables = cursor.fetchall()
print(f"User-related tables: {[t[0] for t in tables]}")

# Check token table structure
print("\n=== TOKEN TABLE STRUCTURE ===")
cursor.execute("DESCRIBE authtoken_token")
columns = cursor.fetchall()
for col in columns:
    print(f"  {col}")

# Check foreign key constraints
print("\n=== FOREIGN KEY CONSTRAINTS ===")
cursor.execute("""
    SELECT CONSTRAINT_NAME, TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_NAME = 'authtoken_token'
""")
constraints = cursor.fetchall()
for const in constraints:
    print(f"  {const}")

# Try to create a test user and see where it fails
print("\n=== CREATING TEST USER ===")
try:
    # Delete if exists
    User.objects.filter(username='debug_user').delete()
    
    # Create user
    user = User.objects.create_user(
        username='debug_user',
        email='debug@test.com',
        password='debugpass123',
        is_admin=False
    )
    print(f"✅ User created: {user.id = }, {user.username = }")
    
    # Query to verify user exists
    existing = User.objects.get(id=user.id)
    print(f"✅ User verified from DB: {existing.id = }")
    
    # Try to create token
    print("Creating token...")
    token, created = Token.objects.get_or_create(user=existing)
    print(f"✅ Token created: {token.key = }")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
