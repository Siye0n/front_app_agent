# Adeptus Mechanicus — Vitrine + Canal de communication

Site vitrine dans l'univers Warhammer 40,000 (Adeptus Mechanicus) avec un
**canal de communication visuel** (chat type messagerie) permettant aux
visiteurs de contacter le Magos (l'assistant).

Contenu 100 % original, aucune image ni texte copyrighté Games Workshop.
Palette : noir charbon `#0d0b0a`, laiton `#b08d57`, rouge Mechanicus `#9e2b25`,
vert phosphore `#36c46a`, ivoire `#e8dcc0`.

## Lancement

```bash
cd adeptus-mechanicus
pip install -r requirements.txt
python app.py
# -> http://localhost:5001
```

Le serveur tourne sur le **port 5001** (pour éviter le conflit avec l'agent
osint sur 5000).

## Fonctionnement du chat (asynchrone, sans push temps réel)

- Le visiteur envoie un message via le panneau « Canal de communication // Magos ».
- `POST /api/contact` reçoit `{nom?, message}`, valide (message non vide → 400),
  et **logge dans `messages.json`** avec le champ `"de": "visiteur"`.
- L'UI **poll `GET /api/contact` toutes les ~4 s** et affiche les bulles :
  - **Visiteur** : bulle à **droite** (fond laiton/bronze, texte sombre).
  - **Magos** : bulle à **gauche** (fond charbon, bordure vert phosphore, avatar
    aquila SVG, léger typing effect).
- Animations (CSS/JS, sans librairie) : fade-in des bulles, **aquila qui pulse**
  dans l'en-tête, indicateur de frappe « Le Magos retranscrit… » (3 points) après
  l'envoi d'un message visiteur, bandeau binaire décoratif.

### Comment le headmaster répond « via le site »

Le serveur fusionne `messages.json` (visiteur) et **`reponses.json`** (Magos),
triés par `ts` (ordre chronologique global). Pour répondre, le headmaster écrit
une entrée dans `reponses.json` au format :

```json
[
  { "de": "magos", "message": "Votre communiqué est reçu, fils du code.", "ts": 1754956800, "id": "abc123" }
]
```

L'UI, au prochain poll (≤ 4 s), affiche la bulle Magos à gauche. `reponses.json`
est **lu en lecture seule** côté serveur (écrit hors process par le headmaster) —
pas de verrou nécessaire. S'il est absent, la liste Magos est vide.

> Astuce : `ts` en epoch Unix (secondes). `id` doit être unique.

## Endpoints

| Méthode | Route          | Corps / Retour                                    |
|---------|----------------|---------------------------------------------------|
| GET     | `/api/contact` | Liste fusionnée (visiteur + Magos), triée par ts  |
| POST    | `/api/contact` | `{nom?, message}` → 200 `{ok,id}` / 400 si vide    |

Réponse GET (exemple) :

```json
[
  {"id":"v1","de":"visiteur","nom":"Test","message":"Salut","ts":1754956700},
  {"id":"m1","de":"magos","message":"Transmission reçue.","ts":1754956800}
]
```

## Fichiers

```
adeptus-mechanicus/
├── app.py              # Serveur Flask (vitrine + API chat)
├── requirements.txt    # flask
├── templates/
│   └── index.html      # Vitrine + chat visuel + aquila SVG
├── static/
│   ├── style.css       # Palette Adeptus, bulles, animations
│   └── app.js          # Polling, fade-in, typing indicator/effect
├── messages.json       # (git-ignored) messages visiteurs
├── reponses.json       # (git-ignored) réponses du Magos
└── README.md
```

`messages.json` et `reponses.json` sont **git-ignorés** (ne contiennent pas de
secrets, mais les messages des visiteurs ne doivent pas être versionnés).
