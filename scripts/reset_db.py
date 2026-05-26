#!/usr/bin/env python3
"""
Reset database to work with the new simplified 2-table structure
"""

import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command

print("="*80)
print("RESETTING DATABASE FOR NEW 2-TABLE STRUCTURE")
print("="*80)

# Step 1: Delete all migration history
print("\n🗑️  Cleaning migration history...")
try:
    call_command('migrate', 'api', 'zero', '--noinput')
    print("✓ Migration history cleared")
except Exception as e:
    print(f"⚠️  Could not clear history: {e}")

# Step 2: Delete migration files except __init__.py
print("\n🗑️  Cleaning migration files...")
migration_dir = 'api/migrations'
for file in os.listdir(migration_dir):
    if file not in ['__init__.py', '__pycache__']:
        file_path = os.path.join(migration_dir, file)
        try:
            os.remove(file_path)
            print(f"✓ Deleted {file}")
        except Exception as e:
            print(f"⚠️  Could not delete {file}: {e}")

# Step 3: Create new migrations
print("\n📝 Creating new migrations...")
try:
    call_command('makemigrations', 'api')
    print("✓ New migrations created")
except Exception as e:
    print(f"❌ Error creating migrations: {e}")
    sys.exit(1)

# Step 4: Apply fresh migrations
print("\n📝 Applying migrations...")
try:
    call_command('migrate', 'api')
    print("✓ Migrations applied successfully")
except Exception as e:
    print(f"❌ Error applying migrations: {e}")
    sys.exit(1)

print("\n" + "="*80)
print("✅ DATABASE RESET COMPLETE!")
print("="*80)
print("\n✓ Database is now ready with 2-table structure:")
print("  - Protein table")
print("  - Epitope table (linked to Protein)")
print("\nYou can now:")
print("  1. Restart the server")
print("  2. Send requests to find epitopes")
print("="*80 + "\n")
