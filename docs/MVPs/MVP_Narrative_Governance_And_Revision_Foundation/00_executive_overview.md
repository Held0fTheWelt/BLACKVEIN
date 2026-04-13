# Executive Overview

## Core thesis

World of Shadows should not treat the language model as narrative authority.

The model is a **constrained narrative executor** operating inside a governed runtime.
Narrative truth lives in approved compiled packages, resolved policies, canonical runtime state, and engine-side validation.

## What changed in this complete collection

The prior revised collection already established the right direction:

- compiled narrative packages
- scene packet execution contracts
- research-to-revision instead of direct mutation
- evaluation-gated promotion
- governance surfaces in the administration-tool
- rollback safety, conflicts, workflow state, and notifications

This complete version closes the remaining operational gap for **live play**:

1. **Validation failure no longer implies a dead turn.**
2. **Retry is now corrective, not blind.**
3. **Safe fallback responses are package-defined and guaranteed valid.**
4. **Runtime health now tracks retry and fallback behavior explicitly.**
5. **Player-affect detection is framed as an enum-based model, not only frustration handling.**
6. **Future dramatic-quality seams are documented without collapsing MVP scope.**

## Architecture north star

The governed content chain is:

**Authored source -> Draft workspace -> Compiled preview package -> Preview evaluation -> Manual promotion -> Active runtime package**

The governed improvement chain is:

**Runtime observations + research -> Findings -> Revision candidates -> Conflict resolution -> Draft patch bundle -> Preview rebuild -> Preview evaluation -> Approval -> Promotion**

The governed live-play recovery chain is:

**Turn generation -> Validation -> Corrective feedback retry -> Safe fallback -> Runtime health event -> Operator visibility**

No AI subsystem may bypass these chains.

## Non-negotiable principles

- Runtime consumes only approved compiled packages.
- Research may recommend and draft, but may not publish canonical runtime content.
- Promotion is append-only and reversible through package history.
- Revision candidates are review-bound and conflict-aware.
- Runtime model output is never authoritative by itself.
- Validation failure must degrade gracefully, never leave the player hanging.
- Evaluation is a quality gate, not a reporting afterthought.
- Administration-tool is both an operator console and a narrative governance surface.

## Top operator journeys this design explicitly supports

### 1. Emergency rollback
A promoted package causes live instability or narrative breakage.
Operator must inspect history and roll back the active package immediately.

### 2. Review high-confidence research findings
Research identifies a likely content issue and proposes revision candidates.
Operator reviews evidence, resolves conflicts, applies a candidate to draft, triggers preview build and evaluation.

### 3. Compare preview package against active package
Operator compares effective policy, package contents, evaluation deltas, and promotion readiness before approval.

### 4. Investigate live fallback spike
Runtime health reports an abnormal corrective retry or safe-fallback rate.
Operator inspects recent validation failures, affected scenes, and suggested root causes.

## Design stance on "magic"

The system should not fake dramatic quality by handing unrestricted freedom to the model.
It should produce dramatic quality by combining:

- constrained generation
- persistent state
- policy layering
- package-defined fallbacks
- evaluation and review
- future dramatic-quality layers such as emotional continuity and contradiction checks

That is how the system becomes both **playable** and **trustworthy**.
