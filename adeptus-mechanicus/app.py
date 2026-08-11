"""Serveur Flask de la vitrine Adeptus Mechanicus + chat de contact.

Sert la vitrine statique (HTML/CSS/JS) et expose une petite API de contact
qui LOGGE les messages des visiteurs dans messages.json (contact reel, pas
une maquette). Le headmaster (assistant) lit messages.json pour repondre
hors ligne.

Lancement : python app.py  (ecoute sur le port 5001)
"""

import json
import os
import threading
import time
from flask import Flask, jsonify, request, send_from_directory, render_template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_PATH = os.path.join(BASE_DIR, "messages.json")

app = Flask(__name__, template_folder="templates", static_folder="static")

# Verrou pour les ecritures concurrentes dans messages.json.
_messages_lock = threading.Lock()


def _load_messages():
    """Charge la liste des messages depuis messages.json (array)."""
    if not os.path.exists(MESSAGES_PATH):
        return []
    try:
        with open(MESSAGES_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        # Fichier corrompu ou illisible : on repart d'une liste vide.
        return []


def _next_id(messages):
    """Calcule le prochain id (entier croissant) a partir de la liste."""
    if not messages:
        return 1
    return max(int(m.get("id", 0)) for m in messages) + 1


@app.route("/")
def index():
    """Page vitrine principale."""
    return render_template("index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    """Fichiers statiques (style.css, app.js)."""
    return send_from_directory(os.path.join(BASE_DIR, "static"), filename)


@app.route("/api/contact", methods=["GET"])
def get_contact():
    """Renvoie la liste des messages deja recus."""
    messages = _load_messages()
    # On renvoie du plus recent au plus ancien pour l'affichage.
    messages_inverted = list(reversed(messages))
    return jsonify(messages_inverted), 200


@app.route("/api/contact", methods=["POST"])
def post_contact():
    """Enregistre un nouveau message de contact dans messages.json."""
    payload = request.get_json(silent=True) or {}
    nom = (payload.get("nom") or "").strip()
    message = (payload.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "message requis"}), 400

    entry = {
        "id": 0,  # rempli ci-dessous sous verrou
        "nom": nom or "Inconnu",
        "message": message,
        "ts": int(time.time()),
    }

    with _messages_lock:
        messages = _load_messages()
        entry["id"] = _next_id(messages)
        messages.append(entry)
        with open(MESSAGES_PATH, "w", encoding="utf-8") as fh:
            json.dump(messages, fh, ensure_ascii=False, indent=2)

    return jsonify({"ok": True, "id": entry["id"]}), 200


if __name__ == "__main__":
    # Port 5001 pour eviter le conflit avec l'autre service (osint/5000).
    app.run(host="0.0.0.0", port=5001, debug=False)
