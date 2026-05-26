#!/usr/bin/env python
import MySQLdb

conn = MySQLdb.connect(
    user='root',
    passwd='',
    db='backend_db',
    host='127.0.0.1'
)
cursor = conn.cursor()

# Afficher toutes les séquences DNA
cursor.execute("SELECT id, name, sequence, created_at FROM api_dnasequence ORDER BY id DESC")
results = cursor.fetchall()

print("=" * 80)
print("Contenu de la table api_dnasequence:")
print("=" * 80)
print(f"Nombre total de séquences: {len(results)}\n")

for row in results:
    id_seq, name, sequence, created_at = row
    print(f"ID: {id_seq}")
    print(f"Nom: {name}")
    print(f"Séquence: {sequence}")
    print(f"Créé à: {created_at}")
    print("-" * 80)

cursor.close()
conn.close()
