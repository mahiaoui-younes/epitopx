# 🚀 API Protéines - Admin Public (Automatique)

## 📝 Logique Simplifiée

**AVANT:** Les utilisateurs devaient gérer manuellement `is_public`  
**MAINTENANT:** C'est automatique!

- **Admin ajoute** → Protéine = **PUBLIQUE** (`is_public=true`)
- **User normal ajoute** → Protéine = **PRIVÉE** (`is_public=false`)

---

## 🎯 Utilisateurs Prêts

```
Admin:  username: admin1    password: admin123
User:   username: user1     password: password123
```

---

## 📋 Tester avec Postman

### Étape 1: Importer la Collection
1. Ouvrez **Postman**
2. **Import** → `Postman_Protein_Simple.json`

### Étape 2: Exécuter les Requêtes

```
1. Login User Normal       → récupère {{user_token}}
2. Login Admin            → récupère {{admin_token}}
3. User Normal - Ajoute Protéine   → créée avec is_public=false
4. Admin - Ajoute Protéine         → créée avec is_public=true
5. Voir Protéines Publiques (sans token) → voir protéine admin
6. User Normal - Mes Protéines     → voir sa protéine + admin's
7. Admin - Toutes les Protéines    → voir tout
```

---

## 📤 Exemple de Requête

### User Normal (reçoit is_public=false automatiquement)
```bash
POST http://localhost:8000/api/proteins/
Authorization: Token {{user_token}}

{
  "name": "ProteinUserNormal",
  "sequence": "MVSKQ...",
  "description": "Protéine créée par user normal"
}
```

**Réponse:** `is_public=false` ✓

---

### Admin (reçoit is_public=true automatiquement)
```bash
POST http://localhost:8000/api/proteins/
Authorization: Token {{admin_token}}

{
  "name": "AdminPublicProtein",
  "sequence": "MVSKQ...",
  "description": "Protéine créée par admin"
}
```

**Réponse:** `is_public=true` ✓

---

## ✅ Résumé des Changements

| Fichier | Modification |
|---------|------------|
| `serializers.py` | `is_public` maintenant read-only (automatique) |
| `views.py` | `perform_create()` → admin get `is_public=true`, user get `is_public=false` |

**Le serveur tourne!** → http://localhost:8000/ 🎉
