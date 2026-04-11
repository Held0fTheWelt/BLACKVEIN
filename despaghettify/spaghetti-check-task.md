# Task: Structure / spaghetti check (reproducible)

*Path:* `despaghettify/spaghetti-check-task.md` — Overview: [README.md](README.md).

This task describes the **full** analysis track for the Despaghettify hub: collect **structure metrics**, name **hotspots**, maintain the canonical [input list](despaghettification_implementation_input.md) — **without** code refactors (implementation stays with the implementer and follows `[EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md)` for real waves).

**Scan timestamp (non-negotiable):** Any run that updates § *Latest structure scan* in the input list **must** set **As of (date & time)** to the **actual moment** the scan steps were executed (see §1 under *Maintaining the input list*).

**Threshold:** Compute the weighted 7-category score **M7** as defined in the input list. **Update § *Information input list* and § *Recommended implementation order* (and § *DS-ID → primary workstream* for new IDs)** when **any** trigger below fires; otherwise do **not** touch those sections (no new DS rows, no phase reshuffle) — **Latest structure scan** including **M7**, category breakdown, AST telemetry, and **Open hotspots** is **always** updated (see below).

**Per-category triggers** (each **C** is the same 0–100 style score as in the input list; strict **>**):


| Category                           | Symbol | Trigger (update DS + phases if score is **greater than**) |
| ---------------------------------- | ------ | --------------------------------------------------------- |
| Circular dependencies              | **C1** | **5**                                                     |
| Nesting depth                      | **C2** | **8**                                                     |
| Long functions + complexity        | **C3** | **25**                                                    |
| Multi-responsibility modules       | **C4** | **20**                                                    |
| Magic numbers + global state       | **C5** | **12**                                                    |
| Missing abstractions / duplication | **C6** | **14**                                                    |
| Confusing control flow             | **C7** | **10**                                                    |


**Composite M7 trigger:** also update those sections if **`M7 ≥ M7_ref`**, where **`M7_ref`** is the weighted **M7** obtained when **each** of **C1..C7** is set to **exactly** its **trigger value** from the **Per-category triggers** table above (same 0–100 numbers as in the input list, **before** the `%` suffix in Markdown). With the weights from [despaghettification_implementation_input.md](despaghettification_implementation_input.md) § *Score M7*:

`M7_ref = 0.20×C1 + 0.10×C2 + 0.20×C3 + 0.15×C4 + 0.10×C5 + 0.15×C6 + 0.10×C7`

Substituting the current trigger row (**C1=5, C2=8, C3=25, C4=20, C5=12, C6=14, C7=10**):

`**M7_ref = 0.20×5 + 0.10×8 + 0.20×25 + 0.15×20 + 0.10×12 + 0.15×14 + 0.10×10 = 14.1%**` (i.e. **14.1** on the 0–100 scale).

So: **if `M7 ≥ 14.1%`** (same unit as the main table), treat as trigger **even if** no single per-category line crossed yet *(rare; aligns composite with the chosen per-category bars)*.

**Scan-only pass:** update **only** § *Latest structure scan* when **no** per-category trigger fires **and** **`M7 < 14.1%`** (strictly below **M7_ref**).

## Binding sources


| Document                                                                                   | Role                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | **Always:** **Latest structure scan** (as-of **date and time**; **M7** and **C1..C7** with **`%`**; AST telemetry in the main table **and** the **extra row under C7** in the § *Score M7* three-column table — §1); extra checks; **Open hotspots** — **prune resolved items**, never re-list solved hotspots. **Only if trigger policy is met** (per-category thresholds **or** **`M7 ≥ M7_ref`**; see **Threshold** above): **information input list** (DS rows), **recommended implementation order** (phase table **plus mandatory** Mermaid `flowchart` — see §3), § **DS-ID → primary workstream** for new IDs. |
| [tools/spaghetti_ast_scan.py](../tools/spaghetti_ast_scan.py)                              | Canonical metric run (repository root = CWD).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| [state/EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md)                             | Analysis and Markdown maintenance create **no** new pre/post artefacts; those appear only when a **wave** with evidence runs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Local planning / issues                                                                    | Always share scan numbers; mirror proposed order / new DS rows to external tickets only after agreement — and in-repo **only** if trigger policy is met (otherwise the scan section suffices).                                                                                                                                                                                                                                                                                                                                                                                                                         |


## Do not

- Do **not** change `docs/archive/documentation-consolidation-2026/`*.
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

**Ignore:** `.state_tmp`, `site/`, `node_modules`, `.venv`, `venv`, `__pycache_`_ (and everything under them).

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

All in [despaghettification_implementation_input.md](despaghettification_implementation_input.md). The trigger policy is the per-category table **plus** composite `**M7 ≥ M7_ref`** (see **Threshold** above); the input list mirrors the same rules under § *Trigger policy for check task updates*.

### 1) Latest structure scan — **always**

- **As of (date & time) — required:** Fill the **As of (date & time)** cell with the **timestamp when this check run’s scan commands ran** (not a hand-waved day only). Use `**YYYY-MM-DD HH:mm:ss`** (24-hour). **Timezone:** optional; add **once** in parentheses after the time if it matters (e.g. `(Europe/Berlin)` or `(UTC)`). If the repo assumes one zone everywhere, a single sentence in the input list header is enough and the cell may omit the suffix.
- **Metrics — percent display:** In the **main** § *Latest structure scan* table, write **C1..C7** with a trailing **percent sign** (e.g. `**17%`**, not bare `**17**`). **M7** must also read as a **percentage** (e.g. `**≈ 24.3%`**). Triggers and the **M7** formula still use the **numeric** 0–100 values (17 for 17%); the `**%`** in Markdown is for human readers and consistency with **M7_ref** wording.
- **AST telemetry:** In the **main** § *Latest structure scan* table, keep the row **AST telemetry N / L₅₀ / L₁₀₀ / D₆** with the four **counts** from `python tools/spaghetti_ast_scan.py` (not **%**).
- **Score *M7* subsection:** In the **Symbol | Meaning | Value** table, copy **C1..C7** with the **same** `**%`** values as the main scan table, then add **one** extra row **immediately below** **C7**: first column `**AST telemetry`**, second column `**N / L₅₀ / L₁₀₀ / D₆**`, third column the **same** four counts as the main scan row. **Do not** duplicate telemetry in the trigger-policy table; **do not** add a separate mini-table or filler comments in cells.
- **Extra checks** (builtins, runtime spot check `TYPE_CHECKING` / cycle hints) briefly in the scan section if you run them.
- Longest functions and top nesting **fully** only in **script output**; in Markdown **core findings** and the **Open hotspots** table row as follows:
  - **Open hotspots must not show solved problems.** Before writing, read the previous **Open hotspots** text and reconcile with the **current** repo and this run’s script output (line counts, paths, names). If a named function or theme is **no longer** a top offender or was **split / moved / shortened** by an implemented wave, **drop** that fragment from **Open hotspots**; use **—** when nothing structural remains to call out beyond the numeric row.
  - Only list **still-open** structural issues (typically 2–5 short clauses aligned with current top lines / nesting or checks). Do **not** reintroduce text that [spaghetti-solve-task.md](spaghetti-solve-task.md) already cleared unless the problem has **regressed** in the tree.
  - Do **not** duplicate the full script leaderboard in **Open hotspots** — that belongs in terminal output only; the cell is for **curated, unresolved** callouts.

### 2) Information input list (table) — **only if trigger policy is met**

- Each recognised or worsened **structure / spaghetti gap** gets its **own row** with columns: **ID**, **pattern**, **location**, **hint / measurement idea**, **direction** (one-sentence sketch), **collision hint** (what would be risky in parallel).
- **Pattern column:** Begin **pattern** with the **M7 category symbol(s)** this wave primarily addresses — **C1** … **C7** as in the **Per-category triggers** table above (same names as § *Latest structure scan* / input list triggers). Use `**C3 · short free-text hook`**; if several categories apply, `**C2 · C3 · hook**`. Pick symbols from the current scan story (length, nesting, cycles, duplication, etc.), not arbitrary tags.
- **IDs:** **update** existing **DS-*** rows (measurements, location, collision) instead of inventing duplicates; assign the next free **DS-*** number only for **new** topics.
- Then maintain the **DS-ID → primary workstream** table in the same document (slug → `artifacts/workstreams/<slug>/pre|post/` per [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)).
- **If trigger policy is not met:** do **not** change this section or the workstream table within the spaghetti check.

### 3) Recommended implementation order — **only if trigger policy is met**

- Section **“Recommended implementation order”** as the analysis agent’s **proposal**: table **priority / phase**, **DS-ID(s)**, **short logic**, **workstream (primary)**, **note** (dependencies, gates).
- **Mermaid (mandatory when phases are filled):** If the phase table still contains only placeholders (`—`), **omit** the diagram until a pass fills real rows. Once **any** phase row has real **DS-ID(s)**, immediately **below** the table include a **fenced** `mermaid` code block ( ````mermaid` … `````) with a `**flowchart**` or `**graph**` that reflects the **same** sequencing **and parallelism** as the table:
  - **Node labels (readability + compatibility):** **one source line per node**, shape `**id["label"]`**. Put **phase · DS-ID · very short hook** in `label`, parts separated by `**·`** (U+00B7 middle dot, spaces around it). Example: `P1["1 · DS-010 · AI turn"]`. **Do not** break labels across multiple lines in the repo file, **do not** use `\n`, `<br/>`, or inner ``` “markdown string” wrappers in hub diagrams — different viewers disagree on those, and the result is often worse than one dense line.
  - **Edges:** draw a **hard** dependency as a single arrow. For **parallel** work (independent DS phases after a common predecessor, separate workstreams, no import conflict), use a **fork** (`Predecessor --> A` and `Predecessor --> B`) and a **join** (`A --> Merge`, `B --> Merge`) when a later phase truly requires both; if independence is documented but no join is needed, fork only and end branches on leaf phases.
  - **Linear fallback:** use a simple chain **only** when every phase is strictly sequential or soft-ordered with no credible parallel band.
  - **Do not** omit the diagram when non-placeholder phase rows exist — keep syntax valid for MkDocs / GitHub Mermaid.
- **Heuristic (order):** interfaces and shared edges (**DTOs, clear module boundaries**) before large moves; **high coupling / deep nesting hotspots** not in parallel by two owners without aligned artefact sets; do not hide builtins/import topics behind large runtime refactors when the scan surfaces them first.
- If only numbers change without a new substantive thesis: **confirm** the phase table or add a row **“no change vs last scan”** — do not leave empty placeholder phases when the input table has rows; **still refresh** the Mermaid if the phase table row text or order changed.
- **If trigger policy is not met:** do **not** change this section within the spaghetti check (no phase shuffle for scan noise only).

**How to build a *suitable* phase table (required whenever DS rows are filled):**

1. **Cover every open DS-ID** from § *Information input list* with at least one **phase** row (unless two IDs are explicitly merged into one wave with team agreement — then one row may list multiple **DS-*** and the note must say so). **Never** leave the phase table as `—` while the DS table has real rows. Each **DS-*** row’s **pattern** must already carry the **C1..C7** prefix rule from §2.
2. **Order phases by risk and blast radius**, not by DS number: prefer topics that **stabilise shared runtime / import seams** (turn pipeline, narrative commit, `app.runtime` edges, `ds005`-visible modules) **before** very large **service orchestration** functions that pull many imports. Put **package-separated** hotspots (e.g. `ai_stack` only) in a **later** phase unless the scan shows they block backend work.
3. **One primary workstream per phase row** (see [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md)): it must match where **pre/post** artefacts would go for that wave. If a phase touches two packages, pick the **primary** workstream and mention the other in **note** (“call sites only”, “no separate pre/post”).
4. **Short logic** = one line: *what* this phase achieves structurally (e.g. “shrink X before refactoring Y”). **Note** = concrete **gates**: which `pytest` paths, `ds005`, or integration checks the implementer should run after the slice.
5. **Dependencies:** if phase B genuinely requires interfaces from phase A, say so in **note** on phase B; avoid claiming a hard dependency unless imports or tests prove it — default is **soft ordering** (risk reduction), which is still valid to document as “prefer A before B”.
6. **Parallelism / independence:** explicitly ask which DS phases could run **in parallel** (different **primary workstream**, no shared hot files, no hard import coupling). When credible, use **parallel phase bands** in the table (e.g. `3a` / `3b` with **Parallel** in **note**, or two rows sharing the same priority with an explicit **parallel** sentence) instead of a fake linear order. Call out **collision** risks if two “parallel” tasks still touch the same module surface. The Mermaid must **show** forks/joins consistent with those notes.
7. **Mermaid:** after the table, add or update the **mandatory** diagram; **single-line** `["…"]` labels (§3) and edges must stay in sync with the **priority / phase** and **DS-ID(s)** columns and with **parallel** vs **hard** dependencies above.

### Optional

- **Progress / work log** and `WORKSTREAM_*_STATE.md`: only for a **formal wave** with pre/post (see governance).

## Output format for the requester (short)

After the run: **3–8 sentences** on **M7**, category outliers, and whether **Open hotspots** shrank or cleared (no solved items left listed). When citing **C1..C7**, use **percent** wording consistent with the input list (e.g. “C3 at 44%”). **Only if trigger policy is met** (any **C** above its bar **or** `**M7 ≥ M7_ref`**): additionally **1–3 sentences** on **proposed implementation order** (first phase and why), whether **parallel** bands were identified and how the **Mermaid** shows fork/join, confirm diagram nodes use **single-line** `["phase · DS-ID · hook"]` labels, and point to changed sections (**scan**, **DS table**, **phase table + diagram**). If trigger policy is not met: reference **Latest structure scan** (including **Open hotspots** pruned to unresolved only) — no obligation to change DS / phases / Mermaid.

## Counterpart: implementation wave by wave

The **execution track** (review order, adjust if needed, then Despaghettify waves with pre/post until the list is empty): [spaghetti-solve-task.md](spaghetti-solve-task.md).