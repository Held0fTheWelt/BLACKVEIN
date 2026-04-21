# Governed package lifecycle, revision, and runtime health

## Why this document now belongs in the canonical MVP

One of the biggest loss risks in the older-to-newer MVP chain was not the core authority model itself.
It was the **governed lifecycle around that model**.

Several earlier complete MVPs made this explicit:
World of Shadows was not only supposed to execute authored material safely.
It was also supposed to support a governed path for:

- draft source,
- preview build,
- evaluation,
- promotion,
- rollback,
- research-driven findings,
- revision candidates,
- and live runtime-health feedback.

Later slice-centered packages kept the runtime core strong, but this surrounding lifecycle became easier to compress away.
That compression is now reversed.

## Canonical governed package chain

The preserved source set consistently points to this lifecycle:

**Authored source -> Draft workspace -> Compiled preview package -> Preview evaluation -> Manual promotion -> Active runtime package**

The meaning of that chain is canonical:

- authored source remains the human-edited source boundary,
- preview packages are real but not yet live truth,
- evaluation is a promotion gate rather than a decorative report,
- promotion moves a reviewed package into live runtime eligibility,
- active runtime packages are the only packages ordinary live play may treat as canonical truth,
- and package history must remain inspectable and reversible.

## Improvement loop is part of MVP truth

The same source family also preserved a governed improvement loop:

**Runtime observations + research -> Findings -> Revision candidates -> Conflict resolution -> Draft patch bundle -> Preview rebuild -> Preview evaluation -> Approval -> Promotion**

This is not platform ambition for a distant future.
It is a core anti-drift posture for the MVP.

The point is that World of Shadows should improve by:

- observing runtime behavior,
- localizing issues,
- drafting bounded changes,
- evaluating those changes against the current active baseline,
- and promoting only through governed approval.

What may not happen is silent narrative mutation through research, runtime, or admin convenience.

## Revision candidates remain pre-canonical objects

Revision candidates are useful precisely because they are **not yet runtime truth**.
They are review-bound objects.

The preserved expectations include:

- candidate storage,
- target localization down to content unit,
- conflict detection,
- review state,
- structured patch application to draft workspace,
- and explicit promotion boundaries.

This matters because it keeps three things separate:

- authored truth,
- candidate change proposals,
- and active runtime truth.

## Preview isolation is not optional

Preview behavior was one of the most explicit loss-prone areas in the earlier MVPs.
The canonical rule remains:

- preview execution must be isolated from the active runtime package,
- preview sessions may never silently replace active live package truth,
- and preview comparison must stay legible to operators before promotion.

Acceptable implementation modes remain source-supported as bounded technical choices:

- dedicated preview process or container,
- dedicated in-memory preview loader plus preview namespace,
- or a dedicated preview resolver keyed by preview identity.

The architectural point is stronger than the implementation detail:
preview is for governed comparison, not for accidental live mutation.

## Rollback remains part of the canonical operating picture

Rollback is not only an ops nice-to-have.
It belongs to the MVP because package promotion is supposed to be **append-only, inspectable, and reversible**.

The canonical operator expectation is that a live package history exists and that emergency rollback is reachable without deep incident improvisation.
A package that destabilizes runtime behavior, damages dramatic quality, or increases degraded execution must be reversible through a governed path.

## Live recovery chain must remain visible

The older governance MVPs also preserved a live-play recovery chain that should not be lost:

**Turn generation -> Validation -> Corrective feedback retry -> Safe fallback -> Runtime-health event -> Operator visibility**

This means:

- validation failure must not produce a dead player turn,
- retry should be corrective rather than blind,
- fallback must remain package-defined, legal, and narratively acceptable,
- and degraded execution should become explicit runtime-health signal rather than invisible suffering.

## Runtime health is a quality signal, not only an ops metric

The preserved material is unusually clear on this point.
World of Shadows should treat these as meaningful quality indicators:

- first-pass success rate,
- corrective retry rate,
- safe fallback rate,
- scene-specific degradation clusters,
- and spike patterns after package or policy change.

A scene that survives only by repeated retries or frequent fallback may still be technically "up" while being narratively unhealthy.
That is why runtime health belongs to the canonical MVP and not only to infrastructure operations.

## Admin-facing governance surfaces that remain canonical

The administration-tool was repeatedly framed as the main governance surface for this lifecycle.
The preserved operator surface includes:

- overview,
- runtime,
- runtime health,
- packages and package history,
- policy preview,
- findings,
- revisions and conflicts,
- evaluations,
- notifications,
- and compare-preview-vs-active views.

The canonical expectation is not that every page is equally polished today.
The canonical expectation is that these governance domains remain part of the MVP truth and are not silently deleted during consolidation.

## Evaluation is part of promotion discipline

The source set preserved several evaluation ideas that still matter:

- preview vs active delta comparison,
- coverage visibility,
- hard promotion gates,
- regression risk interpretation,
- and scenario families that test more than syntax or schema legality.

The evaluation layer exists to answer a product question:
not just "does this package parse," but "is this package safe enough and dramatically healthy enough to promote?"

## Current status reading

This document carries both current truth and bounded residue:

- **Enduring target:** the full governed package / revision / preview / runtime-health lifecycle belongs to the intended World of Shadows MVP.
- **Implemented in part:** the repository and supplied packages contain real fragments and proofs of publish, activation, preview, evaluation, shell, and diagnostic behavior.
- **Bounded residue:** this final archive still does not justify claiming that the entire lifecycle has been freshly replayed end to end inside the present container.

That is why this document is canonical, but not falsely overclosed.
