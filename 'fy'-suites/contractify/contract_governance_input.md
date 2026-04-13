# Contract governance backlog (CG-*)

| **ID** | **Slice** | **Status** | **Evidence / notes** |
|--------|-----------|------------|----------------------|
| **CG-001** | Re-run `python -m contractify.tools audit --json --out "'fy'-suites/contractify/reports/contract_audit.json"` after OpenAPI or Postman workflow changes; triage `actionable_units`. | open | Deterministic drift: `openapi_sha256` vs file hash |
| **CG-002** | Add explicit normative backlinks or `contractify-projection` front matter to `docs/easy/**` pages flagged with low-severity `DRF-PROJ-BACKREF-*` (heuristic). | open | See audit `drift_findings` |
| **CG-003** | Keep Docify default AST roots including contractify (suite self-governance). | open | `DRF-DOCIFY-ROOT-001` should stay **absent** after integration |
