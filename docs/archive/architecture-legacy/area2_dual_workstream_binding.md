# Area 2 — Dual workstream binding interpretation (minimal)

This file fixes **operational vocabulary** for the dual closure (Workstream A: practical convergence; Workstream B: reproducibility). It does not restate full gate tables.

## Workstream A

| Term | Binding meaning |
|------|-----------------|
| **Practical convergence** | Canonical Runtime, Writers-Room, and Improvement paths each resolve **one** primary Task 2A routing/spec authority line in real execution; auxiliary lines are visible in `AREA2_AUTHORITY_REGISTRY` and do not present a second hidden policy for the same path. |
| **Acceptable bounded auxiliary layering** | Translation, compatibility, and support components are **registered**, **layer-tagged**, and either scoped to explicit surfaces or explicitly **non-canonical** (empty `canonical_for_task2a_paths` for parallel stacks). |
| **Practical split-brain** | Operators could reasonably believe two different routing policies apply to the **same** canonical path (e.g. LangGraph `RoutingPolicy` treated as co-equal with `route_model` on WR/Improvement HTTP). |
| **Healthy canonical coherence** | Under `testing_bootstrap_on`, Runtime staged routing and bounded HTTP stages remain **eligible** (not routine `no_eligible_adapter`) and expose consistent `area2_operator_truth` shapes where applicable. |
| **No-eligible non-normalization** | True `no_eligible_adapter` on routed stages is classified and surfaced so it is **not** read as ordinary healthy canonical success (`route_status` / `NoEligibleDiscipline` honesty). |
| **Operator-grade convergence readability** | `area2_operator_truth.legibility` and `canonical_authority_summary` expose authority, profile, operational state, route status, selected-vs-executed rollup, and primary concern **from existing facts** (no new telemetry). |

## Workstream B

| Term | Binding meaning |
|------|-----------------|
| **Reproducibility** | A fresh machine can install declared dependencies and run **documented** pytest commands for Area 2 gates without undocumented local knowledge. |
| **Startup / bootstrap determinism** | Named profiles in `area2_startup_profiles` map **deterministically** to bootstrap flag, expected registry shape after `create_app`, and classification inputs. |
| **Clean-environment validation** | `setup-test-environment.sh` / `.bat` plus `backend/requirements*.txt` form an explicit install path; validation commands use **`cd backend`** and pytest’s configured `pythonpath`. |
| **Dependency / setup truth** | Production and test requirements files **exist**, are referenced by setup scripts and docs, and list packages needed for async pytest and Area 2 suites. |
| **Test-profile stability** | `testing_isolated` vs `testing_bootstrap_on` is selected by **fixtures / config classes**, not by undocumented per-developer env toggles for the dual-closure regression list. |
| **Validation-command reality** | Documented commands match repository layout (`backend/` cwd), `backend/pytest.ini` behavior (including default `addopts` coverage — gate runs use `--no-cov`), and the module list enforced in code. |
| **Acceptable bounded environment sensitivity** | File DB paths, production secrets, and optional provider credentials may vary; Area 2 **dual-closure** tests must remain valid on in-memory `TestingConfig` without live provider keys. |

## Unchanged semantics (explicit)

Task 2A **`route_model`** policy semantics and precedence, **`StoryAIAdapter`**, guard legality, commit semantics, reject semantics, and authoritative Runtime mutation rules are **out of scope for modification** in this closure; gates and docs may only **observe** them.
