#!/usr/bin/env python
import MySQLdb

conn = MySQLdb.connect(
    user='root',
    passwd='',
    db='backend_db',
    host='127.0.0.1'
)
cursor = conn.cursor()

# Disable foreign key checks
cursor.execute("SET FOREIGN_KEY_CHECKS=0")

# List of tables to drop
tables = [
    'django_migrations',
    'api_dnaseq uence',
    'api_article',
    'api_protein',
    'api_proteinconversion',
    'django_admin_log',
    'django_content_type',
    'auth_permission',
    'auth_group_permissions',
    'auth_user_groups',
    'auth_group',
    'auth_user',
    'django_session',
]

for table in tables:
    try:
        # Fix the table name (remove extra space)
        table = table.replace(' uence', 'uence')
        cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
        print(f"Dropped table: {table}")
    except Exception as e:
        print(f"Could not drop table {table}: {e}")

# Re-enable foreign key checks
cursor.execute("SET FOREIGN_KEY_CHECKS=1")

conn.commit()
cursor.close()
conn.close()

print("All Django tables dropped successfully!")
