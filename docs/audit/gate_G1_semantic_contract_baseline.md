# Gate G1 Baseline: Shared Semantic Contract

## Gate

- Gate name: G1 Shared Semantic Contract
- Gate class: structural
- Audit subject: canonical semantic vocabulary ownership, cross-surface reuse, and redefinition prevention

## Repository Inspection Targets

- `docs/ROADMAP_MVP_GoC.md`
- `ai_stack/goc_frozen_vocab.py`
- `ai_stack/mcp_canonical_surface.py`
- `ai_stack/goc_turn_seams.py`
- `ai_stack/langgraph_runtime.py`
- `ai_stack/tests/test_goc_frozen_vocab.py`
- `backend/app/services/writers_room_model_routing.py`
- `backend/app/services/improvement_task2a_routing.py`

## Required Evidence

- canonical semantic artifact(s)
- semantic import/reference traces across runtime, writers-room, improvement, admin
- equality checks for required semantic sets
- tests proving no productive local override

## Audit Methods Used In This Baseline

- static contract inspection
- symbol/reference tracing
- static test intent review (no runtime execution in this block)

## Command Strategy

| command | status | basis | promotion requirement |
| --- | --- | --- | --- |
| `python -m pytest ai_stack/tests/test_goc_frozen_vocab.py ai_stack/tests/test_goc_roadmap_semantic_surface.py -q --tb=short` | `repo-verified` | Canonical semantic parity surfaces in `ai_stack/tests/`. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g1_semantic_ai_stack.txt` |
| `cd backend && python -m pytest tests/test_goc_semantic_parity.py -q --tb=short --no-cov` | `repo-verified` | Backend semantic parity path tied to runtime/admin vocabulary alignment. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g1_semantic_backend_parity.txt` |

## Baseline Findings

1. `ai_stack/goc_frozen_vocab.py` is a real canonical semantic artifact for the GoC slice, with frozen label sets and assertion helpers.
2. `test_goc_roadmap_semantic_surface.py` and `test_goc_semantic_parity.py` now provide executed equality/parity proof across `ai_stack` and backend semantic surfaces for the roadmap-facing label families.
3. Backend writers-room/improvement routing surfaces consume shared routing contracts (`TaskKind`, `RouteReasonCode`) via runtime contract modules, and the executed parity tests validate this reuse path.
4. No local contradiction was found between canonical semantic artifacts and consumer surfaces on the canonical rerun.

## Status Baseline

- structural_status: `green`
- closure_level_status: `level_a_capable`

Rationale: canonical semantic source exists, cross-surface reuse is present, and canonical parity/equality test paths passed with archived execution evidence.

## Evidence Quality

- evidence_quality: `high`
- justification: direct implementation evidence plus executed canonical semantic/parity test transcripts in `tests/reports/evidence/all_gates_closure_20260409/`.

## Execution Risks Carried Forward

- Maintain parity checks as mandatory regression paths for future semantic-surface changes.
