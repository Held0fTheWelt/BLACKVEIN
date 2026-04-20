# Wave 1 Pre-Work Stand-Check (Completion Pass)

Date: 2026-04-13

## Classification Before This Pass

| Area | Classification | Evidence |
|---|---|---|
| Shared resolver/path decoupling | mostly fulfilled | `repo_paths.py` in all suites uses `marker_text=None`; no active `marker_text="world-of-shadows-hub"` matches in suite runtime paths |
| Despaghettify portability | mostly fulfilled | import-time guards and fallback root logic present; non-WoS portability test already exists |
| Manifest/bootstrap core | fulfilled | `fy_platform/tools/cli.py` supports `--project-root` and env override; manifest tests present |
| Envelope versioning/stability | fulfilled | `artifact_envelope.py` has versioned fields; golden serialization test exists |
| Contractify base-envelope alignment | fulfilled | `contractify/tools/hub_cli.py` projects suite payload to shared `findings`/`evidence` |
| Compatibility matrix completeness | partially fulfilled | matrix had suites/help/exit/output surfaces but incomplete command flag coverage and filename surface inventory |
| Deprecation matrix completeness | open | `deprecation_matrix.wave1.json` had empty `entries` |
| Deprecation regression evidence | partially fulfilled | deprecation behavior implemented in code, but tests did not consistently assert sidecar + envelope deprecation evidence |
| Portability verification | mostly fulfilled | synthetic portability tests present (`library_only`, `backend_service`) plus despag non-WoS check test |

## Remaining Closure-Critical Gaps Identified

1. `deprecation_matrix.wave1.json` lacked concrete active entries for implemented deprecations.
2. Compatibility baseline lacked explicit command flag surface coverage.
3. Regression tests were missing explicit assertions for deprecation sidecar/envelope outputs across migrated suites.

## Scope Guard

No archetype adapter, plugin marketplace, or Wave-2 extension work required for this pass.
