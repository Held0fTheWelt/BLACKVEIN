# A1-next Gate Report — Natural input interpretation hardening

Date: 2026-04-04

## 1. Scope completed

- Deepened **`interpret_player_input`**: conflicting action+reaction (short utterances), dialogue lead-ins without quotes (`Tell him …`, `I ask …`), silence/withhold patterns mapped to **`intent_only`**, explicit **`ambiguity`** code `conflicting_action_reaction`, and conservative **`runtime_delivery_hint`** (`say` / `emote` / `narrative_body`).
- Added **`story_runtime_core.runtime_delivery`**: `natural_input_to_room_command` and `extract_spoken_text_for_delivery` so thin hosts map NL to `say` vs `emote` consistently with interpretation.
- Wired **World-Engine WebSocket live-run** [`world-engine/app/runtime/manager.py`](../../world-engine/app/runtime/manager.py) to use the shared mapper (material path: natural input → room command shape).
- Appended a **structured interpretation summary** to **`model_prompt`** in [`wos_ai_stack/langgraph_runtime.py`](../../wos_ai_stack/langgraph_runtime.py) after retrieval so generation sees kind, confidence, ambiguity, intent, path, and delivery hint (authoritative story graph path).
- Updated [`docs/architecture/player_input_interpretation_contract.md`](../../docs/architecture/player_input_interpretation_contract.md): delivery hints, ambiguity codes, low-confidence continuation, backend preview vs authoritative graph interpretation.

## 2. Files changed

- `story_runtime_core/models.py`
- `story_runtime_core/input_interpreter.py`
- `story_runtime_core/runtime_delivery.py` (new)
- `story_runtime_core/__init__.py`
- `story_runtime_core/tests/test_input_interpreter.py`
- `story_runtime_core/tests/test_runtime_delivery.py` (new)
- `wos_ai_stack/langgraph_runtime.py`
- `wos_ai_stack/tests/test_langgraph_runtime.py`
- `world-engine/app/runtime/manager.py`
- `world-engine/tests/test_story_runtime_api.py`
- `docs/architecture/player_input_interpretation_contract.md`
- `docs/reports/ai_stack_gates/A1_NEXT_GATE_REPORT.md`

## 3. What was deepened versus what already existed

- **Already existed:** Single-pass keyword interpreter; graph `interpreted_input`; backend `backend_interpretation_preview`; WebSocket path collapsing almost all NL to `say` if `speech|mixed` else `emote`.
- **Deepened:** Competing-signal honesty, richer speech detection without exploding taxonomy, shared delivery mapping, **prompt-level** coupling of interpretation to the model call, contract clarity on authority and continuation under low confidence.

## 4. Interpretation behaviors that became stronger

- **Mixed / ambiguous honesty:** Action + short interjection without dialogue → `mixed` + `conflicting_action_reaction` + lower confidence + `narrative_body` delivery (avoids fake “clean” action).
- **Speech without quotes:** `Tell him …` / `I ask …` classify as **`speech`** with `SAY` when appropriate.
- **Silence / refusal:** Clear withhold phrases → **`intent_only`** / `withheld_response_or_silence` instead of generic long-string `ambiguous`.
- **Commands:** Unchanged prefix recognition; still **`selected_handling_path="command"`** and no delivery hint on command/meta rows.

## 5. How ambiguous / mixed input is handled

- **Ambiguous kind:** Still used for long undifferentiated prose; **`narrative_body`** delivery and explicit ambiguity string.
- **Mixed with conflict:** Dedicated ambiguity code; conservative emote channel for thin hosts; graph prompt exposes the ambiguity to generation.

## 6. Command-special-case behaviors that still remain

- **`/` and `!` prefixes** → `explicit_command` with `command_name` / `command_args`.
- WebSocket **`_map_explicit_command`** still bypasses NL interpretation for slash forms (bounded special case).

## 7. Tests added/updated

- `story_runtime_core`: extended interpreter tests; new `test_runtime_delivery.py`.
- `wos_ai_stack`: `test_runtime_turn_graph_appends_interpretation_summary_to_model_prompt` (prompt + `interpreted_input` assertions).
- `world-engine`: extended `test_story_turns_cover_primary_free_input_paths` (withhold → `intent_only`, conflicting → `mixed`).

## 8. Exact test commands run

```text
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows
$env:PYTHONPATH="c:\Users\YvesT\PycharmProjects\WorldOfShadows"
python -m pytest story_runtime_core/tests -v --tb=short
```

Result: **21 passed**, exit code **0** (Windows, Python 3.13.12).

```text
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows\backend
$env:PYTHONPATH="c:\Users\YvesT\PycharmProjects\WorldOfShadows;c:\Users\YvesT\PycharmProjects\WorldOfShadows\backend"
python -m pytest ..\wos_ai_stack\tests\test_langgraph_runtime.py -v --tb=short --override-ini="addopts="
```

Result: **10 passed**, exit code **0**.

```text
cd c:\Users\YvesT\PycharmProjects\WorldOfShadows\world-engine
$env:PYTHONPATH="c:\Users\YvesT\PycharmProjects\WorldOfShadows;c:\Users\YvesT\PycharmProjects\WorldOfShadows\world-engine"
python -m pytest tests\test_story_runtime_api.py -v --tb=short
```

Result: **2 passed**, exit code **0** (runtime ~36s in this environment).

## 9. Verdict

**Pass**

## 10. Reason for verdict

- Interpretation robustness and **downstream effects** are materially improved: delivery mapping, graph **prompt** content, and tests cover ambiguous/mixed/reaction/command paths plus integration surfaces.
- Command handling remains **secondary and bounded**; NL remains default semantics.
- Report does not claim full NLP maturity; progression logic stays conservative (scene rules unchanged in this milestone).

## 11. Remaining risk

- Heuristics can still misclassify rare phrasing; token-based scene hints in progression (A2-next) remain separate from interpretation quality.
- Full-stack latency for world-engine HTTP tests is high in some environments; CI should allow sufficient timeout.
