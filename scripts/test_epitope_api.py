#!/usr/bin/env python3
"""
Test script for EpiTop1 API integration.
Tests all epitope analysis endpoints.
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

# Test sequences
TEST_SEQUENCES = {
    "short": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
    "medium": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKRQTLGQHDFSAGEGLYTHMKALRPDEDRLSPLHSVYVDQWDWERVMGDGERQFSTLKSTVEAIWAGIKATEAAVSEEFGLAPFLPDQIHFVHSQELLSRYPDLDAKGRERAIAKDLGAVFLVGIGGKLSDGHRHDVRAPDYDDWSTPSELGHAGLNGDILVWNPVLEDAFELSSMGIRVDADTLKHQLALTGDEDRLELEWHQALLRGEMPQTIGGGIGQSRLTMLLLQLPHIGQVQAGVWPAAVRESVPSLL",
    "fasta": ">Spike protein from SARS-CoV-2\nMFVFLVLLPLVSSTQWFVFLVLLPLVSST\nQWFVFLVLLPLVSSTQWFVFLVLLPLVSST",
}

def test_basic_epitope_analysis():
    """Test basic epitope analysis with core module"""
    print("\n" + "="*60)
    print("TEST 1: Basic Epitope Analysis (Core Module)")
    print("="*60)
    
    payload = {
        "sequence": TEST_SEQUENCES["short"],
        "method": "core",
        "min_score": 0.5,
        "top_n": 5
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/epitopes/analyze/",
            json=payload,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✓ Analysis ID: {data.get('id')}")
            print(f"✓ Sequence Header: {data.get('sequence_header')}")
            print(f"✓ Epitope Count: {data.get('epitope_count')}")
            print(f"✓ Found {len(data.get('epitopes', []))} epitopes:")
            
            for epi in data.get('epitopes', [])[:3]:  # Show first 3
                print(f"  - {epi['sequence']:20} (pos {epi['start']}-{epi['end']}, score: {epi['score']:.2f})")
            
            return data.get('id')
        else:
            print(f"✗ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        return None


def test_bio_module():
    """Test bio module analysis"""
    print("\n" + "="*60)
    print("TEST 2: Bio Module Analysis")
    print("="*60)
    
    payload = {
        "sequence": TEST_SEQUENCES["medium"],
        "method": "bio",
        "min_length": 10,
        "max_length": 18,
        "min_score": 0.6,
        "top_n": 10
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/epitopes/analyze/",
            json=payload,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✓ Analysis ID: {data.get('id')}")
            print(f"✓ Method: {data.get('method')}")
            print(f"✓ Epitope Count: {data.get('epitope_count')}")
            print(f"✓ Parameters:")
            print(f"  - Min Length: {data.get('min_length')}")
            print(f"  - Max Length: {data.get('max_length')}")
            print(f"  - Min Score: {data.get('min_score')}")
            return data.get('id')
        else:
            print(f"✗ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        return None


def test_fasta_format():
    """Test FASTA format parsing"""
    print("\n" + "="*60)
    print("TEST 3: FASTA Format Parsing")
    print("="*60)
    
    payload = {
        "sequence": TEST_SEQUENCES["fasta"],
        "method": "core"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/epitopes/analyze/",
            json=payload,
            timeout=30
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✓ Sequence Header parsed: {data.get('sequence_header')}")
            print(f"✓ Sequence Length: {data.get('sequence_length')}")
            print(f"✓ Epitope Count: {data.get('epitope_count')}")
        else:
            print(f"✗ Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_list_analyses():
    """Test listing all analyses"""
    print("\n" + "="*60)
    print("TEST 4: List All Analyses")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/epitopes/",
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Total Analyses: {data.get('count', len(data) if isinstance(data, list) else 0)}")
            
            analyses = data.get('results', data) if isinstance(data, dict) else data
            print(f"✓ Showing first {min(3, len(analyses))} analyses:")
            
            for analysis in analyses[:3]:
                print(f"  - ID {analysis['id']}: {analysis['sequence_header']} ({analysis.get('method', 'unknown')})")
        else:
            print(f"✗ Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_recent_analyses(limit=5):
    """Test getting recent analyses"""
    print("\n" + "="*60)
    print("TEST 5: Recent Analyses")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/epitopes/recent/?limit={limit}",
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Recent analyses (limit={limit}):")
            
            for analysis in data[:3]:
                print(f"  - ID {analysis['id']}: {analysis['sequence_header']} ({analysis.get('epitope_count', 0)} epitopes)")
        else:
            print(f"✗ Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_filter_by_method(method="core"):
    """Test filtering by method"""
    print("\n" + "="*60)
    print(f"TEST 6: Filter by Method ({method})")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/epitopes/by_method/?method={method}",
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Analyses with method '{method}':")
            print(f"  Total: {len(data)}")
            
            for analysis in data[:3]:
                print(f"  - ID {analysis['id']}: {analysis['sequence_header']}")
        else:
            print(f"✗ Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_get_detail(analysis_id):
    """Test getting analysis detail"""
    print("\n" + "="*60)
    print(f"TEST 7: Get Analysis Detail (ID: {analysis_id})")
    print("="*60)
    
    try:
        response = requests.get(
            f"{BASE_URL}/epitopes/{analysis_id}/",
            timeout=10
        )
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Analysis Details:")
            print(f"  ID: {data.get('id')}")
            print(f"  Header: {data.get('sequence_header')}")
            print(f"  Method: {data.get('method')}")
            print(f"  Sequence Length: {len(data.get('sequence', ''))}")
            print(f"  Parameters:")
            print(f"    - Min Length: {data.get('min_length')}")
            print(f"    - Max Length: {data.get('max_length')}")
            print(f"    - Min Score: {data.get('min_score')}")
            print(f"  Epitopes: {len(data.get('epitopes', []))}")
            print(f"  Created: {data.get('created_at')}")
        else:
            print(f"✗ Error: {response.text}")
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")


def test_invalid_input():
    """Test invalid input handling"""
    print("\n" + "="*60)
    print("TEST 8: Invalid Input Handling")
    print("="*60)
    
    invalid_payloads = [
        {
            "name": "Empty sequence",
            "payload": {"sequence": ""}
        },
        {
            "name": "Invalid characters",
            "payload": {"sequence": "MFVFLVLL@#$%PLVSSTQ"}
        },
        {
            "name": "Invalid method",
            "payload": {"sequence": "MFVFLVLLPLVSSTQ", "method": "invalid_method"}
        },
    ]
    
    for test_case in invalid_payloads:
        print(f"\nTesting: {test_case['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/epitopes/analyze/",
                json=test_case['payload'],
                timeout=10
            )
            
            if response.status_code >= 400:
                print(f"  ✓ Correctly rejected with status {response.status_code}")
            else:
                print(f"  ✗ Should have been rejected but got {response.status_code}")
                
        except Exception as e:
            print(f"  ✗ Exception: {str(e)}")


def main():
    """Run all tests"""
    print("\n" + "#"*60)
    print("# EpiTop1 API Integration Tests")
    print("#"*60)
    
    print("\nWARNING: Make sure Django server is running on http://localhost:8000")
    print("Start server with: python manage.py runserver")
    print("\nWaiting 2 seconds...")
    time.sleep(2)
    
    # Run tests
    analysis_id_1 = test_basic_epitope_analysis()
    time.sleep(1)
    
    analysis_id_2 = test_bio_module()
    time.sleep(1)
    
    test_fasta_format()
    time.sleep(1)
    
    test_list_analyses()
    time.sleep(1)
    
    test_recent_analyses(limit=5)
    time.sleep(1)
    
    test_filter_by_method("core")
    time.sleep(1)
    
    if analysis_id_1:
        test_get_detail(analysis_id_1)
        time.sleep(1)
    
    test_invalid_input()
    
    # Summary
    print("\n" + "#"*60)
    print("# Test Summary")
    print("#"*60)
    print("""
✓ All tests completed!

Next steps:
1. Check Django logs for any errors
2. Verify database has new EpitopeAnalysis records
3. Test with more real sequences
4. Integrate with frontend application
5. Configure production settings

For more information, see EPITOPE_API_DOCUMENTATION.md
    """)


if __name__ == "__main__":
    main()
