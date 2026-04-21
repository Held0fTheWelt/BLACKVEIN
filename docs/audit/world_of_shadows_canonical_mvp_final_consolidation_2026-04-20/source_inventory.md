# Source inventory

## Inventory principle

This inventory covers the **actually supplied artifacts in this pass** plus the major internal source families extracted from those archives.

It does not pretend that every older historical package mentioned inside previous audit notes was re-audited directly as a separate uploaded artifact in this conversation.

## Audited source inventory

| Artifact | Type | Classification | Why used | Outcome |
|---|---|---|---|---|
| World_of_Shadows_v21_closure_plus_inventory_audit.md | supplied markdown audit | audit evidence; historical but still content-bearing; inventory authority for v21 package breadth | Provides a direct written inventory of the v21 canonical closure package and confirms broad-system scope such as memory, authoring, UI, and reference scaffold coverage. | Preserved as evidence for v21 breadth and used as a cross-check against later compressed MVP summaries. |
| world_of_shadows_mvp_v24_lean_finishable.zip | supplied archive | partial MVP fragment; comparison artifact; curated lean package | Useful for drift detection, omission checking, and understanding what the lean packaging intentionally removed or compressed. | Used as a comparison artifact only, not as the final canonical base. |
| world_of_shadows_mvp_v24_f_line_closed_FULL_MVP_DIRECTORY.zip | supplied archive | primary implementation evidence; audit evidence; canonical candidate; experience-proof anchor | Strongest repo-centered source for code reality, GoC A-F experience closures, publish/runtime continuity, UI docs, validation corpus, and service boundaries. | Preserved as the primary implementation and proof anchor for this pass. |
| world_of_shadows_canonical_mvp_preservation_audit_2026-04-20.zip | supplied archive | prior supplied-archive audit package; previous canonical attempt; audit evidence | Carries the earlier preservation-first audit pass and the first subject-based canonical MVP family for this source set. | Preserved as prior consolidation evidence and anti-loss comparator. |
| world_of_shadows_final_consolidated_mvp_archive_extended_2026-04-20.zip | supplied archive | strongest prior canonical candidate; canonical base; extension package | Already preserved the extended canonical document family, including governed package lifecycle and operational governance seams. | Chosen as the working base for the final consolidation pass. |
| world_of_shadows_final_consolidated_mvp_archive_collection_only_2026-04-20.zip | supplied archive | collection-first canonical attempt; recovery addendum; historical but still content-bearing | Useful for checking that prior collection work did not recover any still-valid material beyond the extended package, and for identifying where collection scope notes should remain audit context rather than canonical MVP truth. | Used as a cross-check and preserved as audit context, but not taken as the final base because this pass performs its own runtime-proof judgment. |
| ai_stack.zip | related supplied archive | related implementation archive; duplicate-heavy support surface; spot-check source | Used to verify that the AI-stack, research, and MCP-support surfaces were not merely mentioned in docs but also represented in code and tests. | Used as a related implementation cross-check, not as a separate canonical-document driver. |
| embedded mvp/docs family inside supplied archives | internal source family | historical but still content-bearing; broad-system canonical source; superseded but unique | Carries the v21-style broad WoS target, memory/world-model depth, writers-room scope, multi-session continuity, and runtime-maturity framing. | Direct carry-forward source for enduring-target restoration. |
| docs/MVPs/world_of_shadows_canonical_mvp inside prior canonical archives | internal source family | normalized canonical reading layer; canonical candidate | Strongest already-normalized subject-based canonical MVP family before this pass. | Preserved and strengthened, not replaced. |
| v24 validation corpus under validation/ | internal source family | audit evidence; experience-proof evidence; implementation evidence | Carries GoC A-F closure reports, shell-loop proof, backend transitional retirement posture, and activation-path evidence. | Preserved as load-bearing packaged proof. |
| docs/user, docs/admin, docs/start-here, roadmap docs, and related UX/governance docs | internal source family | UX authority; architecture authority; implementation-adjacent guidance | Preserve player-shell clarity, publish/runtime continuity, GoC player-facing expectations, room/object pressure reading, operator journeys, and settings/control-plane governance. | Strengthened and integrated into the canonical MVP family. |
| mvp/reference_scaffold/tests, world-engine/tests, ai_stack/tests | executable proof surfaces | direct execution evidence; test evidence | Available for direct rerun in this container and therefore valuable for fresh reality checking. | Rerun directly in this pass and recorded under final-consolidation raw outputs. |
| backend/frontend Flask-backed tests | execution targets inside supplied archive | important proof surfaces; environment-limited execution targets | High-value route-level proof for session and player-shell seams. | Kept explicit as blocked proof surfaces because Flask is unavailable in this container. |

## Direct-execution surfaces used in this pass

| Command | Status | Summary | Raw output |
|---|---|---|---|
| python -m pytest -q mvp/reference_scaffold/tests --tb=short | NONZERO | See raw output | `evidence/raw_test_outputs/final_consolidation_2026-04-20/mvp_reference_scaffold_tests.txt` |
| PYTHONPATH=world-engine:. python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short | PASS | 18 passed, 1 warning | `evidence/raw_test_outputs/final_consolidation_2026-04-20/world_engine_shell_readout.txt` |
| PYTHONPATH=world-engine:. python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py --tb=short | PASS | 18 passed, 1 warning | `evidence/raw_test_outputs/final_consolidation_2026-04-20/world_engine_narrative_commit.txt` |
| python -m pytest -q ai_stack/tests/test_goc_scene_identity.py ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short | PASS | 10 passed | `evidence/raw_test_outputs/final_consolidation_2026-04-20/ai_stack_goc_support_tests.txt` |
| python -m pytest -q ai_stack/tests/test_goc_mvp_breadth_playability_regression.py -rs --tb=short | SKIPPED / ENV-LIMITED | 1 skipped | `evidence/raw_test_outputs/final_consolidation_2026-04-20/ai_stack_goc_breadth_playability.txt` |
| python -m pytest -q backend/tests/test_session_routes.py -k "shell_readout_projection or execute_turn_proxies_to_world_engine" --tb=short | BLOCKED IN THIS CONTAINER | ModuleNotFoundError: No module named 'flask' | `evidence/raw_test_outputs/final_consolidation_2026-04-20/backend_session_routes_targeted.txt` |
| PYTHONPATH=frontend python -m pytest -q frontend/tests/test_routes_extended.py -k "play_shell_frames_latest_transcript_with_runtime_response_prefix" --tb=short | BLOCKED IN THIS CONTAINER | ModuleNotFoundError: No module named 'flask' | `evidence/raw_test_outputs/final_consolidation_2026-04-20/frontend_routes_targeted.txt` |
