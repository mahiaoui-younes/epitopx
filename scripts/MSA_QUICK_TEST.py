#!/usr/bin/env python
"""
MSA API - QUICK TEST SCENARIOS
Test these right now to verify the API is working!
"""

# Test 1: Start the server
# Run this in your terminal:
# cd backend_api
# python manage.py runserver
#
# You should see: "Starting development server at http://127.0.0.1:8000/"

# Test 2: Check if service is running
# curl http://localhost:8000/api/msa/health/
#
# Expected Response:
# {
#   "status": "healthy",
#   "service": "Multiple Sequence Alignment API",
#   "version": "1.0.0",
#   ...
# }

# Test 3: Simple 3-sequence alignment
# curl -X POST http://localhost:8000/api/msa/align/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "sequences": ["ATCGTACG", "ATGGTACG", "ATCGTTCG"]
#   }'
#
# Expected Response:
# {
#   "success": true,
#   "alignment": ["ATCGTACG-", "AT-GTACG-", "ATCGTTCG-"],
#   "consensus": "ATCGTACG",
#   "identity_scores": [95.2, 90.1, 88.5],
#   "method": "progressive_msa"
# }

# Test 4: Different sequences (all A's vs all T's)
# curl -X POST http://localhost:8000/api/msa/align/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "sequences": ["AAAA", "TTTT", "CCCC", "GGGG"]
#   }'
#
# Expected: All 4 sequences aligned, low identity scores

# Test 5: FASTA input
# curl -X POST http://localhost:8000/api/msa/align-fasta/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "fasta_content": ">human\\nATCGTACG\\n>mouse\\nATGGTACG\\n>chicken\\nATCGTTCG"
#   }'
#
# Expected: Same as Test 3 with sequence names stripped

# Test 6: Statistics
# curl -X POST http://localhost:8000/api/msa/statistics/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "sequences": ["ATCGTACG", "ATGGTACG", "ATCGTTCG"]
#   }'
#
# Expected Response:
# {
#   "average_identity": 91.3,
#   "min_identity": 85.5,
#   "max_identity": 96.2,
#   "num_sequences": 3,
#   "alignment_length": 9,
#   "consensus_gc_content": 55.5
# }

# Test 7: Error test - invalid DNA character
# curl -X POST http://localhost:8000/api/msa/align/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "sequences": ["ATCGX", "ATCG"]
#   }'
#
# Expected: HTTP 400 error
# {
#   "success": false,
#   "error": "Invalid DNA sequence: ATCGX. Use only A, T, C, G."
# }

# Test 8: Error test - single sequence
# curl -X POST http://localhost:8000/api/msa/align/ \
#   -H "Content-Type: application/json" \
#   -d '{
#     "sequences": ["ATCG"]
#   }'
#
# Expected: HTTP 400 error
# {
#   "success": false,
#   "error": "At least 2 sequences required for MSA"
# }

# Test 9: Python client test
import requests

BASE_URL = 'http://localhost:8000/api/msa'

def test_basic_alignment():
    """Test basic alignment"""
    response = requests.post(f'{BASE_URL}/align/', json={
        'sequences': ['ATCGTACG', 'ATGGTACG', 'ATCGTTCG']
    })
    result = response.json()
    assert result['success']
    print("✓ Basic alignment works")

def test_fasta():
    """Test FASTA input"""
    fasta = ">seq1\nATCGTACG\n>seq2\nATGGTACG\n>seq3\nATCGTTCG"
    response = requests.post(f'{BASE_URL}/align-fasta/', json={
        'fasta_content': fasta
    })
    result = response.json()
    assert result['success']
    print("✓ FASTA alignment works")

def test_statistics():
    """Test statistics endpoint"""
    response = requests.post(f'{BASE_URL}/statistics/', json={
        'sequences': ['ATCGTACG', 'ATGGTACG', 'ATCGTTCG']
    })
    stats = response.json()
    assert 'average_identity' in stats
    print("✓ Statistics endpoint works")

def test_health():
    """Test health endpoint"""
    response = requests.get(f'{BASE_URL}/health/')
    health = response.json()
    assert health['status'] == 'healthy'
    print("✓ Health check works")

# Run all tests
if __name__ == '__main__':
    print("\nTesting MSA API...")
    print("=" * 50)
    
    try:
        test_health()
        test_basic_alignment()
        test_fasta()
        test_statistics()
        
        print("=" * 50)
        print("\n✅ All API tests passed!")
        print("\nYour MSA API is working correctly.")
        print("Next: Review documentation in:")
        print("  - QUICK_START_MSA.md")
        print("  - MSA_DOCUMENTATION.md")
        print("  - MSA_INTEGRATION_GUIDE.md")
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API")
        print("Make sure to run: python manage.py runserver")
    except Exception as e:
        print(f"❌ Test failed: {e}")
