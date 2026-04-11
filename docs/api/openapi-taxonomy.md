# OpenAPI-Tags und Backend-Info-Mapping

Diese Datei ist die **normative Landkarte** zwischen:

- OpenAPI-`tags` in [`openapi.yaml`](openapi.yaml) (Explorer, maschinenlesbar)
- den fünf Themenseiten unter `/backend/*` (Flask-Info-Oberfläche)
- den MkDocs-Einträgen unter **API** in [`mkdocs.yml`](../../mkdocs.yml)

## Tag-Übersicht (Domänen)

| Tag | Bedeutung | Flask-Module (Orientierung) |
|-----|-----------|-----------------------------|
| **Auth** | Login, Tokens, Registrierung, Passwort-Flows | `auth_routes` |
| **Users** | Nutzerprofile, Einstellungen, Moderation auf Nutzer-Ebene | `user_routes` |
| **Roles** | Rollenverwaltung (Admin/autorisierte Clients) | `role_routes` |
| **Forum** | Forum, Moderation, Suche, Tags, Benachrichtigungen | `forum_routes*`, Forum-Notifications |
| **SiteContent** | News, Wiki (öffentlich + Admin-Übersetzungen), Site-Settings, Slogans, Sprachen | `news_routes`, `wiki_*`, `site_routes`, `slogan_routes` |
| **GameBootstrap** | Spielstart, Charaktere, Runs, Tickets, Save-Slots, Content-Pipeline, Play-Service-Steuerung | `game_routes`, `play_service_control_routes`, `game-content` |
| **GameAdmin** | Veröffentlichung und Laufzeit-Admin für Experiences | `game_admin_routes` |
| **SessionsBridge** | In-Prozess-Session / Operator-Brücke (**nicht** autoritative Live-Play-Authority) | `session_routes` |
| **WritersRoom** | Writers-Room-Reviews und Entscheidungen | `writers_room_routes` |
| **Improvement** | Improvement-Pakete, Experimente, Varianten | `improvement_routes` |
| **Admin** | Admin-Dashboards, Export/Import, Moderator-Zuweisungen, allgemeine Admin-JSON | `admin_routes`, `data_routes` (ohne AI/MCP/Analytics-Unterpfade) |
| **Analytics** | Aggregierte Admin-Analysen | `admin_routes` (Pfad `/admin/analytics`) |
| **AIStackGovernance** | AI-Stack-Inspector, Evidence, Release-Readiness | `ai_stack_governance_routes` |
| **MCP** | MCP-Operator-Oberfläche und Telemetrie-Ingest | `mcp_operations_routes` |
| **System** | Health, Diagnose, interne Test-Endpunkte | `system_routes`, `system_diagnosis_routes` |
| **Areas** | Feature-Areas und Areas-CRUD | `area_routes` |

Zuordnung erfolgt im Generator [`backend/scripts/generate_openapi_spec.py`](../../backend/scripts/generate_openapi_spec.py) per **längstem Pfad-Präfix** (spezifische Regeln vor allgemeinen).

## Mapping: `/backend`-Themenseite → Tags

| Info-Seite | Tags (Explorer-Filter) | MkDocs-Anker (API-Referenz) |
|------------|-------------------------|-----------------------------|
| **API** (`/backend/api`) | alle REST-Tags | [REFERENCE.md – Backend API](REFERENCE.md#backend-api) (gesamtes Dokument) |
| **Engine** (`/backend/engine`) | `GameBootstrap`, `GameAdmin` | [API README — World Engine](README.md#world-engine-api) + [REFERENCE.md](REFERENCE.md) (Game-/Bootstrap-Pfade) |
| **AI** (`/backend/ai`) | `SessionsBridge`, `WritersRoom`, `Improvement`, `AIStackGovernance` | [REFERENCE.md](REFERENCE.md) (Writers-Room, Improvement, Sessions) + Dev: [AI stack & GoC seams](../dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md) |
| **Auth** (`/backend/auth`) | `Auth`, `Users`, `Roles` (AuthN/AuthZ-relevant) | [REFERENCE.md – Authentication](REFERENCE.md#authentication-endpoints) |
| **Ops** (`/backend/ops`) | `System`, `Admin` (Logs/Metriken), `MCP`, `Analytics` | [Admin runbook](../admin/operations-runbook.md), [services & health](../admin/services-and-health-checks.md) |

## Maschinenlesbare Pflege

- **`openapi.yaml`** wird mit `python backend/scripts/generate_openapi_spec.py --write` aus den registrierten Flask-Routen erzeugt (Pfad-Inventar + Tags + Stub-Operationen).
- **Drift-Test:** [`backend/tests/test_openapi_drift.py`](../../backend/tests/test_openapi_drift.py) — schlägt fehl, wenn Routen und Spec auseinanderlaufen.

## World Engine (FastAPI)

Die **Play-Service-HTTP-API** des `world-engine/`-Repos ist **nicht** in dieser Spec enthalten. Siehe [API README — World Engine](README.md#world-engine-api); Backend-Game-Endpunkte in [REFERENCE.md](REFERENCE.md).
