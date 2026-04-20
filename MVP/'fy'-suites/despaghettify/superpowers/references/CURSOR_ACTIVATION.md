# Activating Despaghettify superpowers in Cursor

## Default — project skills (same on Windows, macOS, Linux)

This repository **commits real files** under `.cursor/skills/despaghettify-*/SKILL.md` (not symlinks, not junctions). Root [`.gitignore`](../../../../.gitignore) ignores `.cursor/*` **except** `.cursor/skills/**`, so a normal `git clone` / pull gives you **on-disk copies** Cursor can load everywhere.

**No symlink workflow:** Do **not** use `ln -s`, `mklink`, or Developer Mode for skills. The supported path is always:

```bash
python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"
```

after editing `'fy'-suites/despaghettify/superpowers/<name>/SKILL.md`. That command **copies** files into `.cursor/skills/` — identical behaviour on **Windows** and Unix.

## Skill auto-load vs @‑mention

- **Auto-load:** Cursor picks up **project** skills from `.cursor/skills/` when the folder is present in the workspace (after clone or pull). No extra install step.
- **@‑mention** (e.g. `@despaghettify/superpowers/despaghettify-orchestrate/SKILL.md`): useful for one-off context; it does **not** replace committed `.cursor/skills/` for discovery. If your branch is missing or stale under `.cursor/skills/`, run **`python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"`** and commit the result — do not rely on @‑only workflows on Windows (or any OS).

## After pulling someone else’s branch

If `git pull` changed only `'fy'-suites/despaghettify/superpowers/` but not `.cursor/skills/` (merge conflict or partial update), run:

```bash
python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py"
```

Optional drift guard: `python "./'fy'-suites/despaghettify/tools/sync_despag_skills.py" --check` (must exit **0** before push if your CI enforces it).
