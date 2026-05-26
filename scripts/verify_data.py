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
print("Vérification de la table api_dnasequence")
print("=" * 80)

# Vérifier le nombre de lignes
cursor.execute("SELECT COUNT(*) FROM api_dnasequence")
count = cursor.fetchone()[0]
print(f"\nNombre total de séquences: {count}")

# Afficher toutes les séquences avec détails
print("\n" + "=" * 80)
cursor.execute("""
SELECT id, name, sequence, created_at FROM api_dnasequence 
ORDER BY id DESC
""")
results = cursor.fetchall()

for row in results:
    id_seq, name, sequence, created_at = row
    print(f"\nID: {id_seq} | Nom: {name}")
    print(f"Séquence ({len(sequence)} caractères): {sequence}")
    print(f"Créé: {created_at}")
    print("-" * 80)

# Vérifier la structure de la table
print("\n" + "=" * 80)
print("Structure de la table:")
print("=" * 80)
cursor.execute("SHOW COLUMNS FROM api_dnasequence")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[0]}: {col[1]}")

cursor.close()
conn.close()
