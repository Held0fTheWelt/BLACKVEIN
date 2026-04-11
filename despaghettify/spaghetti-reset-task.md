# Spaghetti reset task (clean slate + one check pass)

**Purpose:** Remove **ephemeral / local** artefacts from the working tree (including **despaghettification-adjacent** caches and scratch), reset [`despaghettification_implementation_input.md`](despaghettification_implementation_input.md) to the **canonical empty template**, then run **[`spaghetti-check-task.md`](spaghetti-check-task.md)** **once** to repopulate § *Latest structure scan* (and, if the trigger policy is met, the DS table and recommended order).

**Language:** English (hub policy).

---

## Preconditions

- Work from **repository root** (the folder that contains `tools/`, `backend/`, `despaghettify/`).
- **Do not** delete or rewrite anything under `despaghettify/state/artifacts/**` as part of “temp cleanup” — those are **governance pre/post evidence**. If you intentionally prune old sessions, do it only per team policy and **never** conflate with this reset.
- If you use `git clean`, **never** use `-x` or `-fd` without reviewing what would be removed; this task uses **explicit paths** only.

---

## Step 1 — Remove ephemeral directories and despaghettification-adjacent temp

### 1a — Repo-wide caches and build scratch

Delete the following **if they exist** (ignored or regenerable; commonly filled while running checks, pytest, or MkDocs during despaghettification work):

| Path (relative to repo root) | Notes |
|--------------------------------|--------|
| `.state_tmp/` | MkDocs / tooling scratch (see `.gitignore`). Often holds **HTML mirrors** of docs paths (including under `despaghettify/…`) — safe to delete; not governance evidence. |
| `.pytest_cache/` | Pytest cache. |
| `htmlcov/` | Coverage HTML output. |
| `temp_tests_backup/` | Local backup folder if present. |
| `_tmp_goc_dbg/` | Debug scratch if present. |
| `site/` | MkDocs `site/` output **only if** you treat it as disposable build output. |
| `.wos/` | Local operational scratch (see `.gitignore`) if present. |

### 1b — Stores often touched during despag waves / improvement loops

These are **not** under `despaghettify/state/artifacts/**` but are typical **local JSON / run** outputs while exercising backend or engine paths referenced from the input list and solve task:

| Path (relative to repo root) | Notes |
|--------------------------------|--------|
| `backend/var/improvement/` | Improvement-loop operational store (local / test). |
| `backend/var/writers_room/` | Writers Room local store (test / dev). |
| `world-engine/app/var/runs/` | Engine run artefacts (see `.gitignore`). |

### 1c — Ephemeral files inside `despaghettify/` (hub only, not governance)

Remove **loose** scratch files under `despaghettify/` that agents or editors sometimes leave next to the hub docs — **never** delete the canonical task docs, `templates/`, or anything under `despaghettify/state/` (including `state/artifacts/**`).

**Eligible patterns** (files only; skip directories `state/`, `templates/`):

- `*.tmp`, `*.bak`, `*.log`, `*~`, `*.swp`, `.DS_Store` (when under `despaghettify/`).

**PowerShell (repo root) — dirs 1a–1b + file sweep 1c:**

```powershell
$dirs = @(
  '.state_tmp', '.pytest_cache', 'htmlcov', 'temp_tests_backup', '_tmp_goc_dbg', 'site', '.wos',
  'backend/var/improvement', 'backend/var/writers_room', 'world-engine/app/var/runs'
)
foreach ($d in $dirs) { if (Test-Path $d) { Remove-Item -Recurse -Force $d } }

$hub = 'despaghettify'
$ext = @('*.tmp', '*.bak', '*.log', '*~', '*.swp')
foreach ($pattern in $ext) {
  Get-ChildItem -Path $hub -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue |
    Where-Object {
      $p = $_.FullName
      $p -notmatch '[\\/]despaghettify[\\/]state[\\/]' -and
      $p -notmatch '[\\/]despaghettify[\\/]templates[\\/]'
    } | Remove-Item -Force
}
if (Test-Path (Join-Path $hub '.DS_Store')) { Remove-Item -Force (Join-Path $hub '.DS_Store') }
Get-ChildItem -Path $hub -Recurse -File -Filter '.DS_Store' -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -notmatch '[\\/]despaghettify[\\/]state[\\/]' } | Remove-Item -Force
```

**Bash (repo root):**

```bash
for d in .state_tmp .pytest_cache htmlcov temp_tests_backup _tmp_goc_dbg site .wos \
         backend/var/improvement backend/var/writers_room world-engine/app/var/runs; do
  [ -e "$d" ] && rm -rf "$d"
done

# 1c: scratch files under despaghettify/ excluding state/ and templates/
find despaghettify -type f \( -name '*.tmp' -o -name '*.bak' -o -name '*.log' -o -name '*~' -o -name '*.swp' -o -name '.DS_Store' \) \
  ! -path 'despaghettify/state/*' ! -path 'despaghettify/templates/*' -delete 2>/dev/null || true
```

**Do not** add `despaghettify/state/`, `.git/`, or user-owned secrets (e.g. `.env`) to deletion lists. **Never** treat `despaghettify/state/artifacts/**/pre|post/**` as “temp” for this reset.

---

## Step 2 — Reset the implementation input file

**Canonical empty body:** [`templates/despaghettification_implementation_input.EMPTY.md`](templates/despaghettification_implementation_input.EMPTY.md)

Copy it over the live input (overwrites in place):

**PowerShell:**

```powershell
Copy-Item -Force despaghettify\templates\despaghettification_implementation_input.EMPTY.md despaghettify\despaghettification_implementation_input.md
```

**Bash:**

```bash
cp -f despaghettify/templates/despaghettification_implementation_input.EMPTY.md despaghettify/despaghettification_implementation_input.md
```

After copy, the input list contains **placeholders** (`—`) for M7, C1–C7, AST telemetry, tables, and open hotspots — ready for the next check pass.

---

## Step 3 — Run [`spaghetti-check-task.md`](spaghetti-check-task.md) exactly once

Execute the full procedure from that document **in order**, at minimum:

1. `python tools/spaghetti_ast_scan.py` from repo root; capture **N**, **L₅₀**, **L₁₀₀**, **D₆**, and category-relevant context for your **C1–C7** assessment.
2. **Duplicate builtins** grep and **runtime** spot checks as described in `spaghetti-check-task.md` § *Extra checks*.
3. `python tools/ds005_runtime_import_check.py` as described there.
4. Update [`despaghettification_implementation_input.md`](despaghettification_implementation_input.md) per **Maintaining the input list** in `spaghetti-check-task.md`:
   - **Always:** § *Latest structure scan* (date, **M7**, **C1..C7**, telemetry, extra checks, **Open hotspots** pruned to **unresolved** only).
   - **Only if trigger met** (`M7 >= 25%` **or** any category **>= 45%**): § *Information input list* and § *Recommended implementation order*.
   - **If trigger not met:** do **not** change the DS table or phase table beyond what the reset already set to placeholders.

**Output to requester:** follow the short **Output format** paragraph at the end of `spaghetti-check-task.md`.

---

## Completion checklist

- [ ] Step **1a–1c** completed: repo caches, wave-adjacent `var/` trees (where present), hub scratch files under `despaghettify/` (excluding `state/` and `templates/`).
- [ ] `despaghettification_implementation_input.md` matches the **EMPTY** template before the check (byte-for-byte optional: diff against `templates/…EMPTY.md`).
- [ ] One full **spaghetti-check** pass completed; scan section filled; DS/phases updated only per trigger policy.

---

## Maintenance

If governance text in the **EMPTY** template drifts from [`spaghetti-check-task.md`](spaghetti-check-task.md) (e.g. new columns or trigger wording), update **`templates/despaghettification_implementation_input.EMPTY.md`** first, then re-export or copy to the live input when running this reset again.
