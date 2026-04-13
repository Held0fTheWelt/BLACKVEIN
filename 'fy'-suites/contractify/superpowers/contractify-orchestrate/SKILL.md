---
name: contractify-orchestrate
description: Routes agents to Contractify tasks — contract discovery, anchoring, drift, backlog slices. Triggers on contractify, contract governance, normative vs observed drift, repository contracts audit.
---

# Contractify orchestrate (router)

**Do not duplicate repository language policy here.** Pick **one** track and follow **only** that task file end-to-end:

| Intent | Open and follow |
|--------|-------------------|
| **Governance pass** — discover contracts, classify anchors/projections, drift JSON | [`contract-audit-task.md`](../../contract-audit-task.md) |
| **Execute one bounded slice** — anchor, link, or repair projections with evidence | [`contract-solve-task.md`](../../contract-solve-task.md) |
| **Recovery** — reset inventory template + re-audit | [`contract-reset-task.md`](../../contract-reset-task.md) |

**CLI:** ``python -m contractify.tools`` (or ``contractify`` after editable install): ``discover``, ``audit``, ``self-check``.

**Scope ceilings:** [`CONTRACT_GOVERNANCE_SCOPE.md`](../../CONTRACT_GOVERNANCE_SCOPE.md)

Hub orientation: [`README.md`](../../README.md).
