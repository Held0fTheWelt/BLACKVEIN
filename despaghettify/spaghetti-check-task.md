# Task: Structure / spaghetti check (reproducible)

*Path:* `despaghettify/spaghetti-check-task.md` — Overview: [README.md](README.md).

This task describes the **full** analysis track for the Despaghettify hub: collect **structure metrics**, name **hotspots**, maintain the canonical [input list](despaghettification_implementation_input.md) — **without** code refactors (implementation stays with the implementer and follows [`EXECUTION_GOVERNANCE.md`](state/EXECUTION_GOVERNANCE.md) for real waves).

**Scan timestamp (non-negotiable):** Any run that updates § *Latest structure scan* in the input list **must** set **As of (date & time)** to the **actual moment** the scan steps were executed (see §1 under *Maintaining the input list*).

**Threshold:** Compute the weighted 7-category score **M7** as defined in the input list. **Update § *Information input list* and § *Recommended implementation order* (and § *DS-ID → primary workstream* for new IDs)** when **any** trigger below fires; otherwise do **not** touch those sections (no new DS rows, no phase reshuffle) — **Latest structure scan** including **M7**, category breakdown, AST telemetry, and **Open hotspots** is **always** updated (see below).

**Per-category triggers** (each **C** is the same 0–100 style score as in the input list; strict **>**):

| Category | Symbol | Trigger (update DS + phases if score is **greater than**) |
|----------|--------|---------------------------------------------------------------|
| Circular dependencies | **C1** | **5** |
| Nesting depth | **C2** | **10** |
| Long functions + complexity | **C3** | **35** |
| Multi-responsibility modules | **C4** | **25** |
| Magic numbers + global state | **C5** | **20** *(default; tune in input list if team agrees a different bar)* |
| Missing abstractions / duplication | **C6** | **15** |
| Confusing control flow | **C7** | **20** |

**Composite M7 trigger:** also update those sections if **`M7 ≥ M7_ref`**, where **`M7_ref`** is the weighted score obtained when **each** category **C1..C7** is set to its trigger value from the table above (including **C5 = 20**). With the standard weights: **`M7_ref = 0.20×5 + 0.10×10 + 0.20×35 + 0.15×25 + 0.10×20 + 0.15×15 + 0.10×20 = 19.0%`**. So: **if `M7 ≥ 19%`** (same unit as the main table), treat as trigger **even if** no single per-category line crossed yet *(rare; mainly aligns composite with the chosen per-category bars)*.

**Scan-only pass:** update **only** § *Latest structure scan* when **no** per-category trigger fires **and** **`M7 < 19%`**.

## Binding sources

| Document | Role |
|----------|------|
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | **Always:** **Latest structure scan** (as-of **date and time**, **M7**, category scores C1..C7, AST telemetry **N/L₅₀/L₁₀₀/D₆**, extra checks, **Open hotspots** — **prune resolved items**, never re-list solved hotspots; see §1). **Only if trigger policy is met** (per-category thresholds **or** **`M7 ≥ M7_ref`**; see **Threshold** above): **information input list** (DS rows), **recommended implementation order** (phase proposal), § **DS-ID → primary workstream** for new IDs. |
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

All in [despaghettification_implementation_input.md](despaghettification_implementation_input.md). The trigger policy is the per-category table **plus** composite **`M7 ≥ M7_ref`** (see **Threshold** above); the input list mirrors the same rules under § *Trigger policy for check task updates*.

### 1) Latest structure scan — **always**

- **As of (date & time) — required:** Fill the **As of (date & time)** cell with the **timestamp when this check run’s scan commands ran** (not a hand-waved day only). Use **`YYYY-MM-DD HH:mm:ss`** (24-hour). **Timezone:** optional; add **once** in parentheses after the time if it matters (e.g. `(Europe/Berlin)` or `(UTC)`). If the repo assumes one zone everywhere, a single sentence in the input list header is enough and the cell may omit the suffix.
- **Metrics:** category scores **C1..C7**, weighted **M7**, and AST telemetry (**N**, **L₅₀**, **L₁₀₀**, **D₆**).
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

**How to build a *suitable* phase table (required whenever DS rows are filled):**

1. **Cover every open DS-ID** from § *Information input list* with at least one **phase** row (unless two IDs are explicitly merged into one wave with team agreement — then one row may list multiple **DS-*** and the note must say so). **Never** leave the phase table as `—` while the DS table has real rows.
2. **Order phases by risk and blast radius**, not by DS number: prefer topics that **stabilise shared runtime / import seams** (turn pipeline, narrative commit, `app.runtime` edges, `ds005`-visible modules) **before** very large **service orchestration** functions that pull many imports. Put **package-separated** hotspots (e.g. `ai_stack` only) in a **later** phase unless the scan shows they block backend work.
3. **One primary workstream per phase row** (see [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)): it must match where **pre/post** artefacts would go for that wave. If a phase touches two packages, pick the **primary** workstream and mention the other in **note** (“call sites only”, “no separate pre/post”).
4. **Short logic** = one line: *what* this phase achieves structurally (e.g. “shrink X before refactoring Y”). **Note** = concrete **gates**: which `pytest` paths, `ds005`, or integration checks the implementer should run after the slice.
5. **Dependencies:** if phase B genuinely requires interfaces from phase A, say so in **note** on phase B; avoid claiming a hard dependency unless imports or tests prove it — default is **soft ordering** (risk reduction), which is still valid to document as “prefer A before B”.

### Optional

- **Progress / work log** and **`WORKSTREAM_*_STATE.md`**: only for a **formal wave** with pre/post (see governance).

## Output format for the requester (short)

After the run: **3–8 sentences** on **M7**, category outliers, and whether **Open hotspots** shrank or cleared (no solved items left listed). **Only if trigger policy is met** (any **C** above its bar **or** **`M7 ≥ M7_ref`**): additionally **1–3 sentences** on **proposed implementation order** (first phase and why) plus pointer to changed sections (**scan**, **DS table**, **phase table**). If trigger policy is not met: reference **Latest structure scan** (including **Open hotspots** pruned to unresolved only) — no obligation to change DS / phases.

## Counterpart: implementation wave by wave

The **execution track** (review order, adjust if needed, then Despaghettify waves with pre/post until the list is empty): [spaghetti-solve-task.md](spaghetti-solve-task.md).
