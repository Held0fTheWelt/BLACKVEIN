# Runtime/MVP Contractify attachment report

Generated from the curated runtime/MVP spine attachment pass.

## Outcome

- Audit JSON: `'fy'-suites/contractify/reports/contract_audit.json`
- Contracts discovered in audit: **43**
- Relations discovered in audit: **225**
- Manual unresolved areas kept explicit: **2**

## Precedence / weight handling

- **runtime_authority** (rank 1): Highest-order runtime authority and boundary contracts. These outrank slice detail, implementation observations, and projections when authority clashes are reviewed.
- **slice_normative** (rank 2): Binding MVP / slice contracts and accepted slice-scoped ADRs. These govern GoC behavior beneath the runtime authority layer.
- **implementation_evidence** (rank 3): Observed code surfaces that embody or operationalize contracts but do not replace normative authority.
- **verification_evidence** (rank 4): Test and verification surfaces that support claims about implementation and documented paths.
- **projection_low** (rank 5): Lower-weight audience projections and convenience summaries. Useful for navigation, never equal to runtime authority or slice contracts.

## Explicit documented contracts promoted

- `docs/governance/adr-0001-runtime-authority-in-world-engine.md` → `CTR-ADR-0001-RUNTIME-AUTHORITY` (runtime_authority)
- `docs/governance/adr-0002-backend-session-surface-quarantine.md` → `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE` (runtime_authority)
- `docs/governance/adr-0003-scene-identity-canonical-surface.md` → `CTR-ADR-0003-SCENE-IDENTITY` (slice_normative)
- `docs/technical/runtime/runtime-authority-and-state-flow.md` → `CTR-RUNTIME-AUTHORITY-STATE-FLOW` (runtime_authority)
- `docs/technical/architecture/backend-runtime-classification.md` → `CTR-BACKEND-RUNTIME-CLASSIFICATION` (runtime_authority)
- `docs/technical/architecture/canonical_runtime_contract.md` → `CTR-CANONICAL-RUNTIME-CONTRACT` (runtime_authority)
- `docs/technical/runtime/player_input_interpretation_contract.md` → `CTR-PLAYER-INPUT-INTERPRETATION` (slice_normative)
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` → `CTR-GOC-VERTICAL-SLICE` (slice_normative)
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md` → `CTR-GOC-CANONICAL-TURN` (slice_normative)
- `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md` → `CTR-GOC-GATE-SCORING` (slice_normative)
- `docs/technical/content/writers-room-and-publishing-flow.md` → `CTR-WRITERS-ROOM-PUBLISHING-FLOW` (slice_normative)
- `docs/technical/ai/RAG.md` → `CTR-RAG-GOVERNANCE` (slice_normative)

## Code-embodied contract surfaces promoted

- `world-engine/app/story_runtime/manager.py` → `OBS-WE-STORY-RUNTIME-MANAGER`
- `world-engine/app/api/http.py` → `OBS-WE-HTTP-API`
- `backend/app/api/v1/session_routes.py` → `OBS-BE-SESSION-ROUTES`
- `backend/app/runtime/session_store.py` → `OBS-BE-SESSION-STORE`
- `backend/app/services/session_service.py` → `OBS-BE-SESSION-SERVICE`
- `backend/app/api/v1/world_engine_console_routes.py` → `OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES`
- `backend/app/api/v1/writers_room_routes.py` → `OBS-BE-WRITERS-ROOM-ROUTES`
- `story_runtime_core/input_interpreter.py` → `OBS-CORE-INPUT-INTERPRETER`
- `ai_stack/goc_scene_identity.py` → `OBS-AI-GOC-SCENE-IDENTITY`
- `ai_stack/goc_yaml_authority.py` → `OBS-AI-GOC-YAML-AUTHORITY`
- `ai_stack/rag.py` → `OBS-AI-RAG`
- `backend/app/services/game_service.py` → `OBS-BE-GAME-SERVICE`

## Test-evidenced / verification anchors promoted

- `tests/TESTING.md` → `CTR-TESTING-ORCHESTRATION`
- `tests/run_tests.py` → `VER-TEST-RUNNER-CLI`
- `ai_stack/tests/test_goc_scene_identity.py` → `VER-AI-GOC-SCENE-IDENTITY-TEST`
- `story_runtime_core/tests/test_input_interpreter.py` → `VER-CORE-INPUT-INTERPRETER-TEST`
- `tests/experience_scoring_cli/test_experience_score_matrix_cli.py` → `VER-GOC-EXPERIENCE-SCORE-CLI-TEST`
- `tests/smoke/test_repository_documented_paths_resolve.py` → `VER-SMOKE-DOCUMENTED-PATHS`
- `backend/tests/test_world_engine_console_routes.py` → `VER-BE-WORLD-ENGINE-CONSOLE-ROUTES-TEST`
- `world-engine/tests/test_story_runtime_api.py` → `VER-WE-STORY-RUNTIME-API-TEST`

## Inferred candidate contracts intentionally left out of the curated spine

- No new broad semantic-mining candidates were promoted in this pass.
- The curated pass stayed bounded to the runtime/MVP spine, supporting code/test surfaces, and existing suite/governance anchors already discovered elsewhere by Contractify.

## Newly added / changed first-class records

- `CTR-ADR-0001-RUNTIME-AUTHORITY` — `docs/governance/adr-0001-runtime-authority-in-world-engine.md`
- `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE` — `docs/governance/adr-0002-backend-session-surface-quarantine.md`
- `CTR-ADR-0003-SCENE-IDENTITY` — `docs/governance/adr-0003-scene-identity-canonical-surface.md`
- `CTR-RUNTIME-AUTHORITY-STATE-FLOW` — `docs/technical/runtime/runtime-authority-and-state-flow.md`
- `CTR-BACKEND-RUNTIME-CLASSIFICATION` — `docs/technical/architecture/backend-runtime-classification.md`
- `CTR-CANONICAL-RUNTIME-CONTRACT` — `docs/technical/architecture/canonical_runtime_contract.md`
- `CTR-PLAYER-INPUT-INTERPRETATION` — `docs/technical/runtime/player_input_interpretation_contract.md`
- `CTR-GOC-VERTICAL-SLICE` — `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`
- `CTR-GOC-CANONICAL-TURN` — `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`
- `CTR-GOC-GATE-SCORING` — `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md`
- `CTR-WRITERS-ROOM-PUBLISHING-FLOW` — `docs/technical/content/writers-room-and-publishing-flow.md`
- `CTR-RAG-GOVERNANCE` — `docs/technical/ai/RAG.md`
- `CTR-TESTING-ORCHESTRATION` — `tests/TESTING.md`
- `OBS-WE-STORY-RUNTIME-MANAGER` — `world-engine/app/story_runtime/manager.py`
- `OBS-WE-HTTP-API` — `world-engine/app/api/http.py`
- `OBS-BE-SESSION-ROUTES` — `backend/app/api/v1/session_routes.py`
- `OBS-BE-SESSION-STORE` — `backend/app/runtime/session_store.py`
- `OBS-BE-SESSION-SERVICE` — `backend/app/services/session_service.py`
- `OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES` — `backend/app/api/v1/world_engine_console_routes.py`
- `OBS-BE-WRITERS-ROOM-ROUTES` — `backend/app/api/v1/writers_room_routes.py`
- `OBS-CORE-INPUT-INTERPRETER` — `story_runtime_core/input_interpreter.py`
- `OBS-AI-GOC-SCENE-IDENTITY` — `ai_stack/goc_scene_identity.py`
- `OBS-AI-GOC-YAML-AUTHORITY` — `ai_stack/goc_yaml_authority.py`
- `OBS-AI-RAG` — `ai_stack/rag.py`
- `OBS-BE-GAME-SERVICE` — `backend/app/services/game_service.py`
- `VER-TEST-RUNNER-CLI` — `tests/run_tests.py`
- `VER-AI-GOC-SCENE-IDENTITY-TEST` — `ai_stack/tests/test_goc_scene_identity.py`
- `VER-CORE-INPUT-INTERPRETER-TEST` — `story_runtime_core/tests/test_input_interpreter.py`
- `VER-GOC-EXPERIENCE-SCORE-CLI-TEST` — `tests/experience_scoring_cli/test_experience_score_matrix_cli.py`
- `VER-SMOKE-DOCUMENTED-PATHS` — `tests/smoke/test_repository_documented_paths_resolve.py`
- `VER-BE-WORLD-ENGINE-CONSOLE-ROUTES-TEST` — `backend/tests/test_world_engine_console_routes.py`
- `VER-WE-STORY-RUNTIME-API-TEST` — `world-engine/tests/test_story_runtime_api.py`

## Newly added / changed core relations

- `implemented_by`: `CTR-ADR-0003-SCENE-IDENTITY` -> `OBS-AI-GOC-SCENE-IDENTITY`
- `implemented_by`: `CTR-ADR-0003-SCENE-IDENTITY` -> `OBS-AI-GOC-YAML-AUTHORITY`
- `validated_by`: `CTR-ADR-0003-SCENE-IDENTITY` -> `VER-AI-GOC-SCENE-IDENTITY-TEST`
- `derives_from`: `CTR-RUNTIME-AUTHORITY-STATE-FLOW` -> `CTR-ADR-0001-RUNTIME-AUTHORITY`
- `implemented_by`: `CTR-CANONICAL-RUNTIME-CONTRACT` -> `OBS-WE-HTTP-API`
- `implemented_by`: `CTR-CANONICAL-RUNTIME-CONTRACT` -> `OBS-BE-GAME-SERVICE`
- `validated_by`: `CTR-CANONICAL-RUNTIME-CONTRACT` -> `VER-BE-WORLD-ENGINE-CONSOLE-ROUTES-TEST`
- `implemented_by`: `CTR-PLAYER-INPUT-INTERPRETATION` -> `OBS-CORE-INPUT-INTERPRETER`
- `implemented_by`: `CTR-PLAYER-INPUT-INTERPRETATION` -> `OBS-WE-STORY-RUNTIME-MANAGER`
- `implemented_by`: `CTR-PLAYER-INPUT-INTERPRETATION` -> `OBS-BE-SESSION-ROUTES`
- `validated_by`: `CTR-PLAYER-INPUT-INTERPRETATION` -> `VER-CORE-INPUT-INTERPRETER-TEST`
- `validated_by`: `CTR-PLAYER-INPUT-INTERPRETATION` -> `VER-WE-STORY-RUNTIME-API-TEST`
- `derives_from`: `CTR-GOC-CANONICAL-TURN` -> `CTR-GOC-VERTICAL-SLICE`
- `implemented_by`: `CTR-WRITERS-ROOM-PUBLISHING-FLOW` -> `OBS-BE-WRITERS-ROOM-ROUTES`
- `implemented_by`: `CTR-RAG-GOVERNANCE` -> `OBS-AI-RAG`
- `implemented_by`: `CTR-RAG-GOVERNANCE` -> `OBS-WE-STORY-RUNTIME-MANAGER`
- `validated_by`: `CTR-RAG-GOVERNANCE` -> `VER-WE-STORY-RUNTIME-API-TEST`
- `refines`: `CTR-RUNTIME-AUTHORITY-STATE-FLOW` -> `CTR-ADR-0001-RUNTIME-AUTHORITY`
- `refines`: `CTR-BACKEND-RUNTIME-CLASSIFICATION` -> `CTR-ADR-0001-RUNTIME-AUTHORITY`
- `operationalizes`: `CTR-BACKEND-RUNTIME-CLASSIFICATION` -> `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE`
- `depends_on`: `CTR-CANONICAL-RUNTIME-CONTRACT` -> `CTR-ADR-0001-RUNTIME-AUTHORITY`
- `depends_on`: `CTR-CANONICAL-RUNTIME-CONTRACT` -> `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE`
- `depends_on`: `CTR-GOC-GATE-SCORING` -> `CTR-GOC-CANONICAL-TURN`
- `depends_on`: `CTR-GOC-GATE-SCORING` -> `CTR-GOC-VERTICAL-SLICE`
- `overlaps_with`: `CTR-WRITERS-ROOM-PUBLISHING-FLOW` -> `CTR-RAG-GOVERNANCE`
- `overlaps_with`: `CTR-RAG-GOVERNANCE` -> `CTR-WRITERS-ROOM-PUBLISHING-FLOW`
- `operationalizes`: `OBS-WE-STORY-RUNTIME-MANAGER` -> `CTR-RUNTIME-AUTHORITY-STATE-FLOW`
- `operationalizes`: `OBS-BE-SESSION-ROUTES` -> `CTR-BACKEND-RUNTIME-CLASSIFICATION`
- `operationalizes`: `OBS-BE-WORLD-ENGINE-CONSOLE-ROUTES` -> `CTR-ADR-0002-BACKEND-SESSION-QUARANTINE`
- `operationalizes`: `OBS-BE-WRITERS-ROOM-ROUTES` -> `CTR-WRITERS-ROOM-PUBLISHING-FLOW`
- `operationalizes`: `OBS-AI-RAG` -> `CTR-RAG-GOVERNANCE`
- `derives_from`: `PRJ-RUNTIME-AUTH-ONBOARDING` -> `CTR-RUNTIME-AUTHORITY-STATE-FLOW`
- `derives_from`: `PRJ-GOC-PLAYER-GUIDE` -> `CTR-GOC-VERTICAL-SLICE`
- `derives_from`: `PRJ-PUBLISHING-ADMIN-GUIDE` -> `CTR-WRITERS-ROOM-PUBLISHING-FLOW`
- `derives_from`: `PRJ-AI-SYSTEM-RAG-SUMMARY` -> `CTR-RAG-GOVERNANCE`

## Unresolved conflicts / disputed areas kept explicit

- `CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT` — Backend transitional session surfaces are now attached and weighted, but the actual retirement timeline remains intentionally unresolved.
  - sources: docs/governance/adr-0002-backend-session-surface-quarantine.md, docs/technical/architecture/backend-runtime-classification.md, backend/app/api/v1/session_routes.py, backend/app/runtime/session_store.py, backend/app/services/session_service.py
- `CNF-RUNTIME-SPINE-WRITERS-RAG-OVERLAP` — Writers’ Room workflow and RAG governance intentionally overlap at retrieval/context-pack assembly, but publishing authority and runtime truth remain distinct and should stay explicitly reviewed.
  - sources: docs/technical/content/writers-room-and-publishing-flow.md, docs/technical/ai/RAG.md, backend/app/api/v1/writers_room_routes.py, ai_stack/rag.py

## Family index

- **runtime_authority**: CTR-ADR-0001-RUNTIME-AUTHORITY, CTR-ADR-0002-BACKEND-SESSION-QUARANTINE, CTR-RUNTIME-AUTHORITY-STATE-FLOW, CTR-BACKEND-RUNTIME-CLASSIFICATION, CTR-CANONICAL-RUNTIME-CONTRACT
- **input_turn**: CTR-PLAYER-INPUT-INTERPRETATION, OBS-CORE-INPUT-INTERPRETER, VER-CORE-INPUT-INTERPRETER-TEST
- **goc**: CTR-GOC-VERTICAL-SLICE, CTR-GOC-CANONICAL-TURN, CTR-GOC-GATE-SCORING, VER-GOC-EXPERIENCE-SCORE-CLI-TEST
- **scene_identity**: CTR-ADR-0003-SCENE-IDENTITY, OBS-AI-GOC-SCENE-IDENTITY, OBS-AI-GOC-YAML-AUTHORITY, VER-AI-GOC-SCENE-IDENTITY-TEST
- **publish_rag**: CTR-WRITERS-ROOM-PUBLISHING-FLOW, CTR-RAG-GOVERNANCE, OBS-BE-WRITERS-ROOM-ROUTES, OBS-AI-RAG
- **testing**: CTR-TESTING-ORCHESTRATION, VER-TEST-RUNNER-CLI, VER-SMOKE-DOCUMENTED-PATHS

## Notes

- `detect_adr_vocabulary_overlap` now suppresses the formerly noisy ADR-0001/ADR-0002 runtime/session overlap because that layering is now explicitly governed through curated precedence and relations.
- Writers’ Room vs RAG overlap remains visible on purpose and was not flattened into fake certainty.
