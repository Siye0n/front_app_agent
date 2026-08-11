# Spécification — Vitrine Adeptus Mechanicus + chat de contact

- **Dossier repo** : `adeptus-mechanicus/`
- **Type** : serveur Flask (Python) + UI HTML/CSS/JS vanilla
- **Lancement local** : `python app.py` (port 5001)
- **Statut** : en cours de construction (profil frontend, branche feature/adeptus-mechanicus)

## Objectif
Vitrine dans l'univers Warhammer 40,000 (Adeptus Mechanicus — culte de la machine) + un chat
permettant de contacter l'assistant (headmaster). Le chat est serveur-backé : les messages sont
loggés côté serveur et relus par l'assistant (pas de gateway messaging externe).

## Périmètre fonctionnel
- Page vitrine : hero "Adeptus Mechanicus", sections (Omnimessie, Skitarii, Tech-Priests,
  Forge-Monde, Dogme de la Machine).
- Thème : noir charbon, laiton/bronze, rouge Mechanicus, vert binaire phosphore ; polices Cinzel/EB Garamond.
- Panneau de chat "Communique avec le Magos" :
  - champ nom/appellation (optionnel) + zone message (requis) + bouton "Transmettre".
  - `POST /api/contact` : reçoit {nom?, message}, ajoute à `messages.json`, répond 200.
  - `GET /api/contact` : liste les messages reçus (chargement initial UI).
  - UI indique "Transmission enregistrée — le Magos répondra par canal sécurisé".

## Contraintes
- Aucune image / texte copyrighté GW (contenu original, SVG/CSS inline).
- `messages.json` git-ignoré (contient les messages visiteurs).
- Port 5001 (évite conflit avec osint/5000).

## Hors périmètre
- Pas de réponse automatique du chat (l'assistant répond hors-ligne en lisant messages.json).
- Pas de notification push (pas de gateway messaging externe, par choix du boss).

## Vérification (prévue)
- `POST /api/contact` {nom, message} → 200 ; `GET /api/contact` renvoie le message.
- UI affiche/envoi fonctionne via le serveur.
