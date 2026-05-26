# EpiTop1 - B-Cell Epitope Prediction API

## Vue d'ensemble

Cette API intègre l'outil de prédiction d'épitopes **EpiTop1** dans le backend Django. Elle permet de prédire des épitopes B-linéaires à partir de séquences protéiques en utilisant plusieurs méthodes bioinformatiques validées scientifiquement.

---

## Endpoints disponibles

### 1. Analyse d'épitopes
**POST** `/api/epitopes/analyze/`

Prédis des épitopes B-linéaires à partir d'une séquence protéique.

**Paramètres:**

| Paramètre | Type | Par défaut | Description |
|-----------|------|-----------|-------------|
| `sequence` | string | **requis** | Séquence protéique brute ou format FASTA |
| `method` | string | "core" | Méthode: `core`, `bio`, ou `iedb` |
| `min_length` | integer | 9 | Longueur minimale d'épitope |
| `max_length` | integer | 20 | Longueur maximale d'épitope |
| `min_score` | float | 0.5 | Score minimum (0-1) |
| `top_n` | integer | 20 | Nombre d'épitopes à retourner |
| `pdb_file` | file | null | Structure PDB pour calcul SASA (optionnel) |
| `chain_id` | string | "A" | Chaîne PDB |

**Request (JSON):**
```json
{
  "sequence": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
  "method": "core",
  "min_length": 9,
  "max_length": 20,
  "min_score": 0.5,
  "top_n": 20
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "sequence_header": "Spike protein",
  "sequence_length": 30,
  "method": "core",
  "epitope_count": 5,
  "epitopes": [
    {
      "start": 1,
      "end": 15,
      "sequence": "MFVFLVLLPLVSST",
      "length": 15,
      "score": 0.78,
      "hopp_woods": 0.65,
      "kyte_doolittle": 0.72,
      "karplus_schulz": 0.81,
      "emini": 0.85,
      "kolaskar": 0.74
    }
  ],
  "epitopes_table": "Top candidates:\n  Rank         Pos   Len   Score Sequence\n  ............................................................\n     1       1-15    15   0.7800  MFVFLVLLPLVSST",
  "residue_scores": [
    {
      "position": 1,
      "amino_acid": "M",
      "global_score": 0.65,
      "hydrophilicity": 0.45,
      "hydrophobicity": 0.52,
      "flexibility": 0.70,
      "accessibility": 0.60,
      "antigenicity": 0.55
    }
  ],
  "message": "Analysis completed successfully"
}
```

**Champs de réponse:**

| Champ | Description |
|-------|-------------|
| `id` | Identifiant unique de l'analyse |
| `sequence_header` | En-tête ou nom de la séquence |
| `sequence_length` | Longueur de la séquence protéique |
| `epitope_count` | Nombre total d'épitopes trouvés |
| `epitopes` | Tableau détaillé des épitopes avec scores individuels |
| `epitopes_table` | **Tableau formaté** en texte lisible (voir exemple ci-dessous) |
| `residue_scores` | Scores de prédiction pour chaque résidu |
| `message` | Message de statut |

**Exemple du tableau formaté (`epitopes_table`):**
```
Top candidates:
  Rank         Pos   Len   Score Sequence
  ----------------------------------------------------------------
     1      156-180    25   0.7651  GKESKSDHDKRPKDKKPFVPKTSQC
     2       88-122    35   0.7463  VPEPVTSEEPKESDQTEEQKHEEPEASPAPEPVDE
     3      140-174    35   0.7104  DGAAVCHGKHHDYDSDGKESKSDHDKRPKDKKPFV
```

**Erreurs:**
- `400 Bad Request`: Séquence invalide ou paramètres incorrects
- `500 Internal Server Error`: Erreur lors de l'analyse

---

### 2. Lister les analyses
**GET** `/api/epitopes/`

Liste toutes les analyses d'épitopes sauvegardées avec pagination.

**Query Parameters:**
- `limit` (integer): Nombre de résultats par page
- `offset` (integer): Décalage pour pagination

**Response (200 OK):**
```json
{
  "count": 42,
  "next": "http://localhost:8000/api/epitopes/?limit=10&offset=10",
  "previous": null,
  "results": [
    {
      "id": 1,
      "sequence_header": "Spike protein",
      "method": "core",
      "min_score": 0.5,
      "epitope_count": 15,
      "created_at": "2026-03-02T12:00:00Z"
    }
  ]
}
```

---

### 3. Détails d'une analyse
**GET** `/api/epitopes/{id}/`

Récupère les détails complets d'une analyse d'épitopes.

**Response (200 OK):**
```json
{
  "id": 1,
  "sequence_header": "Spike protein",
  "sequence": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
  "method": "core",
  "min_length": 9,
  "max_length": 20,
  "min_score": 0.5,
  "top_n": 20,
  "epitopes": [...],
  "epitopes_table": "Top candidates:\n  Rank         Pos   Len   Score Sequence\n  .............................................\n     1      156-180    25   0.7651  GKESKSDHDKRPKDKKPFVPKTSQC",
  "residue_scores": [...],
  "created_at": "2026-03-02T12:00:00Z"
}
```

---

### 4. Supprimer une analyse
**DELETE** `/api/epitopes/{id}/`

Supprime une analyse sauvegardée.

**Response (204 No Content)**

---

### 5. Analyses récentes
**GET** `/api/epitopes/recent/`

Récupère les analyses les plus récentes.

**Query Parameters:**
- `limit` (integer, default: 10): Nombre d'analyses à retourner

**Response (200 OK):**
```json
[
  {
    "id": 3,
    "sequence_header": "Protein A",
    "method": "core",
    "min_score": 0.5,
    "epitope_count": 12,
    "created_at": "2026-03-02T15:30:00Z"
  }
]
```

---

### 6. Analyses filtrées par méthode
**GET** `/api/epitopes/by_method/`

Récupère les analyses filtrées par méthode de prédiction.

**Query Parameters:**
- `method` (string, **required**): `core`, `bio`, ou `iedb`

**Response (200 OK):**
```json
[
  {
    "id": 1,
    "sequence_header": "Spike protein",
    "method": "core",
    "min_score": 0.5,
    "epitope_count": 15,
    "created_at": "2026-03-02T12:00:00Z"
  }
]
```

---

## Méthodes de prédiction

### Core Module (5 méthodes)
Les 5 méthodes classiques de prédiction d'épitopes:

1. **Hopp & Woods (1981)** - Hydrophilicité
   - Prédis les régions hydrophiles (favorables aux épitopes)
   - Score: 0-1 (0=hydrophobe, 1=hydrophile)

2. **Kyte & Doolittle (1982)** - Hydrophobicité
   - Détecte les régions hydrophobes (membrane)
   - Score: -2 à +2

3. **Karplus & Schulz (1985)** - Flexibilité de la chaîne principale
   - Prédis la flexibilité structurelle
   - Score: 0-1 (0=rigid, 1=flexible)

4. **Emini et al. (1985)** - Accessibilité de surface
   - Prédis l'accessibilité à la surface
   - Score: 0-1

5. **Kolaskar & Tongaonkar (1990)** - Antigénicité
   - Prédis le potentiel antigénique
   - Score: 0-1

### Bio Module (7 méthodes)
Toutes les méthodes du Core Module PLUS:

6. **Parker (1986)** - Hydrophilicité alternative
   - Approche alternative pour l'hydrophilicité

7. **Chou & Fasman (1978)** - Propensité de coude bêta
   - Prédis les structures secondaires favorables aux épitopes

### IEDB Module
- Intégration **API IEDB Tools**
- Utilise **BepiPred-2.0** (méthode machine learning)
- Meilleure précision mais nécessite connexion Internet

---

## Exemples d'utilisation

### Exemple 1: Analyse simple (Core module)
```bash
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
    "method": "core",
    "min_score": 0.5,
    "top_n": 10
  }'
```

### Exemple 2: Analyse avec tous les paramètres (Bio module)
```bash
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
    "method": "bio",
    "min_length": 10,
    "max_length": 18,
    "min_score": 0.6,
    "top_n": 15
  }'
```

### Exemple 3: Analyse depuis fichier FASTA
```bash
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": ">Spike protein\nMFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
    "method": "core"
  }'
```

### Exemple 4: Analyse avec structure PDB
```bash
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -F "sequence=MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ" \
  -F "method=core" \
  -F "pdb_file=@structure.pdb" \
  -F "chain_id=A"
```

### Exemple 5: Lister les analyses récentes
```bash
curl "http://localhost:8000/api/epitopes/recent/?limit=5"
```

### Exemple 6: Analyses filtrées par méthode
```bash
curl "http://localhost:8000/api/epitopes/by_method/?method=bio"
```

### Exemple 7: Récupérer les détails d'une analyse
```bash
curl "http://localhost:8000/api/epitopes/1/"
```

### Exemple 8: Supprimer une analyse
```bash
curl -X DELETE "http://localhost:8000/api/epitopes/1/"
```

---

## Format des données

### Séquence protéique
Accepte les formats suivants:

**Format brut:**
```
MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ
```

**Format FASTA:**
```
>Spike protein
MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ
WFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ
```

**Acides aminés standards:**
```
A C D E F G H I K L M N P Q R S T V W Y
```

Caractères spéciaux acceptés:
- `*` = Stop codon
- `X` = Acide aminé inconnu
- `-` = Gap (insertion/deletion)

### Structure des scores d'épitope

Chaque épitope contient:
```json
{
  "start": 1,                  // Position de début (1-indexed)
  "end": 15,                   // Position de fin (1-indexed)
  "sequence": "MFVFLVLLPLVSST",  // Séquence de l'épitope
  "length": 15,                // Longueur
  "score": 0.78,               // Score global combiné (0-1)
  "hopp_woods": 0.65,          // Score Hopp & Woods
  "kyte_doolittle": 0.72,      // Score Kyte & Doolittle
  "karplus_schulz": 0.81,      // Score Karplus & Schulz
  "emini": 0.85,               // Score Emini
  "kolaskar": 0.74             // Score Kolaskar & Tongaonkar
}
```

### Structure des scores de residus

Chaque résidu contient:
```json
{
  "position": 1,               // Position (1-indexed)
  "amino_acid": "M",           // Code 1-lettre
  "global_score": 0.65,        // Score global (0-1)
  "hydrophilicity": 0.45,      // Hopp & Woods
  "hydrophobicity": 0.52,      // Kyte & Doolittle
  "flexibility": 0.70,         // Karplus & Schulz
  "accessibility": 0.60,       // Emini
  "antigenicity": 0.55         // Kolaskar & Tongaonkar
}
```

---

## Interprétation des résultats

### Score global
- **0.0 - 0.3**: Faible potentiel épitopique
- **0.3 - 0.6**: Potentiel modéré
- **0.6 - 0.8**: Potentiel élevé (excellents candidats épitopes)
- **0.8 - 1.0**: Potentiel très élevé (épitopes prédits)

### Caractéristiques d'un bon épitope
✓ Score global élevé (> 0.6)
✓ Haute hydrophilicité (Hopp & Woods > 0.5)
✓ Haute accessibilité (Emini > 0.5)
✓ Bonne antigénicité (Kolaskar > 0.5)
✓ Flexibilité modérée (Karplus > 0.5)
✗ Pas de régions transmembranaires

---

## Configuration

### Paramètres par défaut (config.json)
```json
{
  "min_length": 9,
  "max_length": 20,
  "min_global_score": 0.5,
  "top_n_epitopes": 20,
  "scoring_weights": {
    "hydrophilicity": 0.20,
    "surface_accessibility": 0.20,
    "flexibility": 0.20,
    "antigenicity": 0.20,
    "hydrophobicity": -0.20
  }
}
```

### Ajuster les poids de scoring
Les poids peuvent être modifiés dans `epitop1/config.py` pour ajuster l'importance relative de chaque méthode.

---

## Limitations et notes

⚠️ **Résultats computationnels**: Les alignements de structure (PDB) peuvent avoir des erreurs
⚠️ **Accuracités**: Typiquement 60-70% de sensibilité/spécificité
⚠️ **IEDB API**: Nécessite connexion Internet, limites de débit
⚠️ **Longueur de séquence**: Fonctionnne mieux avec séquences > 20 résidus
⚠️ **Contexte**: Les résultats ne considèrent que la structure linéaire

---

## Intégration avec Django REST Framework

L'API respecte les standards DRF:
- ✓ HTTP status codes appropriés
- ✓ Gestion d'erreurs avec messages descriptifs
- ✓ Pagination supportée
- ✓ Filtrage et recherche disponibles
- ✓ Serializers avec validation
- ✓ ViewSets réutilisables
- ✓ Auto-documentation avec Swagger/ReDoc

---

## Performance

- **Analyse Core**: ~0.1-0.5 sec per 100 residues
- **Analyse Bio**: ~0.5-2 sec per 100 residues
- **Analyse IEDB**: 5-30 sec (API call)
- **Stockage BD**: Chaque analyse ~50 KB

---

## Troubleshooting

### Erreur: "Invalid protein sequence"
✓ Vérifier que la séquence ne contient que des acides aminés standards
✓ Supprimer espaces, retours à la ligne
✓ Vérifier format FASTA si applicable

### Erreur: "PDB parsing error"
✓ Vérifier que le fichier PDB est valide
✓ Vérifier que la chaîne spécifiée existe dans le PDB
✓ Vérifier que la séquence correspond à celle du PDB

### Erreur: "IEDB API error"
✓ Vérifier la connexion Internet
✓ Vérifier les quotas/rate limits d'IEDB
✓ Recommencer la requête après quelques secondes

---

## Support et documentation

- **EpiTop1 Documentation**: Voir `epitop1/README.md`
- **API Documentation principale**: Voir `API_DOCUMENTATION.md`
- **Code source**: `epitop1/` folder
- **Configuration**: `epitop1/config.py`

