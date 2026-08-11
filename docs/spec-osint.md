# Spécification — Site OSINT (entreprises par ville)

- **Dossier repo** : `osint/`
- **Type** : serveur Flask (Python) + UI HTML/CSS/JS vanilla
- **Lancement local** : `python app.py` (port 5000)
- **Statut** : livré V1 (PR #2 mergée) ; évolution WHOIS en cours (branche feature/osint-whois)

## Objectif (V1 — livrée)
Récupérer les N (paramétrable, défaut 10, max 50) premières entreprises d'une ville (paramétrable)
et afficher au minimum : nom, adresse, site internet (si existant).

## Architecture (V1)
- `app.py` : serveur Flask, endpoint `GET /api/entreprises?ville=&limit=`.
- Source de données abstraite `CompanySource` :
  - `MockSource` : données de démonstration déterministes (défaut, aucune clé API).
  - `PappersSource` : interroge l'API Pappers si `PAPPERS_API_KEY` définie ; fallback Mock si 401/crédits.
- UI : formulaire ville/limit + tableau des résultats (site web cliquable).

## Évolution prévue (WHOIS — en cours)
Changement de source : remplacer la logique ville/Pappers par un **scan WHOIS par domaines**.
- Upload d'un fichier CSV (colonne `domaine`, un par ligne) via l'IHM.
- Pour chaque domaine : WHOIS (`python-whois`), retry max 10 en cas d'erreur.
- Résultats affichés dans un **dashboard futuriste** (cartes métriques + tableau) :
  domaine | registrar | création | expiration | statut | DNS | erreur.
- Endpoints : `POST /api/scan` (upload CSV), `GET /api/results`.

## Contraintes
- Clé API jamais exposée côté client (hors du repo, dans `osint/.env` git-ignoré).
- Légal : données publiques uniquement (registres, WHOIS public).
- `osint/.venv/`, `osint/.env`, `osint/results.json` git-ignorés.

## Vérification (V1)
- `GET /api/entreprises?ville=Paris&limit=3` → JSON valide, 3 entreprises, champs corrects.
- ville manquante → 400.
- fallback Pappers→Mock OK (clé sans crédits).
