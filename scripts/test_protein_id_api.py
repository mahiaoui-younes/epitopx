#!/usr/bin/env python3
"""Test epitope analysis with protein_id"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

# Test 1: Without protein_id (creates new protein)
print("=" * 80)
print("TEST 1: WITHOUT protein_id (Creates new protein)")
print("=" * 80)

payload1 = {
    "sequence": "LKBHINIKKHIBILGYUGGU",
    "method": "core",
    "min_length": 9,
    "max_length": 20,
    "min_score": 0.5,
    "top_n": 9
}

print("\nRequest:")
print(json.dumps(payload1, indent=2))

response1 = requests.post(f"{BASE_URL}/epitopes/analyze/", json=payload1)
print(f"\nStatus: {response1.status_code}")

if response1.status_code == 201:
    data1 = response1.json()
    print(f"✓ Success!")
    print(f"  Protein ID: {data1.get('protein_id')}")
    print(f"  Epitopes found: {data1.get('epitope_count')}")
    print("\nResponse:")
    print(json.dumps(data1, indent=2)[:500] + "...")
    
    protein_id = data1.get('protein_id')
    
    # Test 2: WITH protein_id (add epitopes to existing protein)
    print("\n" + "=" * 80)
    print(f"TEST 2: WITH protein_id={protein_id} (Add to existing protein)")
    print("=" * 80)
    
    payload2 = {
        "protein_id": protein_id,
        "sequence": "LKBHINIKKHIBILGYUGGU",
        "method": "bio",  # Different method
        "min_score": 0.5,
        "top_n": 5
    }
    
    print("\nRequest:")
    print(json.dumps(payload2, indent=2))
    
    response2 = requests.post(f"{BASE_URL}/epitopes/analyze/", json=payload2)
    print(f"\nStatus: {response2.status_code}")
    
    if response2.status_code == 201:
        data2 = response2.json()
        print(f"✓ Success!")
        print(f"  Protein ID: {data2.get('protein_id')} (Same protein)")
        print(f"  Epitopes found: {data2.get('epitope_count')}")
        print(f"  Method: {data2.get('method')}")
else:
    print(f"✗ Error: {response1.text}")
