# Task 4 — Residual Risk Register

| Risk ID | Residual risk | Scope class | Owner | Mitigation | Status |
|---|---|---|---|---|---|
| R-01 | Physical GoC namespace move remains blocked because per-reference P0 closure is incomplete | blocker | cleanup owner | keep hard no-move gate; complete per-reference dependency closure before movement | open |
| R-02 | Path-sensitive RAG lane behavior may drift under future movement (`content/modules` vs `content/published`) | contract/workflow | ai_stack owner | movement precheck must include RAG lane golden tests and path-map proof | open |
| R-03 | Writers-room `implementation.god_of_carnage.*` renamespace could break presets/registry chains | ownership/registry | writers-room owner | maintain no-renamespace rule until dependency gate lift and registry repair plan | open |
| R-04 | Mirror drift risk between `outgoing/*` and `docs/g9_evaluator_b_external_package/*` | docs/ownership | docs + release owner | enforce mirror-sync policy and closure check in validation command set | open |
| R-05 | Clone-local evidence references can still mislead if new docs omit caveats | docs truth | audit docs owner | require tracked-vs-local evidence framing in gate/audit docs | open |
| R-06 | Mixed audience in `docs/testing/README.md` may continue causing interpretation drift | docs placement | docs owner | continue Task 2 audience split and remove stale mixed-role text | open |
| R-07 | ~~Nested `backend/world-engine/app/var/runs/*`~~ **closed (2026-04-09):** tracked `improvement_experiment_*.json` relocated to `backend/fixtures/improvement_experiment_runs/`; residual empty tree policy is non-P0 | residue/path taxonomy | backend owner | optional `.gitkeep` or prune empty dirs if policy requires | closed |

## Acceptance rule

- None of the residual risks above are accepted as allowing GoC physical namespace movement.
- Movement remains prohibited until R-01, R-02, and R-03 are closed with explicit evidence.

