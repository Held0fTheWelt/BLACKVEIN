# Area 2 — Workstream B reproducibility gates (G-B)

Workstream B closes **operational** reproducibility: deterministic startup profiles, real clean-environment install paths, explicit dependencies, stable test profiles, **real** documented pytest commands aligned with `backend/pytest.ini`, and honest documentation (no over-claimed smoke coverage).

These gates **do not** change `route_model` semantics, `StoryAIAdapter`, or guard/commit/reject authority.

**Binding vocabulary:** [`area2_dual_workstream_binding.md`](./area2_dual_workstream_binding.md)

**Canonical commands (code):** [`backend/app/runtime/area2_validation_commands.py`](../../backend/app/runtime/area2_validation_commands.py)

| Gate ID | Pass condition | Failure meaning | Test |
|---------|----------------|-----------------|------|
| **G-B-01** | Named startup profiles map deterministically to bootstrap and registry expectations. | Ambiguous profile → bootstrap truth. | `test_g_b_01_startup_profile_determinism_gate` |
| **G-B-02** | Healthy bootstrap-on and isolated bootstrap-off behaviors are testable and distinct. | Bootstrap posture confusion between tests and prod-like paths. | `test_g_b_02_bootstrap_reproducibility_gate` |
| **G-B-03** | Repository provides explicit setup scripts and requirements paths for clean install. | No real clean-environment path. | `test_g_b_03_clean_environment_validation_gate` |
| **G-B-04** | Declared requirements files exist and include pytest + asyncio tooling used by Area 2 suites. | Dependency truth insufficient. | `test_g_b_04_dependency_setup_explicitness_gate` |
| **G-B-05** | Dual-closure regression modules collect under default backend pytest config without undocumented env requirements. | Hidden machine-local state required. | `test_g_b_05_test_profile_stability_gate` |
| **G-B-06** | Documented markdown contains the canonical invocation string and module list from `area2_validation_commands`; collect-only run succeeds from `backend/`. | Docs/commands/repo layout diverge. | `test_g_b_06_validation_command_reality_gate` |
| **G-B-07** | Listed docs reference every **G-B-01** … **G-B-07** and `area2_validation_commands` or equivalent pointer. | Documentation drift from reproducibility truth. | `test_g_b_07_documentation_truth_for_reproducibility_gate` |

## Related

- Combined closure: [`area2_dual_workstream_closure_report.md`](./area2_dual_workstream_closure_report.md)
- Workstream B report: [`area2_reproducibility_closure_report.md`](./area2_reproducibility_closure_report.md)
- Setup guide: [`docs/testing-setup.md`](../testing-setup.md)
