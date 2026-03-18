# World of Shadows Play Service Prototype

A first downloadable prototype for the runtime architecture we discussed:

- **one shared runtime model** for
  - single-player stories,
  - group story instances,
  - and a future open multiplayer world,
- **a separate play service** from the Flask control plane,
- **authoritative state on the server**,
- **WebSocket delivery** for live updates,
- **template -> runtime instance** separation,
- **a lobby/seat/rejoin layer for group stories**,
- and **switchable runtime persistence** with a JSON dev store or an SQL-backed store for local Postgres.

This prototype is intentionally **standalone**. It does **not** integrate with your current Flask backend yet.
That later integration step can plug into the ticket contract and run catalog without throwing away the runtime.

---

## What is included

### Runtime architecture

The prototype already distinguishes between:

1. **Experience templates**
   - content-side, versionable, reusable definitions
   - rooms, props, beats, roles, actions, join policy

2. **Runtime instances**
   - live state created from templates
   - participants, beat, tension, flags, transcript, prop states

3. **Participants and lobby seats**
   - human seats and NPC seats
   - reserved seats for group stories
   - ready state and explicit run start
   - account-based rejoin without seat drift

4. **Server-side command processing**
   - move
   - say
   - emote
   - inspect
   - use scripted action
   - set ready / unready in group lobbies
   - start group run from the lobby

5. **Snapshot broadcasting over WebSockets**
   - every connected client receives updated state
   - snapshots are viewer-specific and visibility-filtered
   - the client only renders

6. **Persistence backends**
   - JSON persistence for lightweight local development
   - SQLAlchemy-backed persistence for Postgres (and SQLite for tests/local proofing)

### Included built-in templates

- `god_of_carnage_solo`
  - a social vertical slice for single-player use
  - still running on the multiplayer-capable architecture

- `apartment_confrontation_group`
  - a party-style pre-authored scenario with multiple human seats
  - includes lobby occupancy, ready state, host start, and rejoin behavior

- `better_tomorrow_district_alpha`
  - a tiny public open-world shard proving the architecture can host a persistent shared layer

---

## Why the prototype is structured this way

The main goal is **not** to build a one-off demo. The goal is to create a first clean foundation that already respects your later needs:

- pre-authored solo stories
- pre-authored group stories
- persistent open-world multiplayer
- AI-assisted asset/content production later on
- Flask integration later on

So the prototype avoids the usual trap of writing a single-player toy that later has to be ripped apart.

---

## Project structure

```text
world-engine/
├── app/
│   ├── api/
│   │   ├── http.py
│   │   └── ws.py
│   ├── auth/
│   │   └── tickets.py
│   ├── content/
│   │   ├── builtins.py
│   │   └── models.py
│   ├── runtime/
│   │   ├── engine.py
│   │   ├── manager.py
│   │   ├── models.py
│   │   ├── npc_behaviors.py
│   │   ├── store.py
│   │   └── visibility.py
│   ├── web/
│   │   ├── static/
│   │   │   ├── app.js
│   │   │   └── styles.css
│   │   └── templates/
│   │       └── index.html
│   ├── var/
│   │   └── runs/
│   ├── config.py
│   └── main.py
├── tests/
├── docker-compose.play-local.yml
└── README.md
```

---

## Core concepts

### ExperienceTemplate
A reusable authored definition.

Contains:
- `kind`: `solo_story`, `group_story`, or `open_world`
- `join_policy`: owner-only, invited party, public
- `roles`
- `rooms`
- `props`
- `beats`
- `scripted actions`
- `min_humans_to_start`

### RuntimeInstance
A live running copy of a template.

Contains:
- active participants
- lobby seats
- current beat
- tension
- flags
- prop states
- transcript
- event log

### RuntimeEngine
Processes commands and emits state changes.

It currently supports:
- movement between linked rooms
- free text speech
- free text emotes
- inspection
- scripted authored actions
- ready/unready toggles in group lobbies
- host-controlled group start
- simple NPC follow-up reactions

### RuntimeManager
Owns all active runs.

Responsibilities:
- load templates
- create runs
- join runs
- preserve seat ownership across reconnects
- manage WebSocket connections
- persist runtime state
- broadcast fresh snapshots

---

## Running locally with the JSON store

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the service

```bash
uvicorn app.main:app --reload
```

### 4. Open the browser client

```text
http://127.0.0.1:8000/
```

---

## Running locally with Postgres

Set the runtime store environment before starting the app:

```bash
export RUN_STORE_BACKEND=sqlalchemy
export RUN_STORE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5434/world_engine
uvicorn app.main:app --reload
```

Or use the included Docker Compose file:

```bash
docker compose -f docker-compose.play-local.yml up --build
```

That starts:
- Postgres on `127.0.0.1:5434`
- the play service on `127.0.0.1:8000`

---

## How to try the three modes

### Solo story
1. Choose `The Apartment Incident — Solo Study`
2. Enter account id and display name
3. Create run
4. Move into the living room
5. Use scripted actions and quick commands

### Group story
1. Open two or more browser tabs
2. Choose `Apartment Incident — Group Story`
3. Create from one tab
4. Join the same run from the other tabs
5. Use different account ids and optionally preferred role ids
6. Mark seats ready in the lobby
7. Start the run once the lobby can start
8. Reload one tab and rejoin with the same account id to verify seat resume

Suggested role ids:
- `mediator`
- `parent_a`
- `parent_b`
- `observer`

### Open world shard
1. Join the existing `Better Tomorrow District Alpha` run
2. Open multiple tabs with different accounts
3. Move between plaza, noodle bar, and service alley
4. Use say/emote and scripted room actions

---

## Current API surface

### HTTP
- `GET /api/health`
- `GET /api/health/ready`
- `GET /api/templates`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs`
- `POST /api/tickets`
- `GET /api/runs/{run_id}/snapshot/{participant_id}`
- `GET /api/runs/{run_id}/transcript`

### WebSocket
- `GET /ws?ticket=...`

### Client command payloads

```json
{ "action": "move", "target_room_id": "living_room" }
```

```json
{ "action": "say", "text": "We need to talk calmly." }
```

```json
{ "action": "emote", "text": "folds your arms and studies the room" }
```

```json
{ "action": "inspect", "target_id": "tulips" }
```

```json
{ "action": "use_action", "action_id": "offer_apology" }
```

```json
{ "action": "set_ready", "ready": true }
```

```json
{ "action": "start_run" }
```

---

## Test status

The current pass covers:
- JSON store flow
- SQL store roundtrip via SQLite (same store abstraction used for Postgres)
- viewer-specific visibility
- account-based rejoin
- group lobby ready/start flow
- websocket resume flow

Run tests with:

```bash
pytest -q
```
