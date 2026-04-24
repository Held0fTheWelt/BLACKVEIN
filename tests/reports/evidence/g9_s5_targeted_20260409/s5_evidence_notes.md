# S5 evidence notes — `g9_s5_targeted_20260409`

**Scope:** `s5_targeted_partial` — not a full six-scenario G9 Level A run. Does not replace `tests/reports/evidence/g9_level_a_fullsix_20260409/` or its score matrix.

## Where primary failure occurs

- Routed primary provider (`openai`) invokes `ErrorAdapter` on turn `trace-p3-c3` (`invoke_model` path fails with `simulated_generation_failure`).
- Graph routing records `fallback_chain` including `openai:gpt-4o-mini` and `ollama:llama3.2`; `fallback_stage_reached` is `graph_fallback_executed` (see `failure_turn.routing` in `scenario_goc_roadmap_s5_primary_failure_fallback.json`).

## Where fallback / recovery occurs

- Runtime node `fallback_model` calls the **`mock`** adapter (graph-managed raw path). The anchor wires `mock` to a succeeding `JsonAdapter` while primary remains `ErrorAdapter`.
- `proposal_normalize` coerces JSON `narrative_response` from raw fallback text into structured proposal when LangChain did not populate `structured_output`.
- After validation `approved` and commit, `visible_output_bundle.gm_narration` shows in-scene lines (Annette + narrative text) instead of preview-only staging.

## Why the path is dramatically stronger (evidence-grounded)

- Prior full-six matrix row (`g9_level_a_fullsix_20260409`) scored low on dramatic/character dimensions partly because `mock` matched the failing primary adapter, so recovery never produced a committed beat.
- This bundle shows committed `blame_pressure` continuity, `dramatic_quality_status` / `run_classification` **pass**, and operator-visible routing aligned with the outcome.

## Reproduce

- Pytest: see `pytest_s5_anchor.txt` in this directory.
- Structured capture: `python scripts/g9_level_a_evidence_capture.py tests/reports/evidence/<audit_run_id> --audit-run-id <audit_run_id> --evidence-run-scope s5_targeted_partial` from repo root with `PYTHONPATH` set to the repo root.
