#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000/api"

print("=" * 60)
print("Test de persistance: Rechercher la séquence ajoutée")
print("=" * 60)

# Rechercher la séquence TEST001 qu'on vient d'ajouter
response = requests.post(
    f"{BASE_URL}/conversions/search/",
    data={"dna_sequence": "ATGATGATGATGATG"}
)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Réponse: {json.dumps(result, indent=2)}")

if result['found']:
    print("\n✅ La séquence a été trouvée dans la base!")
    print(f"   Nom: {result['name']}")
    print(f"   ID: {result['id']}")
    print(f"   Longueur: {result['sequence_length']}")
else:
    print("\n❌ Erreur: La séquence n'a pas été trouvée")

print("\n" + "=" * 60)
print("Test: Afficher toutes les séquences DNA")
print("=" * 60)

response = requests.get(f"{BASE_URL}/dna/")
print(f"Status: {response.status_code}")
sequences = response.json()
print(f"Nombre de séquences: {len(sequences)}")
for seq in sequences:
    print(f"\n  - ID: {seq['id']}")
    print(f"    Nom: {seq['name']}")
    print(f"    Séquence: {seq['sequence'][:50]}..." if len(seq['sequence']) > 50 else f"    Séquence: {seq['sequence']}")
