# Gate G2 Baseline: Capability / Policy / Observation Separation

## Gate

- Gate name: G2 Capability / Policy / Observation Separation
- Gate class: structural
- Audit subject: separation of capability truth, policy truth, and runtime observation truth

## Repository Inspection Targets

- `ai_stack/capabilities.py`
- `ai_stack/operational_profile.py`
- `backend/app/runtime/model_inventory_contract.py`
- `backend/app/runtime/model_routing_contracts.py`
- `backend/app/runtime/model_routing.py`
- `backend/app/runtime/model_routing_evidence.py`
- `backend/app/runtime/area2_routing_authority.py`
- `backend/tests/runtime/test_model_routing_evidence.py`
- `backend/tests/runtime/test_decision_policy.py`

## Required Evidence

- distinct structures for capability, policy, and observation
- routing records containing policy identity/version and route reasoning
- fallback-chain and route-reason visibility
- test evidence that observation does not overwrite policy

## Audit Methods Used In This Baseline

- static structure review
- routing-evidence contract review
- static test intent review (no runtime execution in this block)

## Command Strategy

| command | status | basis | promotion requirement |
| --- | --- | --- | --- |
| `cd backend && python -m pytest tests/runtime/test_model_routing_evidence.py tests/runtime/test_decision_policy.py -q --tb=short --no-cov` | `repo-verified` | Canonical G2 routing evidence and policy taxonomy path. | Archived: `tests/reports/evidence/all_gates_closure_20260409/g2_routing_policy_observation.txt` |

## Baseline Findings

1. Capability/policy/observation boundaries are structurally explicit:
   - capability-facing specs in `model_inventory_contract.py`
   - policy/routing contracts in `model_routing_contracts.py`
   - observation payload in `model_routing_evidence.py`
2. Routing evidence includes route reason, fallback chain, escalation/degradation flags, and policy/selection alignment diagnostics.
3. Tests directly target routing evidence shape and policy taxonomy validation.
4. Canonical runtime tests were executed; behavioral confirmation and evidence-shape validation are now attached in the closure bundle.

## Status Baseline

- structural_status: `green`
- closure_level_status: `level_a_capable`

Rationale: structural separation is explicit and the canonical runtime evidence/policy tests passed with archived transcript evidence.

## Evidence Quality

- evidence_quality: `high`
- justification: comprehensive static contracts plus executed canonical runtime proof (`g2_routing_policy_observation.txt`).

## Execution Risks Carried Forward

- Preserve the executed G2 command as canonical regression path for future policy/routing changes.
