# Docify `state/` hub

This directory holds **optional** session-local or human-written coordination that is **not**
required for Docify to function. Canonical machine-readable outputs should prefer
[`../reports/`](../reports/) so drift and audit JSON stay easy to discover in reviews.

Suggested layout (create on demand):

- `artifacts/` — dated notes, scratch comparisons, or exported tables when a documentation wave
  spans multiple PRs.

Nothing under `state/` is consumed automatically by Docify tools today; it exists to mirror the
**evidence-first** habit established by other “fy” hubs without copying Despaghettify’s numeric
trigger machinery wholesale.
