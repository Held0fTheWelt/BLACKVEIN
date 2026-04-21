# Live story runtime governance — repair audit bundle (English)

This document satisfies the project-facing audit artifacts (A–F) for the governed live story-runtime repair.

## A. Live story runtime repair audit report

- **Intended live story path:** Backend persists **resolved runtime config** (providers, models, routes, `config_version`) → world-engine **play service** fetches `GET /api/v1/internal/runtime-config` at startup and on **POST /api/internal/story/runtime/reload-config** → `StoryRuntimeManager` builds components via `build_governed_story_runtime_components` → `RuntimeTurnGraphExecutor` runs turns with governed registry/adapters.
- **Repaired actual path:** Same, but when `WOS_ALLOW_UNGOVERNED_STORY_RUNTIME` is **not** set, missing/invalid resolved config no longer silently installs `build_default_registry()` / `build_default_model_adapters()`. Instead the manager enters **`governed_config_invalid_or_missing`** with `BlockedLiveStoryRoutingPolicy` and **empty adapters**, and live player APIs raise **`LiveStoryGovernanceError`** (HTTP **503**).
- **Removed/bypassed legacy path(s):** Silent `default_registry` fallback is **disabled** unless `WOS_ALLOW_UNGOVERNED_STORY_RUNTIME=1` (tests / explicit dev). Docker Compose now wires **`BACKEND_RUNTIME_CONFIG_URL`** and **`INTERNAL_RUNTIME_CONFIG_TOKEN`** into `play-service`.
- **Repaired opening path:** Live openings from world-engine pass **`live_player_truth_surface=True`** into the turn graph. `run_visible_render` no longer emits the preview placeholder on that surface; GoC openings additionally require **`commit_applied`** and reject visible text containing the preview placeholder string.
- **Repaired metadata truth path:** `runtime_governance_surface` now includes **`primary_route_selection`** (routed model/provider/fallback chain) and **`final_model_invocation`** (adapter / api_model / invocation mode). Flat `route_selected_*` / `adapter` / `api_model` keys remain for backward compatibility.
- **Administration Center as live authority:** Persisting a resolved snapshot (`build_resolved_runtime_config(..., persist_snapshot=True)`) triggers **`reload_play_story_runtime_governed_config()`** when play-service integration is configured, pushing config into the running engine.

## B. Configuration authority repair report

- **Intended authoritative source:** Administration Center / backend **resolved runtime config** snapshots + internal runtime-config API.
- **Actual repaired authoritative source:** Same; world-engine consumes the internal JSON payload only.
- **Config propagation path:** Admin **reload-resolved-config** → `build_resolved_runtime_config` → DB snapshot → optional **HTTP POST** to play service `/api/internal/story/runtime/reload-config` → in-process `StoryRuntimeManager.reload_runtime_config`.
- **Reload/rebind path:** `world_engine_story_runtime_rebind` object attached to the resolved dict returned on persist (best-effort; failures are captured without rolling back DB).
- **Active config evidence:** `GET /api/internal/story/runtime/config-status` (play service) and `runtime_config_status()` fields: **`governed_runtime_active`**, **`config_version`**, **`live_execution_blocked`**, **`legacy_default_registry_path`**.
- **Remaining limits:** If play-service is down during backend persist, rebind fails softly in `world_engine_story_runtime_rebind` — operators must retry reload or restart play-service after backend is healthy.

## C. Hidden provider / model / adapter remediation report

| Path | Classification | Action |
|------|----------------|--------|
| `story_runtime_core.build_default_registry` / `build_default_model_adapters` | **dev_only / test_only** when `WOS_ALLOW_UNGOVERNED_STORY_RUNTIME=1` | Retained for unit tests; **not** used for strict live posture. |
| Blocked posture (`BlockedLiveStoryRoutingPolicy`, empty adapters) | **live_allowed** as explicit fail-closed | No live generation without governed config. |
| Legacy env-only live overrides | **disabled** for strict live | Governed fetch + token required in production compose. |

**Live-capable ungoverned path remaining:** Only when **`WOS_ALLOW_UNGOVERNED_STORY_RUNTIME=1`** — must stay **false** in production-like deployments.

## D. Routing / invocation / metadata truth report

- **Route choice:** `route_model` writes `state["routing"]` (selected model/provider, fallback chain, governed flag).
- **Final invocation:** `invoke_model` / fallback / self-correction populate `generation.metadata` (adapter, model, invocation mode).
- **Fallback:** Graph mock fallback is **skipped** when `generation_execution_mode == "ai_only"` on the executor (no silent mock graph fallback in AI-only mode).
- **Reporting after repair:** `runtime_governance_surface.primary_route_selection` vs `runtime_governance_surface.final_model_invocation` separates layers; duplicates under legacy flat keys preserved for consumers not yet migrated.

## E. Root-cause to repair map

| ID | Symptom | Location | Repair | Evidence | Status |
|----|---------|----------|--------|----------|--------|
| R1 | Silent default registry | `StoryRuntimeManager._apply_runtime_components` | Strict branch → blocked components | `tests/test_live_story_runtime_governance.py` | **Closed** |
| R2 | No runtime-config wiring in Docker | `docker-compose.yml` | Added `BACKEND_RUNTIME_CONFIG_URL`, `INTERNAL_RUNTIME_CONFIG_TOKEN` | Compose diff | **Closed** |
| R3 | Admin reload did not rebind play | `build_resolved_runtime_config` | Calls `reload_play_story_runtime_governed_config` | Code path + `world_engine_story_runtime_rebind` | **Closed** |
| R4 | Preview placeholder in live openings | `run_visible_render` + graph `live_player_truth_surface` | Truth surface branch + opening acceptance | Langgraph tests pass | **Closed** |
| R5 | Contradictory flat metadata | `_finalize_committed_turn` | Nested `primary_route_selection` / `final_model_invocation` | Story diagnostics consumers | **Closed** |
| R6 | Readiness ignored play binding | `evaluate_runtime_readiness` | `play_story_runtime_governance` probe + blockers | Readiness payload | **Closed** |

## F. Validation evidence report

- **Tests:** `world-engine/tests/test_live_story_runtime_governance.py` (strict blocked, governed ok, reload `ok` false when fetch returns `None`); `ai_stack/tests/test_langgraph_runtime.py` (10 passed with PYTHONPATH); `backend/tests/test_operational_governance_mvp.py::test_runtime_readiness_payload_includes_actionable_fields` (passed).
- **Runtime / config evidence:** Use `GET /api/internal/story/runtime/config-status` after deploy; expect `governed_runtime_active: true`, non-empty `config_version`, `live_execution_blocked: false`, `legacy_default_registry_path: false`.
- **No-preview-placeholder evidence:** Live graph runs with `live_player_truth_surface=true` never select the preview placeholder branch in `run_visible_render`.
- **No hidden live path (strict):** With `WOS_ALLOW_UNGOVERNED_STORY_RUNTIME=0` and missing config, `source=governed_config_invalid_or_missing` and routing `choose` raises before any adapter call.
