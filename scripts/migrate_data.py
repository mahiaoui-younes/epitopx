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
print("Migration des données: dna_sequence → api_dnasequence")
print("=" * 80)

# Activer les foreign keys
cursor.execute("SET FOREIGN_KEY_CHECKS=0")

# Récupérer toutes les données de l'ancienne table
cursor.execute("SELECT name, sequence FROM dna_sequence")
old_data = cursor.fetchall()

print(f"\n📋 Données à migrer: {len(old_data)} enregistrement(s)")

for name, sequence in old_data:
    # Vérifier si la séquence existe déjà dans api_dnasequence
    cursor.execute("SELECT id FROM api_dnasequence WHERE sequence = %s", (sequence,))
    existing = cursor.fetchone()
    
    if not existing:
        # Ajouter à api_dnasequence
        cursor.execute(
            "INSERT INTO api_dnasequence (name, sequence, created_at) VALUES (%s, %s, NOW(6))",
            (name, sequence)
        )
        print(f"  ✓ Migré: {name}")
    else:
        print(f"  ⚠️  Existe déjà: {name} (ID: {existing[0]})")

# Réactiver les foreign keys
cursor.execute("SET FOREIGN_KEY_CHECKS=1")

conn.commit()
cursor.close()
conn.close()

print("\n✅ Migration terminée!")
print("\nNous avons maintenant les données dans la bonne table (api_dnasequence)")
