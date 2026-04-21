# World of Shadows canonical MVP preservation matrix

## Purpose

This matrix is the anti-loss proof for the consolidation pass.
Each materially relevant aspect was given an explicit outcome.

| Aspect | Source basis | Outcome | Canonical destination | Notes |
|---|---|---|---|---|
| World of Shadows product identity | README.md; docs/start-here/what-is-world-of-shadows.md; mvp/docs/00_MASTER_MVP.md | preserved directly | 01_system_identity_and_player_experience.md | Reconciled broad platform identity with current slice-centered docs. |
| Constitutional runtime laws | mvp/docs/48_CANONICAL_IMPLEMENTATION_PROTOCOL.md; mvp/docs/01_RUNTIME_CONSTITUTION.md; mvp/docs/00_WORLD_OF_SHADOWS_MVP_V21_CANONICAL.md | preserved after normalization | 02_authority_architecture_and_runtime_laws.md | Restored as enduring backbone instead of leaving them buried in the historical MVP tree. |
| Broad system target beyond current slice | mvp/docs/00_MASTER_MVP.md; historical memory/emotion/consciousness/writers-room specs | preserved as explicit bounded layer | 01_system_identity_and_player_experience.md and 06_implementation_reality_and_proof_status.md | Not falsely presented as fully implemented in the active repository slice. |
| World-engine as sole runtime authority | docs/technical/runtime/runtime-authority-and-state-flow.md; ADR-0001 | preserved directly | 02_authority_architecture_and_runtime_laws.md |  |
| Proposal → validation → commit → visible render semantics | CANONICAL_TURN_CONTRACT_GOC.md; VERTICAL_SLICE_CONTRACT_GOC.md; world_engine_authoritative_narrative_commit.md | preserved directly | 02_authority_architecture_and_runtime_laws.md |  |
| Scene identity canonical surface | ADR-0003; ai_stack/goc_scene_identity.py; ai_stack/tests/test_goc_scene_identity.py | preserved directly | 02_authority_architecture_and_runtime_laws.md | Kept as implementation-backed governance, not a side note. |
| Authoring / compiler / publish / runtime continuity | writers-room-and-publishing-flow.md; god_of_carnage_canonical_path.md; publishing-and-module-activation.md; activation proof reports | strengthened and integrated now | 03_content_authoring_publish_and_runtime_continuity.md | One of the main underrepresented seams restored into a single coherent canonical document. |
| Writers’ Room ↔ RAG overlap rules | V24_WRITERS_ROOM_RAG_OVERLAP_LEDGER.md; writers-room-and-publishing-flow.md | preserved directly | 03_content_authoring_publish_and_runtime_continuity.md |  |
| GoC authored module structure | content/modules/god_of_carnage/*; god_of_carnage_module_contract.md | preserved directly | 03_content_authoring_publish_and_runtime_continuity.md and 04_god_of_carnage_canonical_experience.md |  |
| GoC player-facing experience baseline | god-of-carnage-as-an-experience.md; god-of-carnage-player-guide.md | preserved directly | 04_god_of_carnage_canonical_experience.md |  |
| GoC A-line experience hardening | GoC wave AF-AY reports; GoC vertical slice hardening closure | strengthened and integrated now | 04_god_of_carnage_canonical_experience.md | Previously scattered over many wave reports; now expressed as canonical experience behavior. |
| GoC B-F experience hardening | GoC wave BA/C1/C2/D1/D2/E1/F1 reports | strengthened and integrated now | 04_god_of_carnage_canonical_experience.md | Restores character/social-performance depth and conversational afterlife. |
| Player shell loop and re-entry behavior | frontend shell loop proof; authoritative shell re-entry hardening | preserved directly | 05_player_ui_ux_and_operator_surfaces.md |  |
| Player-facing UI/UX expectations | backend/docs/UI_USABILITY.md; ROADMAP_MVP_ENGINE_AND_UI.md; runtime-interactions-player-visible.md | strengthened and integrated now | 05_player_ui_ux_and_operator_surfaces.md | Explicitly restored because this requirement family was source-supported but not canonically consolidated. |
| Admin / diagnostics / inspector surfaces | docs/admin/*; ROADMAP_MVP_ADMINISTRATION_TOOL_DIAGNOSIS.md | merged into canonical section | 05_player_ui_ux_and_operator_surfaces.md |  |
| Backend transitional retirement residue | backend transitional retirement ledger + resolution report | preserved as explicit bounded residue | 06_implementation_reality_and_proof_status.md and audit residue/task files | Not hidden under a false closure claim. |
| API projection governance | V24_API_PROJECTION_GOVERNANCE_LEDGER.md; docs/api/* | merged into another canonical section | 02_authority_architecture_and_runtime_laws.md | Kept as a projection-governance concern, not primary runtime truth. |
| Level A vs Level B closure posture | closure_level_classification_summary.md; gate_summary_matrix.md | strengthened and integrated now | 06_implementation_reality_and_proof_status.md | Runtime-proof judgment now made explicit in the canonical MVP set. |
| Reference scaffold proof layer | mvp/reference_scaffold/*; V24_PACKAGE_VALIDATION.md | preserved directly | 06_implementation_reality_and_proof_status.md |  |
| Source-preservation anti-loss rules | V24_SOURCE_PRESERVATION_LEDGER.md | preserved after normalization | audit outputs and changed-files record | This pass extends the anti-loss posture rather than replacing it. |

## Preservation conclusion

No material aspect found in the audited source set was silently dropped.
Where something was not folded into a “fully implemented now” claim, it was kept either as:

- an enduring target-state layer,
- a bounded residue,
- or an explicit runtime-proof follow-up task.
