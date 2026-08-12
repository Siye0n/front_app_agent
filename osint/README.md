# OSINT // SCAN WHOIS — serveur Flask

Petit serveur Flask qui prend en entrée un fichier **CSV de domaines** et
renvoie, pour chacun, son empreinte **WHOIS** (registrar, dates de création /
expiration, statut, serveurs DNS, contacts, pays). Les résultats s'affichent
dans un **dashboard futuriste** (thème néon cyber) : cartes métriques +
tableau cliquable.

Le front-end (HTML/CSS/JS vanilla) appelle l'API du serveur. Pas de build
front, aucune clé API, aucun secret — `python-whois` interroge en local le
port 43.

## Arborescence

```
osint/
├── app.py                 # Serveur Flask + scan WHOIS (retry auto, max 10)
├── requirements.txt       # Dépendances (flask, python-whois)
├── README.md              # Ce fichier
├── results.json           # Cache des derniers résultats (ignoré par git)
├── templates/
│   └── index.html         # Dashboard futuriste
└── static/
    ├── style.css          # Thème sombre néon / cyber
    └── app.js             # Upload CSV (drag & drop) + rendu dashboard
```

## Lancer le serveur

```bash
cd osint
python -m venv .venv        # optionnel mais recommandé
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows (PowerShell)
pip install -r requirements.txt
python app.py
```

Le serveur démarre sur http://127.0.0.1:5000/ (port 5000, `debug=False`).

- Page dashboard : http://127.0.0.1:5000/
- API scan : http://127.0.0.1:5000/api/scan
- API résultats : http://127.0.0.1:5000/api/results

## Format du CSV

Une colonne `domaine` par ligne (un domaine par ligne). Le header est
optionnel : si une colonne nommée `domaine` est présente, elle est utilisée ;
sinon la **première colonne** de chaque ligne est prise. Les doublons et les
lignes vides sont ignorés. Un éventuel `http(s)://` ou chemin résiduel est
tronqué.

Exemple `domaines.csv` :

```csv
domaine
google.com
github.com
exemple.fr
```

## Endpoints API

### `POST /api/scan`

Upload multipart, champ fichier : `csv`.

- Pour chaque domaine (unique, non vide) : appel WHOIS avec **retry
  automatique** (backoff court, max 10 tentatives) en cas d'erreur réseau /
  timeout.
- Réponse `200` :

```json
{
  "count": 3,
  "domaines_scannes": 3,
  "scan_at": "2026-08-11T23:31:00+00:00",
  "resultats": [
    {
      "domaine": "google.com",
      "registrar": "MarkMonitor Inc.",
      "creation_date": "1997-09-15T04:00:00+00:00",
      "expiration_date": "2028-09-14T04:00:00+00:00",
      "status": ["clientUpdateProhibited", "..."],
      "name_servers": ["ns1.google.com", "ns2.google.com"],
      "emails": ["abuse@google.com"],
      "pays": "US",
      "expiry_state": "active",
      "erreur": null
    }
  ]
}
```

- Réponse `400` si aucun domaine valide n'est trouvé dans le CSV, ou si le
  fichier est absent / illisible.

Champs `expiry_state` (pour le dashboard) :
`active` (actif), `soon` (expire sous 60 j), `expired` (déjà expiré),
`unknown` (date indisponible), `error` (WHOIS indisponible après 10
tentatives — `erreur` = `"WHOIS indisponible apres 10 tentatives"`).

### `GET /api/results`

Renvoie les derniers résultats scannés (utile pour rafraîchir le dashboard
sans relancer un scan). Format identique à la clé `resultats` + `count` +
`domaines_scannes` + `scan_at`.

## Règles respectées

- Aucune clé API / secret : `python-whois` est une lib locale (port 43).
- Retry automatique borné (max 10) avec backoff court sur erreurs réseau.
- `results.json` est ignoré par git (ainsi que `.env` et `.venv/`).
- Code commenté, docstrings en français sur les fonctions clés.
- `python app.py` suffit à lancer le serveur.
