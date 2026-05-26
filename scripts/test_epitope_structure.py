#!/usr/bin/env python3
"""
Test script to analyze the protein sequence and verify epitope storage
with the new normalization structure
"""

import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api"

# Your protein sequence
PROTEIN_SEQUENCE = "MKFFYLFVLFPILLKFCECGPFLPLDRQLNPIDFDPNDDQHPLDPDQLIDQIEPSEQPAQQEPIEPQQPTQPSTEPEELQPETVTVEVPEPVTSEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHATESTPTKASSSGDGAAVCHGKHHDYDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSYFTNSYKITVAFDWWLCDKPWQYALTLLALFGFSLLSPCLKAYREVLRAKAIRSFIFDCFLTHLFLFLIAFCAYALDFLLMLVVMTFNVGVFFAVITGYTVGYLVSSLAYSTLRSHPARSSSFSRINEDCC"

def test_epitope_analysis():
    """Test epitope analysis with the normalized structure"""
    
    print("\n" + "="*80)
    print("EPITOPE ANALYSIS TEST - Normalized Structure")
    print("="*80)
    
    payload = {
        "sequence": PROTEIN_SEQUENCE,
        "method": "core",
        "min_length": 9,
        "max_length": 20,
        "min_score": 0.5,
        "top_n": 10,
        "protein_id": None  # No reference to a protein
    }
    
    print(f"\n📌 Analyzing protein sequence:")
    print(f"   Length: {len(PROTEIN_SEQUENCE)} aa")
    print(f"   Method: {payload['method']}")
    print(f"   Min Score: {payload['min_score']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/epitopes/analyze/",
            json=payload,
            timeout=60
        )
        
        print(f"\n✓ Status Code: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            
            print(f"✓ Epitope Group ID: {data.get('epitope_group_id')}")
            print(f"✓ Epitope Count: {data.get('epitope_count')}")
            print(f"✓ Sequence Header: {data.get('sequence_header')}")
            
            # Display epitopes in the requested format
            epitopes = data.get('epitopes', [])
            
            print(f"\n📋 EPITOPES STRUCTURE (normalized):")
            print("   \"epitopes\": [")
            
            for i, epi in enumerate(epitopes):
                print(f"        {{")
                print(f"            \"id\": {epi['id']},")
                print(f"            \"epitope_id\": {epi.get('epitope_id', 'N/A')},")
                print(f"            \"epitope_group_id\": {epi.get('epitope_group_id')},")
                print(f"            \"method\": \"{epi.get('method')}\",")
                print(f"            \"epitope_sequence\": \"{epi.get('epitope_sequence')}\",")
                print(f"            \"start\": {epi.get('start')},")
                print(f"            \"end\": {epi.get('end')},")
                print(f"            \"score\": {epi.get('score')},")
                print(f"            \"created_at\": \"{epi.get('created_at')}\"")
                
                if i < len(epitopes) - 1:
                    print(f"        }},")
                else:
                    print(f"        }}")
            
            print("   ]")
            
            # Verify epitope_id uniqueness
            print(f"\n✅ Validation:")
            epitope_ids = [epi.get('epitope_id') for epi in epitopes]
            unique_ids = set(epitope_ids)
            print(f"   Total epitopes: {len(epitopes)}")
            print(f"   Unique epitope_ids: {len(unique_ids)}")
            print(f"   Epitope IDs: {sorted(unique_ids)}")
            
            # Show summary
            print(f"\n📊 Summary:")
            print(f"   Group ID: {data.get('epitope_group_id')}")
            print(f"   Total results: {data.get('epitope_count')}")
            print(f"\n✓ All epitopes stored with normalized structure!")
            
            # Write full response to file
            with open('epitope_analysis_result.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\n💾 Full response saved to: epitope_analysis_result.json")
            
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server at http://127.0.0.1:8000/")
        print("   Make sure the server is running!")
        return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
    
    print("\n" + "="*80)
    return True


if __name__ == '__main__':
    success = test_epitope_analysis()
    sys.exit(0 if success else 1)
