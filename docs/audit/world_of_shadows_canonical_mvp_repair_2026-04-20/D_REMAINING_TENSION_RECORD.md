# Remaining Tension Record

Only tensions that still do **not** fully carry or are still **not** fully proven are listed here.

## `GT-01-P` Player support and accessibility are now carried, but still under-proven

- Current truth: recap/help/save-load/re-entry/accessibility obligations are now explicit in the canonical surface model.
- What remains open: the active player shell proves re-entry and recovery better than it proves full save/load UI, evaluator-grade accessibility, or fully productized recap/help behavior.
- Where this stays visible: `docs/MVPs/world_of_shadows_canonical_mvp/07_player_ui_ux_admin_and_inspection_surfaces.md`, `docs/user/runtime-interactions-player-visible.md`, `docs/user/god-of-carnage-player-guide.md`.

## `GT-06-O` Player-visible transport convergence remains only partly closed

- Current truth: committed player path, live-room snapshot path, and operator bundle path are now better classified.
- What remains open: the package still does not prove that all session-facing surfaces have been replayed and converged into one cleanly closed player contract.
- Where this stays visible: `docs/MVPs/world_of_shadows_canonical_mvp/07_player_ui_ux_admin_and_inspection_surfaces.md`, `13_authoring_retrieval_and_runtime_boundary_contract.md`, `10_residues_and_runtime_proof_tasks.md`.

## `GT-08-P` Evidence ladder is clearer, but fresh replay is still incomplete

- Current truth: intended scope, implemented reality, carried-forward evidence, newly verified evidence, and unresolved burden are now separated explicitly.
- What remains open: much of the package's strongest runtime evidence is still carried forward from prior validation bundles rather than freshly replayed in this pass.
- Where this stays visible: `docs/MVPs/world_of_shadows_canonical_mvp/09_implementation_reality_runtime_maturity_and_proof.md`, `A_MASTER_REPAIR_REPORT.md`.

## `GT-11-P` Surface ambition still exceeds fully replayed proof

- Current truth: the package now carries the real breadth of player/operator/authoring/control-plane surfaces more honestly.
- What remains open: broader surface ambition is still ahead of fresh end-to-end proof, especially for accessibility, save/load UI, preview/revision surfaces, and full control-plane replay.
- Where this stays visible: `docs/MVPs/world_of_shadows_canonical_mvp/07_*`, `14_*`, `15_*`, `16_*`, `09_*`.

## `GT-12-O` Evaluator-independent Level B closure remains blocked

- Current truth: the package explicitly refuses to claim evaluator-independent Level B closure.
- What remains open: no new evidence in this pass closes that gap.
- Where this stays visible: `docs/MVPs/world_of_shadows_canonical_mvp/09_*`, `10_*`, `11_*`, `A_MASTER_REPAIR_REPORT.md`.

## `NT-01` Root contract mirrors still carry sync risk

- Current truth: root `docs/*_GOC.md` files are now clearly labeled as compatibility mirrors.
- What remains open: duplicate text still exists in two locations, so future edits could drift unless maintainers keep both lanes aligned or retire one lane cleanly.
- Where this stays visible: `docs/MVPs/README.md`, `docs/CANONICAL_TURN_CONTRACT_GOC.md`, `docs/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/GATE_SCORING_POLICY_GOC.md`.

## `NT-02` Touched governance link-check remains failing for pre-existing FY-suite surfaces

- Current truth: the repaired canonical MVP route is no longer the source of the new link-check failures introduced during this pass.
- What remains open: the touched-governance link check still fails because of pre-existing missing FY-suite files and missing despaghettify state files.
- Where this stays visible: `validation/V24_TOUCHED_GOVERNANCE_LINK_CHECK.md`, `validation/V24_TOUCHED_GOVERNANCE_LINK_CHECK.json`.
