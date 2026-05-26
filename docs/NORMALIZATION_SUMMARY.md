# Database Normalization - Épitope Structure

## Problème Résolu

**Redondance éliminée**: Les mêmes séquences d'épitope étaient enregistrées plusieurs fois dans la base de données.

## Solution Implémentée ✓

### Architecture Finale: Structure Optimisée à 2 Tables

#### Table 1: **`Protein`**
- Stocke les séquences protéiques uniques
- Index sur `name` pour recherches rapides
- Structure:
  ```
  id               - ID unique de la protéine (PRIMARY KEY)
  name             - Nom de la protéine (UNIQUE, INDEXED)
  sequence         - Séquence d'acides aminés
  organism         - Organisme
  description      - Description
  method           - Méthode d'analyse utilisée (core/bio/iedb)
  created_at       - Timestamp
  updated_at       - Timestamp
  ```

#### Table 2: **`Epitope`** (Reference directe à Protein)
- Lien direct à la protéine via `protein_id`
- Chaque ligne = un épitope prédit
- Tous les épitopes d'une même protéine ont le même `protein_id`
- Contrainte unique: `(protein_id, epitope_sequence, start, end)`
- Structure:
  ```
  id                   - ID unique du hit d'épitope (PRIMARY KEY)
  protein_id           - FK vers Protein (reference directe)
  epitope_id           - Numéro séquentiel (1, 2, 3... pour chaque protéine)
  epitope_sequence     - Séquence complète de l'épitope (INDEXED)
  method               - Méthode d'analyse
  start, end           - Position dans la séquence protéique
  length, score        - Propriétés du hit
  hopp_woods, kyte_doolittle...  - Scores des hydrophobicités
  created_at           - Timestamp
  ```

## Bénéfices ✓

✅ **Élimine la redondance**: Stockage direct des épitopes liés à leurs protéines  
✅ **Améliore les performances**: Index sur `protein_id` et `epitope_sequence` pour O(1)  
✅ **Simplifie la structure**: Seulement 2 tables, pas d'intermédiaires complexes  
✅ **Facilite les requêtes**: `SELECT * FROM epitopes WHERE protein_id=X` directement  
✅ **Reference claire**: Chaque épitope indique clairement sa protéine source via `protein_id`

## API Response - Example ✓

### Structure Simplifié avec Protein Reference

```json
{
  "epitopes": [
    {"id": 43, "protein_id": 14, "epitope_id": 1, "epitope_sequence": "YDSDGKESKSDHDKRPKDKK", "start": 152, "end": 171, "score": 0.8842},
    {"id": 44, "protein_id": 14, "epitope_id": 2, "epitope_sequence": "TSEEPKESDQTEEQKHEEPE", "start": 93, "end": 112, "score": 0.8680},
    {"id": 45, "protein_id": 14, "epitope_id": 3, "epitope_sequence": "EQKHEEPEASPAPEPVDEPA", "start": 105, "end": 124, "score": 0.7100},
    {"id": 46, "protein_id": 14, "epitope_id": 4, "epitope_sequence": "DKRPKDKKPFVPKTSQCCGS", "start": 242, "end": 261, "score": 0.6366},
    {"id": 47, "protein_id": 14, "epitope_id": 5, "epitope_sequence": "QPSTEPEELQ", "start": 274, "end": 283, "score": 0.6168}
  ]
}
```

🔑 **Remarque importante**: 
- Tous les épitopes à `protein_id=14` = tous de la **même protéine**
- `epitope_id` = numérotation séquentielle (1, 2, 3... par protéine)
- Chaque ligne = un épitope distinct avec ses propriétés

## Migration Effectuée ✓

### Structure Finale
- Fichiers de migration: `api/migrations/0001_initial.py`
- Actions:
  1. ✅ Créé table `Protein` avec index sur `name`
  2. ✅ Créé table `Epitope` avec FK directe vers `Protein`
  3. ✅ Index sur `epitope_sequence` pour recherches rapides
  4. ✅ Contrainte unique sur (protein_id, epitope_sequence, start, end)

### Fichiers Modifiés
1. **api/models.py**
   - `Protein` model: sequencePrincipale, name (unique), method
   - `Epitope` model: FK directe à Protein, epitope_id (séquentiel), epitope_sequence

2. **api/serializers.py**
   - `EpitopeSerializer`: expose `protein_id`, `epitope_id`, `epitope_sequence`
   - Les données retournées incluent le référence protéique

3. **api/views.py**
   - `analyze()` action: crée Protein directement
   - Boucle d'épitopes: assigne protein_id automatiquement
   - epitope_id assigné séquentiellement (1, 2, 3...)

## Utilisation dans les Requêtes ✓

### Chercher tous les épitopes d'une protéine
```python
from api.models import Protein, Epitope

# Méthode 1: Via la relation reverse
protein = Protein.objects.get(id=14)
all_epitopes = protein.epitopes.all()

# Méthode 2: Directement sur Epitope
epitopes = Epitope.objects.filter(protein_id=14)

# Résultat: 7 épitopes avec protein_id=14
```

### Chercher un épitope spécifique
```python
# Par protéine + numéro
epitope = Epitope.objects.get(protein_id=14, epitope_id=3)
# Retourne: epitope_id=3, epitope_sequence="EQKHEEPEASPAPEPVDEPA", score=0.7100

# Par séquence d'acides aminés
epitopes = Epitope.objects.filter(epitope_sequence="YDSDGKESKSDHDKRPKDKK")
```

### Grouper par protéine
```python
proteins = Protein.objects.all()
for protein in proteins:
    print(f"Protéine {protein.name}: {protein.epitopes.count()} épitopes")
    for ep in protein.epitopes.all():
        print(f"  - {ep.epitope_id}: {ep.epitope_sequence} (score: {ep.score})")
```

## Vérification Données ✓

**Résultat du test** (`test_protein_epitope_reference.py`):
```
✓ Total epitopes: 14
✓ Protein ID: 14
  Name: User_Input_Sequence
  Epitopes count: 7
  
  [1] epitope_id=1, protein_id=14, sequence=YDSDGKESKSDHDKRPKDKK, score=0.8842
  [2] epitope_id=2, protein_id=14, sequence=TSEEPKESDQTEEQKHEEPE, score=0.8680
  [3] epitope_id=3, protein_id=14, sequence=EQKHEEPEASPAPEPVDEPA, score=0.7100
  [4] epitope_id=4, protein_id=14, sequence=DKRPKDKKPFVPKTSQCCGS, score=0.6366
  [5] epitope_id=5, protein_id=14, sequence=QPSTEPEELQ, score=0.6168
  [6] epitope_id=6, protein_id=14, sequence=DPNDDQHPLD, score=0.5826
  [7] epitope_id=7, protein_id=14, sequence=PIEPQQPTQPSTEPEELQ, score=0.5818
```

**Résumé**:
- ✅ Tous 7 épitopes ont `protein_id=14` (même protéine source)
- ✅ Chaque épitope a un `epitope_id` unique (1-7)
- ✅ L'API retourne le `protein_id` pour chaque épitope
- ✅ Aucune redondance: structure normalisée et optimale
