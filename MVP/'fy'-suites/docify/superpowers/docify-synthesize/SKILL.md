---
name: docify-synthesize
description: Routes agents to docify/python_docstring_synthesize.py — PEP 8 # comments for a range (--apply) or Google-style docstring draft for one --function (--emit-google-docstring, --apply-docstring). Triggers on docify synthesize, explain source block, inline comments, google docstring draft, documentation synthesize.
---

# Docify synthesize (router)

**Do not duplicate repository language policy here.** Follow **only** this task end-to-end:

| Intent | Open and follow (single source) |
|--------|----------------------------------|
| **PEP 8 `#` comments for a line range** — dry-run → edit → `--apply` | [`documentation-docstring-synthesize-task.md`](../../documentation-docstring-synthesize-task.md) |
| **Google-style docstring draft** for one `--function` — `--emit-google-docstring` → edit TODOs → `--apply-docstring` | same task doc |

**Tool:** ``'fy'-suites/docify/tools/python_docstring_synthesize.py`` — AST-guided `#` comments for a span, or a wrapped Google docstring for a single callable.

**Docstring backlog (measurement + manual fixes):** [`documentation-audit-task.md`](../../documentation-audit-task.md) and ``'fy'-suites/docify/tools/python_documentation_audit.py``.

Hub orientation: [`README.md`](../../README.md).
