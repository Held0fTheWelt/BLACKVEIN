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
- and a small browser client to prove the full loop.

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

3. **Participants**
   - human seats and NPC seats
   - same shape for solo, group, and open-world modes

4. **Server-side command processing**
   - move
   - say
   - emote
   - inspect
   - use scripted action

5. **Snapshot broadcasting over WebSockets**
   - every connected client receives updated state
   - the client only renders

6. **JSON persistence**
   - runtime instances are persisted to disk
   - the public open-world shard survives restart

### Included built-in templates

- `god_of_carnage_solo`
  - a social vertical slice for single-player use
  - still running on the multiplayer-capable architecture

- `apartment_confrontation_group`
  - a party-style pre-authored scenario with multiple human seats

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
wos_scene_prototype/
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
│   │   └── store.py
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
├── render.yaml
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

### RuntimeInstance
A live running copy of a template.

Contains:
- active participants
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
- simple NPC follow-up reactions

### RuntimeManager
Owns all active runs.

Responsibilities:
- load templates
- create runs
- join runs
- manage WebSocket connections
- persist runtime state
- broadcast fresh snapshots

---

## Running locally

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

## How to try the three modes

### Solo story
1. Choose `The Apartment Incident — Solo Study`
2. Enter a player name
3. Create run
4. Move into the living room
5. Use scripted actions and quick commands

### Group story
1. Open two or more browser tabs
2. Choose `Apartment Incident — Group Story`
3. Create from one tab
4. Join the same run from the other tabs
5. Use different player names and optionally preferred role ids

Suggested role ids:
- `mediator`
- `parent_a`
- `parent_b`
- `observer`

### Open world shard
1. Join the existing `Better Tomorrow District Alpha` run
2. Open multiple tabs with different names
3. Move between plaza, noodle bar, and service alley
4. Use say/emote and scripted room actions

---

## Current API surface

### HTTP
- `GET /api/health`
- `GET /api/templates`
- `GET /api/runs`
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

---

## Persistence model in the prototype

This version stores runtime state as JSON files under:

```text
app/var/runs/
```

That is deliberate for the first prototype:

- easy to inspect
- no external services required
- simple restart persistence
- easy to replace later with Postgres + Redis

### Later replacement path

For your real system, the intended next step is:

- **Flask control plane**: users, characters, story catalog, assets, admin, writers room
- **Postgres**: authoritative persistent content + runtime records
- **Redis**: presence, pub/sub, short-lived locks, shard routing
- **Play service**: real-time authoritative runtime

---

## Planned integration with your Flask backend

This prototype already leaves a clean insertion point:

### Later Flask responsibilities
- issue authenticated game tickets
- decide what templates/runs a user can access
- provide character metadata
- provide content and asset manifests
- own admin/moderation workflows

### Later play-service responsibilities
- verify Flask-issued tickets
- load or create runtime instances
- run simulation
- broadcast snapshots and transcripts

### Ticket contract shape
The current local ticket contains:

```json
{
  "run_id": "...",
  "participant_id": "...",
  "player_name": "...",
  "role_id": "...",
  "iat": 123,
  "exp": 456
}
```

Later your Flask backend can issue the same kind of signed ticket, and the play service can trust it after signature verification.

---

## What is intentionally simplified in this first prototype

This is a foundation build, not yet the full product. So several things are still intentionally small:

- no database integration yet
- no Redis yet
- no moderation or observer tools yet
- no replay UI yet
- no rich NPC reasoning yet
- no AI asset generation pipeline yet
- no proper lobby / invites / ready-check flow yet
- no save-slot browser yet
- no Flask SSO yet
- no horizontal scaling yet

But the shape already points in the right direction.

---

## Suggested next implementation steps

### Step 1
Integrate the play-service ticket flow into your Flask backend.

### Step 2
Move templates from hard-coded Python into a real content source:
- database
- JSON content packs
- writers-room publish flow

### Step 3
Add party orchestration for group stories:
- invitations
- reserved seats
- ready checks
- reconnect handling

### Step 4
Add proper instance persistence:
- Postgres snapshots
- event log table
- resumable story runs

### Step 5
Add client rendering layers for retro presentation:
- room background art
- portraits
- props as hotspots
- light 80s-adventure layout

### Step 6
Add controlled NPC logic and later AI-assisted NPC output under strict guardrails.

---

## Testing

Run:

```bash
pytest
```

The included tests focus on:
- run creation
- snapshot shape
- movement and scripted actions
- persistent public shard bootstrapping

---

## Deployment note

A minimal `render.yaml` is included to make a first free-hosting attempt easier.
For the eventual target system, this play service should remain separate from the Flask control plane.

---

## Summary

This prototype is already a real first cut of the architecture we discussed:

- shared runtime model across all three content modes
- authoritative play service
- WebSocket live updates
- template vs. runtime split
- enough structure to be worth extending instead of discarding

That makes it a useful entry point for the next round instead of just a throwaway demo.
