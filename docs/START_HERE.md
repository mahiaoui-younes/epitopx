# 🚀 DÉMARRAGE RAPIDE - 5 MINUTES

## ⚡ What you need to know NOW

**Ton système fonctionne!** ✅

---

## 1️⃣ DÉMARRER LE SERVEUR

```bash
cd c:\Users\asus\Desktop\new\backend_api
python manage.py runserver
```

Server runs on: **http://localhost:8000**

---

## 2️⃣ TEST RAPIDE (Au choix)

### 🏃 FASTEST: Script Python (2 min)
```bash
python test_auth_system.py
```
Voir résumé de tous les tests ✓

### 📮 EASY: Postman (2 min)
1. Ouvrir Postman
2. Import: `Epitop1_User_Auth_API_Collection.postman_collection.json`
3. Click "TestUser Login" → enter token → click other requests
4. See results

### 🌐 BROWSER: Django Admin (1 min)
```
http://localhost:8000/admin
Login: admin / admin123
See users & proteins
```

---

## 3️⃣ USED TEST ACCOUNTS

| User | Password | Role |
|------|----------|------|
| admin | admin123 | ADMIN - voir tout |
| testuser | test123 | USER - voir publique + sien |

---

## 4️⃣ TRY THESE 3 THINGS

### A) Login & Get Token
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"test123"}'
```
**Response:**
```json
{
  "token": "abc123xyz...",
  "user": {
    "username": "testuser",
    "is_admin": false
  }
}
```
✅ Copy le token!

### B) List Proteins (avec token)
```bash
curl -X GET http://localhost:8000/api/proteins/ \
  -H "Authorization: Token abc123xyz..."
```
**Result:** Tu vois 13 proteins (4 public + 2 tienne + 7 legacy)

### C) Create Protein (avec token)
```bash
curl -X POST http://localhost:8000/api/proteins/ \
  -H "Authorization: Token abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MVSKQSLLW...",
    "name": "MyNewProtein"
  }'
```
**Result:** Status 201 ✓ (created_by=testuser, is_public=false)

---

## 5️⃣ KEY ENDPOINTS

| Method | Endpoint | Auth | Result |
|--------|----------|------|--------|
| POST | /api/users/register/ | ❌ | Créer user |
| POST | /api/users/login/ | ❌ | Get token |
| GET | /api/users/profile/ | ✅ | Voir profil |
| POST | /api/users/logout/ | ✅ | Supprimer token |
| GET | /api/proteins/ | ✅ | List (filtrée) |
| POST | /api/proteins/ | ✅ | Create (auto private) |
| GET | /api/proteins/{id}/ | ✅ | View |
| PUT | /api/proteins/{id}/ | ✅ | Edit (owner/admin) |
| DELETE | /api/proteins/{id}/ | ✅ | Delete (owner/admin) |

---

## 6️⃣ WHAT TO UNDERSTAND

### Permission Logic
```
Je suis: testuser (user)
Je vois:
  ✓ Proteins publiques (is_public=true)
  ✓ Mes proteins (created_by=testuser)
  ✗ Proteins privées d'autres

Je peux:
  ✓ Créer proteins (forcément private)
  ✓ Éditer mes proteins
  ✗ Créer publique
  ✗ Éditer d'autres
```

### Admin Privilege
```
Je suis: admin (is_admin=true)
Je vois:
  ✓ TOUTES les proteins (public + private)

Je peux:
  ✓ Créer publique ET private
  ✓ Éditer TOUTES
  ✓ Supprimer TOUTES
```

---

## 7️⃣ COMMON TASKS

### Créer un nouvel user
```bash
curl -X POST http://localhost:8000/api/users/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "new@example.com",
    "password": "password123",
    "password_confirm": "password123"
  }'
```

### Login cet nouveau user
```bash
curl -X POST http://localhost:8000/api/users/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","password":"password123"}'
```

### Créer protein PUBLIQUE (admin seulement)
```bash
curl -X POST http://localhost:8000/api/proteins/ \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MVSKQ...",
    "name": "AdminPublicProtein",
    "is_public": true
  }'
```

### Créer protein PRIVÉE (user)
```bash
curl -X POST http://localhost:8000/api/proteins/ \
  -H "Authorization: Token USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MVSKQ...",
    "name": "MyPrivateProtein"
  }'
```
Note: `is_public` est ignoré pour users (toujours private)

---

## 8️⃣ TROUBLESHOOTING

**Q: "401 Unauthorized"**
A: T'as oublié le token dans Authorization header. Format:
```
Authorization: Token abc123xyz...
```

**Q: "403 Forbidden"**
A: T'as pas la permission. C'est normal!
- User essayant éditer protein d'admin → 403 ✓
- User essayant créer publique → 400 ✓

**Q: "404 Not Found"**
A: T'essaies d'accéder une protein que tu vois pas
- User regex protein privée d'autre → 404 ✓

**Q: Server doesn't start**
A: 
```bash
python manage.py migrate
python manage.py runserver
```

**Q: Resets tests (veux fresh data)**
A:
```bash
python reset_db.py
python create_demo_users.py
```

---

## 9️⃣ FILES YOU HAVE

| File | What | Use When |
|------|------|----------|
| test_auth_system.py | Auto tests | Want validation ✓✓ |
| Epitop1_User_Auth_API_Collection.postman_collection.json | Postman | Want GUI testing |
| USER_AUTHENTICATION_API_GUIDE.md | Full docs | Need details |
| API_IMPLEMENTATION_SUMMARY.md | This | Want overview |
| QUICK_TEST_GUIDE.md | Examples | Want code samples |

---

## 🔟 READY?

```
✅ Server: running
✅ Authentication: working
✅ Permissions: enforced
✅ Tests: passing
✅ Documentation: complete

👉 NOW: Pick a test method above & TRY IT!
```

---

## 🎊 C'EST OK!

Tu as:
- ✅ User authentication system
- ✅ Token-based API
- ✅ Role-based permissions (user/admin)
- ✅ Private/public proteins
- ✅ Complete documentation
- ✅ Working tests

**Time to build the frontend!** 🚀

---

**Questions? Check:**
- USER_AUTHENTICATION_API_GUIDE.md (detailed)
- QUICK_TEST_GUIDE.md (examples)
- test_auth_system.py (working code)

**Need help?** Look at test_auth_system.py - it shows exactly how to use every endpoint!
