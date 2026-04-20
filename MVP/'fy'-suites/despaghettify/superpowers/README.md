# Despaghettify superpowers (in-repo skills)

**Cursor-style router skills** for the Despaghettify hub: each `SKILL.md` has YAML frontmatter (`name`, `description`) and **only** points at the canonical **task Markdown** — no duplicated checklists or trigger tables. **Numeric** trigger policy (**C1..C7** bars, **M7** weights, **`M7_ref`**) is canonical in [`../spaghetti-setup.md`](../spaghetti-setup.md). The **full analysis procedure** lives in [`../spaghetti-check-task.md`](../spaghetti-check-task.md).

**Cursor discovery:** project skills are **mirrored** into **`.cursor/skills/`** (committed) so Cursor loads them automatically. After **any** edit under `despaghettify/superpowers/*/SKILL.md`, run from repo root:

```bash
python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"
```

CI or pre-push (optional): `python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py" --check` must exit **0**.

You can still **@‑mention** a skill path (for example `despaghettify/superpowers/despaghettify-check/SKILL.md`) in chat for discovery; execution always follows the linked **task** file.

| Skill folder | Purpose |
|--------------|---------|
| [`despaghettify-orchestrate`](despaghettify-orchestrate/SKILL.md) | **Router:** which task markdown to open (check / solve / add-task / autonomous / clean / reset). |
| [`despaghettify-check`](despaghettify-check/SKILL.md) | **Router** → [`../spaghetti-setup.md`](../spaghetti-setup.md) (numeric policy) **+** [`../spaghetti-check-task.md`](../spaghetti-check-task.md) (scan procedure). |
| [`despaghettify-solve`](despaghettify-solve/SKILL.md) | **Router** → [`../spaghetti-solve-task.md`](../spaghetti-solve-task.md). |
| [`despaghettify-add-task`](despaghettify-add-task/SKILL.md) | **Router** → [`../spaghetti-add-task-to-meet-trigger.md`](../spaghetti-add-task-to-meet-trigger.md). |
| [`despaghettify-autonomous-agent`](despaghettify-autonomous-agent/SKILL.md) | **Router** → [`../spaghetti-autonomous-agent-task.md`](../spaghetti-autonomous-agent-task.md) (Step 0: slice → check `--out` → `backlog-implement`; after row closed → `backlog-solve`; then main check → solve loop). |
| [`despaghettify-clean`](despaghettify-clean/SKILL.md) | **Router** → [`../spaghetti-clean-task.md`](../spaghetti-clean-task.md) (workstream artefact wipe + optional ephemeral cleanup). |
| [`despaghettify-reset`](despaghettify-reset/SKILL.md) | **Router** → [`../spaghetti-reset-task.md`](../spaghetti-reset-task.md) (clean + EMPTY template + one check). |

**Canonical hub docs:** numeric trigger policy [`../spaghetti-setup.md`](../spaghetti-setup.md); procedure per track [`../spaghetti-check-task.md`](../spaghetti-check-task.md), [`../spaghetti-solve-task.md`](../spaghetti-solve-task.md), [`../spaghetti-add-task-to-meet-trigger.md`](../spaghetti-add-task-to-meet-trigger.md), [`../spaghetti-autonomous-agent-task.md`](../spaghetti-autonomous-agent-task.md), [`../spaghetti-clean-task.md`](../spaghetti-clean-task.md), [`../spaghetti-reset-task.md`](../spaghetti-reset-task.md); live data: [`../despaghettification_implementation_input.md`](../despaghettification_implementation_input.md).

See [`references/CURSOR_ACTIVATION.md`](references/CURSOR_ACTIVATION.md) for activation options.

## Automation CLI (machine leg)

Hub CLI: **`python -m despaghettify.tools`** (subcommands **`check`** (optional **`--with-metrics`**), **`open-ds`**, **`solve-preflight`**, **`wave-plan-validate`**, **`autonomous-init`** / **`autonomous-advance`** / **`autonomous-status`** / **`autonomous-verify`**, **`metrics-emit`**, **`trigger-eval`**) — same implementation as [`../tools/hub_cli.py`](../tools/hub_cli.py). Optional: after **`pip install -e .`** at repo root, scripts **`despag-check`** / **`wos-despag`**. Full flags in [`references/CLI.md`](references/CLI.md).

## Path validation

[`references/VALIDATION.md`](references/VALIDATION.md) — `python "./'fy'-suites/despaghettify/tools/validate_despag_skill_paths.py"` and the GitHub Actions workflow for broken links in skill markdown.
