"""Adeptus Mechanicus — vitrine + canal de communication (chat bilatéral).

Le serveur Flask :
  * sert la vitrine (templates/index.html) et les assets statiques ;
  * expose /api/contact pour recevoir les messages visiteurs (POST) et renvoyer
    l'historique fusionné (GET) ;
  * fusionne messages.json (visiteur) + reponses.json (Magos) triés par ts.

Le headmaster répond « via le site » en écrivant dans reponses.json ; l'UI poll
et affiche les bulles Magos sans rechargement.
"""

import json
import os
import threading
import time
import uuid
from flask import Flask, jsonify, request, render_template, send_from_directory

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")
REPONSES_FILE = os.path.join(BASE_DIR, "reponses.json")

# Verrou thread-safe sur l'écriture de messages.json (les visiteurs écrivent en
# concurrence). reponses.json est lu en lecture seule côté serveur (écrit par le
# headmaster hors process, jamais par Flask) — pas de verrou nécessaire.
_messages_lock = threading.Lock()

app = Flask(__name__, template_folder="templates", static_folder="static")


def _now_ts() -> float:
    return time.time()


def _load_json(path: str) -> list:
    """Lit une liste d'objets JSON depuis path. Retourne [] si absent/invalide."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_messages(messages: list) -> None:
    with _messages_lock:
        with open(MESSAGES_FILE, "w", encoding="utf-8") as fh:
            json.dump(messages, fh, ensure_ascii=False, indent=2)


def _merged_history() -> list:
    """Fusionne messages.json (visiteur) + reponses.json (Magos), tri chronologique."""
    visiteur = _load_json(MESSAGES_FILE)
    magos = _load_json(REPONSES_FILE)
    for m in visiteur:
        m.setdefault("de", "visiteur")
    for m in magos:
        m.setdefault("de", "magos")
    merged = visiteur + magos
    # Tri par ts (epoch). À ts égal, le visiteur avant le Magos pour lisibilité.
    merged.sort(key=lambda x: (x.get("ts", 0), 0 if x.get("de") == "visiteur" else 1))
    return merged


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)


@app.route("/api/contact", methods=["GET"])
def api_contact_get():
    """Renvoie l'historique fusionné (visiteur + Magos) trié chronologiquement."""
    return jsonify(_merged_history())


@app.route("/api/contact", methods=["POST"])
def api_contact_post():
    """Reçoit {nom?, message}, valide, stocke dans messages.json (de: visiteur)."""
    # Parsing robuste : get_json peut échouer (content-type / encodage UTF-8
    # depuis curl ou un navigateur). On force le parsing du corps brut en UTF-8
    # pour ne jamais perdre un message accentué (cas réel : utilisateurs FR).
    payload = request.get_json(force=True, silent=True)
    if not isinstance(payload, dict):
        try:
            raw = request.get_data(as_text=True)
            payload = json.loads(raw) if raw else {}
        except (ValueError, TypeError):
            payload = {}
    if not isinstance(payload, dict):
        payload = {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"ok": False, "error": "message vide"}), 400

    nom = (payload.get("nom") or "").strip()
    entry = {
        "id": uuid.uuid4().hex,
        "de": "visiteur",
        "nom": nom,
        "message": message,
        "ts": _now_ts(),
    }
    messages = _load_json(MESSAGES_FILE)
    messages.append(entry)
    _save_messages(messages)
    return jsonify({"ok": True, "id": entry["id"]}), 200


if __name__ == "__main__":
    # Port 5001 par défaut (évite le conflit avec l'agent osint sur 5000).
    # Overridable via PORT pour les tests / cohabitation.
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=False)
