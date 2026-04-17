# Docify hub

**Language:** Same canonical policy as [`docs/dev/contributing.md`](../../docs/dev/contributing.md#repository-language). This suite is a **documentation governance** hub: repeatable audits, drift triage, slice-based execution, and evidence-backed backlog rows — not a one-off script drop.

## What Docify is responsible for

- Python **code-adjacent** documentation hygiene (AST audit; optional Google layout hints).
- **Heuristic** documentation drift triage after edits (`git diff` path classification — explicit disclaimer in JSON).
- **Operating discipline** — canonical backlog file, check/solve/reset task tracks, JSON reports.
- **Inline explain assist** — targeted PEP 8 `#` comments / optional synthesizer drafts for a chosen range.

## What Docify is not responsible for

- Semantic proof that prose “matches” behaviour (heuristics only; humans/agents review).
- Product copy, marketing pages, or non-Python ecosystems (unless a task explicitly expands scope).
- Replacing code review, CI, or Despaghettify structural governance.

## Merge-time enforcement

**Docstring coverage is enforced at merge time by the `fy-docify-gate` GitHub Actions workflow.** The gate is **mandatory** and blocks PR merge if:
- New parse errors are introduced (BOM, syntax issues)
- Docstring coverage degradates (new missing docstrings)
- Files with missing docstrings increase from baseline

See `'fy'-suites/fy_governance_enforcement.yaml` for enforcement thresholds and `'fy'-suites/docify/baseline_docstring_coverage.json` for baseline snapshot.

## Layout

| Path | Role |
|------|------|
| [`superpowers/`](superpowers/) | Minimal Cursor **router** `SKILL.md` files → task docs |
| [`tools/`](tools/) | Docify Python package (`docify.tools`) — hub CLI, audit, drift |
| [`documentation_implementation_input.md`](documentation_implementation_input.md) | Canonical **DOC-*** backlog + evidence links |
| [`documentation-check-task.md`](documentation-check-task.md) | Analysis track — audit + drift + backlog maintenance |
| [`documentation-solve-task.md`](documentation-solve-task.md) | Implementation track — one bounded DOC slice |
| [`documentation-reset-task.md`](documentation-reset-task.md) | Recovery — controlled backlog reset from template |
| [`documentation-audit-task.md`](documentation-audit-task.md) | Python-only audit procedure (still useful for narrow slices) |
| [`documentation-docstring-synthesize-task.md`](documentation-docstring-synthesize-task.md) | Inline `#` assist → review → `--apply` |
| [`DOCUMENTATION_QUALITY_STANDARD.md`](DOCUMENTATION_QUALITY_STANDARD.md) | House documentation standard for Docify work |
| [`reports/`](reports/) | JSON/text outputs (git-ignored bundles optional; `.gitkeep` holds directory) |
| [`state/`](state/README.md) | Optional human/session notes — **not** consumed by tools today |
| [`templates/documentation_implementation_input.EMPTY.md`](templates/documentation_implementation_input.EMPTY.md) | Empty backlog template |

## Hub CLI (preferred)

With **`pip install -e .`** at the repository root ([`pyproject.toml`](../../pyproject.toml)) the **`docify`** console script is available. Equivalent: **`python -m docify.tools`**.

| Command | Role |
|---------|------|
| `docify audit …` | Same flags as [`tools/python_documentation_audit.py`](tools/python_documentation_audit.py) |
| `docify drift …` | Path-only drift hints from `git diff` (or `--paths-file`) → JSON/text |
| `docify open-doc` | Print open **DOC-*** IDs from the hub backlog (or pass **`--input path/to/documentation_implementation_input.md`** for archives and CI without monorepo discovery). |

Examples:

```bash
docify audit --json --out "'fy'-suites/docify/reports/doc_audit.json" --exit-zero
docify drift --json --out "'fy'-suites/docify/reports/doc_drift.json"
docify open-doc
```

Optional shared-platform output:

- `docify audit ... --envelope-out path/to/docify.envelope.json` writes a versioned shared envelope.

Legacy script paths remain supported for older automation:

```bash
python "./'fy'-suites/docify/tools/python_documentation_audit.py" --json --exit-zero
python "./'fy'-suites/docify/tools/python_docstring_synthesize.py" --help
```

## Default AST scan roots

When `audit` runs **without** `--root`, it walks: `backend`, `world-engine`, `ai_stack`, `frontend`, `administration-tool`, `story_runtime_core`, `'fy'-suites/despaghettify`, `'fy'-suites/postmanify`, **`'fy'-suites/docify`**, **`'fy'-suites/contractify`**, `tools/mcp_server` — excluding `**/migrations/**`, `**/site-packages/**`, `world-engine/source/**`, and (unless `--include-tests`) any path with a `tests` path segment. Override with one or more `--root` arguments for narrower slices.

If `fy-manifest.yaml` defines `suites.docify.roots`, those roots become the default audit targets.

## Adjunct / maintenance scripts

These ship under [`tools/`](tools/) but are **adjacent utilities**, not the core governance CLI:

| Script | Role |
|--------|------|
| [`tools/bulk_google_docstrings_package.py`](tools/bulk_google_docstrings_package.py) | Legacy bulk Google docstring helper |
| [`tools/repair_google_docstrings_package.py`](tools/repair_google_docstrings_package.py) | Legacy Google docstring repair helper |
| [`tools/strip_ai_stack_docstring_placeholders.py`](tools/strip_ai_stack_docstring_placeholders.py) | AI-stack placeholder cleanup (use only when in scope) |
| [`tools/sync_docify_skills.py`](tools/sync_docify_skills.py) | Copy hub skills → `.cursor/skills/` |
| [`tools/validate_docify_skill_paths.py`](tools/validate_docify_skill_paths.py) | Validate skill markdown path targets |

## Cursor skills

Canonical skills: ``'fy'-suites/docify/superpowers/<skill-name>/SKILL.md``. **Committed** copies for auto-discovery: `.cursor/skills/<skill-name>/SKILL.md`.

After editing any canonical Docify skill, run from repository root:

```bash
python "./'fy'-suites/docify/tools/sync_docify_skills.py"
```

Optional drift check (exit 1 if copies differ):

```bash
python "./'fy'-suites/docify/tools/sync_docify_skills.py" --check
```

Do **not** hand-edit only `.cursor/skills/` for Docify — sync overwrites those files.

## Path validation

```bash
python "./'fy'-suites/docify/tools/validate_docify_skill_paths.py"
```

## Tests

```bash
python -m pytest "'fy'-suites/docify/tools/tests" -q
```

See root [`AGENTS.md`](../../AGENTS.md) for how Docify relates to the rest of the monorepo.

## Patterns adopted vs rejected (vs Despaghettify)

| Pattern | Verdict | Notes |
|---------|---------|-------|
| Hub package + `python -m …` entry | **Adopted** | Same ergonomics as other “fy” hubs (`docify.tools`). |
| Canonical Markdown input list | **Adopted** | `documentation_implementation_input.md` with **DOC-*** rows. |
| `state/` narrative / evidence | **Adapted** | Lightweight `state/README.md`; no autonomous loop JSON. |
| Numeric trigger matrix + setup sync | **Rejected** | Documentation quality is not reduced to a single M7-style scalar in Docify. |
| `reports/` JSON bundles | **Adopted** | Drift + audit JSON for before/after evidence. |
