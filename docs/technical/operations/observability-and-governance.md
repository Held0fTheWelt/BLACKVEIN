# Observability and Governance in World of Shadows

This document is the canonical reference for **cross-stack observability**, **auditability**, and **governance** across the unified AI stack (backend, World-Engine authoritative story runtime, `ai_stack`, Writers-Room, improvement loop, MCP). It complements milestone-specific architecture notes (RAG, LangGraph, MCP, improvement loop) by defining how traces, audits, and human-review surfaces must behave together.

## Authority split (unchanged)

- **World-Engine** hosts the authoritative story runtime execution path.
- **Backend / administration-tool** own policy, review, publishing, and governance visibility.
- **AI outputs** remain non-authoritative for commit, review approval, and publishing decisions.

## Trace propagation model

### Identifier

- **`X-WoS-Trace-Id`**: UUID (or opaque string) carried on HTTP requests and echoed on HTTP responses where the stack controls the server.
- **Backend (Flask `api_v1`)**: `before_request` calls `ensure_trace_id()` from the incoming header or generates a new id; `after_request` sets the response header.
- **World-Engine (FastAPI)**: middleware clears a per-request contextvar, applies the same `ensure_trace_id` semantics, attaches `request.state.trace_id`, and sets the response header.
- **Internal play/story bridge**: `game_service._request(..., internal=True, trace_id=...)` forwards `X-WoS-Trace-Id` on calls to World-Engine story endpoints.

### Canonical end-to-end path (story turn via backend proxy)

1. Client calls `POST /api/v1/sessions/<id>/turns` (trace id from header or generated).
2. Backend forwards `X-WoS-Trace-Id` on `POST /api/story/sessions/.../turns` (and related story GETs).
3. World-Engine middleware binds the same trace to the request.
4. `StoryRuntimeManager.execute_turn` passes `trace_id` into `RuntimeTurnGraphExecutor.run`.
5. LangGraph packaging attaches **`repro_metadata`** (including `trace_id`) under `graph_diagnostics` on the turn payload returned to clients and stored in session diagnostics.

### Partial / out-of-scope in M11

- **Standalone MCP operator tools** may still mint their own trace ids when they do not receive a caller-supplied id; tightening that path is a follow-up (see gate review).
- **In-process legacy backend turn execution** (non-proxy) uses contextvar trace id where Flask context exists; it is explicitly not the canonical authoritative runtime.

## Event and audit model

### Structured audit logger (`wos.audit`, backend)

JSON lines (dict messages) for:

- `api.endpoint` — session-scoped HTTP (existing).
- `turn.request` / `turn.execute` / `mcp.tool_call` (existing).
- **`world_engine.bridge`** — backend ↔ World-Engine story operations (`operation`, `outcome`, optional `failure_class`, `status_code`, session ids).
- **`workflow.run`** — Writers-Room and improvement boundaries (`workflow`, `actor_id`, `resource_id`, `outcome`).

Rules:

- Do not log raw secrets, tokens, or full operator prompts unless a dedicated, access-controlled export requires it.
- Prefer **hashes and lengths** for free-text inputs at trust boundaries (World-Engine story audit uses hashed player input).

### World-Engine audit logger (`wos.world_engine.audit`)

JSON lines for:

- `story.turn.execute` — per turn, with `player_input_hash`, `player_input_length`, `graph_error_count`, `outcome`.
- `story.runtime.failure` — uncaught graph execution errors before re-raise.

## Correlation boundaries

| Boundary | Mechanism |
|----------|-----------|
| Browser / tool → Backend | `X-WoS-Trace-Id` header |
| Backend → World-Engine (internal) | Same header on httpx requests |
| Graph internals | `trace_id` on `RuntimeTurnState` → `repro_metadata` |
| MCP service token session APIs | Trace on Flask `g` + response fields where applicable |

## Model-call observability

Captured in **`generation`** summaries on the runtime turn state and mirrored under `model_route` / `graph_diagnostics`:

- `attempted`, `success`, `error` (sanitized string), `fallback_used`, `metadata` from adapters (must not include secrets).

## Retrieval observability

`retrieval` dict and `repro_metadata` include:

- `domain`, `profile`, `status`, `hit_count` (and source paths in diagnostics payloads for governance review).

Capability invocations when using `CapabilityRegistry` continue to populate `capability_audit` on the graph diagnostics.

## MCP audit expectations

- Backend MCP enrichment paths remain governed by existing MCP audit fields and session capability audit extraction from World-Engine diagnostics.
- Tool permission denials should surface as structured errors or audit rows, not silent no-ops.

## Governance surfaces and responsibilities

| Surface | Responsibility |
|---------|------------------|
| `GET /api/v1/sessions/<id>/capability-audit` | MCP operator: capability rows from World-Engine turn diagnostics; includes `trace_id`; surfaces `bridge_error` if World-Engine unreachable. |
| `POST /api/v1/sessions/<id>/turns` | Returns `trace_id`, World-Engine turn payload, diagnostics; `502` with `failure_class: world_engine_unreachable` when bridge fails. |
| `GET /api/v1/admin/ai-stack/session-evidence/<session_id>` | Moderator/admin (game operations feature): aggregated backend + World-Engine evidence bundle. |
| `GET /api/v1/admin/ai-stack/improvement-packages` | Same audience: improvement recommendation packages listing. |
| `GET /api/v1/admin/ai-stack/release-readiness` | Same audience: honest readiness summary (`ready`/`partial`) per area; story-runtime cross-layer remains `partial` in this aggregate (use session-evidence after real turns); Writers-Room LangGraph depth is explicitly `partial` (seed stub). |
| `GET /api/v1/admin/system-diagnosis` | Moderator/admin with feature `manage.system_diagnosis`: aggregated operator diagnosis (backend `/api/v1/health`, DB, play-service config and internal `/api/health` + `/api/health/ready`, published experiences feed, `build_release_readiness_report`); 5 s TTL cache, `?refresh=1` forces refresh. |
| `GET`/`POST` `/api/v1/admin/play-service-control`, `POST` `.../test`, `POST` `.../apply` | **Admin** with feature `manage.play_service_control`: persisted **desired** state in `site_settings`, **observed** snapshot from canonical `app.config` + bounded play-service health/ready probes; apply updates in-process config only (no shell/Docker/systemd); secrets never returned. |
| Administration-tool **`/manage/ai-stack/governance`** | UI shell calling the above APIs via the existing proxy (JWT in browser). |
| Administration-tool **`/manage/diagnosis`** | Loads only `GET /api/v1/admin/system-diagnosis` through the proxy (no direct play-service calls from the browser). **Observed** health only; use **`/manage/play-service-control`** for desired state and apply. |
| Administration-tool **`/manage/play-service-control`** | Play-Service **control** UI: save/test/apply via admin APIs above (proxy); complements diagnosis (control ≠ diagnosis). |
| Activity log | `ai_stack` / `session_evidence_view` entries when evidence API is used. |

### Play-Service control: known implementation limits

- **Modes (`local` / `docker` / `remote`)** are **operator labels** on top of the **same** backend routing model: one **public URL + internal URL** pair in `app.config`, not separate transport stacks per mode.
- **Timeouts**: upstream checks use explicit bounds (e.g. httpx client timeout) at execution points; there is **no** single hard **end-to-end 250 ms SLA** for all local validation in one wall-clock envelope.
- **`allow_new_sessions`**: enforced at the **primary** session-creation entry points in `game_service` (e.g. new play runs and new story sessions). Other code paths that call the play service are **not** universally gated by this flag yet.

## Secrets and privacy

- Never log API keys, JWTs, or shared play-service secrets.
- Player text: hash at World-Engine audit boundary; diagnostics may still contain `raw_input` for **authorized** internal diagnostics endpoints—treat as sensitive and restrict by auth/feature flags.

## Release-readiness criteria (summary)

See `docs/reports/AI_STACK_RELEASE_READINESS_CHECKLIST.md` for executable checks. At minimum before calling the stack production-grade:

- Trace continuity on the canonical story path is verifiable end-to-end.
- Governance APIs return real underlying diagnostics, not placeholders.
- Failure modes (bridge down, graph error lists, model failure) are visible in API payloads or audit streams.
- Repro metadata identifies graph version, stack semantic version, routing/retrieval profile, and host version hints.

Readiness reporting must remain honest:

- Missing repaired-path evidence yields `partial`, not silent success.
- Known partiality (for example local JSON storage, unsigned audit retention) is explicitly listed in readiness payloads.
- Writers-Room **`writers_room_retrieval_evidence_surface`** treats only `moderate`/`strong` retrieval tiers as `ready`; `none`/`weak` remain `partial` with an explicit `evidence_posture`.
- Improvement loop: **`improvement_retrieval_evidence_backing`** can be `partial` when `evidence_strength_map.retrieval_context` is `none` even if comparison + `governance_review_bundle_id` exist (governance artifacts without retrieval-backed substance).
- `GET /admin/ai-stack/release-readiness` includes **`decision_support`** (cross-cutting booleans and latest artifact hints), optional **`known_environment_sensitivities`**, and per-area **`evidence_posture`** strings—still aggregate-only for story runtime until session evidence is fetched.

### Session evidence bundle (`build_session_evidence_bundle`)

Moderator/admin session evidence includes **`execution_truth`**:

- **`committed_narrative_surface`**: World-Engine `committed_state` and `authoritative_history_tail` (no graph envelope)—authoritative committed narrative summary (`narrative_commit`).
- **`last_turn_graph_mode`**: `execution_health`, `fallback_path_taken`, `graph_path_summary`, `adapter_invocation_mode` from the last diagnostic turn’s `graph`.
- **`retrieval_influence`**: normalized tier/strength via `build_retrieval_trace` from the last turn’s `retrieval` payload.
- **`tool_influence`**: trimmed `capability_audit` entries and **`material_influence`** when material capabilities (`wos.context_pack.build`, `wos.transcript.read`, `wos.review_bundle.build`) appear with non-error outcomes.

**`degraded_path_signals`** lists active degradation markers (for example `fallback_path_taken`, `execution_health:model_fallback`); avoid treating empty diagnostic history as “healthy.”

**`cross_layer_classifiers`** summarizes the same bundle for operators: committed-vs-diagnostic authority note, whether the last diagnostic turn exists, graph execution posture (`primary_graph_path` vs fallback/degraded vs `no_turn_diagnostics`), runtime retrieval tier (or `no_turn_diagnostics` when no turn row), tool influence flag, bridge reachability, and active degradation markers.

**`reproducibility_metadata`** merges graph `repro_metadata` with last-turn retrieval fingerprint fields (`retrieval_index_version`, `retrieval_corpus_fingerprint`, `retrieval_route`) when present.

Persisted Writers-Room reviews add **`repaired_layer_signals.writers_room`** (including **`review_readiness`**: whether retrieval tier is sufficient for graded review vs seed-stub orchestration note).

## Version constants

- **`ai_stack.version`**: `AI_STACK_SEMANTIC_VERSION`, `RUNTIME_TURN_GRAPH_VERSION` (exported from `ai_stack` package).
- **World-Engine** contributes `world_engine_app_version` via `host_versions` into `repro_metadata`.
