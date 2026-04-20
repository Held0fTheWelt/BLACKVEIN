# Contractify — last-mile closure (2026-04-13)

Narrow pass: **operational evidence**, **one lifecycle conflict gap**, **doc alignment**, **closure record**, **fixture reuse** — no scope expansion.

## 1. Verified gaps before this pass

| Topic | Status before |
|-------|-----------------|
| **A. Reports** | `reports/` had only `.gitkeep` + README; no committed full JSON proving discover/audit output. |
| **B. Conflict / lifecycle** | Index row vs retired ADR and supersession gaps were covered; **projections still allowed to pin retired contract ids** without a dedicated signal. |
| **C. Versioning** | Declared OpenAPI version + ADR `Status:` + `Supersedes:` relations already operational; no change to breaking-change policy. |
| **D. Packaging** | Hub `.gitignore`, git-tracked hygiene test — already sufficient; no new bytecode tracked. |
| **E. Closure artifact** | `FINALIZATION_PASS_2026-04-13.md` existed; this file adds **last-mile** evidence-specific closure. |

## 2. Already sufficient (left untouched)

- Hermetic `conftest` strategy (moved to shared [`../tools/minimal_repo.py`](../tools/minimal_repo.py), same tree).
- Postmanify SHA drift, docify scan-root drift, despag JSON hint, duplicate index, ADR vocabulary, fingerprint mismatch, orphan projection, Active-row vs retired ADR.
- Relation caps, `max_contracts` discipline, anti-bureaucracy ceilings in scope doc.

## 3. Closure slices executed

1. **Committed report fixtures** — [`reports/committed/audit.hermetic-fixture.json`](../reports/committed/audit.hermetic-fixture.json), [`discover.hermetic-fixture.json`](../reports/committed/discover.hermetic-fixture.json) with fixed `generated_at` and neutral `repo_root` label; [`../tools/freeze_committed_reports.py`](../tools/freeze_committed_reports.py) to regenerate.
2. **Lifecycle / projection** — `detect_projection_pins_retired_source_contract` when `contracts=` is supplied to `detect_all_conflicts`.
3. **Evidence alignment** — `reports/README.md`, hub `README.md`, `CONTRACT_GOVERNANCE_SCOPE.md`, `examples/README.md` pointers; `build_discover_payload` shared with CLI.
4. **Hygiene / structure** — `minimal_repo.py` deduplicates fixture source; no `__pycache__` committed.

## 4. Real report artifacts added

- `reports/committed/audit.hermetic-fixture.json` — full audit: contracts, projections, relations, drifts, conflicts, actionable_units, stats.
- `reports/committed/discover.hermetic-fixture.json` — discover payload including `repo_root` + `automation_tiers_sample`.

## 5. Conflict / versioning / lifecycle improvement

- New **`classification`**: `lifecycle_projection_vs_retired_anchor` when a projection’s `source_contract_id` maps to a **superseded** or **deprecated** discovered contract (inventory-only; not semantic code proof).

## 6. Docs / evidence aligned

- README + scope conflict tables; reports README explains gitignore depth vs `committed/`.

## 7. Hygiene

- No new generated noise under `contractify/tools/` beyond the intentional freeze script; `repo_root` in fixtures scrubbed to a stable label.

## 8. Tests

- `python -m pytest "'fy'-suites/contractify/tools/tests" -q` — includes `test_committed_reports.py` and `test_projection_pins_retired_source_contract_unit`.

## 9. Completeness within scope

The suite now ships **reviewable, committed, full JSON** evidence alongside small `examples/*.sample.json` shapes, one additional **bounded** lifecycle/projection conflict, and a **regeneration** path — without widening discovery or inventing semantic code analysis.

## 10. Intentionally limited (unchanged rationale)

- No normative↔implementation semantic mining; no test-assertion conflict classes; no release-management platform; monorepo-local `reports/*.json` remains gitignored at one directory depth by design.
