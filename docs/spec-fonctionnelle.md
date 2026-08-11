# Spécification Fonctionnelle — front_app_agent

> Webapp permettant à un chef d'équipe (headmaster) de piloter visuellement une squad d'agents IA :
> visualiser les tâches en cours, l'état de chaque agent, et leur envoyer des briefs.
> Composants : UI web (client) + API (backend).

---

## 1. Contexte

Le headmaster supervise une squad de 4 rôles (backend, frontend, qa, devops) exécutés comme agents IA isolés.
Aujourd'hui le pilotage se fait au cas par cas via le CLI Hermes et le Web Dashboard. Il n'existe pas de
vue centralisée dédiée "squad" : état des tâches, progression, et envoi de briefs groupés/manuels.

front_app_agent comble ce vide : une application web autonome (UI + API) qui devient le poste de commandement
visuel du chef d'équipe.

## 2. Objectifs

- O1 : Donner au chef d'équipe une vue d'ensemble en temps réel de la squad (qui fait quoi, statut).
- O2 : Permettre de suivre les tâches de chaque agent (création, progression, état, clôture).
- O3 : Permettre d'envoyer un brief à un ou plusieurs agents depuis l'UI.
- O4 : Centraliser la traçabilité des briefs et de leurs accusés de réception.

## 3. Périmètre

### In (dans le périmètre)
- UI web responsive (desktop d'abord) : tableau de bord squad, fiches agent, fiches tâche.
- API REST + flux temps réel (SSE) pour l'état et les tâches.
- Gestion des agents : référence (rôle, nom, statut, dernière activité).
- Gestion des tâches : création via brief, statuts, progression, assignation à un agent.
- Envoi de briefs (texte libre + contexte structuré) à un ou plusieurs agents.
- Accusé de réception et suivi d'état d'exécution du brief par l'agent.
- Persistance dans une base locale (SQLite).

### Out (hors périmètre — voir section 9)
- Exécution réelle des agents IA (l'orchestration Hermes reste en dehors de cette app).
- Authentification multi-utilisateur / gestion des rôles au-delà du chef d'équipe.
- Messagerie bidirectionnelle continue (chat libre) — seul le brief structuré est géré ici.
- Intégration CI/CD, facturation, ou analytics tiers.

## 4. Acteurs

| Acteur | Rôle | Droits |
|--------|------|--------|
| Chef d'équipe (headmaster) | Utilisateur unique de l'app | CRUD agents, tâches, briefs ; lecture temps réel |
| Agent IA (entité supervisée) | Cible des briefs, émetteur d'état | Écrit son état/tâches via l'API (service account) |

## 5. Cas d'usage

### US1 — Voir la squad en un coup d'œil
**En tant que** chef d'équipe, **je veux** un tableau de bord listant tous les agents et leur état,
**afin de** savoir instantanément qui est actif, occupé ou inactif.

Critères d'acceptation :
- Le tableau liste chaque agent (nom, rôle, statut, tâche courante, dernière activité).
- Le statut est l'un de : `idle`, `busy`, `blocked`, `offline`.
- L'affichage se met à jour automatiquement sans recharge manuelle (SSE).
- Un indicateur visuel (couleur/pastille) distingue les statuts.

### US2 — Consulter le détail d'un agent
**En tant que** chef d'équipe, **je veux** ouvrir la fiche d'un agent avec ses tâches,
**afin de** comprendre sa charge et sa progression.

Critères d'acceptation :
- La fiche affiche les tâches assignées (tri par statut/priorité).
- Chaque tâche montre titre, statut, progression (%), échéance, brief source.
- L'historique des briefs reçus par l'agent est consultable.

### US3 — Suivre les tâches en cours
**En tant que** chef d'équipe, **je veux** voir la liste de toutes les tâches de la squad,
**afin de** repérer les retardataires et les bloquées.

Critères d'acceptation :
- Liste filtrable par agent, statut, priorité.
- Chaque tâche affiche progression et dernier événement.
- Les tâches `blocked` sont mises en évidence.

### US4 — Envoyer un brief à un agent
**En tant que** chef d'équipe, **je veux** rédiger et envoyer un brief à un agent sélectionné,
**afin de** lui confier une mission sans passer par le CLI.

Critères d'acceptation :
- Le formulaire demande : agent cible, titre, description (brief libre), priorité, échéance optionnelle.
- À l'envoi, une tâche est créée (statut `todo`) et le brief est transmis à l'agent.
- Un accusé de réception (`received`) est attendu de l'agent sous 60 s ; sinon alerte visuelle.

### US5 — Envoyer un brief groupé
**En tant que** chef d'équipe, **je veux** envoyer un même brief à plusieurs agents,
**afin de** lancer une mission parallèle sur la squad.

Critères d'acceptation :
- Sélection multiple d'agents.
- Une tâche est créée par agent cible à partir du même brief.
- Suivi individuel des accusés de réception.

### US6 — L'agent met à jour son état/tâche
**En tant qu'** agent IA (via API), **je veux** publier mon statut et la progression de mes tâches,
**afin que** le chef d'équipe ait une vue vivante.

Critères d'acceptation :
- Endpoint dédié (service account) acceptant un payload d'état.
- Transition de statut de tâche valide (voir règles R3).
- Les mises à jour sont diffusées en SSE aux clients UI.

### US7 — Clôturer / annuler une tâche
**En tant que** chef d'équipe, **je veux** clôturer ou annuler une tâche,
**afin de** maintenir le tableau de bord à jour.

Critères d'acceptation :
- Statut cible `done` ou `cancelled`.
- Impossible de clôturer une tâche `blocked` sans commentaire (règle R4).
- Historique conservé.

## 6. Règles métier

- **R1 — Unicité agent** : un agent est identifié par un `agent_id` stable (rôle = backend/frontend/qa/devops).
- **R2 — Statut agent** : `idle` (disponible), `busy` (travaille), `blocked` (en attente), `offline` (non joignable).
- **R3 — Cycle de vie tâche** : `todo` → `in_progress` → (`blocked` ⇄ `in_progress`) → `done` | `cancelled`.
  Transition valide uniquement entre états adjacents ; `cancelled` reachable depuis `todo`/`in_progress`/`blocked`.
- **R4 — Blocage** : passer en `blocked` exige un champ `block_reason` (obligatoire). Sortir de `blocked` exige un `unblock_note`.
- **R5 — Brief → Tâche** : tout brief envoyé crée au moins une tâche. Un brief groupé crée N tâches (1/agent).
- **R6 — Accusé de réception** : champ `ack_status` sur tâche = `pending` (initial), `received`, `executing`, `done`, `failed`.
  Valeur par défaut `pending` ; seul l'agent (service account) peut le faire évoluer.
- **R7 — Progression** : `progress` entier 0–100 ; passage automatique `in_progress` quand `progress` > 0 et < 100.
- **R8 — Timestamps** : `created_at`, `updated_at`, `last_activity_at` gérés par le serveur (UTC).

## 7. Flux principaux

### Flux A — Envoi d'un brief (chef → agent)
```
[UI] Chef sélectionne agent + rédige brief
  → [API] POST /briefs  → crée Tâche(s) (status=todo, ack=pending)
  → [API] diffuse SSE "task.created"
  → [Agent] reçoit brief (webhook/poll) → POST /agents/{id}/state (ack=received, status=busy)
  → [API] diffuse SSE "task.updated"
  → [Agent] POST /tasks/{id} progression → SSE "task.updated"
  → [Agent] tâche finie → POST /tasks/{id} (status=done, ack=done) → SSE "task.updated"
```

### Flux B — Mise à jour temps réel (agent → UI)
```
[Agent] POST /agents/{id}/state ou /tasks/{id}
  → [API] valide + persiste + diffuse SSE
  → [UI] composant écoute le flux et met à jour la vue (pas de reload)
```

## 8. Maquettes textuelles (ASCII)

### Tableau de bord squad
```
┌──────────────────────────────────────────────────────────────┐
│  SQUAD COMMAND  —  Chef: headmaster        [+ Nouveau brief]  │
├──────────┬─────────┬──────────┬──────────┬───────────────────┤
│ Agent    │ Rôle    │ Statut   │ Tâche    │ Dernière activité │
├──────────┼─────────┼──────────┼──────────┼───────────────────┤
│ backend  │ backend │ 🟢 busy  │ API auth │ il y a 2 min      │
│ frontend │ frontend│ 🟡 idle  │ —        │ il y a 18 min     │
│ qa       │ qa      │ 🔴 block │ tests E2E│ il y a 5 min      │
│ devops   │ devops  │ 🟢 busy  │ deploy   │ il y a 1 min      │
└──────────┴─────────┴──────────┴──────────┴───────────────────┘
```

### Fiche tâche
```
┌─ Tâche #42 ──────────────────────────────┐
│ Titre : Implémenter auth JWT             │
│ Agent : backend     Statut : in_progress │
│ Progression : [██████░░░░] 60%           │
│ Priorité : high    Échéance : 12/08 18h  │
│ Brief : "Ajoute un middleware JWT..."    │
│ Ack : received                        │
│ Historique :                          │
│  19:02 créée   19:03 reçue   19:10 60% │
└──────────────────────────────────────────┘
```

## 9. Hors-périmètre (explicite)

- L'application ne lance pas les agents ; elle consomme/produit leur état via l'API.
- Pas d'auth utilisateur fine (un seul chef) ; un service account agent protège les endpoints d'écriture agent.
- Pas de persistance de longue durée multi-session utilisateur au-delà de la squad.
- Pas de mobile natif (UI web responsive uniquement).

---

## 10. Points d'attention (hypothèses retenues — à valider)

- **H1 (source de vérité)** : on suppose que les agents Hermes existants exposent/consomment l'API front_app_agent
  via un adaptateur sur l'architecture profils (backend/frontend/qa/devops). Si la squad est générique/découplée,
  seuls les contrats d'API changent, pas l'UI.
- **H2 (nature du brief)** : un brief = mission structurée (titre + description libre + priorité + échéance) créant
  une ou plusieurs tâches. Un adaptateur (hors périmètre ici) traduit le brief en prompt/commande côté agent.
- **H3 (temps réel)** : on adopte SSE (Server-Sent Events) pour la diffusion temps réel — plus simple que WebSocket
  pour une mise à jour unidirectionnelle serveur→client. Le client peut aussi interroger l'API en REST.
- **H4 (mode demo)** : livraison "DEMO" → seed de 4 agents + données d'exemple ; pas d'intégration Hermes réelle
  exigée pour la v1 de la démo.
