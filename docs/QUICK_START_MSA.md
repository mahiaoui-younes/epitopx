# MSA API - Quick Start Guide

## Installation

1. **App Already Integrated**: The bioinformatics app is registered in Django settings

2. **No Additional Dependencies**: Uses only Python standard library and Django/DRF

## Quick API Test

### Using Python Requests

```python
import requests
import json

# Test 1: Basic alignment
print("Test 1: Basic MSA Alignment")
response = requests.post('http://localhost:8000/api/msa/align/', json={
    "sequences": ["ATCGTACG", "ATGGTACG", "ATCGTTCG"],
    "match": 1,
    "mismatch": -1,
    "gap": -2
})

result = response.json()
print(f"Success: {result['success']}")
print(f"Consensus: {result['consensus']}")
print(f"Identity Scores: {result['identity_scores']}")
print(f"Alignment:\n")
for i, seq in enumerate(result['alignment']):
    print(f"  Seq {i+1}: {seq}")

# Test 2: FASTA input
print("\nTest 2: FASTA Input")
fasta_content = """>sequence_1
ATCGTACG
>sequence_2
ATGGTACG
>sequence_3
ATCGTTCG"""

response = requests.post('http://localhost:8000/api/msa/align-fasta/', json={
    "fasta_content": fasta_content
})
result = response.json()
print(f"Success: {result['success']}")

# Test 3: Statistics
print("\nTest 3: Alignment Statistics")
response = requests.post('http://localhost:8000/api/msa/statistics/', json={
    "sequences": ["ATCGTACG", "ATGGTACG", "ATCGTTCG"]
})
stats = response.json()
print(f"Average Identity: {stats['average_identity']}%")
print(f"Min Identity: {stats['min_identity']}%")
print(f"Max Identity: {stats['max_identity']}%")

# Test 4: Health Check
print("\nTest 4: Service Health")
response = requests.get('http://localhost:8000/api/msa/health/')
health = response.json()
print(f"Status: {health['status']}")
print(f"Version: {health['version']}")
```

### Using cURL

```bash
# Test alignment
curl -X POST http://localhost:8000/api/msa/align/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequences": ["ATCGTACG", "ATGGTACG", "ATCGTTCG"]
  }' | python -m json.tool

# Test FASTA input
curl -X POST http://localhost:8000/api/msa/align-fasta/ \
  -H "Content-Type: application/json" \
  -d '{
    "fasta_content": ">seq1\nATCGTACG\n>seq2\nATGGTACG"
  }' | python -m json.tool

# Health check
curl http://localhost:8000/api/msa/health/ | python -m json.tool
```

## Running Django Tests

```bash
# From backend_api directory
python manage.py test bioinformatics

# With verbose output
python manage.py test bioinformatics -v 2

# Run specific test class
python manage.py test bioinformatics.tests.TestNeedlemanWunsch
```

## Expected Output

### Sample Alignment Result
```json
{
  "success": true,
  "alignment": [
    "ATCGTACG-",
    "AT-GTACG-", 
    "ATCGTTCG-"
  ],
  "consensus": "ATCGTACG",
  "identity_scores": [95.2, 90.1, 88.5],
  "method": "progressive_msa",
  "num_sequences": 3,
  "alignment_length": 9
}
```

## Validation Examples

### Valid Input ✓
```json
{
  "sequences": ["ATCG", "ATCG", "ATCG"]
}
```

### Invalid Input ✗
```json
{
  "sequences": ["ATCGX", "ATCG"]  // X is not valid DNA
}
```

## Performance Estimates

| Input | Time (est.) | Notes |
|-------|-----------|-------|
| 3 sequences × 100 bp | < 100ms | Very fast |
| 10 sequences × 500 bp | < 500ms | Fast |
| 20 sequences × 1000 bp | 1-2 sec | Moderate |
| 50 sequences × 2000 bp | 5-10 sec | Slower |

## Next Steps

1. Start Django development server: `python manage.py runserver`
2. Test endpoints with provided examples
3. Review MSA_DOCUMENTATION.md for detailed algorithm information
4. Integrate into your frontend application

## Troubleshooting

**Server not responding?**
- Ensure Django is running: `python manage.py runserver`
- Check URL is correct: `http://localhost:8000/api/msa/align/`

**Invalid sequence error?**
- Only A, T, C, G characters are allowed
- Check for spaces, lowercase U, or other characters

**Alignment taking too long?**
- Reduce number of sequences
- Reduce sequence length
- Increase server capacity if needed
