# Stage 15 Release Report

## Scope

This stage integrates `mvpify` as a first-class suite into the autark fy workspace and adds a concrete AI capability layer report across all suites.

## Implemented in this stage

- added `mvpify` as a core suite with:
  - `adapter/service.py`
  - `adapter/cli.py`
  - tool tests and adapter tests
- extended generic `fy-suite` runner to support `mvpify`
- extended suite catalog, command reference, quality policy, and cross-suite intelligence to include `mvpify`
- implemented `mvpify` import materialization:
  - normalize imported prepared MVP bundles under `mvpify/imports/<id>/normalized`
  - mirror imported MVP documentation under `docs/MVPs/imports/<id>`
  - write reference manifests so temporary implementation folders can later be removed without losing documentation traceability
- implemented `fy-platform ai-capability-report` support in the product layer
- extended `observifyfy` to track `mvpify` and its mirrored MVP import lane
- hardened `contractify` import detection so it can import nested prepared MVP bundles like the current World of Shadows MVP v24 bundle in both normal and legacy modes

## Real validation performed

- `compileall`: passed
- full test suite: **75 passed**
- real bundle import checks performed against:
  - `/mnt/data/world_of_shadows_mvp_v24_backend_transitional_retirement_ultra_narrow_final_blockers.zip`
- validation outcome:
  - `contractify import`: passed
  - `contractify legacy-import`: passed
  - `mvpify` prepared-MVP import + docs mirroring: passed
  - `observifyfy` refresh after import: passed

## AI / Graph / Retrieval improvements actually wired in

The package now exposes and documents the following implemented mechanisms:

- shared semantic index
- shared context pack service
- shared model router with task-aware SLM/LLM policy lanes
- shared decision policy
- shared graph recipe surfaces for inspect / audit / triage / context-pack flows
- cross-suite intelligence signals
- suite-level status pages and most-recent-next-steps surfaces
- AI capability matrix exported under `docs/platform/ai_capability_matrix.*`
- mvpify AI context with managed roots, mirrored docs references, and suite-family orchestration guidance

## Aspirational but not directly executed here

These remain valuable next upgrades, but were kept as documented aspirations rather than fake implementations:

- real external LangGraph runtime checkpointers with pause/resume durability
- direct LangChain-backed provider integrations for structured output and model backends
- stronger vector/embedding retrieval backends beyond the current lightweight internal index
- richer per-suite subgraph orchestration when external runtime dependencies are allowed

## Packaging note

This release package is rooted at `'fy'-suites` and includes the integrated Stage 15 state only.
