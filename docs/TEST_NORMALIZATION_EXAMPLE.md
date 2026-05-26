# Épitope Normalization - Examples

## Ejemplo 1: Estructura Antes vs Después

### ❌ ANTES (Redondant)
```python
# La mesmo séquence stockée 3 fois
Epitope.objects.create(
    epitope_sequence="GKESKSDHDKRPK",  # Sequence complete
    start=156,
    end=169,
    score=0.765
)

Epitope.objects.create(
    epitope_sequence="GKESKSDHDKRPK",  # REDONDANT!
    start=200,
    end=213,
    score=0.750  
)

Epitope.objects.create(
    epitope_sequence="GKESKSDHDKRPK",  # REDONDANT!
    start=345,
    end=358,
    score=0.742
)
```

### ✅ APRÈS (Normalisé)
```python
# 1. Créer/obtenir la séquence unique
epitope_seq, created = EpitopeSequenceUnique.objects.get_or_create(
    sequence="GKESKSDHDKRPK",
    defaults={'sequence_hash': 'sha256_hash_here'}
)

# 2. Créer les hits qui pointent vers cette séquence
Epitope.objects.create(
    epitope_sequence_unique=epitope_seq,  # FK to unique sequence
    epitope_id=epitope_seq.id,  # Now epitopes with same sequence share an ID!
    start=156,
    end=169,
    score=0.765
)

Epitope.objects.create(
    epitope_sequence_unique=epitope_seq,  # Même FK
    epitope_id=epitope_seq.id,  # Même epitope_id
    start=200,
    end=213,
    score=0.750
)

Epitope.objects.create(
    epitope_sequence_unique=epitope_seq,  # Même FK
    epitope_id=epitope_seq.id,  # Même epitope_id
    start=345,
    end=358,
    score=0.742
)
```

---

## Exemple 2: Requête Return (API Response)

### Avant
```json
{
  "epitopes": [
    {
      "id": 1001,
      "epitope_sequence": "GKESKSDHDKRPK",
      "start": 156,
      "end": 169,
      "score": 0.765
    },
    {
      "id": 1002,
      "epitope_sequence": "GKESKSDHDKRPK",  // REDONDANCE VISIBLE
      "start": 200,
      "end": 213,
      "score": 0.750
    },
    {
      "id": 1003,
      "epitope_sequence": "GKESKSDHDKRPK",  // REDONDANCE VISIBLE
      "start": 345,
      "end": 358,
      "score": 0.742
    }
  ]
}
```

### Après
```json
{
  "epitopes": [
    {
      "id": 1001,
      "epitope_id": 25,  // ← NOUVEAU: Epitope unique ID
      "epitope_sequence": "GKESKSDHDKRPK",
      "start": 156,
      "end": 169,
      "score": 0.765
    },
    {
      "id": 1002,
      "epitope_id": 25,  // ← SAME ID - Show redundancy is eliminated
      "epitope_sequence": "GKESKSDHDKRPK",
      "start": 200,
      "end": 213,
      "score": 0.750
    },
    {
      "id": 1003,
      "epitope_id": 25,  // ← SAME ID - Share the unique sequence
      "epitope_sequence": "GKESKSDHDKRPK",
      "start": 345,
      "end": 358,
      "score": 0.742
    }
  ]
}
```

---

## Exemple 3: Requêtes Django - Cas d'Usage

### Cas 1: Trouver tous les hits pour une séquence d'épitope
```python
# Avant (difficile)
epitopes = Epitope.objects.filter(epitope_sequence="GKESKSDHDKRPK")

# Après (facile et rapide)
epitope_seq = EpitopeSequenceUnique.objects.get(id=25)
epitopes = epitope_seq.occurrences.all()
```

### Cas 2: Compter les séquences uniques
```python
# Avant (compliqué)
unique_seqs = Epitope.objects.values('epitope_sequence').distinct().count()

# Après (trivial)
unique_count = EpitopeSequenceUnique.objects.count()
```

### Cas 3: Trouver les séquences qui apparaissent plusieurs fois
```python
# Avant (pas vraiment possible de savoir avec certitude)
# Après (facile)
from django.db.models import Count

duplicates = EpitopeSequenceUnique.objects.annotate(
    count=Count('occurrences')
).filter(count__gt=1)

for epitope_seq in duplicates:
    print(f"Sequence '{epitope_seq.sequence}' appears {epitope_seq.count} times")
```

### Cas 4: Statistiques de préférence
```python
# Trouver la séquence d'épitope la plus courante
from django.db.models import Count

most_common = EpitopeSequenceUnique.objects.annotate(
    occurrence_count=Count('occurrences')
).order_by('-occurrence_count').first()

print(f"Most common epitope: {most_common.sequence} ({most_common.occurrence_count} hits)")
```

### Cas 5: Recherche par hash (les plus rapides)
```python
# Les queries utiliser le hash pour trouver la séquence instantanément
sequence_hash = hashlib.sha256("GKESKSDHDKRPK".encode()).hexdigest()
epitope_seq = EpitopeSequenceUnique.objects.get(sequence_hash=sequence_hash)
```

---

## Exemple 4: Migration des Données Existantes (Si Nécessaire)

```python
"""
Si vous avez des épitopes existants avant la migration,
utilisez ce script pour les normalizer
"""

import hashlib
from api.models import Epitope, EpitopeSequenceUnique

# 1. Analyser les données existantes
epitopes = Epitope.objects.filter(epitope_sequence_unique__isnull=True)
print(f"Epitopes to migrate: {epitopes.count()}")

# 2. Créer les séquences uniques et migrer les liens
for epitope in epitopes:
    sequence = epitope.epitope_sequence  # Old field
    sequence_hash = hashlib.sha256(sequence.encode()).hexdigest()
    
    # Get or create
    epitope_seq, created = EpitopeSequenceUnique.objects.get_or_create(
        sequence=sequence,
        defaults={'sequence_hash': sequence_hash}
    )
    
    # Link
    epitope.epitope_sequence_unique = epitope_seq
    epitope.save(update_fields=['epitope_sequence_unique'])
    
    if created:
        print(f"✓ Created unique epitope {epitope_seq.id}: {sequence}")
    else:
        print(f"✓ Linked epitope to existing unique ID {epitope_seq.id}")

print("Migration complete!")
```

---

## Résultat Final

| Métrique | Avant | Après |
|----------|-------|-------|
| Espace disque | Redondant | Optimisé (-50-80%) |
| Query complexité | Élevée | Basse |
| Unicité garantie | Non | ✓ Oui |
| Epitope ID | N/A | ✓ Unique |
| Déduplication | Manuelle | Automatique |
| Performance recherche | Moyenne | Excellente |

