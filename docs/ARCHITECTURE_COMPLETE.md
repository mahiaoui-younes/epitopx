# 🏗️ ARCHITECTURE COMPLÈTE DU SYSTÈME - BACKEND API

## 📋 TABLE DES MATIÈRES
1. [Vue d'ensemble générale](#vue-densemble)
2. [Architecture en couches](#architecture-en-couches)
3. [Structure des dossiers](#structure-des-dossiers)
4. [Modèles de données](#modèles-de-données)
5. [Endpoints API](#endpoints-api)
6. [Flux d'authentification](#flux-dauthentification)
7. [Modules métier](#modules-métier)
8. [Stack technologique](#stack-technologique)

---

## 🌐 VUE D'ENSEMBLE {#vue-densemble}

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React/Vue)                      │
│        Browser │ Mobile │ Desktop Application                    │
└────────────────────────────────┬────────────────────────────────┘
                                 │
                    HTTP/HTTPS (REST API)
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│                   DJANGO REST FRAMEWORK                          │
│                  (Backend API Server)                            │
│          Running on: http://127.0.0.1:8000                       │
└────────┬──────────────────────────────────────────────┬──────────┘
         │                                              │
    ┌────▼──────────┐                          ┌──────────▼───────┐
    │  REQUEST      │                          │  AUTHENTICATION  │
    │  PROCESSING   │                          │  & PERMISSIONS   │
    │               │                          │                  │
    │ • Routing     │                          │ • Token Auth     │
    │ • Views       │                          │ • User Roles     │
    │ • Serializers │                          │ • Permissions    │
    └────┬──────────┘                          └──────────┬───────┘
         │                                              │
         │              ┌─────────────────────┐         │
         └──────────────│   BUSINESS LOGIC    │─────────┘
                        │                     │
                        │ • Epitope Analysis  │
                        │ • DNA→RNA→Protein   │
                        │ • Data Filtering    │
                        │ • Search & Filter   │
                        └────────┬────────────┘
                                 │
            ┌────────────────────┴────────────────────┐
            │                                         │
    ┌───────▼────────┐                       ┌──────▼────────┐
    │   DATABASE     │                       │   FILE STORAGE│
    │   SQLite3      │                       │   (Media)      │
    │                │                       │                │
    │ • Users        │                       │ • Uploads      │
    │ • Proteins     │                       │ • Results      │
    │ • Epitopes     │                       │ • Conversions  │
    │ • Conversions  │                       │                │
    │ • Articles     │                       └────────────────┘
    └────────────────┘
```

---

## 🏢 ARCHITECTURE EN COUCHES {#architecture-en-couches}

### 1️⃣ **COUCHE DE PRÉSENTATION (Views)**
```
┌─────────────────────────────────────────────┐
│           API Endpoints (ViewSets)          │
├─────────────────────────────────────────────┤
│                                             │
│  • UserViewSet                              │
│    - register()                             │
│    - login()                                │
│    - profile()                              │
│    - logout()                               │
│                                             │
│  • ProteinViewSet                           │
│    - list() → CRUD                          │
│    - public_list()                          │
│    - my_proteins()                          │
│    - my_own()                               │
│    - all_proteins()                         │
│                                             │
│  • EpitopeAnalysisViewSet                   │
│    - analyze()                              │
│    - list()                                 │
│                                             │
│  • ProteinConversionViewSet                 │
│    - convert()                              │
│    - convert_large()                        │
│    - history()                              │
│    - search()                               │
│                                             │
│  • ArticleViewSet (CRUD)                    │
│  • DNASequenceViewSet (CRUD)                │
│                                             │
└─────────────────────────────────────────────┘
```

### 2️⃣ **COUCHE DE SÉRIALISATION (Serializers)**
```
┌──────────────────────────────────────────────┐
│          Data Transformation Layer           │
├──────────────────────────────────────────────┤
│                                              │
│  AUTHENTICATION                              │
│  ├─ UserRegisterSerializer                   │
│  ├─ UserLoginSerializer                      │
│  └─ UserSerializer                           │
│                                              │
│  PROTEINS                                    │
│  ├─ ProteinSerializer                        │
│  └─ ProteinConversionSerializer              │
│                                              │
│  EPITOPES                                    │
│  ├─ EpitopeSerializer                        │
│  ├─ EpitopeFullSerializer                    │
│  ├─ EpitopeListSerializer                    │
│  ├─ EpitopeAnalysisRequestSerializer         │
│  └─ EpitopeAnalysisResponseSerializer        │
│                                              │
│  DNA CONVERSIONS                             │
│  ├─ ConversionRequestSerializer              │
│  └─ ConversionResponseSerializer             │
│                                              │
│  AUTRES                                      │
│  ├─ ArticleSerializer                        │
│  └─ DNASequenceSerializer                    │
│                                              │
└──────────────────────────────────────────────┘
```

### 3️⃣ **COUCHE MÉTIER (Business Logic)**
```
┌──────────────────────────────────────────────┐
│        Business Logic & Processing           │
├──────────────────────────────────────────────┤
│                                              │
│  AUTHENTIFICATION                            │
│  ├─ generate_tokens()                        │
│  ├─ validate_credentials()                   │
│  └─ check_permissions()                      │
│                                              │
│  EPITOPE ANALYSIS                            │
│  ├─ analyze_epitopes()                       │
│  ├─ filter_by_score()                        │
│  ├─ rank_results()                           │
│  └─ normalize_output()                       │
│                                              │
│  DNA/RNA/PROTEIN CONVERSION                  │
│  ├─ dna_to_rna()                             │
│  ├─ rna_to_protein()                         │
│  ├─ dna_to_protein()                         │
│  └─ validate_sequences()                     │
│                                              │
│  DATA FILTERING & SEARCH                     │
│  ├─ filter_public_proteins()                 │
│  ├─ filter_user_proteins()                   │
│  ├─ search_epitopes()                        │
│  └─ paginate_results()                       │
│                                              │
└──────────────────────────────────────────────┘
```

### 4️⃣ **COUCHE DONNÉES (Models)**
```
┌──────────────────────────────────────────────┐
│         Django ORM Models                    │
├──────────────────────────────────────────────┤
│                                              │
│  User (Authentication)                       │
│  ├─ username                                 │
│  ├─ email                                    │
│  ├─ password (hashed)                        │
│  ├─ is_admin                                 │
│  ├─ created_at                               │
│  └─ ForeignKey relationships                 │
│                                              │
│  Protein (Main Domain)                       │
│  ├─ name                                     │
│  ├─ sequence (TextField)                     │
│  ├─ organism                                 │
│  ├─ description                              │
│  ├─ method                                   │
│  ├─ is_public (Permission)                   │
│  ├─ created_by (ForeignKey→User)             │
│  ├─ created_at                               │
│  ├─ updated_at                               │
│  └─ Relationships: epitopes                  │
│                                              │
│  Epitope (Analysis Results)                  │
│  ├─ protein (ForeignKey→Protein)             │
│  ├─ epitope_sequence                         │
│  ├─ epitope_id                               │
│  ├─ method                                   │
│  ├─ start (position)                         │
│  ├─ end (position)                           │
│  ├─ length                                   │
│  ├─ score                                    │
│  ├─ hopp_woods (metric)                      │
│  ├─ kyte_doolittle (metric)                  │
│  ├─ karplus_schulz (metric)                  │
│  ├─ emini (metric)                           │
│  ├─ kolaskar (metric)                        │
│  └─ created_at                               │
│                                              │
│  ProteinConversion (History)                 │
│  ├─ original_dna                             │
│  ├─ rna                                      │
│  ├─ protein                                  │
│  └─ created_at                               │
│                                              │
│  Article (Content)                           │
│  ├─ titre                                    │
│  ├─ contenu                                  │
│  └─ created_at                               │
│                                              │
│  DNASequence (Reference)                     │
│  ├─ name                                     │
│  ├─ sequence                                 │
│  └─ created_at                               │
│                                              │
└──────────────────────────────────────────────┘
```

### 5️⃣ **COUCHE PERSISTANCE (Database)**
```
SQLite3 Database (db.sqlite3)
│
├─ auth_user / api_user (Authentification)
├─ api_protein (Données principales)
├─ api_epitope (Résultats d'analyse)
├─ api_proteinconversion (Historique)
├─ api_article (Contenu)
├─ api_dnasequence (Référence)
└─ authtoken_token (Tokens)
```

---

## 📁 STRUCTURE DES DOSSIERS {#structure-des-dossiers}

```
backend_api/
│
├── config/                          # Configuration Django
│   ├── __init__.py
│   ├── settings.py                  # 🔑 Configuration (BD, Apps, Middleware)
│   ├── urls.py                      # 🔑 URLs principales
│   ├── asgi.py
│   ├── wsgi.py
│   └── auth.py                      # Custom auth logic
│
├── api/                             # Application principale
│   ├── __init__.py
│   ├── models.py                    # 🔑 Models (User, Protein, Epitope, etc.)
│   ├── views.py                     # 🔑 ViewSets & Actions
│   ├── serializers.py               # 🔑 Data serialization
│   ├── urls.py                      # 🔑 API routes
│   ├── admin.py                     # Django Admin
│   ├── apps.py
│   ├── tests.py
│   ├── db_backend.py                # Custom DB backend
│   ├── permissions.py               # Custom permissions
│   ├── db_backend/                  # Custom database backend
│   │   └── base.py
│   ├── migrations/                  # Database migrations
│   │   ├── 0001_initial.py
│   │   ├── 0002_...py
│   │   └── ...
│
├── epitop1/                         # Epitope analysis module
│   ├── __init__.py
│   ├── _analyze_*.py                # Analysis scripts
│   ├── _diag_*.py                   # Diagnostic scripts
│   ├── epitope_analysis.py          # 🔑 Main analysis (if exists)
│   └── ...
│
├── media/                           # File uploads
│   └── ...
│
├── manage.py                        # 🔑 Entry point
├── db.sqlite3                       # Database
│
└── venv/                            # Virtual environment
```

---

## 💾 MODÈLES DE DONNÉES {#modèles-de-données}

### Entity-Relationship Diagram (ERD)

```
┌────────────────┐
│     User       │
├────────────────┤
│ id (PK)        │
│ username       │
│ email          │
│ password       │
│ is_admin       │
│ created_at     │
└────────┬───────┘
         │ 1
         │ (created_by)
         │ N
     ┌───▼──────────────┐
     │    Protein       │
     ├──────────────────┤
     │ id (PK)          │
     │ name             │
     │ sequence         │
     │ organism         │
     │ description      │
     │ method           │
     │ is_public        │
     │ created_by_id(FK)│
     │ created_at       │
     │ updated_at       │
     └───┬──────────────┘
         │ 1
         │ (protein)
         │ N
         └─────────────────────────┐
                                   │
                        ┌──────────▼──────────┐
                        │     Epitope        │
                        ├────────────────────┤
                        │ id (PK)            │
                        │ protein_id (FK)    │
                        │ epitope_sequence   │
                        │ epitope_id         │
                        │ method             │
                        │ start              │
                        │ end                │
                        │ length             │
                        │ score              │
                        │ hopp_woods         │
                        │ kyte_doolittle     │
                        │ karplus_schulz     │
                        │ emini              │
                        │ kolaskar           │
                        │ created_at         │
                        └────────────────────┘

┌──────────────────────┐
│ProteinConversion     │
├──────────────────────┤
│ id (PK)              │
│ original_dna         │
│ rna                  │
│ protein              │
│ created_at           │
└──────────────────────┘

┌──────────────────────┐
│     Token (Auth)     │
├──────────────────────┤
│ key (PK)             │
│ user_id (FK)         │
│ created_at           │
└──────────────────────┘
```

---

## 🔌 ENDPOINTS API {#endpoints-api}

### 📊 Vue complète

```
BASE_URL: http://localhost:8000/api

╔══════════════════════════════════════════════════════════════════════════╗
║                      AUTHENTIFICATION (User)                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  POST   /users/register/                     ❌ Auth   → User créé       ║
║  POST   /users/login/                        ❌ Auth   → Token + Profile ║
║  GET    /users/profile/                      ✅ Auth   → User data      ║
║  POST   /users/logout/                       ✅ Auth   → Token supprimé  ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════╗
║                    PROTEINS (Données principales)                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  CRUD Basique                                                            ║
║  ├─ GET    /proteins/                        ✅ Auth   → Tous publics    ║
║  ├─ POST   /proteins/                        ✅ Auth   → Créer (own)    ║
║  ├─ GET    /proteins/{id}/                   ✅ Auth   → Détails        ║
║  ├─ PUT    /proteins/{id}/                   ✅ Auth   → Modifier (own) ║
║  └─ DELETE /proteins/{id}/                   ✅ Auth   → Supprimer (own)║
║                                                                          ║
║  Filtres Métier                                                          ║
║  ├─ GET    /proteins/public_list/            ❌ Auth   → Public seulement║
║  ├─ GET    /proteins/my_proteins/            ✅ Auth   → Public + Own    ║
║  ├─ GET    /proteins/my_own/                 ✅ Auth   → Own seulement   ║
║  └─ GET    /proteins/all_proteins/           ✅ Admin  → Tous (ANY)      ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════╗
║                  EPITOPES (Analyse & Résultats)                          ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  POST   /epitopes/analyze/                   ❌ Auth   → Epitopes trouvés║
║  GET    /epitopes/                           ✅ Auth   → Liste           ║
║  GET    /epitopes/{id}/                      ✅ Auth   → Détails        ║
║                                                                          ║
║  Paramètres d'analyse (POST /epitopes/analyze/)                          ║
║  ├─ sequence (required): "MVSKQSLLW..."                                 ║
║  ├─ method: "core" | "bio" | "iedb"                                     ║
║  ├─ min_length: 9                                                        ║
║  ├─ max_length: 20                                                       ║
║  ├─ min_score: 0.5                                                       ║
║  └─ top_n: 20                                                            ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════╗
║            CONVERSIONS (DNA → RNA → Protein)                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  POST   /conversions/convert/                ✅ Auth   → Conversion     ║
║  POST   /conversions/convert_large/          ✅ Auth   → Large file     ║
║  GET    /conversions/history/                ✅ Auth   → Historique     ║
║  POST   /conversions/search/                 ✅ Auth   → Rechercher     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

╔══════════════════════════════════════════════════════════════════════════╗
║              AUTRES (Articles, DNA Sequences)                            ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  GET    /articles/                           ✅ Auth   → Article list   ║
║  POST   /articles/                           ✅ Auth   → Créer article  ║
║  GET    /dna/                                ✅ Auth   → DNA sequences   ║
║  POST   /dna/                                ✅ Auth   → Ajouter DNA     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝

Légende:
  ✅ Auth   = Token authentification requise (user connecté)
  ❌ Auth   = Pas d'authentification requise (public)
  Admin    = Seulement pour administrateurs
```

---

## 🔐 FLUX D'AUTHENTIFICATION {#flux-dauthentification}

### Authentification Token

```
1️⃣ INSCRIPTION
   ┌──────────────────┐
   │ Frontend         │
   │ register form    │
   └────────┬─────────┘
            │
            │ POST /api/users/register/
            │ { username, email, password, password_confirm }
            │
   ┌────────▼─────────┐
   │ Backend          │
   │ UserViewSet      │
   │ register()       │
   └────────┬─────────┘
            │
            │ Validation + Hash Password
            │
   ┌────────▼─────────┐
   │ Django Auth      │
   │ create_user()    │
   └────────┬─────────┘
            │
   ┌────────▼─────────┐
   │ Database         │
   │ api_user         │
   └────────┬─────────┘
            │
            │ Response: 201 Created
            │ { user { id, username, email } }
            │
   ┌────────▼─────────┐
   │ Frontend         │
   │ Success message  │
   └──────────────────┘


2️⃣ CONNEXION (LOGIN)
   ┌──────────────────┐
   │ Frontend         │
   │ login form       │
   └────────┬─────────┘
            │
            │ POST /api/users/login/
            │ { username, password }
            │
   ┌────────▼──────────────┐
   │ Backend              │
   │ UserViewSet.login()  │
   │                      │
   │ 1. Authenticate()    │
   │ 2. Get or create Token
   └────────┬──────────────┘
            │
   ┌────────▼──────────────┐
   │ Database             │
   │ Get User             │
   │ Get/Create Token     │
   └────────┬──────────────┘
            │
            │ Response: 200 OK
            │ { 
            │   token: "abc123xyz...",
            │   user: { id, username, is_admin }
            │ }
            │
   ┌────────▼──────────────┐
   │ Frontend             │
   │ Store token          │
   │ localStorage         │
   └──────────────────────┘


3️⃣ UTILISATION (Requêtes authentifiées)
   ┌──────────────────┐
   │ Frontend         │
   │ GET /proteins/   │
   │ Header:          │
   │ Authorization:   │
   │ Token abc123xyz  │
   └────────┬─────────┘
            │
   ┌────────▼──────────────────┐
   │ Backend Middleware        │
   │ Check Token               │
   │ TokenAuthentication()     │
   └────────┬──────────────────┘
            │
   ┌────────▼──────────────────┐
   │ Database                  │
   │ authtoken_token table     │
   │ Find User                 │
   └────────┬──────────────────┘
            │
   ┌────────▼──────────────────┐
   │ ViewSet Permission Check  │
   │ IsAuthenticated           │
   └────────┬──────────────────┘
            │
   ┌────────▼──────────────────┐
   │ Process Request           │
   │ request.user = authenticated
   └────────┬──────────────────┘
            │
            │ Response: Data
            │
   ┌────────▼──────────────────┐
   │ Frontend                  │
   │ Display data              │
   └──────────────────────────┘


4️⃣ DÉCONNEXION (LOGOUT)
   POST /api/users/logout/
   Header: Authorization: Token abc123xyz
   
   → Delete token from database
   → Frontend: Clear localStorage
   → Redirect to login
```

---

## 🧬 MODULES MÉTIER {#modules-métier}

### 1️⃣ Module Authentification

```
UserViewSet:
│
├─ register(@action)
│  ├─ Input: UserRegisterSerializer
│  ├─ Validation:
│  │  ├─ Username unique
│  │  ├─ Email format
│  │  ├─ Password strength (min 8)
│  │  ├─ Password confirmation
│  └─ Output: User created
│
├─ login(@action)
│  ├─ Input: UserLoginSerializer (username, password)
│  ├─ Logic:
│  │  ├─ authenticate(username, password)
│  │  ├─ Token.objects.get_or_create(user)
│  │  ├─ is_admin check
│  └─ Output: Token + User profile
│
├─ profile(@action)
│  ├─ Permission: IsAuthenticated
│  ├─ Output: Current user data
│
└─ logout(@action)
   ├─ Permission: IsAuthenticated
   ├─ Logic: token.delete()
   └─ Output: 204 No Content
```

### 2️⃣ Module Protéines

```
ProteinViewSet:
│
├─ list() [GET /proteins/]
│  ├─ Filter: is_public=True (default)
│  └─ Return: Public proteins
│
├─ create() [POST /proteins/]
│  ├─ Permission: IsAuthenticated
│  ├─ Auto-set: created_by = request.user
│  ├─ Auto-set: is_public = False (défaut privé)
│  └─ Return: Created protein
│
├─ retrieve() [GET /proteins/{id}/]
│  └─ Check: Owner OR is_public OR is_admin
│
├─ update() [PUT /proteins/{id}/]
│  ├─ Permission: Owner only
│  └─ Return: Updated protein
│
├─ destroy() [DELETE /proteins/{id}/]
│  ├─ Permission: Owner only
│  └─ Return: 204 No Content
│
├─ public_list(@action) [GET /proteins/public_list/]
│  ├─ Permission: AllowAny
│  ├─ Filter: is_public=True
│  └─ Return: All public proteins (~11 items)
│
├─ my_proteins(@action) [GET /proteins/my_proteins/]
│  ├─ Permission: IsAuthenticated
│  ├─ Filter: is_public=True OR created_by=user
│  └─ Return: Public + user's proteins (~13 items)
│
├─ my_own(@action) [GET /proteins/my_own/]
│  ├─ Permission: IsAuthenticated
│  ├─ Filter: created_by=user
│  └─ Return: Only user's proteins (~3 items)
│
└─ all_proteins(@action) [GET /proteins/all_proteins/]
   ├─ Permission: IsAuthenticated + is_admin check
   ├─ Filter: No filtering (all records)
   └─ Return: All proteins (13 items)
```

### 3️⃣ Module Épitopes

```
EpitopeAnalysisViewSet:
│
├─ analyze(@action) [POST /epitopes/analyze/]
│  ├─ Permission: AllowAny (public endpoint)
│  ├─ Input:
│  │  ├─ sequence (required): Protein sequence
│  │  ├─ method: "core" | "bio" | "iedb"
│  │  ├─ min_length: 9
│  │  ├─ max_length: 20
│  │  ├─ min_score: 0.5
│  │  └─ top_n: 20
│  ├─ Algorithm:
│  │  1. Validate sequence (AA only)
│  │  2. Sliding window analysis
│  │  3. Calculate 5 metrics:
│  │     a) Hopp-Woods (hydrophobicity)
│  │     b) Kyte-Doolittle (hydrophobicity)
│  │     c) Karplus-Schulz (flexibility)
│  │     d) Emini (accessibility)
│  │     e) Kolaskar (propensity)
│  │  4. Combine metrics → score
│  │  5. Filter by min_score
│  │  6. Sort by score DESC
│  │  7. Limit to top_n
│  ├─ Return: Epitopes found
│  └─ Example: 2 epitopes for MVSKQSLLW...
│
├─ list() [GET /epitopes/]
│  ├─ Permission: IsAuthenticated
│  ├─ Return: All epitope results
│
└─ retrieve() [GET /epitopes/{id}/]
   ├─ Permission: IsAuthenticated
   └─ Return: Epitope details
```

### 4️⃣ Module Conversions

```
ProteinConversionViewSet:
│
├─ convert(@action) [POST /conversions/convert/]
│  ├─ Input: DNA sequence (JSON)
│  ├─ Validation:
│  │  └─ Characters: A,T,G,C only
│  ├─ Process:
│  │  1. DNA → RNA (T→U)
│  │  2. RNA → Protein (codons table)
│  │  3. Save to database
│  └─ Return: { dna, rna, protein, id }
│
├─ convert_large(@action) [POST /conversions/convert_large/]
│  ├─ Purpose: Handle long sequences (form-data)
│  ├─ Input: DNA sequence (form field)
│  ├─ Process:
│  │  1. Remove whitespace/newlines
│  │  2. Validate characters
│  │  3. Same conversion as above
│  ├─ Return: { dna_length, rna_length, protein_length, dna, rna, protein, id }
│
├─ history(@action) [GET /conversions/history/]
│  ├─ Return: All conversions (ordered by -created_at)
│
└─ search(@action) [POST /conversions/search/]
   ├─ Input: DNA sequence
   ├─ Purpose: Find in database
   └─ Return: Matching entries
```

---

## 🛠️ STACK TECHNOLOGIQUE {#stack-technologique}

### Backend
```
┌──────────────────────────────────────┐
│         Framework & Libraries        │
├──────────────────────────────────────┤
│                                      │
│  Django 6.0.2                        │
│  ├─ ORM for DB abstraction           │
│  ├─ Admin interface                  │
│  ├─ Middleware system                │
│  └─ Security features                │
│                                      │
│  Django REST Framework               │
│  ├─ Serializers                      │
│  ├─ ViewSets                         │
│  ├─ Routers                          │
│  ├─ Permissions                      │
│  ├─ Authentication                   │
│  └─ Pagination                       │
│                                      │
│  Python 3.13                         │
│  ├─ Genetic code table               │
│  ├─ Sequence analysis                │
│  └─ Data processing                  │
│                                      │
│  SQLite 3 (Development)              │
│  └─ Can be replaced with PostgreSQL  │
│     or MySQL for production          │
│                                      │
└──────────────────────────────────────┘
```

### Outils de Développement
```
├─ Postman               (API testing)
├─ Django Admin          (Management)
├─ Git                   (Version control)
└─ pytest / unittest     (Testing)
```

---

## 📊 FLUX D'EXÉCUTION - CAS D'USAGE {#flux-execution}

### Cas 1: Utilisateur PUBLIC (No auth)

```
1. Accéder à la page d'accueil
   └─ GET /api/proteins/public_list/
      └─ Voir 11 proteins publics

2. Analyser un protein
   └─ POST /api/epitopes/analyze/
      ├─ Envoyer: { sequence, method, params }
      └─ Reçevoir: 2 epitopes trouvés
```

### Cas 2: Utilisateur CONNECTÉ

```
1. S'inscrire
   └─ POST /api/users/register/
      ├─ Envoyer: { username, email, password, password_confirm }
      └─ Créer: New User

2. Se connecter
   └─ POST /api/users/login/
      ├─ Envoyer: { username, password }
      └─ Reçevoir: Token + Profile

3. Voir mon dashboard
   └─ GET /api/proteins/my_proteins/
      ├─ Header: Authorization: Token XXX
      └─ Voir: 13 proteins (4 public + 9 own)

4. Créer un protein personnel
   └─ POST /api/proteins/
      ├─ Header: Authorization: Token XXX
      ├─ Envoyer: { sequence, name, organism, description }
      ├─ Set: created_by = [current user]
      ├─ Set: is_public = false (défaut)
      └─ Créer: New Protein

5. Analyser mes proteins
   └─ GET /api/proteins/{id}/
      └─ Voir: Details + epitopes

6. Me déconnecter
   └─ POST /api/users/logout/
      ├─ Header: Authorization: Token XXX
      └─ Delete: Token
```

### Cas 3: ADMINISTRATEUR

```
1. Se connecter avec compte admin
   └─ POST /api/users/login/
      ├─ Username: admin
      ├─ Password: admin123
      └─ Reçevoir: Token (is_admin=true)

2. Voir TOUS les proteins
   └─ GET /api/proteins/all_proteins/
      ├─ Header: Authorization: Token XXX
      ├─ Check: is_admin = true
      └─ Voir: 13 proteins (ALL)

3. Gérer les proteins
   ├─ Modifier any protein
   │  └─ PUT /api/proteins/{id}/
   │
   ├─ Supprimer any protein
   │  └─ DELETE /api/proteins/{id}/
   │
   └─ Modifier permissions (is_public)

4. Accéder Django Admin
   └─ GET /admin/
      ├─ Login: admin / admin123
      └─ Gérer: Users, Proteins, Epitopes, etc.
```

---

## 🔐 PERMISSIONS & CONTRÔLE D'ACCÈS

```
┌─────────────────────────────────────────────────────────┐
│              Permission Matrix                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Action                    │ Anonymous │ User │ Admin  │
│  ─────────────────────────────────────────────────────  │
│  GET /proteins/public_list │    ✅     │  ✅  │   ✅   │
│  GET /proteins/my_proteins │    ❌     │  ✅  │   ✅   │
│  GET /proteins/my_own/     │    ❌     │  ✅  │   ✅   │
│  GET /proteins/all_proteins│    ❌     │  ❌  │   ✅   │
│  POST /proteins/           │    ❌     │  ✅  │   ✅   │
│  POST /epitopes/analyze/   │    ✅     │  ✅  │   ✅   │
│  POST /users/register/     │    ✅     │  ✅  │   ✅   │
│  POST /users/login/        │    ✅     │  ✅  │   ✅   │
│  POST /users/logout/       │    ❌     │  ✅  │   ✅   │
│  GET /users/profile/       │    ❌     │  ✅  │   ✅   │
│  GET /admin/               │    ❌     │  ❌  │   ✅   │
│                                                         │
│  ✅ = Autorisé                                          │
│  ❌ = Interdit (401 Unauthorized / 403 Forbidden)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📈 SCALABILITÉ & PRODUCTION

### Améliorations possibles

```
1. DATABASE
   ├─ SQLite → PostgreSQL
   ├─ Connection pooling
   └─ Indexing on filtered fields

2. CACHING
   ├─ Redis for frequent queries
   ├─ Cache protein lists
   └─ Cache user sessions

3. ASYNCHRONOUS
   ├─ Celery for background tasks
   ├─ Epitope analysis async
   └─ File processing async

4. API OPTIMIZATION
   ├─ GraphQL alternative
   ├─ Query pagination
   ├─ Response compression
   └─ Rate limiting

5. SECURITY
   ├─ HTTPS/SSL
   ├─ CORS configuration
   ├─ Rate limiting
   ├─ Input validation
   └─ CSRF protection

6. MONITORING
   ├─ Logging
   ├─ Error tracking (Sentry)
   ├─ Performance monitoring
   └─ Analytics
```

---

## 📚 FICHIERS CLÉS - RÉSUMÉ

| Fichier | Rôle |
|---------|------|
| `config/settings.py` | Configuration Django (BD, apps, middleware) |
| `config/urls.py` | URLs principales / router |
| `api/models.py` | Modèles de données (User, Protein, Epitope, etc.) |
| `api/views.py` | Business logic & endpoints |
| `api/serializers.py` | Data transformation |
| `api/urls.py` | Routes API |
| `api/permissions.py` | Custom permission classes |
| `epitop1/` | Epitope analysis algorithms |
| `manage.py` | Django entry point |
| `db.sqlite3` | Database file |

---

## ✨ RÉSUMÉ COMPLET EN UNE IMAGE

```
                   FRONTEND
                      │
              HTTP/REST API (JSON)
                      │
        ┌─────────────▼─────────────┐
        │   Django REST Framework   │
        │  (config/urls.py routing) │
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │          ViewSets (api/views.py)          │
        │                                           │
        │ • UserViewSet (auth)                      │
        │ • ProteinViewSet (CRUD + filters)        │
        │ • EpitopeAnalysisViewSet (analysis)      │
        │ • ProteinConversionViewSet (genetics)    │
        └─────────────┬─────────────────────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │  Serializers (api/serializers.py)        │
        │  + Business Logic (api/views.py)         │
        │  + Permissions (custom classes)          │
        └─────────────┬─────────────────────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │     Models (api/models.py)                │
        │                                           │
        │ • User (auth + admin flag)                │
        │ • Protein (sequences + metadata)          │
        │ • Epitope (analysis results + metrics)    │
        │ • ProteinConversion (DNA→RNA→Protein)    │
        │ • Article, DNASequence                    │
        └─────────────┬─────────────────────────────┘
                      │
        ┌─────────────▼─────────────────────────────┐
        │      SQLite3 Database                     │
        │      (db.sqlite3)                         │
        └───────────────────────────────────────────┘
```

---

## 🎯 POUR ALLER PLUS LOIN

- **Routes complètes**: Voir [ALL_ENDPOINTS_REFERENCE.md](ALL_ENDPOINTS_REFERENCE.md)
- **Frontend guide**: Voir [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md)
- **Testing**: Voir [API_TESTING_GUIDE.md](backend_api/API_TESTING_GUIDE.md)
- **Quick start**: Voir [START_HERE.md](START_HERE.md)

---

**Dernière mise à jour**: 14 Avril 2026
**Version**: 1.0 - Architecture Complète
