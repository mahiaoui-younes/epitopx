#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

print("🔧 FIXING TOKEN FOREIGN KEY...")

try:
    # First check the column types
    print("Checking column types...")
    cursor.execute("DESC authtoken_token")
    token_cols = cursor.fetchall()
    print("authtoken_token columns:")
    for col in token_cols:
        print(f"  {col}")
    
    cursor.execute("DESC api_user")
    user_cols = cursor.fetchall()
    print("api_user columns:")
    for col in user_cols:
        print(f"  {col}")
    
    # Drop old constraint
    print("\n1. Dropping old foreign key constraint...")
    cursor.execute("""
        ALTER TABLE authtoken_token 
        DROP FOREIGN KEY authtoken_token_user_id_35299eff_fk_auth_user_id
    """)
    print("✅ Old constraint dropped")
    
    # Add new constraint pointing to api_user
    print("2. Adding new foreign key constraint (pointing to api_user)...")
    cursor.execute("""
        ALTER TABLE authtoken_token 
        ADD CONSTRAINT authtoken_token_user_id_fk_api_user 
        FOREIGN KEY (user_id) REFERENCES api_user(id)
    """)
    print("✅ New constraint added")
    
    print("\n✨ FIXED! Token table now correctly references api_user")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
