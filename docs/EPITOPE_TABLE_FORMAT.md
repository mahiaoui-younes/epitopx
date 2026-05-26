# Tableau Formaté des Épitopes

## Vue d'ensemble

L'API retourne maintenant un champ `epitopes_table` qui contient un **tableau formaté en texte lisible** des épitopes prédits, en plus des données JSON détaillées. Cela facilite la lecture et la présentation des résultats.

---

## Format du tableau

```
Top candidates:
  Rank         Pos   Len   Score Sequence
  ----------------------------------------------------------------
     1      156-180    25   0.7651  GKESKSDHDKRPKDKKPFVPKTSQC
     2       88-122    35   0.7463  VPEPVTSEEPKESDQTEEQKHEEPEASPAPEPVDE
     3      140-174    35   0.7104  DGAAVCHGKHHDYDSDGKESKSDHDKRPKDKKPFV
     4       72-106    35   0.6778  PSTEPEELQPETVTVEVPEPVTSEEPKESDQTEEQ
     5      104-138    35   0.6045  EEQKHEEPEASPAPEPVDEPAVHATESTPTKASSS
     6       56-90     35   0.5444  EQPAQQEPIEPQQPTQPSTEPEELQPETVTVEVPE
```

### Colonnes du tableau

| Colonne | Description |
|---------|-------------|
| **Rank** | Numéro de classement de l'épitope (1 = score le plus élevé) |
| **Pos** | Position dans la séquence (format: début-fin) |
| **Len** | Longueur de l'épitope en acides aminés |
| **Score** | Score de prédiction normalisé (0.0 à 1.0) |
| **Sequence** | Séquence d'acides aminés de l'épitope |

---

## Utilisation

### Exemple 1: Python avec requests

```python
import requests
import json

response = requests.post(
    'http://127.0.0.1:8000/api/epitopes/analyze/',
    json={
        'sequence': 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEW',
        'method': 'core',
        'min_length': 9,
        'max_length': 20,
        'min_score': 0.5,
        'top_n': 9
    }
)

result = response.json()

# Afficher le tableau formaté
print(result['epitopes_table'])

# Ou accéder aux données JSON
print(f"Total epitopes: {result['epitope_count']}")
for epitope in result['epitopes']:
    print(f"  {epitope['start']}-{epitope['end']}: {epitope['sequence']} ({epitope['score']:.4f})")
```

### Exemple 2: JavaScript/Node.js

```javascript
fetch('http://127.0.0.1:8000/api/epitopes/analyze/', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        sequence: 'MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEW',
        method: 'core',
        min_length: 9,
        max_length: 20,
        min_score: 0.5,
        top_n: 9
    })
})
.then(res => res.json())
.then(data => {
    // Afficher le tableau formaté
    console.log(data.epitopes_table);
});
```

### Exemple 3: curl

```bash
curl -X POST http://127.0.0.1:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEW",
    "method": "core",
    "min_length": 9,
    "max_length": 20,
    "min_score": 0.5,
    "top_n": 9
  }' | jq '.epitopes_table'
```

---

## Structure JSON complète

La réponse contient toujours les deux formats:

```json
{
  "id": 7,
  "sequence_header": "User_Input_Sequence",
  "sequence_length": 69,
  "method": "core",
  "epitope_count": 2,
  
  "epitopes_table": "Top candidates:\n  Rank  ...",  // ← NOUVEAU
  
  "epitopes": [
    {
      "start": 43,
      "end": 62,
      "sequence": "GTQDNLSGAEKAVQVKVKAL",
      "length": 20,
      "score": 0.8975,
      ...
    }
  ],
  
  "residue_scores": [ ... ],
  "message": "Analysis completed successfully"
}
```

---

## Avantages

✓ **Lisibilité**: Tableau facile à lire au lieu de parser JSON
✓ **Affichage CLI**: Paraît élégant dans les logs/terminaux  
✓ **Intégration rapide**: Prêt pour afficher directement dans les rapports
✓ **Retro-compatible**: Les données JSON sont toujours présentes
✓ **Scores clairement visibles**: Comparaison facile entre épitopes

---

## Personnalisation du tableau

Si vous voulez créer votre propre format de tableau, utilisez les données `epitopes` en JSON:

```python
# Format personnalisé avec plus de détails
epitopes = result['epitopes']
for rank, epi in enumerate(epitopes[:3], 1):
    print(f"{rank}. {epi['sequence']:<30} Score: {epi['score']:.4f}")
    print(f"   Position: {epi['start']}-{epi['end']} | Length: {epi['length']}")
```

---

## Notes

- Le tableau formaté respecte le nombre d'épitopes demandés (`top_n`)
- Les épitopes sont triés par score (du plus élevé au plus bas)
- Chaque épitope occupe une ligne pour une meilleure lisibilité
- Le format fonctionne avec tous les endpoints (analyze, detail, recent)
