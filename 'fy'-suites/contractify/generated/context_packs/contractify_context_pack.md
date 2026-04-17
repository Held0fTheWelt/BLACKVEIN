# Context Pack — contractify

Query: `openapi health`

Found 8 indexed evidence hits for query "openapi health". Strongest source: generated/context_packs/contractify_context_pack.md#chunk-1.

## generated/context_packs/contractify_context_pack.md#chunk-1

- lexical: 1.0
- semantic: 0.4773
- hybrid: 0.7909

# Context Pack — contractify  Query: `openapi health`  Found 8 indexed evidence hits for query "openapi health". Strongest source: generated/context_packs/contractify_context_pack.md#chunk-1.  ## generated/context_packs/contractify_context_pack.md#chunk-1  - lexical: 1.0 - semant

## generated/context_packs/contractify_context_pack.json#chunk-1

- lexical: 1.0
- semantic: 0.4057
- hybrid: 0.7623

{   "pack_id": "9cc97dcf71404923ba059043e76d53bf",   "query": "openapi health",   "suite_scope": [     "contractify"   ],   "audience": "developer",   "summary": "Found 8 indexed evidence hits for query \"openapi health\". Strongest source: generated/context_packs/contractify_con

## generated/context_packs/contractify_context_pack.md#chunk-2

- lexical: 1.0
- semantic: 0.4015
- hybrid: 0.7606

openapi: 3.0.0 info:   title: Toy API   version: 1.0.0 paths:   /health:     get:       tags: [system]       summary: Health       responses:         "200":           description: OK  ## generated/context_packs/contractify_context_pack.md#chunk-2  - lexical: 1.0 - semantic: 0.308

## docs/api/openapi.yaml#chunk-1

- lexical: 1.0
- semantic: 0.343
- hybrid: 0.7372

openapi: 3.0.0 info:   title: Toy API   version: 1.0.0 paths:   /health:     get:       tags: [system]       summary: Health       responses:         "200":           description: OK

## state/LATEST_AUDIT_STATE.md#chunk-5

- lexical: 1.0
- semantic: 0.2102
- hybrid: 0.6841

#### Signal Analysis - **Contract Graph Stability:** 60 contracts, 310 relations, 25 projections—all at baseline. No silent regressions. - **Confidence Stability:** 100% >= 0.85 confidence maintained. No erosion of contract strength. - **New Signals:** +1 drift finding (OpenAPI s

## reports/contractify_audit_report_latest.md#chunk-6

- lexical: 1.0
- semantic: 0.1577
- hybrid: 0.6631

**Conclusion:** MVP remains coherent with committed contracts. Contractify enforcement is working—gates are catching the OpenAPI drift and vocabulary overlaps. No dangerous gaps detected. The +3 conflicts and +1 drift signal indicate normal evolution friction, not structural brea

## state/LATEST_AUDIT_STATE.md#chunk-6

- lexical: 1.0
- semantic: 0.1572
- hybrid: 0.6629

**Contractify enforcement is working.** Evidence: - New conflicts flagged (+3): Gates caught Postman fingerprint stale issue and ADR vocabulary overlaps - Drift detection active (+1): Gates flagged OpenAPI spec modification - Zero silent regressions: Contract graph unchanged, sam

## adapter/tests/test_contractify_adapter.py#chunk-1

- lexical: 1.0
- semantic: 0.1104
- hybrid: 0.6442

from fy_platform.tests.fixtures_autark import create_target_repo from contractify.adapter.service import ContractifyAdapter   def test_contractify_adapter_full_cycle(tmp_path, monkeypatch):     repo = create_target_repo(tmp_path)     monkeypatch.chdir(tmp_path)     adapter = Cont
