# Canonical Runtime Contract (Nested Run V1)

**Status:** Gate Block 1 — binding for World Engine (play service) producers and Backend consumers.

**Version:** V1 (`nested-run-v1`)

## Principles

1. **Single source of truth for run identity:** The authoritative run id lives only under the nested `run` object as `run.id`. The backend **must not** silently accept a parallel top-level `run_id` on create/detail payloads unless it is absent or **exactly equal** to `run.id`; otherwise the response is rejected as contradictory.
2. **No ambiguous dual shapes:** Deprecated flat-only run envelopes (e.g. create responses with only top-level `run_id` and no `run`) are **not** supported. Consumers parse V1 only.
3. **Explicit validation:** Malformed or contradictory payloads surface as `GameServiceError` (HTTP status from upstream when applicable, else 502) — no best-effort merging of flat vs nested fields.

## Producer (World Engine HTTP)

### `POST /api/runs` — Create run

**Response (V1):**

| Field   | Type   | Required | Description |
|---------|--------|----------|-------------|
| `run`   | object | yes      | Serialized `RuntimeInstance` (JSON mode). **Authoritative** `id` at `run.id`. |
| `store` | object | yes      | Run store descriptor from `RunStore.describe()`. |
| `hint`  | string | yes      | Human-oriented integration hint (non-authoritative). |

**Deprecated / removed:** Top-level `run_id` on this response (use `run.id` only).

### `GET /api/runs/{run_id}` and `GET /api/internal/runs/{run_id}` — Run details

**Response (V1):**

| Field              | Type   | Required | Description |
|--------------------|--------|----------|-------------|
| `run`              | object | yes      | Full run state; `run.id` must equal the path `run_id`. |
| `template_source`  | string | yes      | e.g. `builtin`, `backend_published`. |
| `template`         | object | yes      | Subset: `id`, `title`, `kind`, `join_policy`, `min_humans_to_start`. |
| `store`            | object | yes      | Store descriptor. |
| `lobby`            | object/null | yes | Lobby payload from the runtime engine. May be `null` when no lobby projection is available for the current run state. |

**Not used:** Top-level `run_id` for details (identity is only `run.id`).

### `GET /api/runs/{run_id}/transcript` (and internal mirror)

**Response (transcript envelope — distinct contract):**

| Field     | Type   | Required |
|-----------|--------|----------|
| `run_id`  | string | yes      | Run the transcript belongs to (path-aligned). |
| `entries` | array  | yes      | Transcript entries. |

This envelope is **not** a duplicate of run details; it intentionally exposes `run_id` at the top level for the transcript resource only.

### Terminate run

**Preferred consumer path (Backend):** `POST /api/internal/runs/{run_id}/terminate` with JSON body (internal API key).

**Request body:**

| Field                 | Type   | Required | Description |
|-----------------------|--------|----------|-------------|
| `actor_display_name`  | string | no       | Audit / ops label (empty string allowed). |
| `reason`              | string | no       | Free-text reason (empty string allowed). |

**Response (terminate envelope V1):**

| Field                 | Type    | Required |
|-----------------------|---------|----------|
| `run_id`              | string  | yes      | Must equal path `run_id`. |
| `terminated`          | boolean | yes      | Must be JSON `true` when termination succeeded. |
| `template_id`         | string  | yes      | Template id of the removed run. |
| `actor_display_name`  | string  | yes      | Echo of request (may be empty). |
| `reason`              | string  | yes      | Echo of request (may be empty). |

**Legacy alias:** `DELETE /api/runs/{run_id}` (internal key) returns the same terminate envelope V1 (with default empty audit fields). Prefer `POST .../terminate` for structured audit.

**Deprecated:** Using a fictional `status: "terminated"` (or similar) as the sole success signal without `terminated: true` — removed in favor of the boolean above.

## Consumer (Backend `game_service`)

- **create_run:** Validates V1 create shape; rejects contradictory `run_id` vs `run.id`.
- **get_run_details:** Validates nested run and required sibling keys; optionally verifies `run.id` matches requested id.
- **terminate_run:** Calls `POST /api/internal/runs/{id}/terminate` with JSON body; validates terminate envelope V1 (strict `terminated === true`).

## Rationale (consolidation)

Earlier drift allowed the backend to expect flat `run_id` on create/details and `status` on terminate while the engine emitted nested `run` and `terminated`/`template_id`. That silent mismatch caused fragile clients and unclear ownership of identity. V1 picks **nested run** for create/details and a **dedicated terminate envelope** for teardown (the run no longer exists, so a nested `run` object is not returned).

## MCP scope note

For this run-lifecycle boundary (`/api/runs*`, join-context, transcript, terminate), MCP is not part of the direct execution chain. MCP-backed endpoints exist on backend operator/session surfaces and are documented separately in `backend_runtime_classification.md`.
