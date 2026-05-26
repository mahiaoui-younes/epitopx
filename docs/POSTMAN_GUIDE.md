# Guide d'utilisation - EpiTop1 API dans Postman

## 📥 Importer la collection Postman

### Méthode 1: Via le fichier JSON
1. Ouvrir **Postman**
2. Cliquer sur **Import** (en haut à gauche)
3. Sélectionner l'onglet **File**
4. Choisir le fichier `EpiTop1_API.postman_collection.json`
5. Cliquer sur **Import**

### Méthode 2: Via URL
1. Cliquer sur **Import**
2. Aller à l'onglet **Link**
3. Coller le chemin du fichier: `file:///c:/Users/asus/Desktop/backend_api/EpiTop1_API.postman_collection.json`
4. Cliquer sur **Import**

---

## 🚀 Avant de tester

### Démarrer le serveur Django
```bash
cd c:\Users\asus\Desktop\backend_api
python manage.py runserver 127.0.0.1:8000
```

**Le serveur doit être en marche** avant de faire les requêtes! ✅

---

## 📊 Endpoints disponibles

### 1. **EPITOPE ANALYSIS** (Créer des analyses)

#### ✅ Basic Analysis (Core Module)
- **Méthode**: POST
- **URL**: `http://127.0.0.1:8000/api/epitopes/analyze/`
- **Description**: Analyse avec 5 méthodes bioinformatiques
- **Réponse**: Analysis ID + résultats des épitopes
- **Exemple**: Séquence Spike COVID-19

#### ✅ Bio Module Analysis  
- **Méthode**: POST
- **URL**: `http://127.0.0.1:8000/api/epitopes/analyze/`
- **Description**: Analyse avec 7 méthodes (Core + Parker + Chou & Fasman)
- **Meilleure précision** que Core module
- **Plus lent** que Core module

#### ✅ Analysis with Long Sequence
- **Méthode**: POST
- **Description**: Support format FASTA
- **Exemple**: Lon

ges séquences protéiques

#### ✅ Strict Analysis (High Score)
- **Score minimum**: 0.8
- **Résultat**: Seulement les meilleurs épitopes

#### ✅ Permissive Analysis (Low Score)
- **Score minimum**: 0.3
- **Résultat**: Plus d'épitopes candidats

---

### 2. **LISTING & FILTERING** (Voir les résultats)

#### ✅ List All Analyses
- **Méthode**: GET
- **URL**: `http://127.0.0.1:8000/api/epitopes/`
- **Résultat**: Toutes les analyses avec pagination

#### ✅ List with Pagination
- **Méthode**: GET
- **Paramètres**: `?limit=10&offset=0`
- **Résultat**: 10 analyses à partir du premier

#### ✅ Get Analysis Details
- **Méthode**: GET
- **URL**: `http://127.0.0.1:8000/api/epitopes/1/`
- **Résultat**: Tous les détails + scores de résidus
- **Note**: Remplacer `1` par l'ID de votre analyse

#### ✅ Recent Analyses
- **Méthode**: GET
- **URL**: `http://127.0.0.1:8000/api/epitopes/recent/?limit=5`
- **Résultat**: Les 5 analyses les plus récentes

#### ✅ Filter by Method
- **Core**: `?method=core`
- **Bio**: `?method=bio`
- **IEDB**: `?method=iedb`
- **Résultat**: Toutes les analyses de cette méthode

#### ✅ Delete Analysis
- **Méthode**: DELETE
- **URL**: `http://127.0.0.1:8000/api/epitopes/1/`
- **Résultat**: Supprime l'analyse

---

## 📝 Paramètres de requête (POST)

```json
{
  "sequence": "MFVFLVLLPLVSSTQ...",    // Requis: séquence protéique ou FASTA
  "method": "core",                     // Optionnel: core, bio, ou iedb (default: core)
  "min_length": 9,                      // Optionnel: min 5 (default: 9)
  "max_length": 20,                     // Optionnel: max 35 (default: 20)
  "min_score": 0.5,                     // Optionnel: 0-1 (default: 0.5)
  "top_n": 20,                          // Optionnel: nombre d'épitopes (default: 20)
  "pdb_file": null,                     // Optionnel: fichier PDB pour SASA
  "chain_id": "A"                       // Optionnel: chaîne PDB (default: A)
}
```

---

## 📊 Résponse (Exemple)

```json
{
  "id": 1,
  "sequence_header": "User_Input_Sequence",
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

---

## 🎯 Workflow de test recommandé

### 1️⃣ Tester une analyse simple
```
Cliquer → "1. Basic Analysis (Core Module)"
↓
Cliquer "Send"
↓
Voir résultat en JSON
```

### 2️⃣ Voir l'analyse créée
```
Cliquer → "List All Analyses"
↓
Cliquer "Send"
↓
Copier l'ID d'une analyse
```

### 3️⃣ Voir les détails
```
Cliquer → "Get Analysis Details"
↓
Remplacer ID dans l'URL: `/api/epitopes/{ID}/`
↓
Cliquer "Send"
↓
Voir tous les scores
```

### 4️⃣ Tester une autre méthode
```
Cliquer → "2. Bio Module Analysis"
↓
Modifier les paramètres si besoin
↓
Cliquer "Send"
```

---

## 🔧 Variables Postman (Optionnel)

La collection inclut des variables pré-configurées:
- `base_url`: `http://127.0.0.1:8000/api`
- `analysis_id`: `1`

Vous pouvez les modifier dans **Environment > Manage Environments**.

---

## 📌 Formats de séquence acceptés

### Format brut:
```
MFVFLVLLPLVSSTQ
```

### Format FASTA:
```
>Spike protein from SARS-CoV-2
MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ
WFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ
```

### Acides aminés standards:
```
A C D E F G H I K L M N P Q R S T V W Y
(X = inconnu, * = stop, - = gap)
```

---

## ✅ Tests à essayer

### Test 1: Séquence courte avec score bas
```json
{
  "sequence": "MFVFLVLLPLVSSTQ",
  "method": "core",
  "min_score": 0.3,
  "top_n": 5
}
```

### Test 2: Séquence moyenne avec filtre strict
```json
{
  "sequence": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ",
  "method": "bio",
  "min_score": 0.7,
  "top_n": 10
}
```

### Test 3: Filtrer par longueur
```json
{
  "sequence": "MFVFLVLLPLVSSTQWFVFLVLLPLVSSTQWFVFLVLLPLVSSTQ...(plus long)",
  "method": "core",
  "min_length": 12,
  "max_length": 16,
  "top_n": 20
}
```

---

## 🐛 Troubleshooting

### Erreur: "Failed to connect"
✓ **Solution**: Assurez-vous que le serveur Django est en marche
```bash
python manage.py runserver 127.0.0.1:8000
```

### Erreur: "Invalid protein sequence"
✓ **Solution**: Vérifier que la séquence ne contient que des acides aminés valides
✓ Éviter les espaces (sauf dans FASTA)
✓ Les majuscules/minuscules sont acceptées

### Erreur 400 Bad Request
✓ **Solution**: Vérifier la validité du JSON dans le body
✓ Vérifier les paramètres (min_score entre 0-1)
✓ Vérifier que min_length < max_length

### Erreur 500 Internal Server Error
✓ **Solution**: Voir les logs du serveur Django
✓ Vérifier que epitop1 est bien installé

---

## 📚 Documentation complète

Voir `EPITOPE_API_DOCUMENTATION.md` pour:
- Explication détaillée de chaque méthode
- Références scientifiques
- Scores et interprétation
- Limites et notes importantes

---

## 🎓 Exemples de requêtes complets

### cURL (Alternative à Postman)

```bash
# Test 1: Analyse simple
curl -X POST http://127.0.0.1:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MFVFLVLLPLVSSTQ","method":"core"}'

# Test 2: Lister les analyses
curl -X GET http://127.0.0.1:8000/api/epitopes/

# Test 3: Voir les détails
curl -X GET http://127.0.0.1:8000/api/epitopes/1/

# Test 4: Analyses récentes
curl -X GET "http://127.0.0.1:8000/api/epitopes/recent/?limit=5"
```

---

## 💡 Tips

1. **Sauvegardez vos collections** générées dans Postman
2. **Testez d'abord avec des séquences courtes** (< 100 aa)
3. **Utilisez le Bio module pour plus de précision** (mais plus lent)
4. **Filtrez par méthode** pour comparer les résultats
5. **Exportez les résultats** en JSON pour analyse ultérieure

---

## 🔗 Ressources

- **API Documentation**: `EPITOPE_API_DOCUMENTATION.md`
- **Test Script Python**: `test_epitope_api.py`
- **EpiTop1 Source**: `epitop1/` folder
- **Database Models**: `api/models.py`

---

**Happy Testing! 🚀**
