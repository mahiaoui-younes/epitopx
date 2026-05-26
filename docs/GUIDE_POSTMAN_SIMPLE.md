# Guide Simple - Tester l'API avec Postman

## 1️⃣ Importer la collection

1. Ouvrir **Postman**
2. Cliquer sur **"File"** → **"Import"** (ou **Ctrl+O**)
3. Choisir le fichier `Simplified_Postman.json`
4. Cliquer sur **"Import"**

---

## 2️⃣ Tester l'API

1. La collection apparaît dans le panneau gauche
2. Cliquer sur la requête **"Tester Analyse d'Épitopes"**
3. Cliquer sur le bouton bleu **"Send"**

---

## 3️⃣ Lire la réponse

La réponse du serveur s'affiche dans le panneau inférieur avec le **tableau formaté**:

```
Top candidates:
  Rank         Pos   Len   Score Sequence
  --------------------------------------------------------
     1      156-180    25   0.7651  GKESKSDHDKRPKDKKPFVPKTSQC
     2       88-122    35   0.7463  VPEPVTSEEPKESDQTEEQKHEEPEASPAPEPVDE
     3      140-174    35   0.7104  DGAAVCHGKHHDYDSDGKESKSDHDKRPKDKKPFV
     4       72-106    35   0.6778  PSTEPEELQPETVTVEVPEPVTSEEPKESDQTEEQ
     5      104-138    35   0.6045  EEQKHEEPEASPAPEPVDEPAVHATESTPTKASSS
     6       56-90     35   0.5444  EQPAQQEPIEPQQPTQPSTEPEELQPETVTVEVPE
     7       40-74     35   0.5208  QHPLDPDQLIDQIEPSEQPAQQEPIEPQQPTQPST
     8       24-58     35   0.4692  PLDRQLNPIDFDPNDDQHPLDPDQLIDQIEPSEQP
     9      295-314    20   0.3669  TLRSHPARSSSFSRINEDCC
```

---

## 4️⃣ Modifier la séquence (optionnel)

Pour tester avec une autre séquence protéique:

1. Cliquer sur l'onglet **"Body"**
2. Modifier le champ `"sequence"` avec votre séquence
3. Ajuster les paramètres si nécessaire:
   - `min_length`: Longueur minimale (défaut: 9)
   - `max_length`: Longueur maximale (défaut: 35)
   - `min_score`: Score minimum (défaut: 0.3)
   - `top_n`: Nombre d'épitopes à retourner (défaut: 20)
4. Cliquer sur **"Send"**

---

## ✓ Résultat attendu

**Status Code: 201 Created** ✅

La réponse contient:
- **id**: Numéro de l'analyse
- **epitope_count**: Nombre d'épitopes trouvés
- **epitopes_table**: Tableau formaté lisible (comme EpiTop1)
- **epitopes**: Données détaillées en JSON

---

## 📌 Notes

- Le serveur Django doit être en cours d'exécution sur `http://127.0.0.1:8000`
- La première requête peut prendre quelques secondes
- Les résultats sont **identiques à EpiTop1** pour les mêmes paramètres
- Les résultats sont automatiquement sauvegardés en base de données
