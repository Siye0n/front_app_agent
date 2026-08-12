"""Adeptus Mechanicus — vitrine + canal de communication (chat bilatéral temps réel).

Le serveur Flask + SocketIO :
  * sert la vitrine (templates/index.html) et les assets statiques ;
  * expose /api/contact (POST visiteur, GET historique fusionné) pour compat/initial ;
  * push en TEMPS RÉEL les nouvelles réponses du Magos (depuis reponses.json) au
    client via l'event SocketIO 'nouvelle_reponse' ;
  * au connect, émet l'historique fusionné (visiteur + magos) trié par ts.

Le headmaster répond « via le site » en écrivant dans reponses.json ; le serveur
détecte le nouveau fichier et le pousse instantanément au navigateur (pas de poll).

Aucun secret / clé API. messages.json et reponses.json sont git-ignorés.
"""

import json
import os
import threading
import time
import uuid

from flask import Flask, jsonify, request, render_template, send_from_directory
from flask_socketio import SocketIO, emit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, "messages.json")
REPONSES_FILE = os.path.join(BASE_DIR, "reponses.json")

# Verrou thread-safe sur l'écriture de messages.json (visiteurs concurrents).
# reponses.json est lu en lecture seule côté serveur (écrit par le headmaster hors
# process) — pas de verrou nécessaire.
_messages_lock = threading.Lock()

app = Flask(__name__, template_folder="templates", static_folder="static")
# async_mode='threading' évite la dépendance eventlet/gevent au lancement ; suffisant
# pour un petit chat 1-1. (eventlet reste supporté si présent.)
socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")


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
    merged.sort(key=lambda x: (x.get("ts", 0), 0 if x.get("de") == "visiteur" else 1))
    return merged


# --- Watch en arrière-plan de reponses.json pour push temps réel ---------------
_watch_thread = None
_watch_stop = threading.Event()
_last_seen_magos = 0  # ts de la dernière réponse Magos déjà poussée


def _watch_responses():
    """Surveille reponses.json ; émet les nouvelles réponses dès qu'elles apparaissent."""
    global _last_seen_magos
    # init : on considère tout ce qui existe déjà comme "déjà vu"
    for m in _load_json(REPONSES_FILE):
        ts = m.get("ts", 0)
        if ts > _last_seen_magos:
            _last_seen_magos = ts
    while not _watch_stop.is_set():
        time.sleep(1.0)
        try:
            magos = _load_json(REPONSES_FILE)
        except Exception:
            continue
        pushed = False
        for m in magos:
            ts = m.get("ts", 0)
            if ts > _last_seen_magos:
                _last_seen_magos = ts
                socketio.emit("nouvelle_reponse", m)
                pushed = True
        # petit sleep pour ne pas spammer en cas de burst
        if pushed:
            time.sleep(0.3)


def _start_watch():
    global _watch_thread
    if _watch_thread is None or not _watch_thread.is_alive():
        _watch_stop.clear()
        _watch_thread = threading.Thread(target=_watch_responses, daemon=True)
        _watch_thread.start()


# --- Routes HTTP (compatibilité + historique initial) --------------------------
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
    # Parsing robuste : get_json peut échouer (content-type / encodage UTF-8 depuis
    # curl ou un navigateur). On force le parsing du corps brut en UTF-8 pour ne
    # jamais perdre un message accentué (cas réel : utilisateurs FR).
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
    # Le visiteur vient d'écrire : on notifie les clients connectés (pour le typing)
    socketio.emit("nouveau_visiteur", entry)
    return jsonify({"ok": True, "id": entry["id"]}), 200


# --- SocketIO -----------------------------------------------------------------
@socketio.on("connect")
def on_connect():
    # Émet l'historique complet dès la connexion (le client n'a pas à poller).
    emit("historique", _merged_history())


if __name__ == "__main__":
    # Port 5001 par défaut (évite le conflit avec l'agent osint sur 5000).
    # Overridable via PORT pour les tests / cohabitation.
    port = int(os.environ.get("PORT", "5001"))
    _start_watch()
    # socketio.run remplace app.run et gère le transport WebSocket.
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
