# MCP M1 — Canonical parity & governance closure report

**Posture:** **Historical evidence only (archived).** This file is **not** the current authoritative MCP M1 verification surface.

- **Current authoritative closure report:** `tests/reports/MCP_M1_CLOSURE_REPORT.md`
- **Current primary gate module:** `tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py` (replaces removed `test_mcp_m1_gates.py`)
- **Current doc strand:** `docs/mcp/12_M1_canonical_parity.md`

Do **not** cite pass counts or suite sizes below as present-day truth; re-run the commands in `MCP_M1_CLOSURE_REPORT.md` after dependency installs.

---

## Superseded body (retained for audit trail)

Superseded by tests/reports/MCP_M1_CLOSURE_REPORT.md

### Scope (as of original draft)

External MCP layer aligned to a **single canonical descriptor strand** (`ai_stack/mcp_canonical_surface.py`), with explicit tool classes, operating profiles, enriched capability mirror, compact operator truth, audit fields, and tests. No expansion of deferred session tools; no `CapabilityRegistry` shortcut from MCP.

### Named gates (historical table)

| Gate | Criterion | Result |
|------|-----------|--------|
| **G-MCP-01** | MCP registry matches canonical descriptors; capability names aligned with `capability_catalog()` via `verify_catalog_names_alignment()`; strict translation documented (`docs/mcp/12_M1_canonical_parity.md`). | **PASS** |
| **G-MCP-02** | Governance keys present on every `tools/list` entry and on every `capability_records_for_mcp()` row; operator-visible. | **PASS** |
| **G-MCP-03** | `read_only` / `review_bound` / `write_capable` in registry; `review_safe` denies `wos.session.create`; audit stderr includes `tool_class`, `authority_source`, `operating_profile`. | **PASS** |
| **G-MCP-04** | `classify_mcp_no_eligible_discipline` distinguishes misconfigured, degraded, test_isolated, true no-eligible, healthy non-applicable; covered in tests. | **PASS** |
| **G-MCP-05** | `build_compact_mcp_operator_truth` / `wos.mcp.operator_truth` expose required compact keys including policy, selected_vs_executed note, evidence readiness, runtime authority preservation posture. | **PASS** |
| **G-MCP-06** | No MCP path to `CapabilityRegistry` or turn commit; stubs remain non-authoritative; session create only via backend client. | **PASS** |
| **G-MCP-07** | Validation commands below executed successfully; no regression in directly exercised related suite. | **PASS** |

### Historical validation commands (do not treat as current bar)

From repository root (examples only):

```text
PYTHONPATH=. python -m pytest tools/mcp_server/tests -q --tb=short --no-cov
python -m pytest ai_stack/tests/test_mcp_canonical_surface.py tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py tools/mcp_server/tests/test_rpc.py -q --tb=short --no-cov
python -m pytest backend/tests/runtime/test_mcp_enrichment.py -q --tb=short --no-cov
```

Historical note: Older revisions of this file cited `56 passed` for `tools/mcp_server/tests` and `96 passed` for full `ai_stack/tests`; the MCP tree and ai_stack suite have since grown, and full `ai_stack/tests` may additionally depend on corpus/policy fixtures—use fresh runs for any claim.

### Limitations explicitly outside scope (unchanged intent)

- Full implementation of deferred session/turn tools on MCP may evolve; deferral posture is defined in canonical MCP docs.
- MCP operating profiles are **process-local** (env-driven); they do not replace Area 2 model-routing operator truth in `app.runtime.area2_operator_truth`.
- No claim of exhaustive parity with every future capability until those capabilities are added to `capability_catalog()` and reflected in the catalog tool.
