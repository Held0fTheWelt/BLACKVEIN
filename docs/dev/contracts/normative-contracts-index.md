# Normative contracts index

**When to read what** for implementers. These documents **bind** behavior for the GoC slice and runtime authority; they are **not** casual onboarding.

## Runtime and platform authority

| Document | Binding scope |
|----------|----------------|
| [`runtime-authority-and-state-flow.md`](../../technical/runtime/runtime-authority-and-state-flow.md) | Consolidated authority: world-engine owns live sessions; backend owns governance/publishing |
| [`world_engine_authoritative_runtime_and_system_interactions.md`](../../technical/runtime/world_engine_authoritative_runtime_and_system_interactions.md) | Runtime/session interaction map, including runtime-aspect evidence such as voice consistency, tonal consistency, information disclosure, expectation variation, social pressure, sensory context, improvisational coherence, meta-narrative awareness, environment state, memory, and commit authority |
| [`runtime_state_and_session_contracts.md`](../../MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/runtime_state_and_session_contracts.md) | Session-state invariants, continuity expectations, voice consistency, tonal consistency, environment-state, social-pressure, sensory-context, improvisational-coherence, expectation-variation, meta-narrative awareness, and information-disclosure contract boundaries |
| [`runtime_authority_decision.md`](../../archive/architecture-legacy/runtime_authority_decision.md) | Archived original decision text (Milestones 0–5); prefer technical page for navigation |
| [`ai-stack-overview.md`](../../technical/ai/ai-stack-overview.md) | Current AI stack — cross-check with vertical slice for implemented graph |
| [`player_input_interpretation_contract.md`](../../technical/runtime/player_input_interpretation_contract.md) | Interpretation pipeline expectations |
| [`callback_web_contract.md`](../../technical/runtime/callback_web_contract.md) | Bounded Pi17 callback-web index: schemas, sources, runtime propagation, operator endpoints, and ADR-0039 oracle boundary |
| [`pacing_rhythm_contract.md`](../../technical/runtime/pacing_rhythm_contract.md) | Bounded Pi18 pacing-rhythm aspect: cadence target, structural validation, ledger/MCP propagation, and ADR-0039 oracle boundary |
| [`subtext_interpretation_contract.md`](../../technical/runtime/subtext_interpretation_contract.md) | Bounded Pi19 surface-vs-intent contract, policy source, runtime propagation, and ADR-0039 oracle boundary |
| [`consequence_cascade_contract.md`](../../technical/runtime/consequence_cascade_contract.md) | Bounded Pi21 consequence cascade: committed-truth derivation, branch-selection edges, graph feedback, operator endpoints, and ADR-0039 oracle boundary |
| [`sensory_context_contract.md`](../../technical/runtime/sensory_context_contract.md) | Bounded Pi26 sensory-context aspect: authored layer selection, structured event validation, ledger/MCP propagation, and ADR-0039 oracle boundary |
| [`temporal_control_contract.md`](../../technical/runtime/temporal_control_contract.md) | Bounded Pi28 temporal-control aspect: selected time operation, committed refs, structured event validation, ledger/MCP diagnostics, and ADR-0039 oracle boundary |
| [`improvisational_coherence_contract.md`](../../technical/runtime/improvisational_coherence_contract.md) | Bounded Pi24 improvisational-coherence aspect: structured contribution acceptance, scene anchors, ledger/MCP diagnostics, and ADR-0039 oracle boundary |
| [`expectation_variation_contract.md`](../../technical/runtime/expectation_variation_contract.md) | Bounded Pi29 expectation-variation aspect: selected surprise budget, setup refs, cooldown, structured event validation, ledger/MCP diagnostics, and ADR-0039 oracle boundary |
| [`no_dead_end_recovery_contract.md`](../../technical/runtime/no_dead_end_recovery_contract.md) | Bounded Pi30 no-dead-end recovery: recovery classes, commit policy, next-step evidence, false-truth boundary, ledger diagnostics, and ADR-0039 oracle boundary |
| [`meta_narrative_awareness_contract.md`](../../technical/runtime/meta_narrative_awareness_contract.md) | Bounded Pi25 meta-narrative awareness aspect: full opt-in gating, adaptive/fourth-wall/cross-session v2 scope, structured event validation, ledger diagnostics, and ADR-0039 oracle boundary |
| [`tonal_consistency_contract.md`](../../technical/runtime/tonal_consistency_contract.md) | Bounded Pi35 tonal-consistency aspect: tone target, structured classification, marker-class validation, ledger/MCP diagnostics, ADR-0039 oracle boundary, and local/partial promotion boundary |

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

Runtime-intelligence maturity and ADR relations live in [`capability_matrix_status_and_adr_relations.md`](../../MVPs/capability_matrix_status_and_adr_relations.md). Dated verification snapshots live in [`capability_matrix_verification_log.md`](../../MVPs/capability_matrix_verification_log.md), and promotion/live-claim rules live in [`capability_matrix_live_claim_gates.md`](../../MVPs/capability_matrix_live_claim_gates.md). Use these files to distinguish historical Π vocabulary from implemented generic runtime aspect names.

## Related

- [Runtime authority and session lifecycle (developer seam)](../architecture/runtime-authority-and-session-lifecycle.md)
- [Glossary](../../reference/glossary.md)
