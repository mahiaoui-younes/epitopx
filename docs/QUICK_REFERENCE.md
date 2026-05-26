# 🎓 QUICK REFERENCE - ARCHITECTURE GUIDE

## 🔥 10 THINGS YOU MUST KNOW

### 1. **This is a Django REST API**
```python
# Framework: Django 6.0.2 + Django REST Framework
# Database: SQLite3 (db.sqlite3)
# Auth: Token-based (REST Framework Auth)
# Port: 8000
```

### 2. **How Authentication Works**
```
1. User sends credentials → POST /users/login/
2. Server validates + creates Token
3. Token stored in database (authtoken_token)
4. Frontend: Header = "Authorization: Token abc123"
5. Each request gets validated
```

### 3. **ViewSets = REST Endpoints**
```python
# One ViewSet = Multiple endpoints
# Example: ProteinViewSet = 7 endpoints
#  ├─ GET     /proteins/           (list all public)
#  ├─ POST    /proteins/           (create new)
#  ├─ GET     /proteins/{id}/      (retrieve)
#  ├─ PUT     /proteins/{id}/      (update)
#  ├─ DELETE  /proteins/{id}/      (delete)
#  ├─ GET     /proteins/public_list/
#  └─ GET     /proteins/my_proteins/
```

### 4. **Serializers = Data Validators**
```python
# UserRegisterSerializer
#   - Validates username, email, password
#   - Checks password confirmation
#   - Creates user on .save()

# ProteinSerializer
#   - Converts Python model ↔ JSON
#   - Auto-sets created_by = request.user
#   - Validates field types
```

### 5. **Models = Database Tables**
```
User              → api_user (custom user model)
Protein           → api_protein (sequences)
Epitope           → api_epitope (analysis results)
ProteinConversion → api_proteinconversion (history)
Article           → api_article (content)
DNASequence       → api_dnasequence (reference)
Token             → authtoken_token (authentication)
```

### 6. **Permissions Check Flow**
```
Request comes in
    ↓
Check @permission_classes
    ├─ AllowAny        → Everyone can access
    ├─ IsAuthenticated → Need valid token
    └─ Custom check    → Custom logic
    ↓
If ✅ Pass → Process request
If ❌ Fail → Return 401/403 error
```

### 7. **Request Validation Pipeline**
```
Raw Data (JSON)
    ↓
Serializer.is_valid()  ← Check types, ranges, requirements
    ↓
If ✅ Valid → Continue
If ❌ Invalid → Return 400 Bad Request
    ↓
Business Logic
    ↓
Save to Database
    ↓
Return Response
```

### 8. **Public vs Private Endpoints**
```
PUBLIC (AllowAny)
├─ GET  /proteins/public_list/     ← Only is_public=true
├─ POST /epitopes/analyze/         ← Free tool
├─ POST /users/register/
└─ POST /users/login/

PRIVATE (IsAuthenticated)
├─ GET  /proteins/my_proteins/     ← Your + public
├─ GET  /proteins/my_own/          ← Only yours
├─ POST /proteins/
└─ DELETE /proteins/{id}/          ← If you own it

ADMIN ONLY
└─ GET  /proteins/all_proteins/    ← EVERYTHING
```

### 9. **Epitope Analysis Algorithm**
```
POST /epitopes/analyze/ { sequence, method, params }
    ↓
1. Validate: Only amino acids? ✅
2. Sliding Window: 9-20 AA at a time
3. For each window, calculate:
   - Hopp-Woods (hydrophobicity)
   - Kyte-Doolittle (hydrophobicity)
   - Karplus-Schulz (flexibility)
   - Emini (accessibility)
   - Kolaskar (propensity)
4. Combine metrics → Score (0-1)
5. Filter: score >= min_score
6. Sort: Highest first
7. Return: Top 20
```

### 10. **File Structure Logic**
```
config/              ← Global configuration
  ├─ settings.py    ← Databases, apps, middleware, allowed hosts
  ├─ urls.py        ← Main routes (include api.urls)
  └─ wsgi.py        ← WSGI app

api/                 ← Main app (Django: 1 project = many apps)
  ├─ models.py      ← ORM Models (User, Protein, etc.)
  ├─ views.py       ← Business logic + endpoints
  ├─ serializers.py ← Data validation + transformation
  ├─ urls.py        ← API routes (registered with router)
  ├─ permissions.py ← Custom auth classes
  └─ admin.py       ← Django admin configuration

epitop1/             ← Separate module (epitope algorithms)
  └─ _*.py          ← Analysis scripts

manage.py            ← Entry point for Django commands

db.sqlite3           ← Database file (development)
```

---

## 🛠️ COMMON TASKS & HOW TO DO THEM

### Task 1: Add a New User

**Option A: Via API**
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "new@example.com",
    "password": "securepass123",
    "password_confirm": "securepass123"
  }'
```

**Option B: Django Admin**
```
1. Open http://localhost:8000/admin
2. Login: admin / admin123
3. Click "Utilisateurs" → "Ajouter"
4. Fill form → Save
```

**Option C: Django Shell**
```bash
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> User = get_user_model()
>>> user = User.objects.create_user(username='newuser', password='pass')
```

### Task 2: Create a Protein via API

```bash
# 1. Get token first
TOKEN=$(curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}' \
  | grep -o '"token":"[^"]*' | cut -d'"' -f4)

# 2. Create protein
curl -X POST http://localhost:8000/api/proteins/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyProtein",
    "sequence": "MVSKQSLLWEFVYPR",
    "organism": "Human",
    "description": "My test protein",
    "method": "core",
    "is_public": false
  }'
```

### Task 3: Analyze Epitopes (NO AUTH)

```bash
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MVSKQSLLWEFVYPR",
    "method": "core",
    "min_length": 9,
    "max_length": 20,
    "min_score": 0.5,
    "top_n": 20
  }'
```

### Task 4: Filter Proteins

```bash
# Get public proteins (no auth)
curl http://localhost:8000/api/proteins/public_list/

# Get my proteins + public (with auth)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/proteins/my_proteins/

# Get only my proteins (with auth)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/proteins/my_own/

# Get ALL proteins (admin only)
curl -H "Authorization: Token ADMIN_TOKEN" \
  http://localhost:8000/api/proteins/all_proteins/
```

### Task 5: Modify Protein (if owner)

```bash
curl -X PUT http://localhost:8000/api/proteins/1/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "UpdatedName",
    "is_public": true
  }'
```

### Task 6: Database Backup

```bash
# SQLite backup (simple copy)
cp db.sqlite3 db.sqlite3.backup

# Export as SQL
sqlite3 db.sqlite3 .dump > backup.sql

# Restore from SQL
sqlite3 db.sqlite3 < backup.sql
```

### Task 7: Clear Database (DEV ONLY)

```bash
# Option 1: Reset everything
python manage.py flush

# Option 2: Drop a table
python manage.py delete_model api.Protein

# Option 3: Fresh start
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Task 8: Add to Production (PostgreSQL)

**Change in settings.py:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'epitope_db',
        'USER': 'postgres',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

Then:
```bash
pip install psycopg2
python manage.py migrate
```

---

## 📊 SQL QUERIES (Direct)

### See All Users
```sql
SELECT id, username, email, is_admin, created_at 
FROM api_user;
```

### Count Proteins by Visibility
```sql
SELECT is_public, COUNT(*) 
FROM api_protein 
GROUP BY is_public;
```

### Find Top Epitopes
```sql
SELECT epitope_sequence, score, start, end 
FROM api_epitope 
ORDER BY score DESC 
LIMIT 10;
```

### User's Proteins
```sql
SELECT name, sequence, is_public, created_at 
FROM api_protein 
WHERE created_by_id = 2;  -- user_id = 2
```

---

## 🐛 DEBUG: Common Issues & Solutions

### Issue: "401 Unauthorized"
```
Solution:
1. Did you send token? Check header: Authorization: Token XXX
2. Token expired? Get a new one from login
3. Wrong token? Copy-paste carefully
```

### Issue: "403 Forbidden"
```
Solution:
1. Are you the owner? created_by must be your user_id
2. Is it an admin-only action? Check permissions
3. Not admin? Use admin account
```

### Issue: "400 Bad Request"
```
Solution:
1. Missing required field? Check serializer fields
2. Wrong data type? Send string not int, etc.
3. Invalid characters? Protein sequence = A-Z only
4. Validation failed? Check error message
```

### Issue: "Database is locked"
```
Solution:
1. Close other connections
2. Restart server: Ctrl+C then python manage.py runserver
3. Check db.sqlite3 not opened in Excel/Notepad
```

### Issue: "Token not found"
```
Solution:
1. Login first: POST /users/login/
2. Copy token from response
3. Use exactly: Authorization: Token <token>
```

---

## 📈 IMPORTANT FIELDS

### User Model
```
id              → Auto PK
username        → Unique, required
email           → Unique, required (can be duplicated)
password        → Hashed (never stored plain)
is_admin        → Boolean (default: false)
created_at      → Auto timestamp
```

### Protein Model
```
id              → Auto PK
name            → String (required)
sequence        → Text (very long, required)
organism        → String (optional)
description     → Text (optional)
method          → Choice: core/bio/iedb
is_public       → Boolean (default: false)  ← WHO CAN SEE
created_by_id   → ForeignKey → User (tracks owner)
created_at      → Auto
updated_at      → Auto
```

### Epitope Model
```
id              → Auto PK
protein_id      → ForeignKey → Protein
epitope_sequence → String (9-20 AA) (required)
score           → Float (0-1) (main ranking metric)
start/end       → Integer (position in protein)
length          → Integer (epitope length)
hopp_woods      → Float (hydrophobicity metric)
kyte_doolittle  → Float (hydrophobicity metric)
karplus_schulz  → Float (flexibility metric)
emini           → Float (accessibility metric)
kolaskar        → Float (propensity metric)
created_at      → Auto
```

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] Change DEBUG = False in settings.py
- [ ] Add your domain to ALLOWED_HOSTS
- [ ] Use PostgreSQL (not SQLite)
- [ ] Set strong SECRET_KEY
- [ ] Enable HTTPS only
- [ ] Setup CORS properly
- [ ] Add rate limiting
- [ ] Setup logging
- [ ] Backup database regularly
- [ ] Monitor performance
- [ ] Setup CI/CD pipeline

---

## 📚 DOCUMENTATION MAP

| Document | Purpose |
|----------|---------|
| [START_HERE.md](START_HERE.md) | 5-minute quickstart |
| [ARCHITECTURE_COMPLETE.md](ARCHITECTURE_COMPLETE.md) | Deep dive (this doc) |
| [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md) | 60-second overview |
| [ALL_ENDPOINTS_REFERENCE.md](ALL_ENDPOINTS_REFERENCE.md) | All endpoints |
| [FRONTEND_INTEGRATION_GUIDE.md](FRONTEND_INTEGRATION_GUIDE.md) | React/JS integration |
| [API_TESTING_GUIDE.md](backend_api/API_TESTING_GUIDE.md) | Testing guide |

---

## 💬 ASK YOURSELF

1. **What's the difference between public_list and my_proteins?**
   - `public_list`: Only is_public=true (everyone sees)
   - `my_proteins`: your proteins PLUS public (you see both)

2. **Can I delete someone else's protein?**
   - Only if you're admin!
   - Regular user can only delete their own

3. **What if I forget my token?**
   - Login again, get new token
   - Old token still works until manually deleted

4. **Is the database persistent?**
   - YES! SQLite saves to disk (db.sqlite3)
   - Even after server restart, data exists

5. **Can multiple users have same username?**
   - NO! username is unique (UNIQUE constraint)

6. **How are passwords stored?**
   - Hashed (bcrypt)
   - Never stored plain text
   - Even admin can't see original

7. **What's the max protein sequence length?**
   - TextField = unlimited (limited by DB)
   - Practically: millions of characters OK

8. **Is this ready for production?**
   - ✅ Pretty much!
   - Just add: PostgreSQL, HTTPS, rate limiting, monitoring

---

**Last Updated**: 14 April 2026  
**Version**: Quick Reference 1.0  
**Status**: Fully Documented & Operational ✅
