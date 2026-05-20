# Live Runtime Empty Session / Missing Narrator Opening Audit

**Repository inspected:** extracted upload at `/mnt/data/repo_frontend` from `frontend.zip`.

**Audit mode:** evidence-only. No production code was changed. No tests were added or rewritten.

**Limitations:** This report is based on repository source evidence and static route tracing. It does not include live container logs from the user's machine, database rows, Langfuse UI traces, or actual `curl` response bodies from a running stack. Any runtime-only conclusion is explicitly marked `UNKNOWN_REQUIRES_VERIFICATION`.

---

## 1. Executive Verdict

**Strongest truthful classification:** `backend-world-engine-boundary-broken`.

The source shows a real intended path from frontend `/play/start` to backend `/api/v1/game/player-sessions`, then to world-engine `/api/runs`, then to world-engine `/api/story/sessions`, then to `StoryRuntimeManager.create_session`. However, the handoff between backend and world-engine story runtime drops the actor-lane/runtime-profile ownership fields that were produced during `/api/runs` creation.

The specific break is:

```text
world-engine /api/runs resolves runtime_profile_id=god_of_carnage_solo
→ produces selected_player_role, human_actor_id, npc_actor_ids, actor_lanes
→ backend parses the run only as a generic run envelope
→ backend recompiles the canonical content module
→ backend sends only the content compiler runtime_projection to /api/story/sessions
→ StoryRuntimeManager expects actor ownership inside runtime_projection
→ actor_lane_context becomes None
```

Evidence:

- Frontend sends `runtime_profile_id` and `selected_player_role`, but not `content_module_id`, in `frontend/app/routes_play.py::play_create`, lines 841-845.
- World-engine `/api/runs` resolves profile and actor ownership, then returns `content_module_id`, `runtime_profile_id`, `runtime_module_id`, `selected_player_role`, `human_actor_id`, `npc_actor_ids`, and `actor_lanes`, in `world-engine/app/api/http.py::create_run`, lines 165-185 and 224-233.
- Backend `_parse_create_run_v1` validates only `run`, `store`, and `hint`; it does not preserve the top-level actor ownership fields from the create-run response, in `backend/app/services/game_service.py`, lines 40-57.
- Backend `_ensure_player_session` calls `_compile_player_module(resolved_template_id)` and then calls `create_story_session` with only that compiled `runtime_projection`, in `backend/app/api/v1/game_routes.py`, lines 388-398.
- The compiler `RuntimeProjection` model contains content fields only; it has `module_id`, `start_scene_id`, `scenes`, `characters`, etc., but no `selected_player_role`, `human_actor_id`, `npc_actor_ids`, `actor_lanes`, `runtime_profile_id`, or `runtime_module_id`, in `backend/app/content/compiler/models.py`, lines 9-22.
- `StoryRuntimeManager._extract_actor_lane_context` states that actor ownership must be in `session.runtime_projection`, and returns `None` if `human_actor_id` is absent, in `world-engine/app/story_runtime/manager.py`, lines 1519-1542.

There is a second important truth issue: for `god_of_carnage`, the session opening currently **does not use LangGraph/LangChain/model generation**. It bypasses `RuntimeTurnGraphExecutor` and builds deterministic LDSS output directly in `StoryRuntimeManager._execute_opening_locked`, lines 2150-2190. That can create a generic narrator block, but it is not the live AI/runtime graph opening described in the expected behavior.

The code-supported explanation for an actually **empty** shell is one of these paths:

1. The running service is using a `StoryRuntimeManager` created with injected registry/adapters, where `_skip_graph_opening_on_create` is true and `create_session` returns state-only. Evidence: `world-engine/app/story_runtime/manager.py`, lines 1095-1097 and 2277-2278.
2. The backend reuses a persisted player-session binding whose world-engine story session has no diagnostics/story window entries. Evidence: `_ensure_player_session` reuses an existing slot if `runtime_session_id`, `module_id`, and `slot_template_id` exist, then returns state from `get_story_state`, in `backend/app/api/v1/game_routes.py`, lines 364-381.
3. The opening was created but not present in `story_window.entries`; frontend renders the explicit placeholder when `story_entries` is empty. Evidence: `frontend/templates/session_shell.html`, lines 51-135, and `frontend/static/play_shell.js`, lines 271-282.

A fresh production session created through `world-engine/app/main.py` should not be state-only by construction because `StoryRuntimeManager` is instantiated without injected registry/adapters, in `world-engine/app/main.py`, lines 64-67. Therefore, if a fresh production session is still empty, the live run must be verified with the commands in section 13 to determine whether the active service is using the production app, reusing persisted state-only sessions, failing governance, or returning an opening that the backend/frontend drops.

---

## 2. Actual Dataflow Found

### Session creation path

```text
frontend/templates/session_start.html form
→ frontend/app/routes_play.py::play_create
→ backend POST /api/v1/game/player-sessions
→ backend/app/api/v1/game_routes.py::game_player_session_create
→ backend/app/services/game_service.py::create_run
→ world-engine POST /api/runs
→ world-engine/app/api/http.py::create_run
→ backend _ensure_player_session
→ backend _compile_player_module
→ backend/app/services/game_service.py::create_story_session
→ world-engine POST /api/story/sessions
→ world-engine/app/api/http.py::create_story_session
→ StoryRuntimeManager.create_session
→ StoryRuntimeManager._execute_opening_locked unless _skip_graph_opening_on_create
→ backend get_story_state
→ backend _player_session_bundle
→ frontend redirect /play/<run_id>
→ frontend play_shell fetches /api/v1/game/player-sessions/<run_id>
→ frontend renders story_entries or empty placeholder
```

Evidence:

- Launcher form posts to `frontend.play_create`; role selector contains only Annette and Alain, in `frontend/templates/session_start.html`, lines 6-21.
- Role selector is shown only for `god_of_carnage_solo`, in `frontend/templates/session_start.html`, lines 35-39.
- Frontend route validates role and posts to `/api/v1/game/player-sessions`, in `frontend/app/routes_play.py`, lines 820-853.
- Backend route receives `/game/player-sessions`, creates play run if needed, and calls `_ensure_player_session`, in `backend/app/api/v1/game_routes.py`, lines 559-596.
- Backend service calls world-engine `/api/runs`, in `backend/app/services/game_service.py`, lines 231-257.
- Backend `_ensure_player_session` compiles a content module and calls `/api/story/sessions`, in `backend/app/api/v1/game_routes.py`, lines 388-398.
- Backend service calls world-engine `/api/story/sessions`, in `backend/app/services/game_service.py`, lines 340-367.
- World-engine route calls `manager.create_session`, in `world-engine/app/api/http.py`, lines 450-523.
- `StoryRuntimeManager.create_session` creates the session, persists it, and then executes opening unless `_skip_graph_opening_on_create` is true, in `world-engine/app/story_runtime/manager.py`, lines 2245-2287.
- Frontend `play_create` uses only the returned `run_id` and redirects to `/play/<run_id>`, in `frontend/app/routes_play.py`, lines 881-885.
- Frontend `play_shell` fetches `/api/v1/game/player-sessions/<session_id>`, normalizes `story_entries`, and renders `session_shell.html`, in `frontend/app/routes_play.py`, lines 888-956.

### Player turn path

```text
frontend/static/play_shell.js submit handler
→ frontend/app/routes_play.py::play_execute
→ backend POST /api/v1/game/player-sessions/<run_id>/turns
→ backend/app/api/v1/game_routes.py::game_player_session_turn
→ backend/app/services/game_service.py::execute_story_turn
→ world-engine POST /api/story/sessions/<session_id>/turns
→ world-engine/app/api/http.py::execute_story_turn
→ StoryRuntimeManager.execute_turn
→ RuntimeTurnGraphExecutor.run
→ LangChain bridge / adapter if provider registered
→ validation seam
→ commit seam
→ visible render
→ package output
→ StoryRuntimeManager._finalize_committed_turn
→ world-engine state
→ backend _player_session_bundle
→ frontend JSON response
→ frontend renderEntries
```

Evidence:

- Frontend JS submits `{player_input}` to the form action, in `frontend/static/play_shell.js`, lines 393-408.
- Frontend route posts to backend `/api/v1/game/player-sessions/{run_id}/turns`, in `frontend/app/routes_play.py`, lines 790-805.
- Backend turn route calls `execute_story_turn_in_engine`, then fetches state and bundles it, in `backend/app/api/v1/game_routes.py`, lines 613-674.
- Backend service calls world-engine `/api/story/sessions/{session_id}/turns`, in `backend/app/services/game_service.py`, lines 370-387.
- World-engine route calls `manager.execute_turn`, in `world-engine/app/api/http.py`, lines 540-627.
- `StoryRuntimeManager._execute_turn_locked` calls `self.turn_graph.run(...)` and passes `actor_lane_context=self._extract_actor_lane_context(session)`, in `world-engine/app/story_runtime/manager.py`, lines 2318-2365.
- `RuntimeTurnGraphExecutor` defines the graph nodes from input interpretation through retrieval, model invocation, validation, commit, render, and package output, in `ai_stack/langgraph/langgraph_runtime_executor.py`, lines 999-1038.
- The graph invokes the compiled LangGraph with `self._graph.invoke(initial_state)`, in `ai_stack/langgraph/langgraph_runtime_executor.py`, line 1156.
- The model invocation uses `invoke_runtime_adapter_with_langchain` only if a provider adapter is registered, in `ai_stack/langgraph/langgraph_runtime_executor.py`, lines 1885-1920; otherwise it records `adapter_not_registered:<provider>` and does not call LangChain, in lines 1950-1958.
- The LangChain bridge calls `adapter.generate(...)` and parses the structured output, in `ai_stack/langchain/bridges.py`, lines 241-323.

---

## 3. Expected Dataflow

### Session creation with narrator opening

```text
POST /api/v1/game/player-sessions
payload includes runtime_profile_id=god_of_carnage_solo and selected_player_role
→ backend creates /api/runs and preserves profile/actor ownership
→ backend creates /api/story/sessions with runtime_profile_id, content_module_id, runtime_module_id, selected_player_role, human_actor_id, npc_actor_ids, actor_lanes
→ world-engine creates StorySession with complete runtime projection
→ opening generation runs through the intended live narrator/LDSS/graph contract
→ opening is validated
→ opening is committed
→ opening is present in story_window.entries
→ backend returns story_entries containing turn 0 opening
→ frontend play shell displays non-empty opening
```

### First visible play shell state

The initial `/play/<run_id>` page must show at least one runtime entry with `kind=opening`, `turn_number=0`, and non-empty narrator/dramatic text. If no opening exists, the shell must not present the session as live-ready.

### Live player turn

```text
player input
→ backend player-session turn endpoint
→ world-engine story turn endpoint
→ StoryRuntimeManager.execute_turn
→ RuntimeTurnGraphExecutor.run
→ LangChain/model adapter when live AI route is enabled
→ validation seam
→ commit seam
→ visible output render
→ returned story_entries include player turn + committed NPC/narrator response
```

### Diagnostics/admin visibility

Diagnostics must expose why output is missing. Empty output must not be represented as live success. The minimum fields needed are: `trace_id`, `story_session_id`, `run_id`, `turn_number`, `runtime_profile_id`, `content_module_id`, `runtime_module_id`, `selected_player_role`, `human_actor_id`, `npc_actor_ids`, `visible_response_source`, `quality_class`, `validation_status`, `commit_reason_code`, `degradation_signals`, `fallback_used`, provider/model, adapter, parser status, graph nodes executed.

---

## 4. Breakpoint Map

| Step | Expected | Actual | Evidence | Status |
|---|---|---|---|---|
| Frontend launch | Select GoC role and start profile | Implemented for Annette/Alain; visitor rejected before backend | `frontend/templates/session_start.html` 15-21; `frontend/app/routes_play.py` 832-845 | `implemented` |
| Frontend session payload | Send `runtime_profile_id`, `selected_player_role`, trace metadata | Sends `runtime_profile_id`, `selected_player_role`, `trace_id`; does not send `content_module_id` | `frontend/app/routes_play.py` 841-845 | `partial` |
| Backend session create route | Validate/propagate profile + actor lanes | Accepts profile fields and creates run, but later does not merge returned actor ownership into story runtime projection | `backend/app/api/v1/game_routes.py` 559-596; 388-398 | `partial` |
| Runtime profile resolution | `god_of_carnage_solo` is profile, `god_of_carnage` content | Implemented in world-engine `/api/runs` | `world-engine/app/runtime/profiles.py` 138-169; `world-engine/app/api/http.py` 178-185 | `implemented` |
| Actor ownership | selected role → human; others → NPCs | Implemented in `/api/runs` response, but lost before `/api/story/sessions` | `world-engine/app/runtime/profiles.py` 216-242; `backend/app/services/game_service.py` 40-57; `backend/app/api/v1/game_routes.py` 391-398 | `backend-world-engine-boundary-broken` |
| Content module compile | Compile `god_of_carnage` content | Mapping exists: `god_of_carnage_solo` → `god_of_carnage` | `backend/app/services/game_content_service.py` 219-249 | `implemented` |
| Story session create route | Receive complete runtime profile/content/actor state | Receives only `module_id`, content `runtime_projection`, provenance | `backend/app/services/game_service.py` 353-360; `world-engine/app/api/http.py` 494-499 | `partial` |
| Opening generation | Real narrator/LDSS/graph opening | GoC opening bypasses LangGraph/model and calls deterministic LDSS directly | `world-engine/app/story_runtime/manager.py` 2150-2190 | `opening-created-but-not-live-graph` |
| Opening validation | Reject empty/no-NPC output | GoC opening state is set `approved`/`healthy` without checking LDSS `visible_actor_response_present` in this path | `world-engine/app/story_runtime/manager.py` 2173-2189; `ai_stack/live_dramatic_scene_simulator.py` 600-617 | `false-green-risk` |
| Opening commit/package | Commit visible opening into diagnostics and story window | `_finalize_committed_turn` appends event to diagnostics/history; story window reads visible bundle | `world-engine/app/story_runtime/manager.py` 2131-2133; 368-381; 384-535 | `implemented-if-opening-event-exists` |
| Frontend opening render | Render opening if present | Renders `story_entries`; if empty, shows placeholder | `frontend/templates/session_shell.html` 51-135 | `implemented` |
| Create response opening render | Use opening returned by create-session | Frontend ignores create response content and redirects only by run id | `frontend/app/routes_play.py` 881-885 | `opening-returned-not-rendered-at-create` |
| First player turn | Reach manager execute_turn | Source path reaches manager if backend/world-engine calls succeed | `backend/app/api/v1/game_routes.py` 651-658; `world-engine/app/api/http.py` 602-627 | `implemented-by-source` |
| Runtime graph execution | Graph runs and calls model | Player turns call graph; model call depends on registered adapter | `world-engine/app/story_runtime/manager.py` 2346-2365; `ai_stack/langgraph/langgraph_runtime_executor.py` 1885-1958 | `partial-live / provider-unproven` |
| Model/provider call | Real provider adapter selected | Code calls LangChain only if adapter is registered; otherwise adapter-not-registered path | `ai_stack/langgraph/langgraph_runtime_executor.py` 1885-1920, 1950-1958 | `unproven` |
| Validation/commit | AI proposal validated before commit | Graph contains validation and commit seams | `ai_stack/langgraph/langgraph_runtime_executor.py` 2297-2309, 2404-2440 | `implemented-by-source` |
| Response render | Return committed visible output to frontend | Backend returns `story_entries` from state; JS renders them | `backend/app/api/v1/game_routes.py` 249-280; `frontend/static/play_shell.js` 415-425 | `implemented-if-state-has-entries` |

---

## 5. Defect Inventory

| Defect ID | Category | Severity | Area | Evidence paths | Symbols/routes | Current behavior | Expected behavior | Impact | Suggested repair direction | Tests/gates needed later |
|---|---:|---:|---|---|---|---|---|---|---|---|
| D-001 | `ACTOR_LANES_MISSING` | `BLOCKER` | Backend → world-engine story boundary | `backend/app/services/game_service.py` 40-57; `backend/app/api/v1/game_routes.py` 391-398; `backend/app/content/compiler/models.py` 9-22; `world-engine/app/story_runtime/manager.py` 1519-1542 | `_parse_create_run_v1`, `_ensure_player_session`, `RuntimeProjection`, `_extract_actor_lane_context` | Actor ownership produced by `/api/runs` is not merged into `/api/story/sessions` runtime projection | Story runtime session must receive selected role, human actor, NPC actors, actor lanes, runtime profile id, runtime module id, content module id | Actor-lane enforcement becomes `None`; NPC/narrator logic lacks selected-role truth | Preserve profile/actor fields from create-run and enrich story runtime projection before `create_story_session` | Gate that inspects `/api/story/sessions` payload and asserts actor fields present |
| D-002 | `NARRATOR_NOT_WIRED` / `RUNTIME_GRAPH_NOT_CALLED` | `HIGH` | Opening lifecycle | `world-engine/app/story_runtime/manager.py` 2150-2190 | `_execute_opening_locked` | GoC opening bypasses LangGraph/LangChain/model and uses deterministic LDSS | Required opening should be explicitly live, or honestly classified as deterministic LDSS bootstrap | User sees non-live/generic opening or no proof of live narrator path | Decide whether turn 0 must use graph/model or mark deterministic bootstrap explicitly and schedule live narrator after it | Gate that fails if GoC opening route never executes expected narrator/graph/model span when live mode requires it |
| D-003 | `DIAGNOSTICS_HIDE_EMPTY_OUTPUT` | `HIGH` | Opening validation/diagnostics | `world-engine/app/story_runtime/manager.py` 2173-2189; `ai_stack/live_dramatic_scene_simulator.py` 600-617 | `_execute_opening_locked`, `build_deterministic_ldss_output` | Direct GoC opening sets validation `approved` and quality `healthy` after LDSS output creation; no local check that `visible_actor_response_present` is true | Opening must fail or degrade if no visible NPC/narrator output exists | Empty or NPC-less opening can be recorded as healthy | Validate LDSS output before graph_state approval and include `visible_actor_response_present` in diagnostics | Gate with missing actor lanes must fail, not produce healthy opening |
| D-004 | `SESSION_START_STATE_ONLY` | `HIGH` | StoryRuntimeManager test/injected paths | `world-engine/app/story_runtime/manager.py` 1095-1097, 2277-2278; `world-engine/tests/test_mvp4_diagnostics_integration.py` 62-70 | `_skip_graph_opening_on_create`, `create_session` | Any manager with injected registry/adapters skips opening on create | Tests that claim opening/session start must not use state-only injected manager unless explicitly testing that mode | False confidence that create_session works while opening is disabled | Separate state-only unit tests from live-opening tests; make skip flag explicit in test name | Gate that creates manager through production app path and asserts turn-0 entry exists |
| D-005 | `OPENING_RETURNED_NOT_RENDERED` | `MEDIUM` | Frontend create flow | `frontend/app/routes_play.py` 881-885; `backend/app/api/v1/game_routes.py` 280 | `play_create`, `_player_session_bundle` | Create response may include `opening_turn`, but frontend discards all content and redirects by `run_id` | If opening is returned in create response, frontend should either render it or verify GET state contains it before showing live shell | Race/stale-state risk; create-time evidence is ignored | Keep redirect flow but assert GET state contains opening; or pass create result through shell bootstrap | Test that create response with opening but state empty does not show live-ready shell |
| D-006 | `FRONTEND_EMPTY_RENDER` / `RESPONSE_PACKAGING_EMPTY` | `HIGH` | Frontend/backend shell | `backend/app/api/v1/game_routes.py` 267-270; `frontend/templates/session_shell.html` 133-135; `frontend/static/play_shell.js` 275-278 | `_player_session_bundle`, `session_shell.html`, `renderEntries` | Backend marks `runtime_session_ready=True` and `can_execute=True` even if `story_entries` is empty; frontend displays placeholder | Empty opening must block live-ready status or surface a hard diagnostic, not a playable shell | Shell appears live but empty | Compute readiness from `story_window.entry_count > 0` for new sessions; expose empty-output reason | Gate that empty `story_entries` cannot return `can_execute=True` on new GoC session |
| D-007 | `BACKEND_WORLD_ENGINE_BOUNDARY_BROKEN` | `BLOCKER` | Backend service payload | `backend/app/services/game_service.py` 353-360, 377-380 | `create_story_session`, `execute_story_turn` | Session create sends no explicit actor state; turn execution sends only `player_input` | Story session create must carry runtime profile/actor state; turn may rely on stored session only if stored session is complete | Story runtime cannot know human/NPC lanes if create payload was thin | Enrich create payload/projection; verify stored session projection | Integration test captures outbound `/api/story/sessions` payload |
| D-008 | `LDSS_NOT_WIRED` | `MEDIUM` | Narrative streaming | `world-engine/app/story_runtime/manager.py` 2022-2051; `frontend/static/play_narrative_stream.js` 17-19, 254-279; `frontend/app/routes_play.py` 998-1009 | `_orchestrate_narrative_agent`, `detectNarratorStreamingFromResponse`, `play_execute` | World-engine turn may set `narrator_streaming`, but frontend JSON response does not include it; SSE endpoint path is `/api/story/...` on frontend origin and is not proxied by `/api/v1` proxy | If narrator streaming is part of live mode, backend/frontend must forward `narrator_streaming` and route SSE to world-engine correctly | Live narrator stream cannot start from normal player turn response | Add backend bundle surface for `narrator_streaming`; add frontend proxy or public play-service URL usage | Browser test that player turn with `narrator_streaming` opens correct EventSource URL |
| D-009 | `PROVIDER_ROUTE_DISABLED` | `HIGH` | AI stack / governed config | `world-engine/app/story_runtime/manager.py` 1279-1327; `ai_stack/langgraph/langgraph_runtime_executor.py` 1885-1958 | `_apply_runtime_components`, `_invoke_model` | Missing/invalid governed config blocks live execution; missing provider adapter skips LangChain and records adapter-not-registered | Live path must have enabled provider/model or fail clearly | Could appear as no live AI output or 503 depending path | Verify resolved runtime config and provider health in running stack | Gate that runtime config has enabled non-mock provider/model for live route, or fails closed with visible error |
| D-010 | `TEST_FALSE_GREEN` | `HIGH` | Tests | `frontend/tests/test_routes_extended.py` 367-489; `world-engine/tests/test_story_window_projection.py` 6-93; `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` 595-615 | Mock rendering tests, projection tests, structural tests | Tests prove mocked entries or source strings, not live create→opening→render | Tests must exercise real frontend→backend→world-engine path with non-empty committed opening | Green tests do not protect live runtime | Add true gate after repair; label existing tests accurately | E2E test from `/play/start` through `/play/<run_id>` with real story window |
| D-011 | `VISITOR_LEGACY_LEAK` | `LOW` | Residual local world-engine web UI | `world-engine/app/web/static/app.js` 289-293; `world-engine/app/web/templates/index.html` 26-33 | Local web bootstrap placeholders | Local demo UI still contains `char:hollywood:visitor` placeholder | Visitor must not appear in story actor, runtime actor, prompt participant, or lobby seat; cosmetic demo placeholders should also be cleaned to avoid confusion | Confusing legacy artifact; not proven to affect canonical player path | Remove/rename demo placeholders; keep canonical live path visitor-free | Static grep gate for visitor in live UI/launch paths, with explicit allowlist if needed |
| D-012 | `DOC_STALE` | `MEDIUM` | Docs/reports/tests comments | `backend/tests/test_e2e_god_of_carnage_full_lifecycle.py` 1-17; `world-engine/tests/test_mvp4_diagnostics_integration.py` 1-5 | Test docstrings | Some claims say real runtime/full lifecycle while tests use legacy in-process services or mocks | Docs/tests must describe what they actually prove | Audits get misled by green tests | Update docs after code repair; do not treat these claims as proof now | Doc drift gate comparing claims to actual covered route |

---

## 6. Actor Lane and Role Mapping Findings

### What is correct

- The frontend launcher provides only Annette and Alain as selectable roles, in `frontend/templates/session_start.html`, lines 15-21.
- The frontend route rejects missing or invalid roles for `god_of_carnage_solo`, in `frontend/app/routes_play.py`, lines 832-845.
- The runtime profile resolver treats `god_of_carnage_solo` as profile-only and binds it to `content_module_id="god_of_carnage"`, in `world-engine/app/runtime/profiles.py`, lines 138-169.
- Valid selectable roles are Annette and Alain, in `world-engine/app/runtime/profiles.py`, lines 16-19 and 172-213.
- Actor ownership maps the selected role to `human_actor_id`, all other canonical actors to `npc_actor_ids`, and `visitor_present=False`, in `world-engine/app/runtime/profiles.py`, lines 216-242.
- The canonical content actors are `veronique`, `michel`, `annette`, and `alain`, in `content/modules/god_of_carnage/characters.yaml`, lines 4-80.
- The builtin GoC solo runtime template explicitly states that `visitor` must never appear, and its roles are Annette/Alain as humans plus Véronique/Michel as NPCs, in `story_runtime_core/goc_solo_builtin_template.py`, lines 17-45, and `story_runtime_core/goc_solo_builtin_roles_rooms.py`, lines 13-54.

### What is broken

The actor ownership created by world-engine `/api/runs` is not carried into the story runtime session projection.

- `world-engine/app/api/http.py::create_run` returns actor ownership only at the top-level response, lines 224-233.
- `backend/app/services/game_service.py::_parse_create_run_v1` does not preserve or validate those top-level fields, lines 40-57.
- `backend/app/api/v1/game_routes.py::_ensure_player_session` ignores those fields and sends a freshly compiled content-only projection, lines 388-398.
- `StoryRuntimeManager._extract_actor_lane_context` returns `None` if `human_actor_id` is absent from the session runtime projection, lines 1519-1542.

**Actor model verdict:** the profile resolver respects the intended actor model, but the live story-session handoff does not reliably preserve it. The canonical player path is therefore `partial`, not proven live-correct.

### Visitor finding

No live profile-path evidence shows `visitor` being mapped as a story actor. The `/api/runs` profile response sets `visitor_present=False`. However, residual world-engine local demo UI still contains `char:hollywood:visitor` placeholders, in `world-engine/app/web/static/app.js`, lines 289-293, and `world-engine/app/web/templates/index.html`, lines 26-33. This is a legacy artifact and should not be allowed in the canonical live player path.

---

## 7. Narrator Opening Lifecycle

| Stage | Finding | Evidence | Classification |
|---|---|---|---|
| Requested by frontend | Frontend does not explicitly request an opening; it starts a session and assumes the runtime creates state | `frontend/app/routes_play.py` 841-853 | `implicit-opening-request` |
| Requested by backend | Backend creates a story session; no explicit `opening=true` contract is sent | `backend/app/services/game_service.py` 353-360 | `implicit-opening-request` |
| Generated by world-engine | Production `create_session` executes `_execute_opening_locked` unless `_skip_graph_opening_on_create` is true | `world-engine/app/story_runtime/manager.py` 2245-2287 | `opening-created-if-production-manager` |
| Generated through graph/model | GoC opening bypasses graph/model and uses deterministic LDSS | `world-engine/app/story_runtime/manager.py` 2150-2190 | `runtime-graph-not-called-for-opening` |
| Rejected/validated | GoC deterministic opening is directly marked approved/healthy | `world-engine/app/story_runtime/manager.py` 2173-2189 | `validation-bypass-risk` |
| Committed | `_finalize_committed_turn` appends event to diagnostics/history and persists | `world-engine/app/story_runtime/manager.py` 2131-2133 | `implemented-if-called` |
| Packaged | Story window reads `visible_output_bundle.gm_narration`, then generation content, then commit status | `world-engine/app/story_runtime/manager.py` 368-381 | `implemented-if-bundle-nonempty` |
| Returned to backend | `/api/story/sessions` returns `opening_turn`; backend bundle includes `opening_turn` | `world-engine/app/api/http.py` 500-522; `backend/app/api/v1/game_routes.py` 280 | `returned-to-backend` |
| Rendered by frontend | Frontend does not render create response directly; it redirects and renders only resumed `story_entries` | `frontend/app/routes_play.py` 881-885; 888-956 | `opening-returned-not-rendered-directly` |
| Empty fallback | If `story_entries` is empty, shell shows placeholder | `frontend/templates/session_shell.html` 133-135 | `empty-render-detected` |

**Opening lifecycle verdict:** `opening-created` in the default production manager path, but not via live graph/model; `state-only` in injected/test manager paths; `opening_returned_not_rendered_directly` in frontend create flow; final display depends on resumed `story_window.entries`.

---

## 8. Live Turn Lifecycle

| Stage | Finding | Evidence | Classification |
|---|---|---|---|
| Player input sent | JS sends `{player_input}` to `/play/<session_id>/execute` | `frontend/static/play_shell.js` 393-408 | `implemented` |
| Backend route receives | Frontend route posts to backend player-session turn endpoint | `frontend/app/routes_play.py` 790-805 | `implemented` |
| Backend forwards | Backend calls `execute_story_turn_in_engine` with runtime story session id | `backend/app/api/v1/game_routes.py` 625-658 | `implemented` |
| World-engine route receives | `/api/story/sessions/{session_id}/turns` calls `manager.execute_turn` | `world-engine/app/api/http.py` 602-627 | `implemented` |
| Manager executes | `StoryRuntimeManager._execute_turn_locked` calls `self.turn_graph.run` | `world-engine/app/story_runtime/manager.py` 2346-2365 | `implemented-by-source` |
| Actor context passed | Manager passes `_extract_actor_lane_context(session)` | `world-engine/app/story_runtime/manager.py` 2364 | `broken-if-projection-missing-actor-fields` |
| Graph runs | Graph node chain includes interpret, retrieve, route, invoke, validate, commit, render, package | `ai_stack/langgraph/langgraph_runtime_executor.py` 999-1038 | `implemented-by-source` |
| Model adapter called | Only if provider adapter is registered | `ai_stack/langgraph/langgraph_runtime_executor.py` 1885-1920 | `provider-unproven` |
| LangChain bridge called | Bridge calls adapter and parser | `ai_stack/langchain/bridges.py` 241-323 | `implemented-if-adapter-registered` |
| Adapter missing | Records `adapter_not_registered` and does not call LangChain | `ai_stack/langgraph/langgraph_runtime_executor.py` 1950-1958 | `fallback/degraded-risk` |
| Validation | Actor lane context passed into `run_validation_seam` only if present | `ai_stack/langgraph/langgraph_runtime_executor.py` 2297-2309 | `partial` |
| Commit/render | Commit and visible render nodes exist | `ai_stack/langgraph/langgraph_runtime_executor.py` 2404-2514 | `implemented-by-source` |
| Frontend render | JSON turn response renders returned `story_entries` | `frontend/static/play_shell.js` 415-425 | `implemented-if-response-nonempty` |

**Live turn verdict:** `partial-live`. The source path reaches `RuntimeTurnGraphExecutor` for player turns, but the live model call is unproven without runtime config/provider health, and actor-lane context is broken if the backend continues sending a content-only runtime projection.

---

## 9. Diagnostics and Degradation Findings

### What diagnostics expose

- `StoryRuntimeManager._finalize_committed_turn` constructs route/model metadata, provider/model/adapter metadata, degradation surfaces, quality class, validation status, actor summaries, LDSS envelopes, and diagnostics envelopes. Evidence: `world-engine/app/story_runtime/manager.py`, lines 1665-1807 and 2099-2113.
- `get_state` exposes `story_window.entries`, committed state, runtime projection, and last committed turn, in `world-engine/app/story_runtime/manager.py`, lines 2512-2566.
- Frontend displays degraded runtime status when entries contain degraded status fields, in `frontend/templates/session_shell.html`, lines 45-48 and 92-129.

### What diagnostics hide or weaken

- Diagnostics envelope construction exceptions are swallowed with `except Exception: pass`, in `world-engine/app/story_runtime/manager.py`, lines 2099-2115. That protects turn execution, but it also means missing diagnostics envelope cannot fail a supposedly live turn.
- The world-engine story-session create response always includes warning `session_includes_committed_turn_0_opening`, even when `opening_turn` can be `None` in `_skip_graph_opening_on_create` paths, in `world-engine/app/api/http.py`, lines 500-522, and `world-engine/app/story_runtime/manager.py`, lines 2277-2278.
- Backend `_player_session_bundle` sets `runtime_session_ready=True` and `can_execute=True` independently of `story_window.entry_count`, in `backend/app/api/v1/game_routes.py`, lines 267-270.
- The frontend placeholder is honest text, but the shell can still be interactable because `can_execute` comes from backend. Evidence: `frontend/templates/session_shell.html`, lines 133-144.

**Diagnostic truthfulness verdict:** `partial`. Diagnostics can be rich once events exist, but they do not currently guarantee that an empty opening fails the session-start contract.

---

## 10. False-Green Test Inventory

| Test | Claim | What it actually proves | Problem | Recommended action |
|---|---|---|---|---|
| `frontend/tests/test_mvp1_play_launcher.py::test_play_start_renders_role_selector_in_html` | Launcher exposes role selector | HTML includes Annette/Alain role selector using mocked backend bootstrap | Valid unit test; not a live session test | Keep as `VALID_UNIT_TEST` |
| `frontend/tests/test_mvp1_play_launcher.py::test_play_create_submits_selected_player_role_annette` | Frontend submits profile + selected role | Captured mocked backend payload contains `runtime_profile_id` and `selected_player_role` | Does not prove backend/world-engine uses those fields | Keep as unit test; add integration gate later |
| `frontend/tests/test_mvp1_play_launcher.py::test_play_create_rejects_visitor_role` | Visitor rejected | Frontend does not call backend when role is visitor | Valid frontend unit test only | Keep; add backend/world-engine visitor absence gate |
| `frontend/tests/test_routes_extended.py::test_play_shell_renders_canonical_story_entries_without_ticket_or_backend_session` | Play shell renders story entries | Fake backend returns a prebuilt opening entry | `MOCK_ONLY`; does not prove runtime creates opening | Keep as renderer unit; rename if needed |
| `frontend/tests/test_routes_extended.py::test_play_execute_json_returns_story_entries` | Turn JSON returns story entries | Fake backend returns synthetic opening/player/runtime entries | `MOCK_ONLY`; no world-engine call | Keep as frontend contract unit; add E2E |
| `frontend/tests/test_routes_extended.py::test_play_shell_transcript_includes_opening_and_returned_turns` | Transcript includes opening/turns | Fake backend supplies all entries | `MOCK_ONLY`; not proof of live path | Keep as render unit |
| `world-engine/tests/test_story_window_projection.py::test_story_window_projection_uses_committed_opening_and_player_turn` | Story window projection uses opening and turns | Manually inserts diagnostics events into a session | Valid projection unit; not creation/opening generation | Keep; add create-session gate |
| `world-engine/tests/test_mvp4_diagnostics_integration.py::*` | Diagnostics envelope in GoC sessions | Manager is created with injected registry/adapters; mocked turn graph returns mocked graph state | `_skip_graph_opening_on_create=True`; cannot prove opening | Reclassify as mocked manager diagnostics tests |
| `world-engine/tests/test_mvp3_narrative_agent_orchestration.py::*` | Narrative agent orchestration works | Uses injected manager and sample LDSS dicts | Does not prove frontend receives streaming trigger or correct SSE URL | Keep as orchestration unit; add route/browser contract |
| `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py::test_mvp04_execute_turn_includes_diagnostics_envelope` | Diagnostics envelope is wired | Reads source files and asserts strings exist | `PRESENCE_ONLY` structural proof | Replace/add runtime gate after repair |
| `backend/tests/test_e2e_god_of_carnage_full_lifecycle.py::*` | “real runtime without artificial mocking” | Uses `app.services.session_service.create_session("god_of_carnage")` and old dispatcher, not `/api/v1/game/player-sessions` → world-engine story runtime | `STALE`/`FALSE_GREEN` for current live player path | Rewrite or quarantine against current canonical route |

---

## 11. Documentation Drift

The most important drift found in source-adjacent docs/test docstrings is that tests claim to prove real/full/live behavior while using mocks, structural string checks, or legacy runtime paths.

- `backend/tests/test_e2e_god_of_carnage_full_lifecycle.py` says it verifies full session lifecycle “using the real runtime without artificial mocking,” but it uses `app.services.session_service.create_session("god_of_carnage")` and `app.runtime.turn_dispatcher.dispatch_turn`, not the frontend/backend/world-engine player-session path. Evidence: lines 1-17 and 25-57.
- `world-engine/tests/test_mvp4_diagnostics_integration.py` says it proves manager integration, but `_make_manager` creates `StoryRuntimeManager(registry=ModelRegistry(), adapters={})`, which activates `_skip_graph_opening_on_create`, and then replaces `turn_graph` with a `MagicMock`. Evidence: lines 1-5 and 62-70.
- `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py::test_mvp04_execute_turn_includes_diagnostics_envelope` explicitly uses “Structural proof” by reading source strings, then cites an integration test that itself uses mocked graph state. Evidence: lines 595-615.

**Documentation drift classification:** `false-green` / `doc-only` for live opening and live turn proof. Existing docs/tests can be useful as implementation history, but they are not evidence that the real live path produces visible story output.

---

## 12. Root Cause Hypotheses Ranked

### 1. Backend drops runtime-profile actor ownership before story-session creation

- **Evidence:** `/api/runs` returns actor ownership at top level (`world-engine/app/api/http.py`, lines 224-233); backend parser ignores it (`backend/app/services/game_service.py`, lines 40-57); backend compiles content-only projection (`backend/app/api/v1/game_routes.py`, lines 330-345 and 391-398); manager expects actor fields in projection (`world-engine/app/story_runtime/manager.py`, lines 1519-1542).
- **Confidence:** High.
- **How to verify:** Capture backend outbound JSON to `/api/story/sessions`; assert whether `runtime_projection.human_actor_id`, `npc_actor_ids`, `actor_lanes`, `selected_player_role`, `runtime_profile_id`, `runtime_module_id`, and `content_module_id` are present.
- **Likely repair direction:** Merge profile/actor ownership from create-run response into story runtime projection before calling `create_story_session`.

### 2. The GoC opening is deterministic LDSS, not a live narrator/graph/model opening

- **Evidence:** `_execute_opening_locked` has a GoC-specific branch that calls `build_deterministic_ldss_output` and does not call `self.turn_graph.run`, in `world-engine/app/story_runtime/manager.py`, lines 2150-2190.
- **Confidence:** High.
- **How to verify:** Start a GoC session and inspect opening diagnostics: `generation.metadata.adapter` should show `ldss_deterministic` if this path executed.
- **Likely repair direction:** Decide whether deterministic turn-0 bootstrap is acceptable. If the requirement is real narrator/graph/model opening, route GoC opening through the same governed graph/model path or add a clearly separate “deterministic bootstrap” state followed by a live opening turn.

### 3. Empty sessions can be created in injected/test manager mode and tests may mask it

- **Evidence:** `_skip_graph_opening_on_create` is true when registry/adapters are injected, and `create_session` returns before opening, in `world-engine/app/story_runtime/manager.py`, lines 1095-1097 and 2277-2278. Tests instantiate exactly that mode in `world-engine/tests/test_mvp4_diagnostics_integration.py`, lines 62-70.
- **Confidence:** High for tests; medium for production until runtime startup path is verified.
- **How to verify:** Check the running world-engine app construction path and runtime config status; confirm it uses `world-engine/app/main.py`, lines 64-67, not a test factory.
- **Likely repair direction:** Make state-only mode explicit and impossible to confuse with live opening tests.

### 4. Frontend ignores create-session opening and relies only on resumed story state

- **Evidence:** `play_create` redirects using only run id, in `frontend/app/routes_play.py`, lines 881-885; rendering happens after GET `/play/<run_id>`, lines 888-956.
- **Confidence:** High.
- **How to verify:** Compare backend create response `opening_turn` with subsequent GET `/api/v1/game/player-sessions/<run_id>` `story_entries`.
- **Likely repair direction:** Make frontend/backend fail if `opening_turn` exists but resumed `story_entries` are empty, or carry opening through bootstrap.

### 5. Frontend narrator streaming cannot start from current player-turn JSON

- **Evidence:** `play_narrative_stream.js` waits for `responseData.narrator_streaming`, lines 254-279, but `play_execute` JSON does not include `narrator_streaming`, lines 998-1009. SSE endpoint is `/api/story/sessions/{session_id}/stream-narrator`, not the `/api/v1` proxy, in `frontend/static/play_narrative_stream.js`, lines 17-19, while frontend proxy only handles `/api/v1/<path>`, in `frontend/app/routes.py`, lines 265-299.
- **Confidence:** High for streaming; medium for main text output because non-streamed story entries can still render.
- **How to verify:** Execute a turn that sets `narrator_streaming` in world-engine event, inspect frontend JSON response and browser network for EventSource URL.
- **Likely repair direction:** Forward streaming metadata and use a correct proxied or public play-service SSE endpoint.

### 6. Governed runtime config/provider may block model-backed live turns

- **Evidence:** Missing/invalid governed config sets `live_execution_blocked=True`, in `world-engine/app/story_runtime/manager.py`, lines 1279-1327. Model invocation calls LangChain only if provider adapter exists, in `ai_stack/langgraph/langgraph_runtime_executor.py`, lines 1885-1958.
- **Confidence:** Medium without live config/logs.
- **How to verify:** Call `/api/internal/story/runtime/config-status`, inspect provider/model route, and inspect turn diagnostics for `selected_provider`, `selected_model`, `adapter_invocation_mode`, `adapter_not_registered`, or fallback markers.
- **Likely repair direction:** Repair runtime config/provider route health and enforce non-empty live output gates.

---

## 13. Audit-Only Verification Commands

Run from repository root on a clean checkout/extracted archive.

### Source locator searches

```bash
rg -n "player-sessions|session start|create_session|start_session|story_session|StoryRuntimeManager|execute_turn|opening|narrator|initial|scene|live" frontend backend world-engine ai_stack tests docs
rg -n "god_of_carnage|god_of_carnage_solo|runtime_profile_id|content_module_id|runtime_module_id|selected_player_role|human_actor_id|npc_actor_ids|visitor" frontend backend world-engine ai_stack tests docs
rg -n "opening|initial_scene|initial beat|opening beat|narrator opening|Narrator|narrator|LDSS|live dramatic|dramatic scene" world-engine ai_stack backend tests docs
rg -n "visible|visible_response|actor_response|no_visible_actor_response|empty|fallback|degraded|mock|stub|placeholder|no-op|noop" frontend backend world-engine ai_stack tests docs
rg -n "RuntimeTurnGraphExecutor|LangGraph|LangChain|invoke_runtime_adapter_with_langchain|generate|model|provider|adapter|NPC|actor lane|proposal|commit|validation" ai_stack world-engine backend tests docs
rg -n "Backend API Unavailable|read timeout|timeout|world-engine|play-service|BACKEND|PLAY_SERVICE|WORLD_ENGINE|backend:8000|8000|8001|health|runs" frontend backend world-engine docker-compose.yml docker-up.py .env.example tests docs
```

### Runtime service health

```bash
docker compose ps
docker compose logs --tail=200 backend
docker compose logs --tail=300 play-service
docker compose logs --tail=200 frontend
curl -sS http://localhost:8001/api/health | jq .
curl -sS http://localhost:8001/api/health/ready | jq .
curl -sS http://localhost:5002/api/v1/game/bootstrap | jq .
```

### Verify profile resolution and actor ownership at `/api/runs`

```bash
curl -sS -X POST http://localhost:8001/api/runs \
  -H 'Content-Type: application/json' \
  -d '{"runtime_profile_id":"god_of_carnage_solo","selected_player_role":"annette","account_id":"audit","display_name":"Audit"}' \
  | jq '{run_id:.run.id, run_template_id:.run.template_id, content_module_id, runtime_profile_id, runtime_module_id, selected_player_role, human_actor_id, npc_actor_ids, actor_lanes, visitor_present}'
```

Expected proof after repair: actor fields are not only returned by `/api/runs`; they are also present in the story runtime session projection.

### Verify story-session create payload/result through backend path

Use backend logs or temporary request logging in an audit branch only. Without changing production, inspect responses:

```bash
# Start through the real frontend/backend route after login/session auth is available.
# Then inspect backend response shape and world-engine state.
curl -sS -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -X POST http://localhost:8000/api/v1/game/player-sessions \
  -d '{"runtime_profile_id":"god_of_carnage_solo","selected_player_role":"annette","trace_id":"audit-goc-opening"}' \
  | tee /tmp/player-session-create.json | jq .

jq '{run_id, template_id, module_id, runtime_session_id, runtime_session_ready, can_execute, opening_turn, story_entries, shell_state_view}' /tmp/player-session-create.json
```

### Verify world-engine story state

```bash
RUNTIME_SESSION_ID=$(jq -r '.runtime_session_id' /tmp/player-session-create.json)
API_KEY=${PLAY_SERVICE_INTERNAL_API_KEY:-dev-internal-key}

curl -sS "http://localhost:8001/api/story/sessions/$RUNTIME_SESSION_ID/state" \
  -H "X-Play-Service-Key: $API_KEY" \
  | tee /tmp/story-state.json | jq '{session_id, module_id, turn_counter, runtime_projection, story_window}'

jq '.runtime_projection | {runtime_profile_id, content_module_id, runtime_module_id, selected_player_role, human_actor_id, npc_actor_ids, actor_lanes}' /tmp/story-state.json
jq '.story_window.entries' /tmp/story-state.json
```

Failure signal to look for:

```text
runtime_projection.human_actor_id == null/empty
runtime_projection.npc_actor_ids == null/empty
story_window.entry_count == 0
```

### Verify first live turn

```bash
RUN_ID=$(jq -r '.run_id' /tmp/player-session-create.json)

curl -sS -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -X POST "http://localhost:8000/api/v1/game/player-sessions/$RUN_ID/turns" \
  -d '{"player_input":"I look at Véronique and say: we need to stop pretending this is polite."}' \
  | tee /tmp/player-turn.json | jq '{turn, story_entries, story_window, shell_state_view, governance}'
```

Inspect for graph/model truth:

```bash
curl -sS "http://localhost:8001/api/story/sessions/$RUNTIME_SESSION_ID/diagnostics" \
  -H "X-Play-Service-Key: $API_KEY" \
  | tee /tmp/story-diagnostics.json \
  | jq '.diagnostics[-1] | {turn_number, turn_kind, nodes_executed, routing, generation, validation_outcome, committed_result, visible_output_bundle, diagnostics_envelope}'
```

### Verify runtime config/provider route

```bash
curl -sS http://localhost:8001/api/internal/story/runtime/config-status \
  -H "X-Play-Service-Key: $API_KEY" | jq .

docker compose logs --tail=500 play-service | rg -n "LIVE_STORY_RUNTIME_BLOCKED|adapter_not_registered|fallback|degraded|story_opening|execute_story_turn|Langfuse|provider|model|graph"
```

### Verify frontend payload/render

```bash
curl -sS -H "Cookie: $FRONTEND_COOKIE" "http://localhost:5002/play/$RUN_ID" \
  | rg -n "No authored opening|play-turn-card|World of Shadows|Degraded runtime path|runtime-player-line|turn-transcript"
```

### Verify narrator streaming route

```bash
# Confirm whether frontend exposes this path. Expected currently: likely 404 unless separately proxied.
curl -i "http://localhost:5002/api/story/sessions/$RUNTIME_SESSION_ID/stream-narrator"

# Confirm whether play-service exposes it directly.
curl -i "http://localhost:8001/api/story/sessions/$RUNTIME_SESSION_ID/stream-narrator" \
  -H "X-Play-Service-Key: $API_KEY"
```

---

## 14. Future Repair Plan Outline

### Wave 0 — Source locator and current-state proof

- **Goal:** Capture real request/response bodies for `/api/v1/game/player-sessions`, `/api/runs`, `/api/story/sessions`, `/state`, `/diagnostics`.
- **Likely files touched later:** none for audit; temporary logging only in local branch if needed.
- **Tests needed later:** none yet.
- **Done criteria:** The exact runtime projection reaching `StoryRuntimeManager.create_session` is known.

### Wave 1 — Session create/opening contract repair

- **Goal:** Define hard contract: GoC session creation requires complete profile/content/actor ownership and must produce or explicitly schedule opening.
- **Likely files touched:** `backend/app/api/v1/game_routes.py`, `backend/app/services/game_service.py`, world-engine request schemas if needed.
- **Tests needed later:** backend payload contract test; world-engine create-session contract test.
- **Done criteria:** `/api/story/sessions` receives actor ownership and runtime provenance.

### Wave 2 — Backend → world-engine live route repair

- **Goal:** Preserve top-level `/api/runs` actor ownership and merge it into story runtime projection.
- **Likely files touched:** `backend/app/services/game_service.py`, `backend/app/api/v1/game_routes.py`.
- **Tests needed later:** integration test that fails if `human_actor_id` is absent from stored world-engine state.
- **Done criteria:** `runtime_projection.human_actor_id`, `npc_actor_ids`, `actor_lanes`, `runtime_profile_id`, `runtime_module_id`, `content_module_id` present in story state.

### Wave 3 — StoryRuntimeManager narrator opening lifecycle repair

- **Goal:** Make opening lifecycle truthful: either real graph/model narrator opening or explicit deterministic bootstrap with validation and non-empty visible output.
- **Likely files touched:** `world-engine/app/story_runtime/manager.py`, `ai_stack/live_dramatic_scene_simulator.py`.
- **Tests needed later:** production-manager create-session test with non-empty opening and actor lanes.
- **Done criteria:** Turn 0 cannot be healthy if no visible narrator/NPC output exists.

### Wave 4 — Runtime graph/live turn output repair

- **Goal:** Ensure first player turn reaches graph, provider/model, validation, commit, and visible output.
- **Likely files touched:** governed config loader/routes, `ai_stack/langgraph/langgraph_runtime_executor.py`, model adapter config.
- **Tests needed later:** live turn gate with provider/mock policy explicitly declared; fail on diagnostics-only output.
- **Done criteria:** Diagnostics show graph nodes, provider/model, parser, validation, commit, and non-empty visible output.

### Wave 5 — Frontend render and empty-state repair

- **Goal:** Prevent empty shell from being playable; render opening or block with actionable error.
- **Likely files touched:** `frontend/app/routes_play.py`, `frontend/templates/session_shell.html`, `frontend/static/play_shell.js`.
- **Tests needed later:** frontend integration test for empty `story_entries` with `can_execute=false`; opening present render test with real backend fixture.
- **Done criteria:** Empty session never appears as live-ready.

### Wave 6 — Diagnostics truthfulness repair

- **Goal:** Make missing opening/output a first-class diagnostic failure.
- **Likely files touched:** `world-engine/app/story_runtime/manager.py`, diagnostics envelope code, backend shell status view.
- **Tests needed later:** diagnostics gate for missing output reason.
- **Done criteria:** `story_window.entry_count=0` includes explicit failure reason and cannot be reported as success.

### Wave 7 — Test-gate repair and false-green elimination

- **Goal:** Separate unit/mocked/structural tests from live gates; add true create→opening→turn gate.
- **Likely files touched:** `tests/gates/`, `frontend/tests/`, `backend/tests/`, `world-engine/tests/`, `run_tests.py`.
- **Tests needed later:** one hard E2E gate that starts GoC solo as Annette and Alain and asserts non-empty opening and first turn output.
- **Done criteria:** Tests fail on empty arrays, placeholders, local-only diagnostics, mocks, or visitor actor leakage.

### Wave 8 — Docs/runbook update

- **Goal:** Align docs with actual repaired contracts and remove false claims.
- **Likely files touched:** `docs/MVPs/`, `docs/ADR/`, `tests/reports/`.
- **Tests needed later:** doc/link/source locator sanity gate.
- **Done criteria:** Docs state the exact live route and acceptance gates; no stale “real runtime” claims for mocked tests.

---

## 15. Final Acceptance Criteria for a Future Fix

A future fix is not acceptable until all of the following are true:

1. Starting `god_of_carnage_solo` requires a valid selected role.
2. `god_of_carnage_solo` resolves to a runtime profile, not a content module.
3. `god_of_carnage` is the canonical content module.
4. No `visitor` actor appears in live runtime state, prompt participants, actor lanes, lobby seats, or story output.
5. Backend preserves and forwards `selected_player_role`, `human_actor_id`, `npc_actor_ids`, `actor_lanes`, `runtime_profile_id`, `runtime_module_id`, and `content_module_id` into the world-engine story session.
6. Session creation produces or explicitly schedules a narrator opening.
7. The first frontend play shell shows a non-empty narrator/dramatic opening.
8. The first player turn reaches `StoryRuntimeManager.execute_turn`.
9. `RuntimeTurnGraphExecutor.run` executes for player turns.
10. A live provider/model route is selected when live mode requires it; otherwise the response is explicitly degraded or blocked.
11. AI proposal is validated and committed by the engine before becoming visible output.
12. NPC/narrator output is returned without speaking for the human-controlled actor.
13. Empty/degraded/fallback output cannot be reported as live success.
14. Tests fail if the live path returns only IDs, empty arrays, placeholder text, mocks, or local diagnostics.
15. Diagnostics explain exactly why output is missing if output is missing.

---

## Appendix A — Required Search Result Summary

The required searches were run under `/mnt/data/repo_frontend`. The highest-signal files from the required search set were:

- `frontend/app/routes_play.py`
- `frontend/templates/session_start.html`
- `frontend/templates/session_shell.html`
- `frontend/static/play_shell.js`
- `frontend/static/play_narrative_stream.js`
- `backend/app/api/v1/game_routes.py`
- `backend/app/services/game_service.py`
- `backend/app/services/game_content_service.py`
- `backend/app/content/compiler/models.py`
- `world-engine/app/api/http.py`
- `world-engine/app/main.py`
- `world-engine/app/runtime/profiles.py`
- `world-engine/app/story_runtime/manager.py`
- `ai_stack/langgraph/langgraph_runtime_executor.py`
- `ai_stack/langchain/bridges.py`
- `ai_stack/live_dramatic_scene_simulator.py`
- `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py`
- `frontend/tests/test_routes_extended.py`
- `frontend/tests/test_mvp1_play_launcher.py`
- `world-engine/tests/test_mvp4_diagnostics_integration.py`
- `world-engine/tests/test_story_window_projection.py`
- `backend/tests/test_e2e_god_of_carnage_full_lifecycle.py`
