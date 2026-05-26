# API Testing Guide - Epitope Analysis

## Base URL
```
http://127.0.0.1:8000/api/
```

## Important: Start Server First
```bash
cd c:\Users\asus\Desktop\new\backend_api\backend_api
python manage.py runserver
```

---

## 1. ANALYZE EPITOPES (Main Endpoint) ✓

### POST `/epitope-analysis/analyze/`

Analyzes a protein sequence and returns predicted epitopes with protein_id reference.

#### Parameters:
```json
{
  "sequence": "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDE...",
  "protein_id": 14,
  "method": "core",
  "min_length": 9,
  "max_length": 20,
  "min_score": 0.5,
  "top_n": 20
}
```

**Parameter Details:**
- `sequence` (required): Protein sequence (FASTA format or raw amino acids)
- `protein_id` (optional): ID of existing protein to associate epitopes with. If NOT provided, creates new protein. If provided, adds epitopes to that protein.
- `method` (optional, default="core"): One of:
  - `"core"` - 5 core hydrophobicity methods
  - `"bio"` - 7 bio methods
  - `"iedb"` - IEDB Tools API
- `min_length` (optional, default=9): Minimum epitope length
- `max_length` (optional, default=20): Maximum epitope length
- `min_score` (optional, default=0.5): Minimum epitope score (0-1)
- `top_n` (optional, default=20): Max results to return

---

## 2. TEST COMMANDS

### Using cURL (Windows PowerShell)

#### Test 0: First - Get List of Proteins
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/proteins/" -Method GET | ConvertTo-Json -Depth 3
```
This shows all proteins with their IDs. Use an ID for Test 2.

#### Test 1: Simple Analysis (Create New Protein) ✓ Recommended
```powershell
$body = @{
    sequence = "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDNFPPKDKDHLKF"
    method = "core"
    min_score = 0.5
    top_n = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/epitope-analysis/analyze/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

#### Test 1B: Analysis with Existing Protein ID ✓ Use This for Existing Proteins
```powershell
$body = @{
    protein_id = 14
    sequence = "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDNFPPKDKDHLKF"
    method = "core"
    min_score = 0.5
    top_n = 10
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/epitope-analysis/analyze/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```
⭐ If you know the protein_id, add it here to associate epitopes with that protein!

#### Test 2: With All Parameters
```powershell
$body = @{
    sequence = "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDNFPPKDKDHLKF"
    method = "core"
    min_length = 8
    max_length = 20
    min_score = 0.55
    top_n = 15
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/epitope-analysis/analyze/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

#### Test 3: Using Bio Method (More Methods)
```powershell
$body = @{
    sequence = "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDNFPPKDKDHLKF"
    method = "bio"
    min_score = 0.5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/epitope-analysis/analyze/" `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```

---

## 3. EXPECTED RESPONSE

### Success Response (200 OK)
```json
{
  "success": true,
  "protein_id": 14,
  "protein_name": "User_Input_Sequence",
  "epitope_count": 7,
  "method": "core",
  "epitopes": [
    {
      "id": 43,
      "protein_id": 14,
      "epitope_id": 1,
      "epitope_sequence": "YDSDGKESKSDHDKRPKDKK",
      "sequence_position": "152-171",
      "length": 20,
      "score": 0.8842,
      "start": 152,
      "end": 171,
      "method": "core",
      "hopp_woods": 0.85,
      "kyte_doolittle": 0.72,
      "karplus_schulz": 0.60,
      "emini": 0.75,
      "kolaskar": 0.80,
      "created_at": "2026-03-09T19:20:00Z"
    },
    {
      "id": 44,
      "protein_id": 14,
      "epitope_id": 2,
      "epitope_sequence": "TSEEPKESDQTEEQKHEEPE",
      "sequence_position": "93-112",
      "length": 20,
      "score": 0.8680,
      "start": 93,
      "end": 112,
      "method": "core",
      ...more fields...
    }
  ]
}
```

### Error Response (400 Bad Request)
```json
{
  "error": "Invalid protein sequence. Contains invalid amino acid characters."
}
```

---

## 4. IMPORTANT FIELDS IN RESPONSE

| Field | Type | Description |
|-------|------|-------------|
| `protein_id` | int | **Reference to the protein** - All epitopes from same protein have same protein_id |
| `epitope_id` | int | Sequential ID (1, 2, 3...) for epitopes in this protein |
| `epitope_sequence` | string | The actual epitope amino acid sequence |
| `score` | float | Overall prediction score (0-1) |
| `start`, `end` | int | Position in protein sequence |
| `hopp_woods`, `kyte_doolittle`, etc | float | Individual method scores |

---

## 5. LIST ALL EPITOPES

### GET `/epitope-analysis/`

Get all epitopes stored in database:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/epitope-analysis/" -Method GET
```

---

## 6. GET SPECIFIC EPITOPE

### GET `/epitope-analysis/{id}/`

Get a single epitope:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/epitope-analysis/43/" -Method GET
```

---

## 7. GET PROTEIN INFO

### GET `/proteins/{id}/`

Get protein and its epitopes:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/proteins/14/" -Method GET
```

Response:
```json
{
  "id": 14,
  "name": "User_Input_Sequence",
  "sequence": "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDNFPPKDKDHLKF...",
  "organism": "Unknown",
  "description": "",
  "method": "core",
  "epitope_count": 7,
  "created_at": "2026-03-09T19:20:00Z",
  "updated_at": "2026-03-09T19:20:00Z"
}
```

---

## 8. QUICK TEST PYTHON SCRIPT

Save as `test_api.py`:

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

# Test sequence
SEQUENCE = "YDSDGKESKSDHDKRPKDKKPFVPKTSQCCGSVDDQHPLDNFPPKDKDHLKF"

# Request data
payload = {
    "sequence": SEQUENCE,
    "method": "core",
    "min_score": 0.5,
    "top_n": 10
}

print("=" * 80)
print("TESTING EPITOPE ANALYSIS API")
print("=" * 80)
print("\nRequest:")
print(json.dumps(payload, indent=2))

# Make request
response = requests.post(f"{BASE_URL}/epitope-analysis/analyze/", json=payload)

print(f"\nStatus Code: {response.status_code}")
print("\nResponse:")
print(json.dumps(response.json(), indent=2))

# Extract key info
if response.status_code == 200:
    data = response.json()
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✓ Protein ID: {data.get('protein_id')}")
    print(f"✓ Epitopes found: {data.get('epitope_count')}")
    print(f"✓ Method used: {data.get('method')}")
    
    print("\nEpitope List:")
    for ep in data.get('epitopes', [])[:5]:
        print(f"  [{ep['epitope_id']}] {ep['epitope_sequence']:20s} @ {ep['start']}-{ep['end']} (score: {ep['score']:.4f}, protein_id: {ep['protein_id']})")
```

Run:
```bash
python test_api.py
```

---

## 9. POSTMAN COLLECTION

Import file: [Postman_Collection.json](Postman_Collection.json) or [EpiTop1_API.postman_collection.json](EpiTop1_API.postman_collection.json)

Then run requests from the collection.

---

## 10. DATABASE QUERY

Check stored epitopes:
```bash
python manage.py shell
```

```python
from api.models import Protein, Epitope

# Get all proteins
proteins = Protein.objects.all()
for p in proteins:
    print(f"Protein ID {p.id}: {p.name} ({p.epitopes.count()} epitopes)")
    for ep in p.epitopes.all():
        print(f"  - epitope_id={ep.epitope_id}, protein_id={ep.protein_id}, seq={ep.epitope_sequence}")
```

---

## 11. VALID AMINO ACIDS

Accepted characters:
```
A C D E F G H I K L M N P Q R S T V W Y * X -
```

---

## SUCCESS CRITERIA ✓

When testing, verify:
- ✅ HTTP 200 response
- ✅ All epitopes have `protein_id` (same value)
- ✅ All epitopes have unique `epitope_id` (1, 2, 3...)
- ✅ `epitope_sequence` is populated (not empty)
- ✅ All hydrophobicity scores present
- ✅ Results sorted by `score` (descending)
