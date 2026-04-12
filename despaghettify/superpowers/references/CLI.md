# `despaghettify/tools/despaghettify.py` — automation CLI

## Canonical entry points

- **No install:** from **repository root** (or any cwd if `PYTHONPATH` includes the repo root), run  
  `python -m despaghettify.tools <subcommand> …`  
  (`despaghettify/tools/__main__.py` prepends the repo root to `sys.path` when needed.)
- **Optional:** after `pip install -e .` at repo root (`pyproject.toml` **world-of-shadows-hub**), use console scripts **`despag-check`** or **`wos-despag`** — same argv as `python -m despaghettify.tools`.
- **Direct script:** `python despaghettify/tools/despaghettify.py …` (path to the file).

## `check`

Runs:

- AST metrics via `spaghetti_ast_scan.collect_ast_stats()` (same logic as `python despaghettify/tools/spaghetti_ast_scan.py`)
- `python despaghettify/tools/ds005_runtime_import_check.py` (non-zero exit if imports fail)
- Builtins / GoC template probe (same idea as check task **extra check builtins**)
- Runtime cycle-hint grep under `backend/app/runtime/` (`TYPE_CHECKING`, `avoid circular`, `circular dependency`)

**Usage**

```bash
python -m despaghettify.tools check
python -m despaghettify.tools check --out .state_tmp/despag_check_report.json
# optional after pip install -e .:
# despag-check check --out .state_tmp/despag_check_report.json
```

**Exit codes:** `0` = success including `ds005`; `1` = `ds005` failure; `3` = mis-invocation.

**Output:** JSON on stdout (or written to `--out`). Use it to paste into a chat or to diff before/after a wave.

**Optional:** `--with-metrics` — if `despaghettify/spaghetti-setup.json` exists, embed a **`metrics_bundle`** (`ast_heuristic_v2` + **`score`** / **`metric_a`**) for `trigger-eval` / autonomous tooling.

## `autonomous-init` / `autonomous-advance` / `autonomous-status` / `autonomous-verify`

Session file (local): `despaghettify/state/artifacts/autonomous_loop/autonomous_state.json` (usually gitignored with `despaghettify/state/`). Schema: [`../../tools/schemas/autonomous_state.schema.json`](../../tools/schemas/autonomous_state.schema.json).

```bash
python -m despaghettify.tools autonomous-init
python -m despaghettify.tools autonomous-init --force
python -m despaghettify.tools autonomous-status
python -m despaghettify.tools autonomous-advance --kind backlog-solve --ds DS-016
python -m despaghettify.tools autonomous-advance --kind main-check --check-json .state_tmp/despag_check_report.json
python -m despaghettify.tools autonomous-advance --kind main-solve --ds DS-020
python -m despaghettify.tools autonomous-verify
python -m despaghettify.tools autonomous-verify --allow-dirty --setup-json despaghettify/spaghetti-setup.json
```

**Exit codes — `autonomous-init`:** `0` created; `2` session already exists (use `--force`).

**`autonomous-advance`:** `0` recorded; `2` illegal transition or **DS-*** still open when recording a solve.

**`autonomous-verify`:** `0` ok; `1` advisory (anti-stall heuristic); `2` hard failure (invalid state, `HEAD` mismatch vs recorded `head_sha_expected`, dirty worktree unless `--allow-dirty`).

## `setup-audit`

Reads **[`../../spaghetti-setup.md`](../../spaghetti-setup.md)** as the **canonical** policy (bars, weights, `M7_ref`), compares [`../../spaghetti-setup.json`](../../spaghetti-setup.json), and optionally prints **Anteil %** vs md bars from a **`check --with-metrics`** JSON.

```bash
python -m despaghettify.tools setup-audit
python -m despaghettify.tools setup-audit --check-json despaghettify/reports/reset_check.json
python -m despaghettify.tools setup-audit --json
```

**Exit:** `0` if md and json match; `1` if drift (update **json** after editing **md**).

## `setup-sync`

Writes [`../../spaghetti-setup.json`](../../spaghetti-setup.json) from the numeric tables in [`../../spaghetti-setup.md`](../../spaghetti-setup.md) (bars, weights, `M7_ref`). Refuses to write if the **M7_ref** cell in Markdown disagrees with Σ(weight×bar) (exit **2**). After editing **md**, run **`setup-sync`** then **`setup-audit`** to confirm.

```bash
python -m despaghettify.tools setup-sync
python -m despaghettify.tools setup-sync --dry-run
```

**Exit:** `0` on success; `2` if Markdown is invalid or `M7_ref` is inconsistent with bars×weights.

**Standalone:** `python -m despaghettify.tools.spaghetti_setup_audit --sync` (same flags as hub: `--setup-md`, `--setup-json`, `--dry-run`).

## `metrics-emit` / `trigger-eval`

Machine line for trigger policy (**`anteil_pct`** vs bars in setup) + [`../../spaghetti-setup.json`](../../spaghetti-setup.json) — mirror must match [`../../spaghetti-setup.md`](../../spaghetti-setup.md) (use **`setup-sync`** or **`setup-audit`** after edits).

```bash
python -m despaghettify.tools check --out .state_tmp/despag_check_report.json
python -m despaghettify.tools metrics-emit --check-json .state_tmp/despag_check_report.json --setup-json despaghettify/spaghetti-setup.json --out .state_tmp/metrics_bundle.json
python -m despaghettify.tools trigger-eval --check-json .state_tmp/despag_check_report.json
```

**Exit:** `0` always if inputs parse; `3` if paths missing.

## `open-ds`

Lists **open** `DS-*` ids (table rows with `| **DS-nnn** |` in § *Information input list*).

```bash
python -m despaghettify.tools open-ds
```

**Exit:** `0` always if the slice parses (empty output = no open rows).

## `solve-preflight`

Validates that a **DS-* id** is present as an **open** row before starting [spaghetti-solve-task.md](../../spaghetti-solve-task.md). When status is **open**, the JSON includes **`wave_sizing`**: path/gate heuristics from the table row and suggested **`n_suggested_min` / `n_suggested_max`** (see solve task **Wave sizing**).

```bash
python -m despaghettify.tools solve-preflight --ds DS-016
```

**Exit codes:** `0` = open; `2` = missing or closed; `3` = bad `--ds` format.

**CI / test only:** `--override-input-list PATH` — markdown file **under** `despaghettify/tools/fixtures/` that contains the same `## Information input list` … `## Recommended implementation order` slice as the real input list (e.g. stub **DS-990**). Used when the canonical list has no open rows but CI must still run `solve-preflight`.

## `wave-plan-validate`

Checks a persisted **`wave_plan.json`** against the schema in [WAVE_PLAN_SCHEMA.md](WAVE_PLAN_SCHEMA.md).

```bash
python -m despaghettify.tools wave-plan-validate --file despaghettify/tools/fixtures/despag_wave_plan_example_valid.json
```

**Optional flags:** `--check-primary-paths` (require `primary_paths[]` files to exist); `--gate-prefix-allowlist python,pytest,ruff` (each `gate_command` must start with one prefix).

**Exit codes:** `0` = valid; `2` = validation errors (details on stderr as JSON); `3` = missing file or JSON parse error.

## `wave_plan_emit.py` (Markdown ↔ JSON)

Standalone helper: `despaghettify/tools/wave_plan_emit.py`.

```bash
python despaghettify/tools/wave_plan_emit.py json2md --json despaghettify/tools/fixtures/despag_wave_plan_example_valid.json --out /tmp/plan.md
python despaghettify/tools/wave_plan_emit.py md2json --md despaghettify/tools/fixtures/wave_plan_embed_example.md --out /tmp/plan.json
python despaghettify/tools/wave_plan_emit.py md2json --from-wave-table --md /tmp/plan.md --out /tmp/plan2.json --ds-id DS-099
```

Use **`json2md --table-only`** when you only want the GFM table; pair with **`md2json --from-wave-table`** to round-trip.

## Skills integration

Skills are **routers** only: they point at the task Markdown files; they **must not** duplicate checklists. **Trigger numbers** live in `spaghetti-setup.md`; analysis steps in `spaghetti-check-task.md`. Optionally run the matching CLI subcommand first for machine output, then follow **only** the task Markdown for the track (`spaghetti-check-task.md`, `spaghetti-solve-task.md`, `spaghetti-add-task-to-meet-trigger.md`, or `spaghetti-autonomous-agent-task.md`) as appropriate, reading **setup** first when evaluating **M7** / triggers.
