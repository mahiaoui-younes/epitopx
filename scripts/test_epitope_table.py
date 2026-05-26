#!/usr/bin/env python
"""
Test script to display the formatted epitope table from API response
"""
import requests
import json

# Test data
test_data = {
    'sequence': 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEW',
    'method': 'core',
    'min_length': 9,
    'max_length': 20,
    'min_score': 0.5,
    'top_n': 9
}

# Make request
response = requests.post(
    'http://127.0.0.1:8000/api/epitopes/analyze/',
    json=test_data,
    headers={'Content-Type': 'application/json'}
)

if response.status_code == 201:
    result = response.json()
    
    print("=" * 70)
    print("EPITOPE ANALYSIS RESULT")
    print("=" * 70)
    print(f"Analysis ID: {result['id']}")
    print(f"Sequence Header: {result['sequence_header']}")
    print(f"Sequence Length: {result['sequence_length']}")
    print(f"Method: {result['method']}")
    print(f"Total Epitopes Found: {result['epitope_count']}")
    print()
    
    # Display the formatted table
    if 'epitopes_table' in result:
        print(result['epitopes_table'])
    
    print()
    print("=" * 70)
    print("DETAILED EPITOPE DATA (JSON)")
    print("=" * 70)
    for epitope in result['epitopes'][:5]:  # Show first 5
        print(f"  Position: {epitope['start']}-{epitope['end']}")
        print(f"  Length: {epitope['length']}")
        print(f"  Score: {epitope['score']:.4f}")
        print(f"  Sequence: {epitope['sequence']}")
        print()
else:
    print(f"Error: {response.status_code}")
    print(response.json())
