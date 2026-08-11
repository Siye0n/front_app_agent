# OSINT Entreprises — serveur Flask

Petit serveur Flask qui récupère les N (paramétrable, défaut 10, max 50)
premières entreprises d'une ville et affiche leur **nom**, **adresse** et
**site web** (si disponible).

Le front-end (HTML/CSS/JS vanilla) appelle l'API du serveur et affiche un
tableau. Pas de build front.

## Arborescence

```
osint/
├── app.py                 # Serveur Flask + sources de données
├── requirements.txt       # Dépendances (flask, requests)
├── README.md              # Ce fichier
├── templates/
│   └── index.html         # Page de recherche
└── static/
    ├── style.css          # Style sobre (thème sombre)
    └── app.js             # Logique front (fetch + tableau)
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

- Page d'accueil : http://127.0.0.1:5000/
- API : http://127.0.0.1:5000/api/entreprises

## Endpoint API

`GET /api/entreprises`

| Paramètre | Type   | Requis | Défaut | Notes                |
|-----------|--------|--------|--------|----------------------|
| `ville`   | string | oui    | —      | Ex : `Paris`         |
| `limit`   | int    | non    | 10     | Borné à 1..50        |

Réponse JSON :

```json
{
  "ville": "Paris",
  "count": 3,
  "entreprises": [
    {"nom": "Atlas Solutions", "adresse": "12 rue Victor Hugo, 75001 Paris", "site_web": "https://www.atlassolutions.fr"},
    {"nom": "Nova Énergie", "adresse": "48 avenue Jean Jaurès, 75002 Paris", "site_web": null},
    {"nom": "Quantum Digital", "adresse": "5 place des Lilas, 75003 Paris", "site_web": "https://www.quantumdigital.fr"}
  ]
}
```

En cas de paramètre `ville` manquant, l'API répond `400` avec
`{"error": "..."}`.

## Sources de données (abstraites)

Le serveur définit une interface `CompanySource` avec deux implémentations.
La source est choisie **au démarrage** :

1. **MockSource** (défaut, aucune clé API) — génère des données de démo
   **réalistes et déterministes** pour la ville demandée. Un seed dérivé du
   nom de la ville garantit des résultats reproductibles (ex : `Paris`
   produit toujours le même jeu). Aucun appel réseau.
2. **PappersSource** — activée **uniquement** si la variable d'environnement
   `PAPPERS_API_KEY` est définie. Elle interroge l'API Pappers
   (`https://api.pappers.fr/v2/recherche`) et mappe les résultats vers
   `{nom, adresse, site_web}`.

### Activer Pappers

```bash
export PAPPERS_API_KEY="votre_clé_ici"   # Linux/macOS
# set PAPPERS_API_KEY=votre_clé_ici      # Windows (cmd)
# $env:PAPPERS_API_KEY="votre_clé_ici"   # Windows (PowerShell)
python app.py
```

Sécurité :
- Sans clé, Pappers n'est **jamais** appelé (évite toute erreur réseau).
- La clé API reste **côté serveur** et n'apparaît **jamais** dans la réponse
  ni côté client.

## Règles respectées

- Aucune clé API hardcodée (lus via `os.getenv`).
- Code commenté, docstrings en français sur les fonctions clés.
- `python app.py` suffit à lancer le serveur.
