# Architecture decision records (ADR)

This directory holds **lightweight ADRs** for decisions that affect multiple services or long-lived boundaries. **Program audit** and **task closure** evidence remain under `docs/audit/` and `docs/governance/audit_resolution/`; they are not ADRs.

For the **record shape** (optional sections, testing expectations), see [`adr-template.md`](adr-template.md). Migration notes from the 2026-04-17 consolidation live in [`migration_from_archive_2026-04-17.md`](migration_from_archive_2026-04-17.md).

## Index

| ADR | Title | Status |
|-----|--------|--------|
| [ADR-0001](adr-0001-runtime-authority-in-world-engine.md) | Runtime authority in world-engine | Accepted |
| [ADR-0002](adr-0002-backend-session-surface-quarantine.md) | Backend session / transitional runtime quarantine | Accepted |
| [ADR-0003](adr-0003-scene-identity-canonical-surface.md) | Single canonical scene identity surface | Accepted |
| [ADR-0004](adr-0004-runtime-model-output-proposal-only-until-validator-approval.md) | Runtime model output is proposal-only until validator approval | Proposed |
| [ADR-0005](adr-0005-research-may-draft-change-but-may-not-publish.md) | Research may draft change, but may not publish change | Proposed |
| [ADR-0006](adr-0006-revision-review-uses-state-machine.md) | Revision review uses a state machine | Proposed |
| [ADR-0007](adr-0007-revision-conflicts-explicit-governance-objects.md) | Revision conflicts are explicit governance objects | Proposed |
| [ADR-0008](adr-0008-validation-strategy-explicit-configurable.md) | Validation strategy must be explicit and configurable | Proposed |
| [ADR-0009](adr-0009-evaluation-is-a-promotion-gate.md) | Evaluation is a promotion gate | Proposed |
| [ADR-0010](adr-0010-governance-workflows-event-driven.md) | Governance workflows are event-driven | Proposed |
| [ADR-0011](adr-0011-validation-failures-degrade-gracefully.md) | Validation failures in live play must degrade gracefully | Proposed |
| [ADR-0012](adr-0012-corrective-retry-provide-actionable-feedback.md) | Corrective retry must provide actionable validation feedback | Proposed |
| [ADR-0013](adr-0013-preview-sessions-isolated-from-active-runtime.md) | Preview sessions must be isolated from active runtime | Proposed |
| [ADR-0014](adr-0014-player-affect-enum-signals.md) | Player affect uses enum-based signals | Proposed |
| [ADR-0015](adr-0015-persist-turnexecutionresult-and-aidecisionlog.md) | Persist TurnExecutionResult and AIDecisionLog in SessionState | Accepted |
| [ADR-0016](adr-0016-frontend-backend-restructure.md) | Frontend / backend restructure | Proposed |
| [ADR-0017](adr-0017-durable-truth-migration-policy.md) | Durable-truth migration verification and archive policy | Proposed |
| [ADR-0018](adr-0018-role-aware-aidecisionlog.md) | Role-aware AIDecisionLog and ParsedRoleAwareDecision | Proposed |
| [ADR-0019](adr-0019-proposal-source-and-responder-gating.md) | ProposalSource enum and responder-only gating | Accepted |
| [ADR-0020](adr-0020-debug-panel-ui.md) | Debug Panel UI — bounded diagnostics | Accepted |
| [ADR-0021](adr-0021-runtime-authority.md) | Runtime authority (early consolidation stub) | Superseded by ADR-0001 |
| [ADR-0022](adr-0022-mvp-expansion-decision-rule.md) | MVP expansion decision rule | Proposed |
| [ADR-0023](adr-0023-decision-framework-for-risk-and-kill-criteria.md) | Decision framework — risk and kill criteria | Proposed |
| [ADR-0024](adr-0024-decision-boundary-record-schema.md) | Decision boundary record schema | Proposed |
| [ADR-0025](adr-0025-canonical-authored-content-model.md) | Canonical authored content model | Proposed |
| [ADR-0026](adr-0026-mcp-host-and-runtime-phase-a.md) | MCP Phase A — host and runtime defaults | Proposed |
| [ADR-0027](adr-0027-mcp-transport-connectivity-phase-a.md) | MCP transport and connectivity — Phase A | Proposed |
| [ADR-0028](adr-0028-mcp-security-baseline-phase-a.md) | MCP security baseline — Phase A | Proposed |
| [ADR-0029](adr-0029-residue-removal-policy.md) | Residue removal policy | Proposed |

_Status values mirror each file’s `## Status` line; update the table when an ADR’s status changes._

## When to write an ADR

- Changing **ownership** of session lifecycle, persistence, or turn commit authority.
- Introducing a **second** runtime graph or duplicate content authority without removing the first.
- Materially changing **security boundaries** between admin, player, MCP, and internal APIs.

## Template

Use [`adr-template.md`](adr-template.md) for new decisions.

## Related

- [Architecture overview](../architecture/README.md)
- [Normative contracts index](../dev/contracts/normative-contracts-index.md)
- [Audit resolution (master prompt, case input, living state)](../governance/audit_resolution/README.md) — closure governance for audit programs (not ADRs)
