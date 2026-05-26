#!/usr/bin/env python
"""
Test avec la séquence longue de l'utilisateur
"""
import requests
import json

# Séquence longue
sequence = "MKFFYLFVLFPILLKFCECGPFLPLDRQLNPIDFDPNDDQHPLDPDQLIDQIEPSEQPAQQEPIEPQQPTQPSTEPEELQPETVTVEVPEPVTSEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHATESTPTKASSSGDGAAVCHGKHHDYDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSYFTNSYKITVAFDWWLCDKPWQYALTLLALFGFSLLSPCLKAYREVLRAKAIRSFIFDCFLTHLFLFLIAFCAYALDFLLMLVVMTFNVGVFFAVITGYTVGYLVSSLAYSTLRSHPARSSSFSRINEDCC"

test_data = {
    'sequence': sequence,
    'method': 'core',
    'min_length': 9,
    'max_length': 35,  # Essayer avec 35 comme dans EpiTop1
    'min_score': 0.3,  # Score minimum plus bas
    'top_n': 20
}

print(f"Séquence length: {len(sequence)}")
print(f"Paramètres: min_length=9, max_length=35, min_score=0.3, top_n=20")
print()

# Make request
response = requests.post(
    'http://127.0.0.1:8000/api/epitopes/analyze/',
    json=test_data,
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 201:
    result = response.json()
    
    print("=" * 70)
    print("RÉSULTATS API")
    print("=" * 70)
    print(f"Analysis ID: {result['id']}")
    print(f"Total Epitopes Found: {result['epitope_count']}")
    print()
    
    # Display the formatted table
    if 'epitopes_table' in result:
        print(result['epitopes_table'])
    
    print()
    print("=" * 70)
    print("DÉTAILS JSON (premiers 9)")
    print("=" * 70)
    for i, epitope in enumerate(result['epitopes'][:9], 1):
        print(f"{i}. Pos {epitope['start']}-{epitope['end']}, "
              f"Len {epitope['length']}, "
              f"Score {epitope['score']:.4f}, "
              f"Seq: {epitope['sequence']}")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
