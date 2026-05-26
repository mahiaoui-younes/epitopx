#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

print("🔧 FIXING TOKEN TABLE...")

try:
    # 1. Modify the user_id column type
    print("1. Converting user_id from int(11) to bigint(20)...")
    cursor.execute("""
        ALTER TABLE authtoken_token 
        MODIFY user_id bigint NOT NULL
    """)
    print("✅ Column type converted")
    
    # 2. Add foreign key constraint  
    print("2. Adding foreign key constraint...")
    cursor.execute("""
        ALTER TABLE authtoken_token 
        ADD CONSTRAINT authtoken_token_user_id_fk 
        FOREIGN KEY (user_id) REFERENCES api_user(id) ON DELETE CASCADE
    """)
    print("✅ Foreign key added")
    
    print("\n✨ SUCCESS! Registration should now work!")
    
except Exception as e:
    print(f"❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
