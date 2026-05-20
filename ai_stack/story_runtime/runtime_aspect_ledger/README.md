# Runtime Aspect Ledger

This package owns the runtime-aspect ledger import surface:
`ai_stack.story_runtime.runtime_aspect_ledger`.

The ledger records per-turn runtime intelligence for LangGraph, world-engine
manager code, validation authority, readiness sidecars, diagnostics, governance
views, and Langfuse/MCP inspection. Callers should continue importing from the
package root, not from implementation submodules.

## Current Layout

| File | Role |
|------|------|
| `__init__.py` | Compatibility-preserving package module. It contains the existing ledger implementation so direct imports and monkeypatch-based tests keep the same module-global semantics as the former `runtime_aspect_ledger.py` file. |
| `README.md` | Package boundary and migration notes. |

## Next Split

The package boundary is now in place so later Despaghettify passes can move
cohesive sections out of `__init__.py` without changing the public import path.
Natural module candidates are:

- `records.py` for `RuntimeAspectLedger`, aspect constants, and stable JSON
  helpers.
- `semantic_capability_projection.py` for capability selection, validator
  plan, and validator dispatch projections.
- `adr0041_authority.py` for ADR-0041 drift classification, feature flags,
  validation authority preview, and harness reporting.
- `runtime_intelligence_projection.py` for the large
  `build_runtime_intelligence_projection` assembly.
- `score_metadata.py` for aspect score metadata and projection labels.

Until those moves happen, keep `__init__.py` as the compatibility module rather
than a thin re-export facade; tests and diagnostic tools patch module globals on
`ai_stack.story_runtime.runtime_aspect_ledger` directly.
