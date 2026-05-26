#!/usr/bin/env python
import requests
import json

BASE_URL = "http://localhost:8000/api"

print("=" * 60)
print("Test API: Recherche DNA")
print("=" * 60)

# Test search - rechercher une séquence qui ne existe pas
response = requests.post(
    f"{BASE_URL}/conversions/search/",
    data={"dna_sequence": "ATGCGCGC"}
)
print(f"Status: {response.status_code}")
print(f"Réponse: {json.dumps(response.json(), indent=2)}")

print("\n" + "=" * 60)
print("Test API: Ajouter une séquence DNA")
print("=" * 60)

# Test add - ajouter une nouvelle séquence
response = requests.post(
    f"{BASE_URL}/dna/add_sequence/",
    data={"name": "TEST001", "dna_sequence": "ATGATGATGATGATG"}
)
print(f"Status: {response.status_code}")
print(f"Réponse: {json.dumps(response.json(), indent=2)}")

print("\n" + "=" * 60)
print("Test API: Conversion DNA → RNA → Protéine")
print("=" * 60)

# Test conversion
response = requests.post(
    f"{BASE_URL}/conversions/convert/",
    json={"dna_sequence": "ATGATGATGATGATG"},
    headers={"Content-Type": "application/json"}
)
print(f"Status: {response.status_code}")
print(f"Réponse: {json.dumps(response.json(), indent=2)}")

print("\n✅ Tests terminés!")
