# Task: Structure / spaghetti check (reproducible)

*Path:* `despaghettify/spaghetti-check-task.md` — Overview: [README.md](README.md).

This task describes the **full** analysis track for the Despaghettify hub: collect **structure metrics**, name **hotspots**, maintain the canonical [input list](despaghettification_implementation_input.md) — **without** code refactors (implementation stays with the implementer and follows [`EXECUTION_GOVERNANCE.md`](state/EXECUTION_GOVERNANCE.md) for real waves).

**Threshold:** Compute the weighted 7-category score **M7** as defined in the input list. **If M7 >= 25% or any single category >= 45%**, also edit or newly propose the **information input list** (DS table including workstream mapping) and **recommended implementation order**. If below both trigger conditions, do **not** touch those two sections in the spaghetti check (no new DS rows, no phase reshuffle) — updating **Latest structure scan** including **M7**, category breakdown, AST telemetry, and the **Open hotspots** field is still required (see below), but only with **still-unresolved** items.

## Binding sources

| Document | Role |
|----------|------|
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | **Always:** **Latest structure scan** (date, **M7**, category scores C1..C7, AST telemetry **N/L₅₀/L₁₀₀/D₆**, extra checks, **Open hotspots** — **prune resolved items**, never re-list solved hotspots; see §1). **Only if trigger policy is met (M7 >= 25% or any category >= 45%)**: **information input list** (DS rows), **recommended implementation order** (phase proposal), § **DS-ID → primary workstream** for new IDs. |
| [tools/spaghetti_ast_scan.py](../tools/spaghetti_ast_scan.py) | Canonical metric run (repository root = CWD). |
| [state/EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md) | Analysis and Markdown maintenance create **no** new pre/post artefacts; those appear only when a **wave** with evidence runs. |
| Local planning / issues | Always share scan numbers; mirror proposed order / new DS rows to external tickets only after agreement — and in-repo **only** if trigger policy is met (otherwise the scan section suffices). |

## Do not

- Do **not** change `docs/archive/documentation-consolidation-2026/*`.
- Do **not** sell percentage scores as “objective” truth — at most **heuristic** placement in the scan table.
- Do **not** leave **resolved** items in the **Open hotspots** field of the structure scan (no stale callouts; no re-copying hotspots that the repo or a prior solve wave already fixed — see §1).
- Not a substitute for green CI: the scan is **read-side**; tests remain authoritative.

## Python AST run scope (fixed)

Always include these directories (paths relative to repository root):

- `backend/app`
- `world-engine/app`
- `ai_stack`
- `story_runtime_core`
- `tools/mcp_server`
- `administration-tool`

**Ignore:** `.state_tmp`, `site/`, `node_modules`, `.venv`, `venv`, `__pycache__` (and everything under them).

## Reproduction: AST scan script

**In repository:** [tools/spaghetti_ast_scan.py](../tools/spaghetti_ast_scan.py) — if metric definitions change, maintain **task document and script together**.

The following block is a **copy** of the logic (if the script is missing or diverges):

```python
from __future__ import annotations

import ast
from pathlib import Path

IGNORE = (".state_tmp", "/site/", "node_modules", ".venv", "venv", "__pycache__")
ROOTS = [
    Path("backend/app"),
    Path("world-engine/app"),
    Path("ai_stack"),
    Path("story_runtime_core"),
    Path("tools/mcp_server"),
    Path("administration-tool"),
]


def walk(root: Path):
    for p in root.rglob("*.py"):
        s = p.as_posix()
        if any(x in s for x in IGNORE):
            continue
        yield p


def nest_depth(body: list[ast.stmt], d: int = 0) -> int:
    m = d
    for b in body:
        if isinstance(b, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.Try)):
            m = max(m, d + 1)
            for attr in ("body", "orelse", "handlers", "finalbody"):
                sub = getattr(b, attr, None)
                if isinstance(sub, list):
                    m = max(m, nest_depth(sub, d + 1))
    return m


def metrics(path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(n, "end_lineno", None) or n.lineno
            out.append((n.name, end - n.lineno + 1, nest_depth(n.body, 0), path))
    return out


def main() -> None:
    allm = []
    for r in ROOTS:
        if r.exists():
            for p in walk(r):
                allm.extend(metrics(p))
    long50 = [x for x in allm if x[1] > 50]
    long100 = [x for x in allm if x[1] > 100]
    deep6 = [x for x in allm if x[2] >= 6]
    print("Total functions:", len(allm))
    print(">50 lines:", len(long50), ">100 lines:", len(long100), "nesting>=6:", len(deep6))
    long100.sort(key=lambda x: -x[1])
    print("Top 12 longest:")
    for name, lines, nd, p in long100[:12]:
        print(f"  {lines:4d}L depth~{nd} {p.as_posix()}:{name}")
    deep6.sort(key=lambda x: (-x[2], -x[1]))
    print("Top 6 nesting:")
    for name, lines, nd, p in deep6[:6]:
        print(f"  depth {nd} {lines:4d}L {p.as_posix()}:{name}")
    ate = Path("backend/app/runtime/ai_turn_executor.py")
    if ate.exists():
        raw = len(ate.read_text(encoding="utf-8", errors="replace").splitlines())
        ex = [x for x in metrics(ate) if x[0] == "execute_turn_with_ai"]
        print("ai_turn_executor.py lines:", raw)
        if ex:
            print("execute_turn_with_ai:", ex[0][1], "lines depth~", ex[0][2])


if __name__ == "__main__":
    main()
```

Run from **repository root**:

```bash
python tools/spaghetti_ast_scan.py
```

## Extra checks (fixed)

1. **Duplicate builtins:** search for `def build_god_of_carnage_solo` in `**/builtins.py` (backend + world-engine) — mention state briefly in the scan table while builtins/drift remains an open theme.
2. **Import workarounds (spot check):** grep under `backend/app/runtime` for `TYPE_CHECKING`, `avoid circular`, `circular dependency` — qualitative only (“still present” / “fewer hits”); no full graph analysis required.

## Maintaining the input list

All in [despaghettification_implementation_input.md](despaghettification_implementation_input.md). The trigger policy refers to the weighted 7-category score **M7** and critical category cutoffs documented in the input list.

### 1) Latest structure scan — **always**

- **Date** and metrics from the scan run: category scores **C1..C7**, weighted **M7**, and AST telemetry (**N**, **L₅₀**, **L₁₀₀**, **D₆**).
- **Extra checks** (builtins, runtime spot check `TYPE_CHECKING` / cycle hints) briefly in the scan section if you run them.
- Longest functions and top nesting **fully** only in **script output**; in Markdown **core findings** and the **Open hotspots** table row as follows:
  - **Open hotspots must not show solved problems.** Before writing, read the previous **Open hotspots** text and reconcile with the **current** repo and this run’s script output (line counts, paths, names). If a named function or theme is **no longer** a top offender or was **split / moved / shortened** by an implemented wave, **drop** that fragment from **Open hotspots**; use **—** when nothing structural remains to call out beyond the numeric row.
  - Only list **still-open** structural issues (typically 2–5 short clauses aligned with current top lines / nesting or checks). Do **not** reintroduce text that [spaghetti-solve-task.md](spaghetti-solve-task.md) already cleared unless the problem has **regressed** in the tree.
  - Do **not** duplicate the full script leaderboard in **Open hotspots** — that belongs in terminal output only; the cell is for **curated, unresolved** callouts.

### 2) Information input list (table) — **only if trigger policy is met**

- Each recognised or worsened **structure / spaghetti gap** gets its **own row** with columns: **ID**, **pattern**, **location**, **hint / measurement idea**, **direction** (one-sentence sketch), **collision hint** (what would be risky in parallel).
- **IDs:** **update** existing **DS-*** rows (measurements, location, collision) instead of inventing duplicates; assign the next free **DS-*** number only for **new** topics.
- Then maintain the **DS-ID → primary workstream** table in the same document (slug → `artifacts/workstreams/<slug>/pre|post/` per [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)).
- **If trigger policy is not met:** do **not** change this section or the workstream table within the spaghetti check.

### 3) Recommended implementation order — **only if trigger policy is met**

- Section **“Recommended implementation order”** as the analysis agent’s **proposal**: table **priority / phase**, **DS-ID(s)**, **short logic**, **workstream (primary)**, **note** (dependencies, gates).
- **Heuristic (order):** interfaces and shared edges (**DTOs, clear module boundaries**) before large moves; **high coupling / deep nesting hotspots** not in parallel by two owners without aligned artefact sets; do not hide builtins/import topics behind large runtime refactors when the scan surfaces them first.
- If only numbers change without a new substantive thesis: **confirm** the phase table or add a row **“no change vs last scan”** — do not leave empty placeholder phases when the input table has rows.
- **If trigger policy is not met:** do **not** change this section within the spaghetti check (no phase shuffle for scan noise only).

### Optional

- **Progress / work log** and **`WORKSTREAM_*_STATE.md`**: only for a **formal wave** with pre/post (see governance).

## Output format for the requester (short)

After the run: **3–8 sentences** on **M7**, category outliers, and whether **Open hotspots** shrank or cleared (no solved items left listed). **Only if trigger policy is met:** additionally **1–3 sentences** on **proposed implementation order** (first phase and why) plus pointer to changed sections (**scan**, **DS table**, **phase table**). If trigger policy is not met: reference **Latest structure scan** (including **Open hotspots** pruned to unresolved only) — no obligation to change DS / phases.

## Counterpart: implementation wave by wave

The **execution track** (review order, adjust if needed, then Despaghettify waves with pre/post until the list is empty): [spaghetti-solve-task.md](spaghetti-solve-task.md).
