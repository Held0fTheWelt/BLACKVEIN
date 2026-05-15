# Normative contracts index

**When to read what** for implementers. These documents **bind** behavior for the GoC slice and runtime authority; they are **not** casual onboarding.

## Runtime and platform authority

| Document | Binding scope |
|----------|----------------|
| [`runtime-authority-and-state-flow.md`](../../technical/runtime/runtime-authority-and-state-flow.md) | Consolidated authority: world-engine owns live sessions; backend owns governance/publishing |
| [`world_engine_authoritative_runtime_and_system_interactions.md`](../../technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md) | Runtime/session interaction map, including runtime-aspect evidence such as voice consistency, information disclosure, environment state, memory, and commit authority |
| [`runtime_state_and_session_contracts.md`](../../MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/runtime_state_and_session_contracts.md) | Session-state invariants, continuity expectations, voice consistency, environment-state, and information-disclosure contract boundaries |
| [`runtime_authority_decision.md`](../../archive/architecture-legacy/runtime_authority_decision.md) | Archived original decision text (Milestones 0–5); prefer technical page for navigation |
| [`ai-stack-overview.md`](../../technical/ai/ai-stack-overview.md) | Current AI stack — cross-check with vertical slice for implemented graph |
| [`player_input_interpretation_contract.md`](../../technical/runtime/player_input_interpretation_contract.md) | Interpretation pipeline expectations |

## God of Carnage (MVP vertical slice)

| Document | Binding scope |
|----------|----------------|
| [`VERTICAL_SLICE_CONTRACT_GOC.md`](../../MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md) | Slice boundaries, YAML authority, graph reality anchor |
| [`CANONICAL_TURN_CONTRACT_GOC.md`](../../MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md) | Turn schema, seams, validation/commit/render semantics |
| [`GATE_SCORING_POLICY_GOC.md`](../../MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md) | Gate/scoring and failure-to-response policy for slice QA |

## Freeze and roadmap (context, amend carefully)

| Document | Notes |
|----------|--------|
| [`FREEZE_OPERATIONALIZATION_MVP_VSL.md`](../../MVPs/MVP_VSL_And_GoC_Contracts/FREEZE_OPERATIONALIZATION_MVP_VSL.md) | Phase 0 freeze operationalization |
| [`ROADMAP_MVP_VSL.md`](../../MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_VSL.md) | Target product arc — aspirational vs shipped must be labeled in stakeholder docs |

## RAG (active technical)

| Document | Notes |
|----------|--------|
| [`RAG.md`](../../technical/ai/RAG.md) | Canonical retrieval, governance lanes, profiles |

Historical task narratives: [`docs/archive/rag-task-legacy/`](../../archive/rag-task-legacy/).

## API reference

| Document | Audience |
|----------|----------|
| [`docs/api/REFERENCE.md`](../../api/REFERENCE.md) | Backend REST surface (large) |
| [`docs/api/README.md`](../../api/README.md) | API doc hub |

## Audit and gates (engineering program, not product docs)

Under `docs/audit/` — use for **closure evidence**, **test suite rationale**, and **dependency gates**. Do not route end users here.

Runtime-intelligence maturity and ADR-0039 verification snapshots live in [`capability_matrix_status_and_adr_relations.md`](../../MVPs/capability_matrix_status_and_adr_relations.md). Use that file to distinguish historical Π vocabulary from implemented generic runtime aspect names.

## Related

- [Runtime authority and session lifecycle (developer seam)](../architecture/runtime-authority-and-session-lifecycle.md)
- [Glossary](../../reference/glossary.md)
