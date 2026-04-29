# MVP_Live_Runtime_Completion

This package is the renamed locator-first implementation guide set for the World of Shadows — God of Carnage live runtime completion MVP.

The package preserves the final implementation target:

- `god_of_carnage` remains the canonical content module.
- `god_of_carnage_solo` remains a runtime profile, not content.
- The player must choose Annette or Alain.
- The selected character is human-controlled.
- The other canonical God of Carnage characters act as free NPC dramatic actors.
- A real `live_dramatic_scene_simulator` runs in the live play path.
- The final output is structured staged dramatic/chat blocks, not legacy blob text.
- Diagnostics, Narrative Gov, and Langfuse or deterministic trace export must prove the live runtime path.
- `docker-up.py`, `tests/run_tests.py`, GitHub workflows, and TOML/tooling configs remain mandatory operational gates.

## Execution Mode

This is a locator-first implementation package.

Before any code patching, each MVP must complete its source locator artifact:

```text
tests/reports/MVP_Live_Runtime_Completion/MVP<NUMBER>_SOURCE_LOCATOR.md
```

Before closing any MVP, each MVP must complete its operational evidence artifact:

```text
tests/reports/MVP_Live_Runtime_Completion/MVP<NUMBER>_OPERATIONAL_EVIDENCE.md
```

## Guide Sequence

1. `01_experience_identity_and_session_start.md`
2. `02_runtime_state_actor_lanes_content_boundary.md`
3. `03_live_dramatic_scene_simulator.md`
4. `04_observability_diagnostics_langfuse_narrative_gov.md`
5. `05_interactive_text_adventure_frontend_e2e.md`

## Included Report

- `tests/reports/MVP_Live_Runtime_Completion_IMPLEMENTATION_REPORT.md`

## Final Status

```text
Guide package status: guides_implementation_ready
Safe to give MVP 1 to Claude/Cursor now: yes, locator-first only
Safe to use all five as full implementation roadmap: yes
```
