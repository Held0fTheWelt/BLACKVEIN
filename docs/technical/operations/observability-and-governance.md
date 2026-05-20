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

1. Client calls `POST /api/v1/game/player-sessions/<run_id>/turns` (trace id from header or generated).
2. Backend forwards `X-WoS-Trace-Id` on `POST /api/story/sessions/.../turns` (and related story GETs).
3. World-Engine middleware binds the same trace to the request.
4. `StoryRuntimeManager.execute_turn` passes `trace_id` into `RuntimeTurnGraphExecutor.run`.
5. LangGraph packaging attaches **`repro_metadata`** (including `trace_id`) under `graph_diagnostics` on the turn payload returned to clients and stored in session diagnostics.

### Partial / out-of-scope in M11

- **Standalone MCP operator tools** may still mint their own trace ids when they do not receive a caller-supplied id; tightening that path is a follow-up (see gate review).
- **In-process transitional backend simulation** uses contextvar trace id where Flask context exists; it is not mounted as a live session API.

## LLM-as-a-Judge vs deterministic gates

- Rubric source of truth: `docs/llm-as-a-judge/LLM-as-a-Judge Definition Table - Judges.csv`, mirrored structurally in `ai_stack/langfuse/langfuse_evaluator_catalog.py` for MCP and CI.
- Categorical judges are **qualitative-only**; they must not override ADR-0033 commit semantics, actor-lane gates, mock/fallback gates, or contract scores surfaced as numeric gates on traces.
- MCP Langfuse helpers attach **interpretation** (`llm_judge_interpretation`, severity bands, suggested repair areas) and flag **missing judge rows** as evaluator-coverage gaps—not runtime failures.
- Preferred Langfuse attachment context for live judges: `Observation Type = GENERATION`, `Observation Name = story.model.generation`, environment supplied by the runtime (`staging`, `live`, or the configured deployment value), trace name `world-engine.session.create` (opening) or `world-engine.turn.execute` (interactive turns), with `backend.turn.execute` still valid as the backend root on the same distributed trace when scores were recorded there.

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

## Langfuse runtime configuration

Langfuse operational truth is backend-managed. The runtime reads the single
`observability_configs` row keyed by `service_id="langfuse"` and active
`observability_credentials` rows keyed by `service_id` + `secret_name`
(`public_key`, `secret_key`). The Admin Tool connection test and automated
backend integration coverage use `test_observability_connection()` /
`verify_langfuse_runtime_connectivity()` so the probe exercises the same
backend-stored config and credential path as production tracing.

Direct trace creation against Langfuse Cloud belongs only in explicitly named
live-cloud tests, and even those must use backend-stored credentials rather
than environment-only or legacy model fields.

### Langfuse observation tree policy

The Langfuse root trace is still controlled by the backend `is_enabled`,
credential, and `sample_rate` settings. The optional child-observation tree is
controlled separately through `enabled_observation_trees` on the same
backend-managed `observability_configs` row.

Operators change this policy in Administration Tool → Observability Settings.
The page reads `observation_tree_catalog` from
`GET /api/v1/admin/observability/status`, renders the backend catalog, and saves
the selected tree ids through `POST /api/v1/admin/observability/update`.

- `[]` means root trace only.
- `["minimal"]` is the default compact path summary.
- Selecting all catalog entries restores the full Langfuse child-observation tree
  including graph phases, model I/O, retrieval, runtime aspects, scene
  projection, narrator spans, deterministic scores, and evidence probes.

Connection-test traces named `world_of_shadows.connection_test` are health
probes and remain intentionally flat; they are not evidence that session
runtime trees were suppressed.

## Retrieval observability

`retrieval` dict and `repro_metadata` include:

- `domain`, `profile`, `status`, `hit_count` (and source paths in diagnostics payloads for governance review).

Capability invocations when using `CapabilityRegistry` continue to populate `capability_audit` on the graph diagnostics.

## Runtime aspect and hierarchical memory observability

The World-Engine turn path emits a backend-owned `turn_aspect_ledger` for runtime intelligence. The ledger is the authority for beat, capability, narrator/NPC authority, information disclosure, visible-origin, commit, and hierarchical-memory proof. The frontend may display backend-provided fields but must not infer correctness from prose or card shape.

Runtime governance is module-policy-driven:

- Module content provides `runtime_intelligence` / `runtime_governance_policy` through `ModuleRuntimePolicy`; generic runtime code does not branch on God of Carnage actor names, locations, phase names, or beat ids.
- Action-resolution short-path eligibility, visible-projection hard-failure behavior, missing/forbidden capability behavior, and continuity hooks are policy values.
- Projection failures that lose required beat/narrator/capability evidence block or recover before canonical commit according to policy; they must not be papered over by frontend card folding.
- The ledger records `committed_result` / commit status so degraded, recoverable, rejected, and committed outcomes remain distinguishable in backend/world-engine/Langfuse data.

Information disclosure is policy-driven runtime evidence:

- Module content provides `information_disclosure_policy.yaml`; runtime code consumes normalized disclosure units and does not use Table-B labels as production behavior switches.
- LangGraph records selected, allowed, withheld, and forbidden unit ids before generation.
- Validation reads structured `disclosure_events` when present and checks selected unit ids, stage/mode, and visible-unit budget.
- Langfuse/MCP expose target-selected, budget-pass, premature-reveal-absent, and contract-pass signals. These are structural contract scores, not story-prose quality ratings.

Hierarchical memory is a bounded projection of canonical committed truth:

- Module content provides `memory_policy` through `ModuleRuntimePolicy`; runtime code stays module-neutral.
- Writes are allowed only from canonical committed turns unless policy explicitly permits otherwise.
- Recoverable or rejected turns may record guard evidence, but they do not create memory truth.
- Stored memory items are JSON-safe summaries with evidence references; raw prompts, secrets, full RAG payloads, and raw player input are excluded.
- Projected memory context is bounded before it enters LangGraph model context.
- Current God of Carnage policy enables session-retained `turn`, `session`, `actor`, and `module` tiers; `long_term` is disabled until a durable cross-session store exists.

Langfuse runtime aspect spans include:

- `story.aspect.input`
- `story.beat.state`
- `story.beat.select`
- `story.beat.realize`
- `story.authority.narrator`
- `story.authority.npc`
- `story.capability.select`
- `story.capability.realize`
- `story.information_disclosure.select`
- `story.information_disclosure.validate`
- `story.sensory_context.target`
- `story.sensory_context.validate`
- `story.npc_agency.plan`
- `story.npc_agency.realize`
- `story.visible.project`
- `story.commit.apply`
- `story.turn.aspect_summary`

Langfuse memory spans include:

- `story.memory.write`
- `story.memory.project`

Deterministic runtime aspect scores include:

- `turn_aspect_ledger_present`
- `beat_selected`
- `beat_realized`
- `beat_realization_visible`
- `beat_transition_valid`
- `beat_contract_pass`
- `narrator_authority_contract_present`
- `narrator_required_when_expected`
- `narrator_owns_consequence`
- `npc_authority_contract_present`
- `npc_takeover_absent`
- `npc_policy_realized`
- `npc_consequence_takeover_absent`
- `player_agency_violation_absent`
- `capability_selection_present`
- `capability_selection_valid`
- `forbidden_capability_absent`
- `selected_capabilities_realized`
- `dramatic_capability_contract_pass`
- `information_disclosure_policy_present`
- `information_disclosure_target_selected`
- `information_disclosure_budget_pass`
- `information_disclosure_premature_reveal_absent`
- `information_disclosure_contract_pass`
- `sensory_context_target_present`
- `sensory_context_contract_pass`
- `sensory_context_required_layers_realized`
- `sensory_context_source_refs_valid`
- `npc_agency_plan_present`
- `npc_independent_planning_used`
- `npc_required_initiatives_realized`
- `multi_npc_initiative_realized`
- `npc_carry_forward_closed`
- `npc_forbidden_actor_absent`
- `visible_block_origin_present`
- `required_visible_origin_preserved`
- `visible_projection_contract_pass`

Deterministic memory scores include:

- `hierarchical_memory_present`
- `memory_policy_applied`
- `memory_write_from_committed_turn`
- `memory_context_bounded`
- `hierarchical_memory_contract_pass`

These scores are contract gates, not LLM-as-a-Judge ratings. Missing provider credentials, fallback generation, or absent committed-turn evidence must remain degraded/partial rather than being counted as healthy memory behavior.

## MCP audit expectations

- Backend MCP enrichment paths remain governed by existing MCP audit fields and session capability audit extraction from World-Engine diagnostics.
- Tool permission denials should surface as structured errors or audit rows, not silent no-ops.

## Governance surfaces and responsibilities

| Surface | Responsibility |
|---------|------------------|
| `POST /api/v1/game/player-sessions/<run_id>/turns` | Returns `trace_id`, World-Engine turn payload, diagnostics; `502` with `failure_class: world_engine_unreachable` when bridge fails. |
| `GET /api/v1/admin/ai-stack/session-evidence/<session_id>` | Moderator/admin (game operations feature): aggregated World-Engine story-session evidence bundle. |
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

Session evidence is keyed by the World-Engine story-session id and is fetched
through the backend `game_service` bridge. The bundle does not inspect removed
backend runtime sessions; a World-Engine 404 returns
`world_engine_story_session_not_found`.

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
