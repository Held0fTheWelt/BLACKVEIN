# World of Shadows Play Service Prototype

This prototype is the standalone play-service half of the architecture discussion.
It intentionally does **not** integrate into the Flask backend yet; instead it proves the runtime shape that Flask can later launch and supervise.

## What changed in this revision

This pass hardens the prototype around the exact weak spots that showed up in review:

- **viewer-scoped visibility** instead of leaking all rooms and all occupants to every client
- **account-based identity** instead of binding runtime ownership to display names
- **per-run locking** instead of one global runtime lock for every active run
- **store abstraction** via `RunStore`, with atomic JSON saves for local development
- **NPC behavior extraction** into a separate module so scene-specific logic stops bloating the core engine

## Runtime model

One runtime supports three experience forms:

- `solo_story`
- `group_story`
- `open_world`

All three use the same basic flow:

1. A template exists in content space.
2. A runtime instance is created or joined.
3. A client receives a viewer-filtered snapshot.
4. Commands go to the authoritative runtime.
5. The runtime emits events and updates transcript/snapshots.

## Identity model

The prototype now treats identity like this:

- `account_id` = stable runtime owner / rejoin key
- `character_id` = optional future-facing character binding
- `display_name` = presentation only

For the current standalone launcher, you type these values manually.
When the Flask backend is integrated later, it should mint the ticket with real account and character identifiers.

## Visibility model

Snapshots are now viewer-scoped.
A player receives only:

- the **current room** payload
- **visible occupants in that room**
- **available actions from that room**
- a **filtered transcript tail** visible to that participant

This keeps solo/group/open-world behavior aligned and prevents early metagame leakage.

## Local run

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/`

## Notes on storage

The included JSON store is for local development only.
It now writes atomically and sits behind a `RunStore` abstraction so a later Postgres-backed implementation can replace it without rewriting runtime orchestration.

## Notes on locking

Commands are now serialized **per run**.
That means one active story instance no longer blocks command processing in another unrelated instance.

## Test suite

```bash
pytest
```

The tests cover:

- run creation and ticket issuing
- WebSocket move flow
- open-world bootstrap
- viewer-scoped snapshots
- account-based rejoin semantics
- remote inspect rejection
