# Research MVP Gate Closure

## Validation commands
- `python -m pytest ai_stack/tests/test_research_intake_golden.py ai_stack/tests/test_research_aspect_golden.py ai_stack/tests/test_research_exploration_golden.py ai_stack/tests/test_research_verification_golden.py ai_stack/tests/test_research_canon_improvement_golden.py ai_stack/tests/test_research_review_bundle_golden.py ai_stack/tests/test_research_contract_enforcement.py ai_stack/tests/test_capabilities.py tools/mcp_server/tests/test_research_mcp_contracts.py`
  - Result: `24 passed`
- `python -m pytest ai_stack/tests/test_mcp_canonical_surface.py tools/mcp_server/tests/test_registry.py tools/mcp_server/tests/test_tools_handlers.py tools/mcp_server/tests/test_mcp_m1_gates.py`
  - Result: `33 passed`
- `python -m pytest administration-tool/tests/test_manage_inspector_suite.py`
  - Result: `11 passed`

## Gate-by-gate closure

### Gate 1 - Truth Separation
Status: Pass
- Distinct statuses implemented: `exploratory`, `candidate`, `validated`, `approved_research`, `canon_applicable`, `canon_adopted`.
- Legal transitions are centralized and validated in `ai_stack/research_contract.py`.

### Gate 2 - Provenance
Status: Pass
- Claims and proposals require evidence anchor linkage in store contracts.
- Unknown anchor and claim references are rejected by the store and verification phase.
- Source and anchor records are persisted with provenance references.
- Empty `provenance` objects are rejected to prevent semantically empty governance fields.

### Gate 3 - Bounded Exploration
Status: Pass
- Exploration enforces depth/branch/node budgets, low-evidence budget, llm/token/time budget, and stable abort reasons.
- Budget validation exists on MCP layer, capability layer, and exploration engine.
- Time budget now emits dedicated abort reason (`time_budget_exhausted`) and consumed budget reports elapsed wall time explicitly.

### Gate 4 - Counterview Support
Status: Pass
- Stable contradiction classes implemented (`none`, `counterview_present`, `soft_conflict`, `hard_conflict`, `unresolved`).
- Verification flow blocks hard conflicts, blocks unresolved low-support claims, and only promotes from `kept_for_validation`.

### Gate 5 - Canon Improvement
Status: Pass
- Structured issue taxonomy and proposal taxonomy implemented as closed enums.
- Proposal generation is issue-mapped and deterministic.
- Stored issues/proposals remain review artifacts (`approved_research`) and do not imply direct canon adoption.

### Gate 6 - Reviewability
Status: Pass
- Review bundle structure is deterministic and includes intake/aspects/exploration/verification/canon/governance sections with governance flags.
- Bundle generation has dedicated tests.
- Comparison projection in inspector workbench renders mandatory structured turn-to-turn view (row+block) and keeps full JSON as secondary diagnostic output.

### Gate 7 - No Silent Mutation
Status: Pass
- Canon mutation is explicitly blocked in review bundle governance metadata.
- No auto-adoption path is exposed in new capability or MCP tool surface.
- Canon relevance hint is no longer hardcoded true; deterministic heuristics gate applicability hints.

### Gate 8 - Deterministic Testability
Status: Pass
- Fixture packs A-F implemented with deterministic assertions for structure/state/abort/budget/classification outputs.
- Golden paths avoid live LLM dependency.
- Closure-repair added stronger expected-value assertions and negative-path tests for budget/governance invariants.

## Residual risks outside MVP boundary
- Taxonomy growth and richer semantic classifiers can improve recall/precision but are out of MVP scope.
- Downstream explicit canon adoption workflow (`canon_applicable -> canon_adopted`) remains intentionally out of direct MVP execution.
