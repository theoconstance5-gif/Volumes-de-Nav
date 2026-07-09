# ⛵ Suivi Voile — application de suivi des volumes d'entraînement

Application web Python (Streamlit) pour enregistrer et analyser les séances
d'entraînement d'un groupe sportif de voile.

## Fonctionnalités

- **📝 Saisie** : lieu, conditions de vent (min/max en nœuds, direction, état
  de mer), groupe, athlètes présents, thématique de travail, durée, commentaires.
- **📊 Analyse** : comparaison groupes ou athlètes, filtres par période, par
  tranche de vent, par thématique, par lieu ; graphiques (barres, courbes,
  camembert, heatmap croisée) + export CSV du détail.
- **⚙️ Configuration** : gestion des listes (groupes, athlètes, lieux,
  thématiques, tranches de vent) — tout est modifiable sans toucher au code.

## 1. Utilisation en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'app s'ouvre sur `http://localhost:8501`. Les données sont stockées dans un
fichier `voile.db` (SQLite) créé automatiquement au premier lancement, avec
quelques données d'exemple pré-remplies (à supprimer/modifier dans
Configuration).

## 2. Partager l'app avec plusieurs entraîneurs (accès web à distance)

Pour un usage multi-entraîneurs à distance, deux choses sont nécessaires :
héberger l'app quelque part, et utiliser une base de données qui **persiste**
et soit **accessible à distance** (SQLite en local ne convient pas dans ce
cas : il vit sur le disque du serveur et n'est pas fait pour les accès
concurrents multiples).

### Option recommandée : Streamlit Community Cloud + base Postgres gratuite

1. **Créer une base Postgres gratuite** — par exemple sur
   [Neon](https://neon.tech) ou [Supabase](https://supabase.com) (offres
   gratuites suffisantes pour ce volume de données). Récupère l'URL de
   connexion, du type :
   `postgresql://user:password@host/dbname`

2. **Déposer le code sur GitHub** (dépôt public ou privé).

3. **Déployer sur** [share.streamlit.io](https://share.streamlit.io) :
   - Connecte ton dépôt GitHub
   - Dans *Settings → Secrets*, ajoute :
     ```toml
     DATABASE_URL = "postgresql://user:password@host/dbname"
     ```
   - Déploie. L'app est alors accessible via une URL publique que tu partages
     à tes collègues entraîneurs.

Le code est déjà prêt pour ça : `db.py` lit automatiquement `DATABASE_URL`
depuis les secrets Streamlit (ou une variable d'environnement) et bascule de
SQLite vers Postgres sans aucune autre modification.

### Alternative

Tu peux aussi héberger l'app sur un autre service compatible Streamlit/Python
(Render, Railway, un VPS...) tant que la variable `DATABASE_URL` pointe vers
une base Postgres accessible depuis ce service.

## 3. Structure du projet

```
voile_app/
├── app.py                     # page d'accueil / tableau de bord
├── db.py                      # modèles de données (SQLAlchemy) + connexion
├── style.py                   # thème visuel partagé (couleurs, polices)
├── requirements.txt
├── pages/
│   ├── 1_📝_Saisie.py          # formulaire de saisie
│   ├── 2_📊_Analyse.py         # tableau de bord d'analyse
│   └── 3_⚙️_Configuration.py   # gestion des listes de référence
└── README.md
```

## 4. Modèle de données (résumé)

- **Groupe** — nom, actif/inactif
- **Athlète** — prénom, nom, groupe d'appartenance, actif/inactif
- **Lieu** — nom
- **Thématique** — nom
- **Tranche de vent** — libellé + bornes min/max en nœuds (utilisée pour
  classer automatiquement chaque séance selon le vent moyen saisi)
- **Séance** — date, lieu, groupe, thématique, vent min/max, direction, état
  de mer, durée (heures), commentaires, encadrant, liste des athlètes présents

Chaque séance capture le vent sous forme de **plage numérique précise**
(nœuds min/max) plutôt qu'une simple étiquette : cela permet un classement
automatique en tranches configurables ET de futures analyses plus fines
(moyenne, écart, corrélations...) si besoin.

## 5. Évolutions possibles

- Authentification par entraîneur (actuellement l'app est ouverte à qui a le lien)
- Export PDF des rapports d'analyse
- Ajout d'un champ "objectif de volume" par athlète avec suivi de l'écart
- Suivi du matériel utilisé (type de bateau, voiles...)
