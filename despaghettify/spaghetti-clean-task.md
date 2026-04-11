# Spaghetti clean task (workstream artefact wipe + ephemeral cleanup)

**Purpose:** Remove **all** session pre/post files under [`state/artifacts/workstreams/`](state/artifacts/workstreams/) (every governed workstream slug), then recreate **empty** `pre/` and `post/` directories so the tree stays usable for the next wave. Optionally continues with the same **ephemeral** repo cleanup as [`spaghetti-reset-task.md`](spaghetti-reset-task.md) (caches, `var/` scratch, hub `*.tmp`).

**Language:** English (hub policy).

**Binding index:** Workstream slugs and paths — [`state/WORKSTREAM_INDEX.md`](state/WORKSTREAM_INDEX.md).

---

## Danger / irreversibility

- This task **deletes governance evidence** (all files under `artifacts/workstreams/<slug>/pre/` and `…/post/` for every slug). **Do not** run on a machine that is the **only** copy of required closure proof; prefer machines with Git history / PRs / CI logs as backup.
- This task **does not** delete `despaghettify/state/WORKSTREAM_*.md` or other state **documents** — only the **artefact file trees** under `artifacts/workstreams/`.
- **`artifacts/repo_governance_rollout/`** is **not** removed here (different scope); delete only if team policy says so, outside this task.

---

## Step 1 — Wipe and recreate `artifacts/workstreams/`

**Effect:** Delete the entire directory `despaghettify/state/artifacts/workstreams/` (all children), then recreate it with one folder per workstream from the index, each containing empty **`pre/`** and **`post/`**.

Canonical slugs (must match [WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)):

| Slug |
|------|
| `backend_runtime_services` |
| `ai_stack` |
| `administration_tool` |
| `documentation` |
| `world_engine` |

**PowerShell (repo root):**

```powershell
$root = 'despaghettify/state/artifacts/workstreams'
if (Test-Path $root) { Remove-Item -Recurse -Force $root }
$slugs = @(
  'backend_runtime_services',
  'ai_stack',
  'administration_tool',
  'documentation',
  'world_engine'
)
foreach ($s in $slugs) {
  New-Item -ItemType Directory -Force -Path (Join-Path $root "$s/pre") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $root "$s/post") | Out-Null
}
```

**Bash (repo root):**

```bash
rm -rf despaghettify/state/artifacts/workstreams
for s in backend_runtime_services ai_stack administration_tool documentation world_engine; do
  mkdir -p "despaghettify/state/artifacts/workstreams/$s/pre"
  mkdir -p "despaghettify/state/artifacts/workstreams/$s/post"
done
```

---

## Step 2 — Ephemeral repo + hub scratch (same scope as reset task 1a–1c)

Reuse **Step 1** (sections 1a–1c) from [`spaghetti-reset-task.md`](spaghetti-reset-task.md): repo caches, wave-adjacent `var/` trees, loose scratch under `despaghettify/` excluding `state/` and `templates/`.

**Order:** Run **Step 1 (workstreams)** of **this** document **before** the reset task’s copy of EMPTY → live input, so no stale session files remain beside a fresh input list.

---

## Relationship to other tasks

| Task | Role |
|------|------|
| **This file (`spaghetti-clean-task`)** | Wipe **all** workstream pre/post trees + optional ephemeral cleanup. |
| [`spaghetti-reset-task.md`](spaghetti-reset-task.md) | **Requires** running this clean (workstream wipe) **first**, then reset input from template + one check pass. |
| [`spaghetti-check-task.md`](spaghetti-check-task.md) | Read-side metrics; **does not** delete artefacts. |

---

## Completion checklist

- [ ] `despaghettify/state/artifacts/workstreams/` was removed and recreated with **five** slugs, each with **empty** `pre/` and `post/`.
- [ ] (If combined with reset) Ephemeral dirs from reset task 1a–1b and hub file sweep 1c completed.
- [ ] Team understands prior session files under workstreams are **gone** from the working tree.
