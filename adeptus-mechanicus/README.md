# Adeptus Mechanicus — Vitrine & Relique de Communication

Vitrine web statique dans l'univers Warhammer 40,000 (Adeptus Mechanicus),
accompagnée d'un **chat de contact réel** : les messages des visiteurs sont
envoyés à un petit serveur Flask qui les **LOGGE** dans `messages.json`.

Contenu original et inspiré du hobby — aucun texte copyrighté Games Workshop.

## Arborescence

```
adeptus-mechanicus/
├── app.py                 # Serveur Flask (port 5001)
├── requirements.txt       # Dépendance : flask
├── .gitignore             # ignore messages.json et .env
├── README.md
├── templates/
│   └── index.html         # Vitrine + panneau de contact
├── static/
│   ├── style.css          # Thème AM (charbon / laiton / rouge / phosphore)
│   └── app.js             # Chat serveur-backed (GET/POST /api/contact)
└── messages.json          # Créé automatiquement au 1er message (ignoré par git)
```

## Lancement

```bash
cd adeptus-mechanicus
pip install -r requirements.txt
python app.py
```

Le serveur écoute sur **http://localhost:5001**. Ouvre cette URL dans ton
navigateur : la vitrine s'affiche et le panneau « Relique de Communication »
permet d'envoyer un message.

## Endpoints de contact

### GET  /api/contact
Renvoie la liste des messages déjà reçus (JSON), du plus récent au plus ancien.

```json
[
  { "id": 2, "nom": "Magos Test", "message": "Salut", "ts": 1754000000 },
  { "id": 1, "nom": "Inconnu",    "message": "Premier contact", "ts": 1753999000 }
]
```

### POST /api/contact
Corps JSON :
```json
{ "nom": "Optionnel", "message": "Texte requis" }
```
- `message` non vide → `200 { "ok": true, "id": <entier> }`
- `message` vide → `400 { "ok": false, "error": "message requis" }`

Le message est ajouté (append) au tableau `messages.json`.

## Où le headmaster lit les messages

Les messages des visiteurs sont stockés dans :

```
adeptus-mechanicus/messages.json
```

C'est un simple tableau JSON. Le headmaster (assistant) le lit pour répondre
hors ligne — le chat n'affiche **pas** de réponse automatique ; il indique
seulement : *« Transmission enregistrée — le Magos répondra par canal sécurisé. »*

## Notes

- Aucune clé API, aucun secret. Pas de build front (HTML/CSS/JS vanilla).
- `messages.json` et `.env` sont ignorés par git (voir `.gitignore`).
- Polices : Cinzel (titres) + EB Garamond (corps) via Google Fonts.
- Aucune image copyrightée : décor SVG/CSS + bandeau binaire animé.
