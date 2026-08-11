# Spécification Technique — front_app_agent

> Architecture proposée, stack, modèle de données, contrats d'API, sécurité et découpage (backlog).
> Complement de `spec-fonctionnelle.md`.

---

## 1. Architecture (diagramme ASCII)

```
┌───────────────────────────────────────────────────────────┐
│                       NAVIGATEUR (UI)                      │
│  React + TypeScript (Vite)  ·  composants squad/tâche      │
│  ── REST (fetch)  ───────────────────────────┐            │
│  ── SSE (/stream)  ◀── flux temps réel ───────┤            │
└───────────────────────────────────────────────┼────────────┘
                                                 │  HTTP/HTTPS
┌───────────────────────────────────────────────┼────────────┐
│                  BACKEND API (FastAPI)          │            │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┴─────────┐ │
│  │ Routes REST│  │ Endpoint SSE│  │ Service métier        │ │
│  │ /agents    │  │ /stream    │  │ (règles R1-R8)        │ │
│  │ /tasks     │  │            │  │                       │ │
│  │ /briefs    │  │            │  │                       │ │
│  └────────────┘  └────────────┘  └─────────────┬─────────┘ │
│                                                │            │
│  Auth : chef (session token) / agent (API key)│            │
└───────────────────────────────────────────────┼────────────┘
                                                 │ ORM (SQLAlchemy)
┌───────────────────────────────────────────────┼────────────┐
│                  BASE SQLITE                     │            │
│  agents · tasks · briefs · task_events                        │
└─────────────────────────────────────────────────────────────┘

Hors app (adaptateur optionnel, non livré ici) :
  Agents Hermes (profils backend/frontend/qa/devops)
    ↔ consomment POST /briefs, publient POST /agents/{id}/state
```

## 2. Stack recommandée (avec justification courte)

| Couche | Techno | Justification |
|--------|--------|---------------|
| Frontend | React 18 + TypeScript + Vite | Écosystème mûr, build rapide, typage pour contrats API |
| UI/state | TanStack Query (cache REST) + Zustand (état SSE) | Séparation claire data-server / temps réel |
| Backend | Python 3.11 + FastAPI | Async natif, SSE trivial via `StreamingResponse`, OpenAPI auto |
| ORM | SQLAlchemy 2.x | Mappage propre, compatible SQLite sans friction |
| Stockage | SQLite (`squad.db`) | Zéro ops pour une DEMO ; un seul fichier |
| Temps réel | SSE (Server-Sent Events) | Unidirectionnel serveur→client (H3) ; plus simple que WS |
| Tests API | pytest + httpx + TestClient | Intégration FastAPI standard |
| Tests UI | Vitest + React Testing Library | Cohérent avec la stack TS |

### Justification des choix clés
- **FastAPI vs Flask** : SSE native (`StreamingResponse` + générateur async) et schémas Pydantic = contrat API documenté sans effort.
- **SQLite vs Postgres** : DEMO mono-instance ; aucune dépendance serveur. Migration Postgres possible plus tard via URL de connexion.
- **SSE vs WebSocket** : le besoin est serveur→client uniquement (état/tâches). SSE suffit et simplifie la reconnexion côté UI.

## 3. Modèle de données

### Entité `agents`
| Champ | Type | Contrainte |
|-------|------|-----------|
| id | UUID | PK |
| role | str | unique, ∈ {backend, frontend, qa, devops} (R1) |
| name | str | |
| status | str | ∈ {idle, busy, blocked, offline} (R2) |
| current_task_id | UUID | FK → tasks.id, nullable |
| last_activity_at | datetime | UTC (R8) |
| created_at / updated_at | datetime | UTC |

### Entité `tasks`
| Champ | Type | Contrainte |
|-------|------|-----------|
| id | UUID | PK |
| title | str | |
| description | text | brief libre |
| status | str | ∈ {todo, in_progress, blocked, done, cancelled} (R3) |
| progress | int | 0–100 (R7) |
| priority | str | ∈ {low, medium, high, critical} |
| due_at | datetime | nullable |
| block_reason | text | requis si status=blocked (R4) |
| unblock_note | text | requis si sortie de blocked (R4) |
| ack_status | str | ∈ {pending, received, executing, done, failed} (R6) |
| agent_id | UUID | FK → agents.id |
| brief_id | UUID | FK → briefs.id |
| created_at / updated_at | datetime | UTC |

### Entité `briefs`
| Champ | Type | Contrainte |
|-------|------|-----------|
| id | UUID | PK |
| title | str | |
| body | text | brief libre |
| priority | str | |
| due_at | datetime | nullable |
| created_by | str | "headmaster" |
| created_at | datetime | UTC |

### Entité `task_events` (journal)
| Champ | Type | Contrainte |
|-------|------|-----------|
| id | UUID | PK |
| task_id | UUID | FK → tasks.id |
| event_type | str | created/received/progress/status/ack |
| payload | json | détail (ex : progress=60) |
| created_at | datetime | UTC |

## 4. Contrats d'API (OpenAPI sommaire)

Base URL : `/api/v1`

### Agents
- `GET /agents` → liste des agents (avec tâche courante)
- `GET /agents/{id}` → détail agent + tâches
- `POST /agents/{id}/state` *(service account agent)* → met à jour status / current_task_id / last_activity_at
  ```json
  { "status": "busy", "current_task_id": "<uuid>" }
  ```
- `POST /agents` *(chef)* → créer/référencer un agent

### Tasks
- `GET /tasks?agent_id=&status=&priority=` → liste filtrable (US3)
- `GET /tasks/{id}` → détail + historique d'events
- `PATCH /tasks/{id}` *(chef)* → clôturer/annuler (US7)
  ```json
  { "status": "done" }
  ```
- `PATCH /tasks/{id}/progress` *(agent)* → progression (R7)
  ```json
  { "progress": 60, "ack_status": "executing" }
  ```

### Briefs
- `POST /briefs` *(chef)* → crée 1+ tâches (US4 / US5) (R5)
  ```json
  {
    "title": "Auth JWT",
    "body": "Ajoute un middleware JWT...",
    "priority": "high",
    "due_at": "2026-08-12T18:00:00Z",
    "agent_ids": ["<uuid-backend>", "<uuid-devops>"]
  }
  ```
  Réponse : `{ "brief_id": "...", "tasks": [ { "id": "...", "agent_id": "..." } ] }`
- `GET /briefs` → historique des briefs
- `GET /briefs/{id}` → brief + tâches liées

### Temps réel
- `GET /stream` *(SSE)* → événements diffusés :
  - `task.created`, `task.updated`, `agent.updated`
  - format : `event: task.updated\ndata: {json}\n\n`

### Sécurité des endpoints
| Endpoint | Autorisé |
|----------|----------|
| GET * | chef (session token) |
| POST /agents, PATCH /tasks, POST /briefs | chef |
| POST /agents/{id}/state, PATCH /tasks/{id}/progress | agent (API key service account) |

## 5. Sécurité

- **Chef** : session token (cookie httpOnly) généré à l'ouverture ; pour la DEMO, un token statique configuré (`config.yaml`/`env`) suffit.
- **Agent** : chaque agent possède une `API_KEY` (header `X-Agent-Key`) ; seuls les endpoints d'écriture agent l'acceptent. Rejet 401 sinon.
- **Validation** : schémas Pydantic stricts ; rejet des transitions de statut illégales (R3) avec 422.
- **CORS** : restreint à l'origine de l'UI en dev (Vite) ; à durcir en prod.
- **SSE** : flux authentifié comme le reste ; reconnexion côté client avec `Last-Event-ID`.
- **Données** : pas de secret stocké hors `API_KEY` agent ; `squad.db` local au dépôt.

## 6. Découpage en tâches (backlog) — voir `backlog.md`

Le découpage complet par rôle (backend / frontend / qa / devops) avec critères d'acceptation
est fourni dans le fichier `backlog.md` companion.

## 7. Hypothèses techniques
- H1/H2/H3/H4 reprises de la spec fonctionnelle ; l'adaptateur Hermes est hors livrable (tâche devops optionnelle en fin de backlog).
- Pour la DEMO, un seed (`seed.py`) crée les 4 agents + 2-3 tâches d'exemple.
- L'UI suit le thème "grim-dark" existant du dashboard (référence : skins Adeptus/Chaos) si réutilisable, sinon thème sobre par défaut.
