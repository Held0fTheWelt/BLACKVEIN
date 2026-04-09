# Task 4 — Reference Repair Inventory

## Scope

- Purpose: class-based pre/post reference repair obligations for Task 4.
- Movement context: no physical GoC namespace move in this pass due blocker status.
- Repair context in this pass: cleanup-relevant tracked references repaired where needed; remaining move-coupled repairs deferred behind blocker.

## Reference class inventory (pre state)

| Class | Representative surfaces | Risk | Status in this pass |
|---|---|---|---|
| imports | `world-engine/app/story_runtime/manager.py`, `ai_stack/*` | drift if namespace move occurs | inventoried |
| path constants | `backend/app/content/module_loader.py`, `ai_stack/goc_yaml_authority.py`, `tools/mcp_server/fs_tools.py`, `ai_stack/rag.py` | loader/rag misrouting | inventoried |
| loader logic | backend content service and MCP handlers | stale discovery assumptions | inventoried |
| registry/discovery | writers-room prompt registry, MCP tool registry | stale IDs after renamespace | inventoried |
| config references | `docker-compose.yml`, play-service env URLs | seam mismatch | inventoried |
| tests | backend/world-engine/ai_stack/tools tests with `god_of_carnage` literals | false confidence if partial updates | inventoried |
| docs links | gate baselines, evidence maps, curated docs indexes | broken or misleading links | repaired + inventoried |
| scripts/tooling | `scripts/g9_level_a_evidence_capture.py` and tool docs | stale path assumptions | inventoried |
| tracked reports/artifacts assumptions | `docs/audit/*`, `outgoing/*` mirrors | stale evidence/mirror semantics | repaired + inventoried |

## Repair actions executed in this pass

| Repair ID | Source | Pre issue | Action | Post verification |
|---|---|---|---|---|
| RR-01 | `docs/README.md` | no explicit Task 4 closure-evidence pointer | added Task 4 closure evidence pointers | local link check pass |
| RR-02 | `docs/INDEX.md` | no explicit Task 4 closure-evidence pointer | added Task 4 closure evidence pointers | local link check pass |
| RR-03 | `docs/audit/gate_summary_matrix.md` | no direct pointer to Task 4 command set / closure pack | added Task 4 closure evidence pointer note | local link check pass |
| RR-04 | Area 2 docs + `docs/testing-setup.md` + `backend/app/runtime/area2_validation_commands.py` | dual-closure pytest lists referenced deleted `test_area2_workstream_*` modules; Task 4 proof list referenced `test_task4_drift_resistance.py` | aligned module lists with merged G-A/G-B tests and `test_runtime_drift_resistance.py`; updated architecture closure reports | `pytest --collect-only` on updated `AREA2_DUAL_CLOSURE_PYTEST_MODULES` from `backend/` (64 tests collected) |
| RR-05 | Root `PATCH_NOTES_FLASK_PLAY_INTEGRATION.md` | root-level process note | `git mv` to `docs/reports/PATCH_NOTES_FLASK_PLAY_INTEGRATION.md`; Task 1A baseline refreshed | path exists under `docs/reports/` |

## Deferred repairs (blocked by no-move rule)

The following repairs are intentionally deferred until movement gate lift:

- path and ID rewrite across code/test surfaces tied to `module_id` and `content/modules/<id>` assumptions,
- renamespace of writers-room `implementation.god_of_carnage.*` IDs,
- post-move import/path rewrites in runtime and test stacks.

These deferrals are compliant with the hard blocker and captured in the residual-risk register.

## Post-state summary

- Repair classes are fully inventoried.
- Documentation/control-surface repairs in scope of this pass are completed.
- Move-coupled repair classes remain blocked and are not falsely marked complete.

