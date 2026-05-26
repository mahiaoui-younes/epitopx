## 🎯 EpiTop1 - USER AUTHENTICATION & PROTEIN PERMISSIONS SYSTEM

### ✨ Système Implémenté

**OBJECTIF**: 
- Chaque user authentifié ne voit que SES PROPRES proteins créées
- Seuls les **admins** peuvent créer des proteins **PUBLIQUES** visibles par tous
- Les users réguliers voient: proteins publiques + leurs propres proteins
- Authentification par **Token JWT**

---

## 🔐 AUTHENTIFICATION - Base URL: http://localhost:8000/api/users/

### 1. **REGISTER** - Créer un compte utilisateur
```http
POST /api/users/register/

Body (JSON):
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "password123",
  "password_confirm": "password123"
}

Response (201 Created):
{
  "user": {
    "id": 1,
    "username": "newuser",
    "email": "newuser@example.com",
    "is_admin": false,
    "created_at": "2026-04-11T23:40:00Z"
  },
  "token": "abc123xyz789...",
  "message": "User registered successfully"
}
```

### 2. **LOGIN** - Se connecter et obtenir le token
```http
POST /api/users/login/

Body (JSON):
{
  "username": "testuser",
  "password": "test123"
}

Response (200 OK):
{
  "user": {
    "id": 2,
    "username": "testuser",
    "email": "testuser@example.com",
    "is_admin": false,
    "created_at": "2026-04-11T23:40:00Z"
  },
  "token": "def456uvw123...",
  "is_admin": false,
  "message": "Login successful"
}

⚠️ IMPORTANT: Sauvegarder le token pour les requêtes suivantes
```

### 3. **PROFILE** - Voir le profil utilisateur courant
```http
GET /api/users/profile/
Headers:
  Authorization: Token def456uvw123...

Response (200 OK):
{
  "id": 2,
  "username": "testuser",
  "email": "testuser@example.com",
  "is_admin": false,
  "created_at": "2026-04-11T23:40:00Z"
}
```

### 4. **LOGOUT** - Se déconnecter
```http
POST /api/users/logout/
Headers:
  Authorization: Token def456uvw123...

Response (200 OK):
{
  "message": "Logout successful"
}
```

---

## 🧬 PROTEINS - Base URL: http://localhost:8000/api/proteins/

### RÈGLES D'ACCÈS:

| Action | User Régulier | Admin |
|--------|---------------|-------|
| Voir proteins publiques | ✅ Oui | ✅ Oui |
| Voir ses propres proteins | ✅ Oui | ✅ Oui |
| Créer une protein (private) | ✅ Oui | ✅ Oui |
| Créer une protein (public) | ❌ Non (403) | ✅ Oui |
| Editer ses proteins | ✅ Oui | ✅ Oui |
| Editer d'autres proteins | ❌ Non (403) | ✅ Oui |
| Supprimer ses proteins | ✅ Oui | ✅ Oui |

---

### 1. **LIST** - Récupérer la liste des proteins visibles
```http
GET /api/proteins/
Headers:
  Authorization: Token def456uvw123...

Response (200 OK):
[
  {
    "id": 1,
    "name": "Insulin",
    "organism": "Human",
    "is_public": true,
    "owner_username": "admin",
    "sequence": "GIVEQCCTSICSLYQLENYCN...",
    "epitope_count": 5,
    "created_at": "2026-04-11T23:40:00Z"
  },
  {
    "id": 2,
    "name": "MyProtein",
    "organism": "Bacterial",
    "is_public": false,
    "owner_username": "testuser",
    "sequence": "MKVLWAALLVTFLAGCAK...",
    "epitope_count": 0,
    "created_at": "2026-04-11T23:41:00Z"
  }
]

ℹ️ User "testuser" voit:
  - Protein 1 (public de admin)
  - Protein 2 (sa propre protein privée)

ℹ️ User "admin" voit:
  - TOUTES les proteins (publiques + privées de tous)
```

---

### 2. **CREATE** - Ajouter une nouvelle protein
```http
POST /api/proteins/
Headers:
  Authorization: Token def456uvw123...
  Content-Type: application/json

Body (JSON):
{
  "name": "MyProtein",
  "sequence": "MKVLWAALLVTFLAGCAKAKAQVKVKALPDAQFEVVHKSENLSPLTSSVDAAMELNGKVVSDQQMQ",
  "organism": "Bacterial",
  "description": "My test protein",
  "method": "core",
  "is_public": false
}

Response (201 Created):
{
  "id": 2,
  "name": "MyProtein",
  "organism": "Bacterial",
  "sequence": "MKVLWAALLVTFLAG...",
  "description": "My test protein",
  "epitope_count": 0,
  "is_public": false,
  "created_by": 2,
  "owner_username": "testuser",
  "created_at": "2026-04-11T23:41:00Z"
}

⚠️ IMPORTANT:
- User régulier: is_public est ignoré, toujours FALSE (privé)
- Admin: peut choisir is_public TRUE/FALSE
```

### 3. **ADMIN CREATE PUBLIC** - Admin crée une protein publique
```http
POST /api/proteins/
Headers:
  Authorization: Token admin_token...
  Content-Type: application/json

Body (JSON):
{
  "name": "PublicProtein",
  "sequence": "MKVLWAALLVTFLAGCAK...",
  "organism": "Human",
  "is_public": true
}

Response (201 Created):
{
  "id": 3,
  "name": "PublicProtein",
  "is_public": true,
  "owner_username": "admin",
  ...
}

✅ Maintenant TOUS les users voient cette protein!
```

### 4. **RETRIEVE** - Voir une protein spécifique
```http
GET /api/proteins/{id}/
Headers:
  Authorization: Token def456uvw123...

Response (200 OK):
{
  "id": 1,
  "name": "Insulin",
  "sequence": "GIVEQCCTSICSLYQLENYCN...",
  "organism": "Human",
  "is_public": true,
  "owner_username": "admin",
  "epitope_count": 5,
  ...
}

❌ 404 Not Found - Si ce n'est pas public et ce n'est pas le propriétaire
```

### 5. **UPDATE** - Modifier une protein
```http
PUT /api/proteins/{id}/
Headers:
  Authorization: Token def456uvw123...
  Content-Type: application/json

Body (JSON):
{
  "name": "MyProtein Updated",
  "description": "Updated description",
  "organism": "Gram-Positive Bacterial"
}

Response (200 OK):
{ updated protein }

❌ 403 Forbidden - Si ce n'est pas votre protein et vous n'êtes pas admin
```

### 6. **DELETE** - Supprimer une protein
```http
DELETE /api/proteins/{id}/
Headers:
  Authorization: Token def456uvw123...

Response (204 No Content):
(No body)

❌ 403 Forbidden - Si ce n'est pas votre protein et vous n'êtes pas admin
```

---

## 🔬 TESTS AVEC POSTMAN

### Test Scenario 1: User Crée une Protein Privée
```
1. POST /api/users/login/
   - Username: testuser
   - Password: test123
   → Sauver TOKEN_USER

2. POST /api/proteins/
   - Authorization: Token TOKEN_USER
   - Body: { "name": "PrivateProtein", "sequence": "...", "is_public": false }
   → Status 201 Created

3. GET /api/proteins/
   - Authorization: Token TOKEN_USER
   → Voir: proteins publiques + PrivateProtein (sa propre)
```

### Test Scenario 2: Admin Crée une Protein Publique
```
1. POST /api/users/login/
   - Username: admin
   - Password: admin123
   → Sauver TOKEN_ADMIN

2. POST /api/proteins/
   - Authorization: Token TOKEN_ADMIN
   - Body: { "name": "PublicProtein", "sequence": "...", "is_public": true }
   → Status 201 Created

3. GET /api/proteins/
   - Authorization: Token TOKEN_USER (ou n'importe quel user)
   → Voir: PublicProtein de l'admin!
```

### Test Scenario 3: User Ne Peut Pas Editer/Supprimer protein d'Admin
```
1. PUT /api/proteins/1/ (protein d'admin)
   - Authorization: Token TOKEN_USER
   - Body: { "name": "Hacked" }
   → Status 403 Forbidden "You can only edit your own proteins"

2. DELETE /api/proteins/1/
   - Authorization: Token TOKEN_USER
   → Status 403 Forbidden "You can only delete your own proteins"
```

---

## 📝 COMPTES DE TEST PRÊTS

```
ADMIN USER:
  - Username: admin
  - Password: admin123
  - Droits: Créer/voir/modifier/supprimer TOUTES les proteins

USER RÉGULIER:
  - Username: testuser
  - Password: test123
  - Droits: Voir publiques + ses propres proteins

Pour tester, utilisez:
  - Postman (collection à créer)
  - cURL
  - Python requests
  - Angular/React frontend (à venir)
```

---

## 🚀 IMPLENTATION BACKEND COMPLÈTE

### Files Modifiés:
1. **models.py** - Ajout Custom User model + fields permissions
2. **serializers.py** - UserRegisterSerializer, UserLoginSerializer, ProteinSerializer mis à jour
3. **views.py** - UserViewSet (login/register/logout) + ProteinViewSet avec permissions
4. **urls.py** - Routes d'authentification accessibles
5. **settings.py** - Token authentification activée

### Architecture:
```
Request (Token)
    ↓
IsAuthenticated Check
    ↓
Permission Class
    ↓
View (User-filtered queryset)
    ↓
- User voit: publiques + ses propres
- Admin voit: toutes
```

---

## 🎯 PROCHAINES ÉTAPES

À faire:
- [ ] Frontend Angular/React pour UI
- [ ] Tests unitaires pour permissions
- [ ] Admin panel pour gérer users
- [ ] Notifications quand un protein devient public
- [ ] Rôles plus granulaires (viewer, editor, owner)

---

## 📞 SUPPORT RAPIDE

**Q: J'essaie accéder une protein et j'ai 404**
A: Vous n'êtes pas propriétaire et elle n'est pas publique. Demandez à l'owner de la rendre publique (admin seulement).

**Q: Je peux créer une protein publique en tant que user?**
A: Non, seuls les admins peuvent créer publique. Votre protein est toujours privée. Demandez à un admin de publier.

**Q: Mon token est expiré?**
A: Non (infinite par défaut). Si erreur 401, faites un login() nouveau.

**Q: Je suis admin mais j'ai 403?**
A: Vérifiez que is_admin=true dans votre compte (database).

---

## ✨ RÉSUMÉ

L'API est maintenant **PRÊTE** avec:
✅ Authentification par Token
✅ Permissions par User/Admin
✅ Proteins privées (users) vs publiques (admin only)
✅ Filtrage automatique des données visibles
✅ Sécurité au niveau API

**Server running**: http://localhost:8000
**Admin Panel**: http://localhost:8000/admin
**API Root**: http://localhost:8000/api/


