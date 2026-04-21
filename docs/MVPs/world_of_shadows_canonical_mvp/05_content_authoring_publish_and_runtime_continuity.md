# Content authoring, publishing, and runtime continuity

## Why this seam is load-bearing

One of the most repeated cross-source themes is that World of Shadows cannot honestly claim authored dramatic runtime if its authored source, publishing layer, activation path, and live runtime diverge.
This seam had to be restored explicitly because it was spread across writers' room docs, module docs, backend activation reports, and runtime proof reports.

## Canonical authored source for the active slice

For the current slice, the canonical authored source is:

`content/modules/god_of_carnage/`

That tree contains structured authored material such as:

- module metadata,
- characters,
- relationships,
- scenes,
- transitions,
- triggers,
- endings,
- escalation structures,
- and direction assets.

This tree is not just prompt fodder. It is the current human-maintained dramatic source of truth for the slice.

## Source-precedence ladder for the active slice

The repaired package now makes the precedence ladder explicit:

1. `content/modules/god_of_carnage/` is the canonical authored source,
2. published artifact identity and release classification are the canonical release-binding layer,
3. world-engine committed state and narrative-commit records are the live runtime truth layer,
4. player-shell observations, cached observations, backend compatibility sessions, writers' room review artifacts, and audit/evidence bundles are subordinate support or residue surfaces.

This is the rule that stops the package from treating support trees as content truth by accident.
Files under areas such as `writers-room/`, `backend/var/`, `runtime_data/`, `docs/audit/`, and `evidence/raw_test_outputs/` may be truth-bearing evidence or useful support, but they do not silently outrank authored source, release identity, or committed runtime truth.

## Projection model

The active source set repeatedly implies or names a projection chain from authored source into runtime use.
For the slice-centered MVP, three projections matter:

1. **runtime projection** for world-engine loading,
2. **retrieval corpus seed** for governed AI support,
3. **player/admin facing metadata and activation identity** for operational use.

Even where the exact implementation surface differs across packages, the core continuity rule remains the same: published content must be traceable back to authored source and forward into runtime activation.

## Publish-bound authoritative birth

The v17-v18 packages sharpened this into a non-negotiable law:

- ordinary player sessions must be born from a **published artifact identity bundle**,
- the bundle must be provenance-complete,
- session birth must not silently depend on compile-based local fallback on the ordinary production path,
- and resume must bind back to the same provenance bundle rather than silently rebinding to a different revision.

This is one of the strongest runtime-maturity laws in the source set.

## Turn 0 and activation continuity

The continuity chain does not start after the first successful player input.
The later packages are explicit that:

- Turn 0 birth is canonical,
- authoritative session birth must either produce a committed opening or fail explicitly,
- and a false playable shell with no authoritative opening is not acceptable as hardened behavior.

## Fallback governance

The active slice allows bounded builtin fallback behavior, but only under explicit classification.
It must remain true that:

- published canon stays primary,
- fallback is visibly bounded,
- fallback does not silently replace published truth,
- and hardened claims do not rely on hidden default fallback.

## Writers' room / retrieval overlap

The later governance ledgers add another important continuity constraint:

- writers' room and retrieval may interact,
- but they may not silently collapse into one uncontrolled authority,
- and overlap must remain governed and inspectable.

This is consistent with the broader WoS rule that support layers assist but do not self-authorize canon.

## Canonical continuity reading

The correct consolidated continuity law is:

- authored modules define the dramatic possibility space,
- publishing produces provenance-bound activation artifacts,
- runtime sessions are born from those artifacts on the authoritative path,
- Turn 0 and resume preserve provenance continuity,
- support layers may retrieve and assist,
- but builtin fallback, retrieval convenience, or preview logic may not silently outrank published canon.
