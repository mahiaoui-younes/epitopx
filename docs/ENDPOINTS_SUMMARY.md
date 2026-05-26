# 🚀 API ENDPOINTS - RÉSUMÉ COMPLET

## 📋 Vue d'ensemble des 4 endpoints principaux

---

## 1️⃣ **LISTER TOUS LES PROTEINS PUBLIQUES** (Sans Token)

```
GET /api/proteins/public_list/
```

### 🔓 Authentification: **NON REQUISE** (AllowAny)

### Réponse:
```json
{
  "count": 11,
  "message": "Public proteins (no token required)",
  "results": [
    {
      "id": 1,
      "name": "Protein1",
      "sequence": "MVSKQSLLW...",
      "is_public": true,
      "created_by": "admin",
      "date_created": "2024-01-15T10:30:00Z"
    },
    ...
  ]
}
```

### cURL:
```bash
curl http://localhost:8000/api/proteins/public_list/
```

### ✅ Cas d'usage:
- Afficher tous les proteins publiques sur la page d'accueil
- Pas besoin de login pour voir les proteins disponibles
- Affichage libre de toutes les proteins publies par adminsdirs

---

## 2️⃣ **FAIRE L'ANALYSE DE EPITOPE** (Sans Token)

```
POST /api/epitopes/analyze/
```

### 🔓 Authentification: **NON REQUISE** (AllowAny)

### Body:
```json
{
  "sequence": "MVSKQSLLWNTFTPPLLLSGLLGWFQAKSDSAVEGVQVKVKALPDAQFEVV",
  "method": "core",
  "min_length": 9,
  "max_length": 20,
  "min_score": 0.5,
  "top_n": 20
}
```

### Réponse:
```json
{
  "id": 123,
  "sequence": "MVSKQSLLW...",
  "epitopes": [
    {
      "start": 5,
      "end": 14,
      "sequence": "QSLLWNTFTP",
      "score": 0.7823,
      "length": 10
    },
    ...
  ],
  "analysis_results": {
    "amino_acid_composition": {...},
    "residue_statistics": {...}
  }
}
```

### cURL:
```bash
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "sequence": "MVSKQSLLW...",
    "method": "core"
  }'
```

### ✅ Cas d'usage:
- Analyser une nouvelle sequence sans se logger
- Tool public de prediction
- Utilisable librement par n'importe qui

---

## 3️⃣ **VOIR MES PROTEINS** (Avec Token - User)

```
GET /api/proteins/my_proteins/
```

### 🔐 Authentification: **REQUISE** (IsAuthenticated)

### Headers:
```
Authorization: Token YOUR_TOKEN_HERE
```

### Réponse (User):
```json
{
  "count": 6,
  "username": "testuser",
  "is_admin": false,
  "message": "Your visible proteins (authenticated)",
  "results": [
    {
      "id": 1,
      "name": "PublicProtein1",
      "is_public": true,
      "created_by": "admin",
      "date_created": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "name": "MyPrivateProtein",
      "is_public": false,
      "created_by": "testuser",
      "date_created": "2024-02-20T15:45:00Z"
    },
    ...
  ]
}
```

### cURL:
```bash
curl  -H "Authorization: Token abc123xyz..." \
  http://localhost:8000/api/proteins/my_proteins/
```

### ✅ Cas d'usage:
- User connecté voit: **proteins publiques + ses propres proteins**
- Dashboard personnel
- Voir quels proteins on peut accéder

### 📊 Quoi voit le user?
- ✅ Tous les proteins publics (is_public=true)
- ✅ Ses propres proteins (created_by=testuser)
- ❌ Proteins privés d'autres users

---

## 4️⃣ **VOIR TOUS LES PROTEINS** (Avec Token - Admin)

```
GET /api/proteins/all_proteins/
```

### 🔐 Authentification: **REQUISE + ADMIN** (IsAuthenticated + Admin)

### Headers:
```
Authorization: Token ADMIN_TOKEN_HERE
```

### Réponse (Admin):
```json
{
  "count": 13,
  "message": "All proteins (admin access)",
  "admin": "admin",
  "results": [
    {
      "id": 1,
      "name": "PublicProtein1",
      "is_public": true,
      "created_by": "admin",
      "date_created": "2024-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "name": "MyPrivateProtein",
      "is_public": false,
      "created_by": "testuser",
      "date_created": "2024-02-20T15:45:00Z"
    },
    {
      "id": 3,
      "name": "AnotherUserPrivate",
      "is_public": false,
      "created_by": "otheruser",
      "date_created": "2024-02-21T09:15:00Z"
    },
    ...
  ]
}
```

### cURL:
```bash
curl -H "Authorization: Token admin_token..." \
  http://localhost:8000/api/proteins/all_proteins/
```

### ✅ Cas d'usage:
- Admin voit TOUS les proteins
- Modération et contrôle
- Dashboard administratif
- Analytics et statistiques

### 📊 Quoi voit l'admin?
- ✅ Tous les proteins (public + privé)
- ✅ Peut voir qui a créé chaque protein
- ✅ Accès complet à toutes les données
- ✅ Note: Si user essaie accéder → **403 Forbidden**

---

## 🔒 RÉSUMÉ: Permissions & Authentification

| Endpoint | Méthode | Token Requis | Accès | Vois |
|----------|---------|--------------|-------|------|
| /api/proteins/public_list/ | GET | ❌ NON | PUBLIC | Proteins publics seulement |
| /api/epitopes/analyze/ | POST | ❌ NON | PUBLIC | Pas de limites |
| /api/proteins/my_proteins/ | GET | ✅ OUI | USER | Public + vos propres |
| /api/proteins/all_proteins/ | GET | ✅ OUI (ADMIN) | ADMIN | TOUT |

---

## 🎯 WORKFLOW EXEMPLE

### 1. Visiteur non-connecté:
```bash
# Voir les proteins publics
curl http://localhost:8000/api/proteins/public_list/

# Faire une analyse
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -d '{"sequence": "MVSKQSLLW..."}'
```

### 2. User connecté:
```bash
# Login d'abord
TOKEN=$(curl -X POST http://localhost:8000/api/users/login/ \
  -d '{"username":"testuser","password":"test123"}' | grep token)

# Voir ses proteins (public + ses propres)
curl -H "Authorization: Token $TOKEN" \
  http://localhost:8000/api/proteins/my_proteins/

# Créer un nouveau protein (sera PRIVATE)
curl -X POST -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"MyProtein","sequence":"MVSK..."}' \
  http://localhost:8000/api/proteins/
```

### 3. Admin:
```bash
# Login admin
TOKEN=$(curl -X POST http://localhost:8000/api/users/login/ \
  -d '{"username":"admin","password":"admin123"}' | grep token)

# Voir TOUS les proteins (public + privé de tout le monde)
curl -H "Authorization: Token $TOKEN" \
  http://localhost:8000/api/proteins/all_proteins/

# Créer un PUBLIC protein
curl -X POST -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"PublicProtein","sequence":"MVSK...","is_public":true}' \
  http://localhost:8000/api/proteins/
```

---

## 🚨 ERREURS COURANTES

### `401 Unauthorized`
```json
{
  "detail": "Authentication credentials were not provided."
}
```
✅ **Solution:** Ajoute le header `Authorization: Token YOUR_TOKEN`

### `403 Forbidden`
```json
{
  "error": "Only admins can access all proteins"
}
```
✅ **Solution:** L'utilisateur n'est pas admin. Utilise un compte admin.

### `404 Not Found`
```json
{
  "detail": "Not found."
}
```
✅ **Solution:** Le protein n'existe pas ou tu n'as pas accès (privé d'un autre user)

---

## 💡 NOTES IMPORTANTES

### Pour `/api/proteins/public_list/`:
- ✅ Aucune authentification requise
- ✅ Retourne seulement `is_public=true`
- ✅ Idéal pour page d'accueil publique

### Pour `/api/epitopes/analyze/`:
- ✅ Aucune authentification requise
- ✅ N'importe qui peut analyser
- ✅ Pas de création de protein associé
- ✅ Tool public gratuit

### Pour `/api/proteins/my_proteins/`:
- ✅ Token obligatoire
- ✅ User voit: public + ses propres
- ✅ Si admin, voit tous les proteins

### Pour `/api/proteins/all_proteins/`:
- ✅ Token obligatoire + Admin seulement
- ✅ Accès complet à tous les proteins
- ✅ User régulier reçoit 403 Forbidden

---

## 🧪 TEST RAPIDE

Copie/colle dans ton terminal:

```bash
# 1. Voir proteins publics (NO TOKEN)
curl http://localhost:8000/api/proteins/public_list/

# 2. Analyser (NO TOKEN)
curl -X POST http://localhost:8000/api/epitopes/analyze/ \
  -H "Content-Type: application/json" \
  -d '{"sequence":"MVSKQSLLWNTFTPPLLLSGLLGWFQ"}'

# 3. Voir mes proteins (AVEC TOKEN testuser)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/proteins/my_proteins/

# 4. Voir tous (ADMIN SEULEMENT)
curl -H "Authorization: Token ADMIN_TOKEN" \
  http://localhost:8000/api/proteins/all_proteins/
```

---

## 📱 Intégration Frontend

### React/Vue Example:
```javascript
// 1. Voir proteins publics (FREE)
fetch('/api/proteins/public_list/')
  .then(r => r.json())
  .then(data => console.log(data.results))

// 2. Analyser (FREE)
fetch('/api/epitopes/analyze/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({sequence: 'MVSK...'})
})

// 3. User - voir ses proteins (LOGIN)
fetch('/api/proteins/my_proteins/', {
  headers: {'Authorization': `Token ${userToken}`}
})

// 4. Admin - voir tous (ADMIN LOGIN)
fetch('/api/proteins/all_proteins/', {
  headers: {'Authorization': `Token ${adminToken}`}
})
```

---

✨ **API est maintenant complète avec 4 endpoints clés!**
