# Contractify finalization pass — baseline, outcomes, and honest limits

**Date:** 2026-04-13. **Scope:** last bounded completion pass for the existing hub (no greenfield rewrite).

**Last-mile follow-up:** committed full JSON under [`../reports/committed/`](../reports/committed/) + closure note [`LAST_MILE_CLOSURE_2026-04-13.md`](LAST_MILE_CLOSURE_2026-04-13.md).

## 1. Verified baseline (before this pass)

| Area | Baseline |
|------|----------|
| Discovery | A–E heuristics; normative index, OpenAPI, ADRs, ops runbook, capped schemas, Despag setup, capped workflows, self-charter; Postman projections; bounded `max_contracts`. |
| Drift | Manifest↔OpenAPI SHA (deterministic); audience backrefs (heuristic); docify scan-root handoff; despag JSON propagation hint. |
| Conflicts | Duplicate index targets; ADR vocabulary buckets; projection 16-hex OpenAPI mismatch; deprecated ADR supersession gap. |
| Relations | `extend_relations`: references, indexes, implements (when `backend/` exists), operationalizes; discover emitted derives/projects/documents. |
| Versioning | OpenAPI `info.version`; ADR `Status:` → contract lifecycle enum. |
| CLI | `discover`, `audit`, `self-check`; discover ran `extend_relations` without conflict-derived edges. |
| Tests | Hermetic `conftest` synthetic tree; 17 tests after hygiene pass. |
| Examples | Small `*.sample.json` shapes; `reports/` policy doc only. |

## 2. Strengths intentionally preserved

- Conservative discovery ceiling and explicit `discovery_reason`.
- Normative vs observed authority model (no auto-promotion of code to truth).
- Deterministic-first drift for Postmanify↔OpenAPI.
- Hermetic default (`repo_root` patch) + optional `CONTRACTIFY_REPO_ROOT`.
- Separation from docify/postmanify/despag as distinct hubs (handoffs, not merged frameworks).

## 3. Verified material gaps (closed in this pass)

- Conflict model lacked structured **severity**, **kind**, and candidate buckets for triage.
- No signal for **Active/Binding index row → retired ADR** (lifecycle navigation honesty).
- No **orphan projection** check when `source_contract_id` ∉ discovered inventory.
- Relations lacked **supersedes**, **validates**, **conflicts_with** (structural truth-flow).
- Versioning lacked parsed **Supersedes:** navigation for relation emission.
- Discovery omitted explicit **fy-suite task** anchors for postmanify/docify handoffs.
- OpenAPI `implemented_by` claimed `backend/` even when absent (false structural drift risk) — now conditional.
- Drift lacked **implementation path presence** check and **postmanify task vs manifest openapi_path** alignment.
- Discover vs audit **relation parity** for index ambiguity shadow edges — discover now runs conflict detection to feed `extend_relations` (same as audit for relation subgraph that depends on conflicts).

## 4. Finalization slices executed

1. **Model + conflict engine** — `ConflictFinding`: `kind`, `severity`, candidate lists; new detectors; `contract_ids` gate for orphan pass.
2. **Versioning** — `adr_supersedes_line`, `resolve_supersedes_markdown_target`.
3. **Relations** — `supersedes`, `validates` (first workflow mentioning openapi/postman), `conflicts_with` (from duplicate-index conflicts), fy handoff `references`/`documents`.
4. **Discovery** — `CTR-POSTMANIFY-TASK-001`, `CTR-DOCIFY-TASK-001`; conditional OpenAPI `implemented_by` / `projected_as`.
5. **Drift** — `run_all_drifts(repo, contracts)`; implementation path missing; postmanify task↔manifest path alignment.
6. **Audit / CLI ordering** — conflicts before `extend_relations`; `build_actionable_units` prefixes `conflict:<severity>|…`.
7. **Fixtures + tests** — richer `conftest`; `test_audit_pipeline`, relations/conflicts/versioning/discovery coverage; **23** tests.
8. **Evidence** — `contract_audit.sample.json` updated for new conflict fields; `examples/README` actionable-unit shape note.
9. **Docs** — README conflict table + integration + relation vocabulary; this state file.

## 5–8. Capability completion (concise)

- **Conflicts:** substantive kinds (anchor duplication, vocabulary overlap, projection stale vs OpenAPI, supersession gap, **lifecycle row vs retired ADR**, **orphan projection**); each row has `classification`, `severity`, `kind`, evidence lists, human-review flag when uncertainty remains.
- **Versioning / lifecycle:** operational parses affect contracts and relations; lifecycle conflict when index prose signals “active/binding” but target ADR is retired.
- **Relations:** truth-flow edges above; bounded caps preserved.
- **Discovery:** fy-suite **task** contracts for postmanify/docify; existing class coverage retained under `max_contracts`.

## 9. Example / report artefacts

- **`examples/*.sample.json`** — remain the committed, reviewable shape contracts (`reports/*.json` stays gitignored by policy).
- Sample audit row demonstrates **`severity` / `kind` / candidates** on conflicts.

## 10. Tests proving behaviour

- `python -m pytest "'fy'-suites/contractify/tools/tests" -q` → **23 passed** (hermetic + isolated `tmp_path_factory` where needed).

## 11. Doc alignment

- `README.md` — conflict table, relation vocabulary, integration handoffs vs drift checks.
- `CONTRACT_GOVERNANCE_SCOPE.md` — extended conflict classification table (severity + new `classification` values).
- `contract-audit-task.md` — references new lifecycle / orphan conflict classes.

## 12. Hygiene

- Prior pass: hub `.gitignore`, `reports/README.md`, git-tracked bytecode invariant test — unchanged by this pass except compatibility.

## 13. Intentionally limited (non-fundamental)

- No semantic **normative↔code** contradiction mining; no test-assertion-derived conflict classes; no full supersession **graph** solver beyond explicit `Supersedes:` edges.
- No automatic **breaking vs non-breaking** taxonomy beyond explicit markers and manual **CG-*** backlog.
- `reports/` remains evidence-local; full JSON proofs are generated via CLI, not bulk-committed.
