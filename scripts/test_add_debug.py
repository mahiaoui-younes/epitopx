#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Nouvelle séquence à ajouter
test_name = "NOUVELLE_SEQUENCE"
test_dna = "ATGCGATCGATCG"

print("=" * 60)
print(f"Test d'ajout de séquence: {test_name}")
print(f"Séquence: {test_dna}")
print("=" * 60)

# Avant: Vérifier si elle existe déjà
print("\n1️⃣ Recherche AVANT ajout...")
response_search_before = requests.post(
    f"{BASE_URL}/conversions/search/",
    data={"dna_sequence": test_dna}
)
print(f"   Réponse: {response_search_before.json()}")

# Ajouter la séquence
print("\n2️⃣ Ajout de la séquence...")
response_add = requests.post(
    f"{BASE_URL}/dna/add_sequence/",
    data={"name": test_name, "dna_sequence": test_dna}
)
print(f"   Status: {response_add.status_code}")
print(f"   Réponse: {json.dumps(response_add.json(), indent=2)}")

# Après: Vérifier que c'est bien ajouté
print("\n3️⃣ Recherche APRÈS ajout...")
response_search_after = requests.post(
    f"{BASE_URL}/conversions/search/",
    data={"dna_sequence": test_dna}
)
search_result = response_search_after.json()
print(f"   Réponse: {search_result}")

if search_result['found']:
    print(f"\n✅ SUCCÈS! La séquence a été ajoutée et trouvée!")
    print(f"   - ID: {search_result['id']}")
    print(f"   - Nom: {search_result['name']}")
else:
    print(f"\n❌ ERREUR! La séquence n'a pas été trouvée après l'ajout")
