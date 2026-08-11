"""
Serveur Flask — Scan OSINT WHOIS par domaines (CSV upload).

Remplace l'ancienne logique Pappers/MockSource (recherche d'entreprises par
ville). Le nouveau flux :

  1. L'utilisateur uploade un fichier CSV listant des domaines (colonne
     `domaine` si un header est présent, sinon la première colonne).
  2. Pour CHAQUE domaine unique et non vide, on interroge le WHOIS
     (lib `python-whois`) avec un retry automatique (backoff court, max 10
     tentatives) en cas d'erreur réseau / timeout.
  3. Le résultat est normalisé vers des champs lisibles et renvoyé au
     dashboard, qui l'affiche sous forme de cartes métriques + tableau.

Aucune clé API, aucun secret : `python-whois` interroge en local le port 43.
"""

from __future__ import annotations

import csv
import io
import os
import threading
import time
from datetime import datetime, timezone

import whois
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Nombre maximal de tentatives WHOIS par domaine (backoff court entre chacune).
MAX_WHOIS_ATTEMPTS = 10
# Délai de base (secondes) avant retry ; on applique un backoff exponentiel plafonné.
RETRY_BACKOFF_BASE = 1.0
RETRY_BACKOFF_MAX = 2.0
# Seuil (jours) sous lequel une expiration est considérée "expire bientôt".
EXPIRING_SOON_DAYS = 60

# Stockage en mémoire des derniers résultats scannés (pour GET /api/results).
# Protégé par un verrou car le serveur Flask est multithread par défaut.
_RESULTS_LOCK = threading.Lock()
_LATEST_RESULTS: dict = {
    "count": 0,
    "domaines_scannes": 0,
    "resultats": [],
    "scan_at": None,
}

# Fichier de sauvegarde (ignoré par git). Permet de recharger le dashboard
# sans relancer un scan. On écrit après chaque scan réussi.
_RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")


def _now_iso() -> str:
    """Renvoie l'instant courant en ISO (UTC, timezone-aware)."""
    return datetime.now(timezone.utc).isoformat()


def _to_list(value) -> list:
    """Normalise une valeur WHOIS (souvent scalaire OU liste) en liste."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v is not None]
    return [str(value)]


def _to_str(value) -> str:
    """Normalise une valeur WHOIS scalaire en chaîne, ou '—' si absente."""
    if value is None or value == "":
        return "—"
    return str(value)


def _parse_date(value) -> str:
    """Convertit une date WHOIS (datetime ou liste) en chaîne ISO, ou '—'."""
    if value is None:
        return "—"
    # python-whois renvoie parfois une liste de dates.
    if isinstance(value, (list, tuple, set)):
        for v in value:
            if v is not None:
                value = v
                break
        else:
            return "—"
    if isinstance(value, datetime):
        # Certaines dates WHOIS sont "naive" ; on les traite comme UTC.
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _days_until(date_value) -> int | None:
    """Renvoie le nombre de jours restants avant `date_value`, ou None."""
    if date_value is None:
        return None
    if isinstance(date_value, (list, tuple, set)):
        for v in date_value:
            if v is not None:
                date_value = v
                break
        else:
            return None
    if not isinstance(date_value, datetime):
        return None
    if date_value.tzinfo is None:
        date_value = date_value.replace(tzinfo=timezone.utc)
    delta = date_value - datetime.now(timezone.utc)
    return delta.days


def _map_whois(domain: str, w) -> dict:
    """Mappe un objet WHOIS (python-whois) vers des champs lisibles.

    :param domain: nom de domaine interrogé.
    :param w: résultat de `whois.whois(domain)` (objet ou dict).
    :return: dict normalisé pour le dashboard.
    """
    # Certaines libs renvoient un dict, d'autres un objet attributé.
    def get(field: str):
        if isinstance(w, dict):
            return w.get(field)
        return getattr(w, field, None)

    creation = _parse_date(get("creation_date"))
    expiration = _parse_date(get("expiration_date"))

    status_list = _to_list(get("status"))
    name_servers = _to_list(get("name_servers"))
    emails = _to_list(get("emails"))

    # Pays : champ `country` parfois présent.
    pays = _to_str(get("country"))

    # Calcul de l'indicateur d'expiration pour le dashboard.
    days_left = _days_until(get("expiration_date"))
    if days_left is None:
        expiry_state = "unknown"  # pas de date -> inconnu
    elif days_left < 0:
        expiry_state = "expired"   # déjà expiré
    elif days_left <= EXPIRING_SOON_DAYS:
        expiry_state = "soon"      # expire bientôt
    else:
        expiry_state = "active"    # encore actif

    return {
        "domaine": domain,
        "registrar": _to_str(get("registrar")),
        "creation_date": creation,
        "expiration_date": expiration,
        "status": status_list,
        "name_servers": name_servers,
        "emails": emails,
        "pays": pays,
        "expiry_state": expiry_state,
        "erreur": None,
    }


def _scan_domain(domain: str) -> dict:
    """Interroge le WHOIS d'un domaine avec retry (max 10 tentatives).

    En cas d'échec persistant (réseau/timeout), renvoie un dict d'erreur
    normalisé avec `erreur` renseigné et les champs à '—'.
    """
    last_error = None
    for attempt in range(1, MAX_WHOIS_ATTEMPTS + 1):
        try:
            w = whois.whois(domain)
            # python-whois ne lève pas toujours d'exception pour un domaine
            # inconnu ; il renvoie un objet (parfois vide). On le mappe quand
            # même — le champ registrar sera '—' si rien n'est trouvé.
            return _map_whois(domain, w)
        except Exception as exc:  # noqa: BLE001 - on capture toute erreur réseau/WHOIS
            last_error = str(exc)
            if attempt < MAX_WHOIS_ATTEMPTS:
                # Backoff court : 1s à 2s, plafonné.
                delay = min(RETRY_BACKOFF_BASE * attempt, RETRY_BACKOFF_MAX)
                time.sleep(delay)

    # Toutes les tentatives ont échoué.
    return {
        "domaine": domain,
        "registrar": "—",
        "creation_date": "—",
        "expiration_date": "—",
        "status": [],
        "name_servers": [],
        "emails": [],
        "pays": "—",
        "expiry_state": "error",
        "erreur": "WHOIS indisponible apres 10 tentatives",
    }


def _extract_domains(csv_text: str) -> list[str]:
    """Extrait les domaines uniques et non vides depuis le texte CSV.

    - Si un header est présent et contient `domaine`, on utilise cette colonne.
    - Sinon, on prend la première colonne de chaque ligne.
    - On déduplique en préservant l'ordre et on ignore les lignes vides.
    """
    reader = csv.reader(io.StringIO(csv_text))
    rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    if not rows:
        return []

    header = [c.strip().lower() for c in rows[0]]
    # Détecte une colonne 'domaine' dans le header (sinon première colonne).
    if "domaine" in header:
        col_idx = header.index("domaine")
        data_rows = rows[1:]
    else:
        col_idx = 0
        data_rows = rows

    seen: set[str] = set()
    domains: list[str] = []
    for row in data_rows:
        if col_idx >= len(row):
            continue
        domain = row[col_idx].strip().lower()
        # Retire un éventuel schéma/protocole ou chemin résiduel.
        domain = domain.split("//")[-1].split("/")[0].strip().rstrip(".")
        if domain and domain not in seen:
            seen.add(domain)
            domains.append(domain)
    return domains


def _persist_results(payload: dict) -> None:
    """Sauvegarde les résultats sur disque (results.json, ignoré par git)."""
    try:
        with open(_RESULTS_FILE, "w", encoding="utf-8") as fh:
            fh.write(jsonify(payload).get_data(as_text=True))
    except Exception:  # noqa: BLE001 - la persistance est best-effort
        pass


@app.route("/")
def index():
    """Sert la page dashboard (upload CSV + tableau de bord)."""
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def api_scan():
    """Endpoint de scan : uploade un CSV de domaines et renvoie les WHOIS.

    Form-data multipart, champ fichier : `csv`.

    Réponse 200 :
        {"count": int, "domaines_scannes": int,
         "resultats": [ {domaine, registrar, creation_date, expiration_date,
                         status, name_servers, emails, pays, expiry_state,
                         erreur}, ... ]}
    Réponse 400 si aucun domaine valide n'a été trouvé dans le CSV.
    """
    if "csv" not in request.files:
        return jsonify({"error": "Aucun fichier 'csv' fourni."}), 400

    f = request.files["csv"]
    if not f or f.filename == "":
        return jsonify({"error": "Fichier CSV vide ou sans nom."}), 400

    try:
        csv_bytes = f.read()
        csv_text = csv_bytes.decode("utf-8-sig", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Impossible de lire le CSV : {exc}"}), 400

    domains = _extract_domains(csv_text)
    if not domains:
        return jsonify({"error": "Aucun domaine valide trouve dans le CSV."}), 400

    resultats: list[dict] = []
    scan_at = _now_iso()
    for domain in domains:
        resultats.append(_scan_domain(domain))

    payload = {
        "count": len(resultats),
        "domaines_scannes": len(domains),
        "resultats": resultats,
        "scan_at": scan_at,
    }

    # Stocke en mémoire + disque pour GET /api/results.
    with _RESULTS_LOCK:
        _LATEST_RESULTS.clear()
        _LATEST_RESULTS.update(payload)
    _persist_results(payload)

    return jsonify(payload), 200


@app.route("/api/results", methods=["GET"])
def api_results():
    """Renvoie les derniers résultats scannés (pour rafraîchir le dashboard)."""
    with _RESULTS_LOCK:
        return jsonify(dict(_LATEST_RESULTS)), 200


if __name__ == "__main__":
    # Tente de charger d'éventuels résultats persistés au démarrage.
    try:
        if os.path.exists(_RESULTS_FILE):
            import json as _json
            with open(_RESULTS_FILE, "r", encoding="utf-8") as fh:
                loaded = _json.load(fh)
            with _RESULTS_LOCK:
                _LATEST_RESULTS.clear()
                _LATEST_RESULTS.update(loaded)
    except Exception:  # noqa: BLE001 - démarrage même si le fichier est corrompu
        pass

    # Port 5000, debug=False en production (OK pour test local).
    app.run(host="127.0.0.1", port=5000, debug=False)
