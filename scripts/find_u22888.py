#!/usr/bin/env python
import MySQLdb

conn = MySQLdb.connect(
    user='root',
    passwd='',
    db='backend_db',
    host='127.0.0.1'
)
cursor = conn.cursor()

print("=" * 80)
print("Toutes les tables dans backend_db:")
print("=" * 80)
cursor.execute("SHOW TABLES")
tables = cursor.fetchall()
for table in tables:
    print(f"  - {table[0]}")

print("\n" + "=" * 80)
print("Recherche de U22888.1 dans toutes les tables:")
print("=" * 80)

# Chercher dans api_dnasequence
print("\n🔍 Cherche dans api_dnasequence...")
cursor.execute("SELECT * FROM api_dnasequence WHERE name LIKE '%U22888%'")
result = cursor.fetchone()
if result:
    print(f"  ✓ Trouvé: {result}")
else:
    print(f"  ✗ Pas trouvé")

# Chercher dans dna_sequence (ancienne table?)
cursor.execute("SHOW TABLES LIKE 'dna_sequence'")
if cursor.fetchone():
    print("\n🔍 Cherche dans dna_sequence...")
    cursor.execute("SELECT * FROM dna_sequence WHERE name LIKE '%U22888%'")
    result = cursor.fetchone()
    if result:
        print(f"  ✓ Trouvé: {result}")
    else:
        print(f"  ✗ Pas trouvé")

cursor.close()
conn.close()
