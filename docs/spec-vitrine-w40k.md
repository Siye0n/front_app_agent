# Spécification — Vitrine Warhammer 40,000 (site statique)

- **Dossier repo** : `w40k/`
- **Type** : site vitrine statique (sans serveur, HTML/CSS/JS vanilla)
- **URL de déploiement** : https://siye0n.github.io/front_app_agent/w40k/
- **Statut** : livré (PR #1 mergée)

## Objectif
Site vitrine non officiel dans l'univers de Warhammer 40,000, à but de démonstration.
Thème dark-fantasy grim-dark (palette noir charnel / ivoire / or impérial / rouge sang).

## Périmètre fonctionnel
- Menu de navigation en haut (sticky), responsive (burger < 760px).
- Pages : Accueil, Personnages, Planètes, Factions, Chronologie, Armes & Arsenal,
  Organes de l'Imperium, Lexique.
- Chaque fiche (personnage, planète, faction, terme) affiche nom + description originale.
- Liens "Source : Lexicanum (FR)" sur les fiches (URLs vérifiées 200), crédit sans copie de texte
  (contenu original, respect copyright GW).

## Contraintes
- Aucun backend, aucune base de données.
- Aucune image / texte copyrighté GW : contenu original + SVG/CSS inline.
- Hébergement : GitHub Pages (branche main, dossier racine du repo ; site servi sous /w40k/).

## Hors périmètre
- Pas d'interactivité serveur, pas de formulaire, pas de données dynamiques.
- Pas de multilingue (FR uniquement).

## Tests / vérification
- Liens internes relatifs valides (vérifiés).
- 32 liens Lexicanum présents, tous URL 200 (vérifiés).
- Site servi en 200 par GitHub Pages.
