# D2 Refocus Gate Report — Improvement Mutation Evaluation Loop Deepening

Date: 2026-04-04

## 1. Scope completed

Replaced the hardcoded keyword-based guard rejection in `_simulate_sandbox_turn()` with
semantic input classification via `interpret_player_input` (from `story_runtime_core`,
shimmed through `app.runtime.input_interpreter`).

Each sandbox turn now:
- calls `interpret_player_input(player_input)` and stores `interpreted_kind` and
  `interpretation_confidence` in the turn result
- determines `guard_rejected` semantically: only `explicit_command` turns whose
  `command_name` is in a defined meta/reset set (`reset`, `restart`, `quit`, `exit`,
  `help`, `pause`, `ooc`, `meta`) set the flag; all other kinds default to `False`
- assigns `triggered_tags` based on the semantic kind rather than raw keyword scans

`_evaluate_transcript()` was updated to:
- document that `guard_reject_rate` is now semantically derived
- compute and expose three new per-transcript metrics:
  `semantic_action_rate`, `semantic_speech_rate`, `semantic_command_rate`

## 2. Files changed

- `backend/app/services/improvement_service.py` — core change (sandbox turn + evaluation)
- `backend/tests/test_improvement_routes.py` — three new semantic tests added

## 3. What is truly wired

- `interpret_player_input` is called on every simulated sandbox turn (not bypassed)
- `interpreted_kind` is written into every turn dict and persisted in experiment JSON
- `guard_reject_rate` in the evaluation metrics is now driven by semantic classification,
  not keyword presence
- Semantic rate metrics (`semantic_speech_rate`, `semantic_action_rate`,
  `semantic_command_rate`) flow through to the full recommendation package via
  `build_recommendation_package → evaluate_experiment → _evaluate_transcript`

## 4. What remains incomplete

- `interpret_player_input` is a rule-based heuristic (keyword/prefix matching), not an
  LLM classifier. Classification confidence is therefore limited; e.g., a sentence like
  "I kill the lights" would not be guard-rejected under the new logic even though it
  contains the word "kill", because it is classified as `action`, not `explicit_command`.
  This is the correct semantics (turn off lights is not an escalation), but it means the
  guard metric is meaningful only as a command-interception signal, not a broad content
  moderation signal.
- The sandbox itself does not run real story engine turns; it simulates them. Evaluation
  metrics are heuristics, not ground-truth quality measurements.
- `_META_COMMAND_NAMES` is a hardcoded frozenset. It is not configurable at runtime or
  per-variant.

## 5. Tests added/updated

Three new tests in `backend/tests/test_improvement_routes.py`:

| Test | What it verifies |
|---|---|
| `test_sandbox_turn_uses_semantic_interpretation` | Speech-quoted input → `interpreted_kind == "speech"`, `guard_rejected == False` |
| `test_sandbox_turn_action_input_is_classified_correctly` | Action-verb input → `interpreted_kind == "action"`, correct tags |
| `test_sandbox_experiment_evaluation_uses_interpretation_signals` | Full experiment run: every turn has `interpreted_kind`, semantic rate metrics present in evaluation output |

## 6. Exact test commands run

```
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows/backend && \
  python -m pytest tests/ -k "improvement" -v 2>&1 | tail -40
```

## 7. Pass / Partial / Fail

**PASS**

## 8. Reason for the verdict

All 8 improvement tests pass (4 pre-existing route tests + 3 new semantic tests + 1
governance test). The semantic classification path is exercised end-to-end: input →
`interpret_player_input` → `interpreted_kind` in turn dict → metrics in evaluation. No
regressions in the broader test suite (3276 tests deselected, 8 selected, all passing).

## 9. Risks introduced or remaining

- **Dependency on `story_runtime_core`**: `improvement_service.py` now imports from
  `app.runtime.input_interpreter`, which wraps `story_runtime_core`. If that package is
  unavailable in a deployment context, the service will fail at import time. The shim
  already existed; this change raises the blast radius from runtime failure to service
  startup failure.
- **`guard_reject_rate` will be 0.0 for most natural language inputs**: Since only
  `explicit_command` turns with meta command names now set `guard_rejected`, typical
  story inputs will all produce rate 0.0. This is semantically accurate but means the
  metric has low discriminating power for most experiments. Downstream consumers
  (recommendation logic) should not treat rate 0.0 as a strong positive signal.
- **No adversarial robustness**: `interpret_player_input` uses prefix/token matching.
  It can be confused by unusual input patterns. The sandbox is not hardened against
  adversarial prompt construction.
