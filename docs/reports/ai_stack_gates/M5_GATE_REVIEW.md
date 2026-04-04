# Milestone 5 — Gate Review

**Date:** 2026-04-04  
**Status:** **PASS**  
**Recommendation:** **Proceed** (to M6 planning)

## Scope

- Player input interpretation contract (`docs/architecture/player_input_interpretation_contract.md`).
- Runtime interpreter producing structured `PlayerInputInterpretation`.
- Story turn path consumes interpretation inside World-Engine `StoryRuntimeManager` (and backend exposes a **preview** of interpretation on the proxy response).
- Explicit commands remain a **special case** inside the same schema.
- Diagnostics expose raw text, kind, confidence/ambiguity, handling path, and model route.

## Files changed (M5 scope)

| Area | Path |
|------|------|
| Architecture | `docs/architecture/player_input_interpretation_contract.md` (new) |
| Core | `story_runtime_core/models.py`, `input_interpreter.py` |
| Core | `story_runtime_core/tests/test_input_interpreter.py` |
| Host | `world-engine/app/story_runtime/manager.py` (interpret → task_type → routing) |
| Backend | `backend/app/api/v1/session_routes.py` (`backend_interpretation_preview` on `/turns`) |
| Backend | `backend/app/runtime/input_interpreter.py` (shim) |
| E2E test | `world-engine/tests/test_story_runtime_api.py` |

## Design decisions

- **Heuristic** interpreter (prefixes, verbs, speech markers, token length) — no claim of LLM-based interpretation in M5.
- **Commands:** Leading `/` or `!` → `InterpretedInputKind.EXPLICIT_COMMAND` with `command_name` / `command_args`.
- **Meta:** `ooc:`, `meta:`, `out of character:` → `META`.
- **Routing hook:** `explicit_command` and `meta` map to `classification` task type for SLM-biased routing; other kinds map to `narrative_generation` (LLM-biased).

## Tests run

```text
cd <repo-root>
python -m pytest story_runtime_core/tests/test_input_interpreter.py -q --tb=short

cd world-engine
python -m pytest tests/test_story_runtime_api.py -q --tb=short

cd backend
python -m pytest tests/test_session_routes.py -q --tb=short
```

**Result:** Pass.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| NL interpretation is a real runtime layer | **Pass** |
| Commands are not the only architecture | **Pass** |
| Structured interpretation visible in diagnostics | **Pass** |
| Tests cover representative input classes | **Pass** |

## Gate review — required extras

### Interpretation object / schema?

- **`PlayerInputInterpretation`** (`story_runtime_core/models.py`): `raw_text`, `normalized_text`, `kind` (`InterpretedInputKind`), `confidence`, optional `ambiguity`, `intent`, `entities`, optional `command_name` / `command_args`, `selected_handling_path`.

### How are commands recognized without dominating?

- Syntactic prefix rule (`/`, `!`) maps to `explicit_command` but **all other** inputs go through NL categories (speech, action, mixed, etc.); routing only uses command/meta for SLM-biased **task_type**, not for replacing NL handling.

### Where is interpretation performed?

- **Authoritative:** `StoryRuntimeManager.execute_turn` (World-Engine).
- **Preview:** `interpret_player_input` in backend before proxying (for operator visibility; engine re-interprets for the committed turn record).

### Ambiguities intentionally unresolved?

- Fine-grained disambiguation between dialogue and inner monologue, multi-intent utterances, and locale-specific phrasing — **deferred** to model-assisted interpretation (M6+).

## Known limitations

- Heuristic boundaries may misclassify edge utterances; confidence scores are not calibrated against human labels.

## Risks

- Writers may need tuning of markers (`ACTION_VERBS`, etc.) per module genre.

## Recommendation

**Proceed** to M6+ (LangChain/LangGraph/RAG/MCP orchestration as per architecture doc).
