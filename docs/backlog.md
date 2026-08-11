# Backlog — front_app_agent

> Découpage des tâches par rôle (backend / frontend / qa / devops) avec critères d'acceptation.
> Calqué sur les User Stories (US1–US7) et règles métier (R1–R8) de `spec-fonctionnelle.md`.

Légende statut : 🔲 à faire · 🔧 en cours · ✅ livré

---

## BACKEND (FastAPI + SQLAlchemy + SQLite)

### B1 — Scaffold projet & modèle de données
**Livrable** : structure FastAPI, `models.py` (agents/tasks/briefs/task_events), `database.py` (SQLite + session).
**Critères d'acceptation** :
- `uvicorn` démarre l'API sur `/api/v1`, OpenAPI dispo sur `/docs`.
- Les 4 tables sont créées au démarrage (SQLite `squad.db`).
- Schémas Pydantic validant les énumérations R1/R2/R3/R6.

### B2 — Endpoints Agents (US1, US2, US6)
**Livrable** : `GET /agents`, `GET /agents/{id}`, `POST /agents`, `POST /agents/{id}/state` (agent key).
**Critères d'acceptation** :
- `POST /agents/{id}/state` rejette sans `X-Agent-Key` (401).
- Mise à jour de `status`, `current_task_id`, `last_activity_at` persistée.
- Transition illégale de statut agent → 422.

### B3 — Endpoints Tasks (US3, US7)
**Livrable** : `GET /tasks` (filtres agent/status/priority), `GET /tasks/{id}` (+ events), `PATCH /tasks/{id}` (chef), `PATCH /tasks/{id}/progress` (agent).
**Critères d'acceptation** :
- Filtres combinables fonctionnels.
- `PATCH` statut respecte R3 ; `blocked` exige `block_reason` (R4) sinon 422.
- `progress` 0–100 ; >0 et <100 force `in_progress` (R7).

### B4 — Endpoint Briefs (US4, US5, R5)
**Livrable** : `POST /briefs` (crée 1+ tâches + brief), `GET /briefs`, `GET /briefs/{id}`.
**Critères d'acceptation** :
- `agent_ids` multiple → N tâches (status=todo, ack=pending) (R5).
- Chaque tâche liée au `brief_id` ; réponse liste les tâches créées.
- Brief sans `agent_ids` → 422.

### B5 — Flux temps réel SSE (US1, US6, H3)
**Livrable** : `GET /stream` diffusant `task.created/updated`, `agent.updated`.
**Critères d'acceptation** :
- Toute mutation B2/B3/B4 émet l'événement SSE correspondant.
- Flux authentifié ; reconnexion client supportée (Last-Event-ID).

### B6 — Auth & seed DEMO (H4)
**Livrable** : session token chef (config), `X-Agent-Key` par agent, `seed.py`.
**Critères d'acceptation** :
- `seed.py` crée 4 agents (backend/frontend/qa/devops) + 3 tâches d'exemple.
- Endpoints chef protégés par token ; endpoints agent par API key.

---

## FRONTEND (React + TS + Vite)

### F1 — Scaffold UI & client API
**Livrable** : Vite + React + TS, client REST (TanStack Query), hook SSE.
**Critères d'acceptation** :
- App démarre, appelle `GET /agents` et affiche un placeholder.
- Hook SSE reçoit et log les événements `task.updated`.

### F2 — Tableau de bord squad (US1)
**Livrable** : page dashboard listant agents (nom, rôle, statut pastille, tâche, dernière activité), bouton "+ Brief".
**Critères d'acceptation** :
- Pastille couleur par statut (idle/busy/blocked/offline).
- Mise à jour live sans reload via SSE.

### F3 — Fiche agent & tâches (US2)
**Livrable** : route `/agents/:id`, liste tâches triées, historique briefs.
**Critères d'acceptation** :
- Tâches affichées avec progression et brief source.
- Clic tâche → F4.

### F4 — Fiche tâche (US2, US3)
**Livrable** : composant tâche (titre, statut, progression bar, priorité, échéance, brief, historique events).
**Critères d'acceptation** :
- Barre de progression reflète `progress`.
- Tâches `blocked` mises en évidence (couleur/icône).

### F5 — Liste tâches filtrable (US3)
**Livrable** : page `/tasks` avec filtres agent/status/priorité.
**Critères d'acceptation** :
- Filtres combinables ; résultat live via SSE.

### F6 — Formulaire d'envoi de brief (US4, US5)
**Livrable** : modal/édition brief (agent cible(s), titre, body, priorité, échéance), envoi `POST /briefs`.
**Critères d'acceptation** :
- Sélection multiple d'agents (brief groupé US5).
- Après envoi, tâche(s) apparaît(issent) en live ; alerte si pas d'accusé sous 60 s.

### F7 — Clôture / annulation tâche (US7)
**Livrable** : actions sur fiche tâche → `PATCH /tasks/{id}` (done/cancelled).
**Critères d'acceptation** :
- Blocage d'une tâche `blocked` impossible sans commentaire (R4) côté UI.
- Feedback visuel post-action.

---

## QA

### Q1 — Tests API (contrats & règles)
**Livrable** : pytest sur B1–B6.
**Critères d'acceptation** :
- Transitions R3/R4/R6 validées (positif + négatif 422).
- `POST /briefs` multi-agent crée N tâches (R5).
- SSE émet bien sur mutation (test avec client SSE).
- Auth : 401 sans clé/token.

### Q2 — Tests UI (composants)
**Livrable** : Vitest + RTL sur F2–F7.
**Critères d'acceptation** :
- Rendu dashboard avec 4 agents seedés.
- Formulaire brief : validation sélection agent + envoi mock.
- Filtres tâches : comportement attendu.

### Q3 — Scénario E2E (happy path)
**Livrable** : script de démo : seed → chef envoie brief → (mock agent) reçoit/progress/clôture → UI reflète.
**Critères d'acceptation** :
- Le parcours complet s'affiche sans erreur console ; SSE mis à jour de bout en bout.

---

## DEVOPS

### D1 — Environnement local reproductible
**Livrable** : `Makefile` / `scripts` (install backend+front, seed, run), `.env.example`.
**Critères d'acceptation** :
- `make dev` lance API + UI ; `make seed` peuple la base.
- README minimal avec commandes.

### D2 — Dockerisation (option DEMO)
**Livrable** : `Dockerfile` API + `docker-compose` (api + ui + volume sqlite).
**Critères d'acceptation** :
- `docker compose up` expose UI sur port défini et API.

### D3 — Adaptateur Hermes (HORS V1 DEMO — suivi)
**Livrable** : bridge profils backend/frontend/qa/devops ↔ endpoints agent (`POST /agents/{id}/state`, consommation `POST /briefs`).
**Critères d'acceptation** :
- Un agent Hermes réel reçoit un brief et publie son état dans front_app_agent.
- *À planifier après validation des specs et de la DEMO.*

---

## Dépendances & ordre suggéré

```
B1 ──► B2 ──► B3 ──► B4 ──► B5 ──► B6 (seed)
              │
F1 ──► F2 ──► F3 ──► F4 ──► F5 ──► F6 ──► F7
              │
Q1 (parallele B) ──► Q2 ──► Q3
D1 ──► D2      (D3 après val)
```

Backend avant Frontend (contrats stables) ; QA accompagne chaque tranche ; DevOps en parallèle tardif.
