# Milestone 2 — Gate Review

**Date:** 2026-04-04  
**Status:** **PARTIAL** (criteria below)  
**Recommendation:** **Proceed with caution**

## Scope

- Introduce `story_runtime_core/` as a reusable package for shared narrative-runtime contracts.
- Reduce backend-only ownership of cross-cutting runtime concerns by centralizing interpretation and (with M4) model metadata/adapters in the core.
- Explicit transitional shims in backend.
- Move or mirror tests into the core package.

## Files changed (M2 scope)

| Area | Path |
|------|------|
| Package | `story_runtime_core/` (`pyproject.toml`, `__init__.py`, `models.py`, `input_interpreter.py`, `model_registry.py`, `adapters.py`) |
| Backend shim | `backend/app/runtime/input_interpreter.py` |
| Architecture | `docs/architecture/backend_runtime_classification.md` |
| Tests | `story_runtime_core/tests/test_input_interpreter.py`, `test_model_registry.py`, `test_adapters.py` |

**Note:** `model_registry.py` and `adapters.py` are **also** the M4 model layer; they live in the same package as the shared core extraction. M4 gate reviews focus on provider/registry behavior; this gate focuses on **extraction boundaries**.

## Design decisions

- **Shared core** holds: `PlayerInputInterpretation`, `InterpretedInputKind`, `interpret_player_input`, model registry types, and HTTP-capable model adapters (M4).
- **Backend shim** re-exports `interpret_player_input` so Flask code can depend on a stable import path while the implementation remains shared.

## Migrations / compatibility

- Backend-local modules (`turn_executor`, `validators`, `ai_adapter`, etc.) remain **in-process** for mock/God-of-Carnage depth; they are **not** deleted in M2.

## Tests run

```text
cd <repo-root>
python -m pytest story_runtime_core/tests -q --tb=short
```

**Result:** Pass.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Shared story runtime core exists | **Pass** |
| Backend story runtime relies on shared core for **all** business logic | **Partial** — relies on core for **NL interpretation** (and model routing types used by the engine path); **full** turn execution, validation stack, and AI story adapters remain backend-local |
| Compatibility shims explicit and minimal | **Pass** (`input_interpreter.py` shim) |
| Shared core tests pass | **Pass** |

## Gate review — required extras

### Which runtime files remain backend-specific and why?

- **`turn_executor.py`, `validators.py`, `scene_legality.py`, `ai_turn_executor.py`, `adapter_registry.py` (story adapters), etc.** — deeply coupled to `ContentModule`, Flask session models, and existing W2/W3 contracts; moving them would be a large refactor and risk God-of-Carnage regressions without a phased plan.

### Which logic moved fully into shared core?

- **Player input interpretation** (heuristic classifier → `PlayerInputInterpretation`).
- **Model registry / routing policy types** and **concrete HTTP adapters** (shared with M4; consumed by World-Engine host).

### Shims and removal plan?

- **`backend/app/runtime/input_interpreter.py`** — transitional re-export; remove when all imports reference `story_runtime_core` directly.

### Duplication after M2?

- **Interpretation:** single implementation in `story_runtime_core` (backend shim only).
- **Turn execution / validation:** still backend-local; **parallel** simplified turn pipeline in World-Engine `StoryRuntimeManager` for authoritative HTTP story API (by design until deeper unification).

## Known limitations

- Full policy/validation extraction into core is **deferred** (see closure report).

## Risks

- Two execution depths (rich backend mock vs engine story host) until further convergence.

## Recommendation

**Proceed with caution** — M3–M5 correctly anchor **authoritative** story turns on World-Engine; plan M6+ to migrate more backend-only logic only with targeted tests.
