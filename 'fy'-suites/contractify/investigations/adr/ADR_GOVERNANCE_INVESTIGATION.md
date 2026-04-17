# ADR governance investigation

- Canonical ADR home: `docs/ADR`
- ADR files discovered: 3
- Canonical ADR files already in place: 0
- Legacy ADR files still outside `docs/ADR`: 3
- Findings: 5

## What this suite is for

This investigation suite makes ADR state visible in one place: current locations, proposed canonical names, duplicate pressure, migration gaps, and relation maps into the governed runtime/MVP spine.

## ADR inventory

| Current path | Declared id | Status | Family | Proposed canonical id | Proposed canonical path | Issues |
|---|---|---|---|---|---|---|
| `docs/ADR/adr-0002-backend-session-surface-quarantine.md` | `ADR-0002` | `accepted` | `BACKEND.SESSION` | `ADR.BACKEND.SESSION.0002` | `docs/ADR/ADR.BACKEND.SESSION.0002-backend-session-transitional-runtime-surface-quarantine-and-retirement.md` | not_in_canonical_adr_directory, missing_explicit_date |
| `docs/ADR/adr-0001-runtime-authority-in-world-engine.md` | `ADR-0001` | `accepted` | `RUNTIME` | `ADR.RUNTIME.0001` | `docs/ADR/ADR.RUNTIME.0001-runtime-authority-in-world-engine.md` | not_in_canonical_adr_directory |
| `docs/ADR/adr-0003-scene-identity-canonical-surface.md` | `ADR-0003` | `accepted` | `SLICE.GOC` | `ADR.SLICE.GOC.0003` | `docs/ADR/ADR.SLICE.GOC.0003-single-canonical-scene-identity-surface-across-compile-ai-guidance-and-commit.md` | not_in_canonical_adr_directory, missing_explicit_date |

## Findings

| Kind | Severity | Summary | Recommended action | Sources |
|---|---|---|---|---|
| `legacy_adr_location` | `medium` | ADR still lives outside the canonical docs/ADR directory: docs/ADR/adr-0002-backend-session-surface-quarantine.md | Migrate to docs/ADR/ADR.BACKEND.SESSION.0002-backend-session-transitional-runtime-surface-quarantine-and-retirement.md and remove the legacy duplicate once links are updated. | `docs/ADR/adr-0002-backend-session-surface-quarantine.md` |
| `legacy_adr_location` | `medium` | ADR still lives outside the canonical docs/ADR directory: docs/ADR/adr-0001-runtime-authority-in-world-engine.md | Migrate to docs/ADR/ADR.RUNTIME.0001-runtime-authority-in-world-engine.md and remove the legacy duplicate once links are updated. | `docs/ADR/adr-0001-runtime-authority-in-world-engine.md` |
| `legacy_adr_location` | `medium` | ADR still lives outside the canonical docs/ADR directory: docs/ADR/adr-0003-scene-identity-canonical-surface.md | Migrate to docs/ADR/ADR.SLICE.GOC.0003-single-canonical-scene-identity-surface-across-compile-ai-guidance-and-commit.md and remove the legacy duplicate once links are updated. | `docs/ADR/adr-0003-scene-identity-canonical-surface.md` |
| `missing_explicit_date` | `medium` | ADR metadata gap in docs/ADR/adr-0002-backend-session-surface-quarantine.md: missing explicit date. | Add an explicit header field instead of relying on historical knowledge. | `docs/ADR/adr-0002-backend-session-surface-quarantine.md` |
| `missing_explicit_date` | `medium` | ADR metadata gap in docs/ADR/adr-0003-scene-identity-canonical-surface.md: missing explicit date. | Add an explicit header field instead of relying on historical knowledge. | `docs/ADR/adr-0003-scene-identity-canonical-surface.md` |

## Governed runtime/MVP ADR attachment view

| ADR contract | Anchor | Implemented by | Validated by | Documented in | Precedence |
|---|---|---|---|---|---|
| `CTR-ADR-0001-RUNTIME-AUTHORITY` | `docs/ADR/adr-0001-runtime-authority-in-world-engine.md` | `world-engine/app/story_runtime/manager.py`, `world-engine/app/api/http.py` | `world-engine/tests/test_story_runtime_api.py` | `docs/technical/runtime/runtime-authority-and-state-flow.md`, `docs/dev/architecture/runtime-authority-and-session-lifecycle.md` | `runtime_authority` |
| `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE` | `docs/ADR/adr-0002-backend-session-surface-quarantine.md` | `backend/app/api/v1/session_routes.py`, `backend/app/runtime/session_store.py`, `backend/app/services/session_service.py`, `backend/app/api/v1/world_engine_console_routes.py` | `backend/tests/test_session_routes.py`, `backend/tests/test_world_engine_console_routes.py` | `docs/technical/architecture/backend-runtime-classification.md`, `docs/technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md` | `runtime_authority` |
| `CTR-ADR-0003-SCENE-IDENTITY` | `docs/ADR/adr-0003-scene-identity-canonical-surface.md` | `ai_stack/goc_scene_identity.py`, `ai_stack/goc_yaml_authority.py` | `ai_stack/tests/test_goc_scene_identity.py` | `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/governance/README.md` | `slice_normative` |

## Maps

- Relation map: `ADR_RELATION_MAP.mmd`
- Conflict / gap map: `ADR_CONFLICT_MAP.mmd`

## Gaps to keep visible

- `legacy_adr_location` — ADR still lives outside the canonical docs/ADR directory: docs/ADR/adr-0002-backend-session-surface-quarantine.md
- `legacy_adr_location` — ADR still lives outside the canonical docs/ADR directory: docs/ADR/adr-0001-runtime-authority-in-world-engine.md
- `legacy_adr_location` — ADR still lives outside the canonical docs/ADR directory: docs/ADR/adr-0003-scene-identity-canonical-surface.md
- `missing_explicit_date` — ADR metadata gap in docs/ADR/adr-0002-backend-session-surface-quarantine.md: missing explicit date.
- `missing_explicit_date` — ADR metadata gap in docs/ADR/adr-0003-scene-identity-canonical-surface.md: missing explicit date.
- manual unresolved `CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT` — Backend transitional session surfaces are now attached and weighted, but the actual retirement timeline remains intentionally unresolved.
