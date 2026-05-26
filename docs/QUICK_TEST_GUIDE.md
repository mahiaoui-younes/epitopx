# 🚀 DÉMARRAGE RAPIDE - EpiTop1 avec Authentification

## ✨ Ce Qui Fonctionne Maintenant

✅ **Authentification par Token**
- Register → nouveau user
- Login → récupère token
- Token stocké automatiquement pour requêtes suivantes

✅ **Permissions par User/Admin**
- Users: Voient proteins publiques + leurs propres privées
- Admins: Voient TOUTES les proteins

✅ **Proteins Publiques vs Privées**
- Users: Créent seulement PRIVÉES (is_public=false)
- Admins: Peuvent créer PUBLIQUES (is_public=true) visibles par tous

✅ **Protection des Données**
- Users ne peuvent pas modifier/supprimer proteins d'autres
- Admins peuvent tout modifier/supprimer

---

## 📝 COMPTES DE TEST PRÊTS À UTILISER

```
👤 USER (Régulier):
   Username: testuser
   Password: test123
   Droits: Voir public + ses propres proteins

👤 ADMIN:
   Username: admin
   Password: admin123
   Droits: Voir tout, créer public, modifier/supprimer tout
```

---

## 🎯 5 TESTS À FAIRE MAINTENANT

### Test 1: Login User (Obtenir Token)
```
POST http://localhost:8000/api/users/login/

Body:
{
  "username": "testuser",
  "password": "test123"
}

✅ Résultat: Vous avez le TOKEN_USER
```

### Test 2: User Crée une Protein Privée
```
POST http://localhost:8000/api/proteins/

Headers:
  Authorization: Token TOKEN_USER
  Content-Type: application/json

Body:
{
  "name": "MyProtein",
  "sequence": "MKVLWAALLVTFLAGCAK",
  "organism": "Bacterial",
  "is_public": false
}

✅ Résultat: Protein créée (privée, seulement visible par testuser)
```

### Test 3: User Voit Ses Proteins
```
GET http://localhost:8000/api/proteins/

Headers:
  Authorization: Token TOKEN_USER

✅ Résultat: Liste = proteins publiques + "MyProtein" de testuser
```

### Test 4: Login Admin (Obtenir Token Admin)
```
POST http://localhost:8000/api/users/login/

Body:
{
  "username": "admin",
  "password": "admin123"
}

✅ Résultat: Vous avez le TOKEN_ADMIN
```

### Test 5: Admin Crée une Protein Publique
```
POST http://localhost:8000/api/proteins/

Headers:
  Authorization: Token TOKEN_ADMIN
  Content-Type: application/json

Body:
{
  "name": "PublicProtein",
  "sequence": "GIVEQCCTSICSLYQLENYCN",
  "organism": "Human",
  "is_public": true
}

✅ Résultat: 
- Protein créée ET publique
- TOUS les users la voient maintenant!
```

---

## 📊 RÉSULTATS ATTENDUS

### Après Tests, Voici Ce Que Vous Verrez:

```
USER (testuser) voit:
✓ MyProtein (privée, créée par lui)
✓ PublicProtein (publique, créée par admin)
✓ Toute autre protein publique

USER (testuser) PNEU PAS voir:
✗ Proteins privées d'autres users
✗ Proteins privées d'admin

ADMIN voit:
✓ ABSOLUMENT TOUT (publiques + privées + propriétaires)

ADMIN peut:
✓ Créer public/privé librement
✓ Modifier toute protein
✓ Supprimer toute protein
```

---

## 🔒 TESTS DE SÉCURITÉ

### ❌ Test: User Essaie d'Editer Protein d'Admin
```
PUT http://localhost:8000/api/proteins/1/

Headers:
  Authorization: Token TOKEN_USER
Body:
  { "name": "Hacked" }

❌ Résultat: 403 Forbidden
   "You can only edit your own proteins"
```

### ❌ Test: User Essaie de Créer PUBLIC
```
POST http://localhost:8000/api/proteins/

Headers:
  Authorization: Token TOKEN_USER
Body:
  {
    "name": "FakePublic",
    "sequence": "...",
    "is_public": true  ← Demande public
  }

✅ Résultat: Créée MAIS is_public=false (ignoré!)
   Les users ne peuvent pas forcer public
```

---

## 🛠️ AVEC POSTMAN

### 1. Importer la Collection
```
1. Ouvrir Postman
2. Cliquer "Import"
3. Importer: Epitop1_User_Auth_API_Collection.postman_collection.json
4. Sélectionner l'environnement
```

### 2. Setup Variables Globales
```
- base_url: http://localhost:8000
- user_token: (auto-rempli après login)
- admin_token: (auto-rempli après login)
- protein_id: (entrer l'ID d'une protein)
```

### 3. Exécuter les Tests dans l'Ordre
```
1. Authentification → 2. Login TestUser
2. Proteins → 1. List All
3. Proteins → 2. Create Private
4. Proteins → 1. List All (voir la nouvelle)
5. Authentification → 3. Login Admin
6. Proteins → 2. Create Public
7. Proteins → 1. List All (comme testuser, voir la public!)
```

---

## 📂 FICHIERS CRÉÉS

```
✅ models.py - Custom User + permissions
✅ serializers.py - Auth serializers 
✅ views.py - UserViewSet + ProteinViewSet
✅ urls.py - Routes auth
✅ settings.py - Token auth config
✅ create_demo_users.py - Créer users test
✅ USER_AUTHENTICATION_API_GUIDE.md - Guide complet
✅ Epitop1_User_Auth_API_Collection.postman_collection.json - Tests Postman
```

---

## 🚀 API ENDPOINTS RÉSUMÉ

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| /api/users/register/ | POST | No | Créer compte |
| /api/users/login/ | POST | No | Login → token |
| /api/users/profile/ | GET | Yes | Voir profil |
| /api/users/logout/ | POST | Yes | Logout |
| /api/proteins/ | GET | Yes | Lister proteins (filtrées) |
| /api/proteins/ | POST | Yes | Créer protein |
| /api/proteins/{id}/ | GET | Yes | Voir une protein |
| /api/proteins/{id}/ | PUT | Yes | Editer (owner/admin only) |
| /api/proteins/{id}/ | DELETE | Yes | Supprimer (owner/admin only) |

---

## 📞 TROUBLESHOOTING

**Q: 401 Unauthorized**
- A: Token manquant ou expiré → faire login()

**Q: 403 Forbidden sur PUT/DELETE**
- A: Vous n'êtes pas propriétaire → demander à owner

**Q: is_public ne change pas à true (user)**
- A: Normal! Users ne peuvent créer que privé

**Q: Ne vois pas protein d'admin**
- A: Elle est privée → admin doit la rendre publique

**Q: Serveur ne démarre?**
- A: Vérifier: `python manage.py migrate` + `python create_demo_users.py`

---

## ✅ CHECKLIST DE VÉRIFICATION

- [ ] Serveur tourne: http://localhost:8000
- [ ] Users créés: admin et testuser
- [ ] Token reçu après login
- [ ] User crée protein privée
- [ ] User voit sa protein privée
- [ ] User NE PEUT PAS créer publique
- [ ] Admin crée protein publique
- [ ] User voit la protein publique d'admin
- [ ] User NE PEUT PAS modifier protein d'admin (403)
- [ ] Postman collection marche

---

## 🎉 RÉSUMÉ

**SYSTÈME COMPLET** avec:
✨ Authentication token-based
✨ Permissions granulaires (user/admin)
✨ Data filtering automatique
✨ Protection des données
✨ Prêt pour production!

**Prochaines étapes:**
- Frontend Angular/React
- Tests automatisés
- Admin panel
- Rôles supplémentaires

