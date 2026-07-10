# ⛵ La Vague Normande Sport — Suivi Voile

Application web Python (Streamlit) pour le suivi d'entraînement d'un groupe
sportif de voile : volumes d'entraînement, thématiques, conditions de vent,
et debrief post-régate.

## Fonctionnalités

### Entraînement (coachs, protégé par mot de passe)
- **📝 Saisie** : lieu, horaires (durée calculée automatiquement), groupe,
  athlètes présents (limités au groupe sélectionné), 1 ou 2 thématiques de
  travail (curseur de répartition si 2), répartition du temps par tranche de
  vent (0-10 / 10-17 / +17 nds).
- **📊 Analyse** : comparaison par groupe ou par athlète, filtres (période,
  thématique, tranche de vent, lieu), graphiques (barres, courbes,
  camemberts, heatmaps), croisement thématiques × tranches de vent (estimation
  proportionnelle), comparaison tête-à-tête entre deux athlètes, export CSV.

### Debrief régate
- **🌊 Mon debrief** (ouvert à tous les athlètes) : formulaire à remplir
  après chaque journée de compétition — épreuve, jour, équipage, notes de 1 à
  5 sur les critères techniques/mentaux, point noir et point positif de la
  journée.
- **🔎 Analyse debrief** (coachs, protégé par mot de passe) : profil moyen du
  groupe (radar), points d'attention/positifs les plus cités (camemberts),
  comparaison individuelle vs groupe, évolution jour par jour.

### Administration
- **⚙️ Configuration** (coachs, protégé par mot de passe) : gestion de toutes
  les listes (groupes, athlètes, lieux, thématiques, tranches de vent,
  épreuves, critères et points de debrief) — rien n'est codé en dur, tout se
  modifie depuis l'interface.

## 1. Utilisation en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

L'app s'ouvre sur `http://localhost:8501`. Les données sont stockées dans un
fichier `voile.db` (SQLite) créé automatiquement au premier lancement, avec
quelques données d'exemple pré-remplies (à supprimer/modifier dans
Configuration).

En local, sans mot de passe configuré (voir section 3), toutes les pages
sont accessibles librement — pratique pour tester.

## 2. Partager l'app avec plusieurs entraîneurs et athlètes (accès web à distance)

Deux choses sont nécessaires : héberger l'app quelque part, et utiliser une
base de données qui **persiste** et soit **accessible à distance** (SQLite
en local ne convient pas : il vit sur le disque du serveur et n'est pas fait
pour les accès concurrents multiples).

### Option recommandée : Streamlit Community Cloud + base Postgres gratuite

1. **Créer une base Postgres gratuite** — par exemple sur
   [Neon](https://neon.tech) ou [Supabase](https://supabase.com). Récupère
   l'URL de connexion complète (copiée directement depuis leur interface,
   sans la retaper à la main), du type :
   `postgresql://user:motdepasse@host/dbname?sslmode=require`

2. **Déposer le code sur GitHub** (dépôt public ou privé).

3. **Déployer sur** [share.streamlit.io](https://share.streamlit.io) :
   - Connecte ton dépôt GitHub, choisis la branche et `app.py` comme fichier principal
   - Dans *Advanced settings → Secrets*, colle le contenu de
     `.streamlit/secrets.toml.example` en remplaçant les valeurs par les tiennes
   - Déploie. L'app est alors accessible via une URL publique
     (`https://ton-app.streamlit.app`) que tu partages à tes coachs et athlètes.

Le code est déjà prêt pour ça : `db.py` lit automatiquement `DATABASE_URL`
depuis les secrets Streamlit (ou une variable d'environnement) et bascule de
SQLite vers Postgres sans aucune autre modification.

## 3. Protéger les pages coachs par mot de passe

Comme la page **Mon debrief** est destinée aux athlètes, un mot de passe
partagé protège les pages réservées aux coachs (Saisie, Analyse,
Configuration, Analyse debrief). Pour l'activer, ajoute dans les Secrets
(local ou Streamlit Cloud) :

```toml
COACH_PASSWORD = "choisis-un-mot-de-passe"
```

Communique ce mot de passe uniquement aux entraîneurs. Sans cette clé, ces
pages restent ouvertes à tous (utile en local pour tester rapidement, à
éviter une fois l'app en ligne).

## 4. Structure du projet

```
voile_app/
├── app.py                     # point d'entrée + navigation (icônes définies en code)
├── db.py                      # modèles de données (SQLAlchemy) + connexion
├── style.py                   # thème visuel partagé + protection par mot de passe
├── requirements.txt
├── assets/                    # logo du club
├── pages/
│   ├── accueil.py              # tableau de bord général
│   ├── saisie.py                # saisie d'une séance d'entraînement
│   ├── analyse.py                # analyse des volumes d'entraînement
│   ├── debrief.py                 # formulaire de debrief post-régate (athlètes)
│   ├── debrief_analyse.py          # analyse du debrief (coachs)
│   └── configuration.py             # gestion de toutes les listes
└── README.md
```

## 5. Modèle de données (résumé)

**Entraînement**
- **Groupe**, **Athlète** (rattaché à un groupe), **Lieu**, **Thématique**,
  **Tranche de vent** (bornes en nœuds)
- **Séance** — date, lieu, groupe, horaires (durée calculée), athlètes
  présents ; le temps est réparti entre 1-2 thématiques et entre les
  tranches de vent (répartitions indépendantes du même volume total)

**Debrief**
- **Épreuve** (nom de la compétition), **Critère** (question notée de 1 à
  5), **Point** (liste utilisée pour le point noir / point positif)
- **Réponse de debrief** — épreuve, jour, équipage (1 ou plusieurs
  athlètes), une note par critère, point noir, point positif, commentaire libre

## 6. Évolutions possibles

- Authentification nominative (actuellement un seul mot de passe partagé pour tous les coachs)
- Export PDF des rapports d'analyse (entraînement et/ou debrief), si le besoin revient
- Ajout d'un champ "objectif de volume" par athlète avec suivi de l'écart
- Suivi du matériel utilisé (type de bateau, voiles...)
- Rappel automatique (email/notif) aux athlètes n'ayant pas encore rempli leur debrief
