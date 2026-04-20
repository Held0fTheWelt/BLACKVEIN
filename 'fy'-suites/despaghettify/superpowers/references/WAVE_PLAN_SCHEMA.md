# Wave plan JSON (`wave_plan.json`)

Machine-readable mirror of the markdown wave-plan table in [spaghetti-solve-task.md](../../spaghetti-solve-task.md). **Same truth as the table:** same **N**, goals, primary paths, and **copy-pastable** `gate_commands`.

## Where to store it

Next to the human-readable plan, under the workstream artefact root (example):

`despaghettify/state/artifacts/workstreams/<slug>/pre/session_YYYYMMDD_DS-016_wave_plan.json`

Use the **same** `session_YYYYMMDD` and **DS-ID** as in pre/post filenames. CI validates fixtures under **`despaghettify/tools/fixtures/`**; production files live under `despaghettify/state/artifacts/…` on branches doing solve work.

## One source, two shapes (optional)

[`../../tools/wave_plan_emit.py`](../../tools/wave_plan_emit.py) can:

- **`json2md`** — build a fenced JSON code block plus a **Wave plan** table from existing valid JSON (paste into `WORKSTREAM_*_STATE.md` or `pre/` notes).
- **`md2json`** — read that JSON code block back into `wave_plan.json`, or use **`--from-wave-table`** after **`json2md --table-only`** to round-trip the table.

Run from repo root; see also [`CLI.md`](CLI.md).

## Schema (version 1)

| Field | Required | Type | Notes |
|-------|----------|------|--------|
| `schema_version` | yes | `1` or `"1"` | Bump only when fields change. |
| `ds_id` | yes | string | `DS-<digits>` only, e.g. `DS-016`. |
| `slug` | no | string | Workstream slug from `WORKSTREAM_INDEX.md`. If present, must be non-empty. |
| `session_date` | no | string | e.g. `20260410` (align with filename prefix). If present, must be non-empty. |
| `completed_wave_ids` | no | array of strings | Subset of `sub_waves[].id` (e.g. `["w01"]`) for resume tooling; omit or `[]` if unused. |
| `next_index` | no | int | Next **1-based** sub-wave to run (`k+1` after completing `k`), or **`N+1`** when all waves are done. Must satisfy **1 ≤ next_index ≤ N+1** when present. |
| `sub_waves` | yes | array | Length **N**, **1 … 8** (solve task: split DS if honest **N > 8**). |

Each element of `sub_waves`:

| Field | Required | Type | Notes |
|-------|----------|------|--------|
| `index` | yes | int | **1 … N**, contiguous, no duplicates. |
| `id` | yes | string | Stable stem token, e.g. `w01` (matches `_w01_` in artefact names). |
| `goal` | yes | string | One sentence; same intent as the markdown row. |
| `gate_commands` | yes | array of strings | Non-empty; each string is a full shell command. |
| `primary_paths` | no | array of strings | Repo-relative paths; may be empty or omitted. |

## Validate locally

```bash
python -m despaghettify.tools wave-plan-validate --file despaghettify/tools/fixtures/despag_wave_plan_example_valid.json
```

**Optional strict flags** (off by default):

- **`--check-primary-paths`** — every `primary_paths[]` entry must exist under the repo root.
- **`--gate-prefix-allowlist a,b,c`** — each `gate_command` must **start with** one of the comma-separated prefixes (e.g. `python,pytest`); use sparingly so legitimate commands are not rejected.

Exit **0** = valid; **2** = validation errors (JSON on stderr); **3** = missing file or JSON parse error.
