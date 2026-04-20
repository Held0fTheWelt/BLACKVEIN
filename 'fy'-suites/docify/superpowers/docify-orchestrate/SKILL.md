---
name: docify-orchestrate
description: Routes agents to Docify documentation tasks — governance check/solve tracks, Python docstring audit, drift hints, inline source explain (PEP 8 comments), slice-based fixes, JSON reports. Triggers on docify, docify orchestrate, documentation audit, explain source block, python docstring backlog, doc audit, run docify.
---

# Docify orchestrate (router)

**Do not duplicate repository language policy here.** Pick **one** track and follow **only** that task file end-to-end:

| Intent | Open and follow (single source) |
|--------|----------------------------------|
| **Governance pass** — drift hints + audit JSON + backlog rows | [`documentation-check-task.md`](../../documentation-check-task.md) |
| **Execute one DOC slice** — bounded documentation change with evidence | [`documentation-solve-task.md`](../../documentation-solve-task.md) |
| **Python-only backlog** — AST audit slices (legacy-focused procedure) | [`documentation-audit-task.md`](../../documentation-audit-task.md) |
| **Inline explain (PEP 8 `#` comments)** — dry-run a range, then `--apply` after review | [`documentation-docstring-synthesize-task.md`](../../documentation-docstring-synthesize-task.md) |
| **Backlog reset** — controlled wipe + rebuild | [`documentation-reset-task.md`](../../documentation-reset-task.md) |

**Tools:** Prefer ``python -m docify.tools`` (or ``docify`` after editable install): ``audit`` (AST JSON/text), ``drift`` (path-only heuristics), ``open-doc`` (open DOC-* IDs). Legacy script paths under ``'fy'-suites/docify/tools/`` remain valid for automation that has not migrated.

**Quality standard:** [`DOCUMENTATION_QUALITY_STANDARD.md`](../../DOCUMENTATION_QUALITY_STANDARD.md)

Hub orientation: [`README.md`](../../README.md).
