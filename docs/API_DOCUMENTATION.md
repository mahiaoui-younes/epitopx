# API DNA → RNA → Protéine

## Endpoints disponibles

### 1. Conversion DNA → RNA → Protéine  
**POST** `/api/conversions/convert/`

Convertit une séquence ADN en ARN et protéine.

**Request body:**
```json
{
  "dna_sequence": "ATGATGATGATG"
}
```

**Response (201 Created):**
```json
{
  "dna": "ATGATGATGATG",
  "rna": "AUGAUGAUGAUG",
  "protein": "MMMM",
  "id": 1
}
```

**Erreurs:**
- 400: Séquence ADN invalide (only A, T, G, C allowed)

---

### 2. Historique des conversions
**GET** `/api/conversions/history/`

Récupère l'historique de toutes les conversions.

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "original_dna": "ATGATGATGATG",
    "rna": "AUGAUGAUGAUG",
    "protein": "MMMM",
    "created_at": "2026-02-07T19:17:04.123456Z"
  }
]
```

---

### 3. Gestion des séquences ADN
**GET** `/api/dna/` - Liste toutes les séquences ADN sauvegardées
**POST** `/api/dna/` - Créer une nouvelle séquence ADN
**GET** `/api/dna/{id}/` - Récupérer une séquence ADN
**PUT** `/api/dna/{id}/` - Modifier une séquence ADN
**DELETE** `/api/dna/{id}/` - Supprimer une séquence ADN

---

## Exemples d'utilisation

### Exemple 1: Conversion simple
```bash
curl -X POST http://localhost:8000/api/conversions/convert/ \
  -H "Content-Type: application/json" \
  -d '{"dna_sequence": "ATGATGATGATG"}'
```

### Exemple 2: Voir l'historique
```bash
curl http://localhost:8000/api/conversions/history/
```

### Exemple 3: Sauvegarder une séquence ADN
```bash
curl -X POST http://localhost:8000/api/dna/ \
  -H "Content-Type: application/json" \
  -d '{"name": "Gene A", "sequence": "ATGATGATGATG"}'
```

---

## Code génétique utilisé

La table de code génétique standard est implémentée pour traduire les codons ARN en acides aminés:
- AUG → M (Méthionine)
- GUC → V (Valine)
- GCC → A (Alanine)
- Etc...

Les codons stop (TAA, TAG, TGA en ADN / UAA, UAG, UGA en ARN) sont représentés par * 

---

## Notes pour le frontend

1. **Port**: Le serveur tourne sur `http://localhost:8000`
2. **Format**: Toutes les réponses sont en JSON
3. **Validation**: L'API valide les séquences ADN (A, T, G, C seulement)
4. **Historique**: Chaque conversion est automatiquement sauvegardée en base de données

---

## Modèles de données

### DNASequence
```
{
  "id": integer,
  "name": string (200 chars max),
  "sequence": string,
  "created_at": datetime
}
```

### ProteinConversion
```
{
  "id": integer,
  "original_dna": string,
  "rna": string,
  "protein": string,
  "created_at": datetime
}
```
