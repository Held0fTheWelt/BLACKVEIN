# Task: Struktur- / Spaghetti-Check (reproduzierbar)

Dieser Auftrag beschreibt **dieselbe** Tätigkeit, die der Analyse-Agent ausgeführt hat: grobe **Strukturmetriken** erheben, **Hotspots** benennen, und den Abschnitt **„Letzter Struktur-Scan“** in der kanonischen Inputliste pflegen — **ohne** Implementierungs-Refactors (die bleiben beim Despag-Umsetzer laut Plan).

## Bindende Quellen

| Dokument | Rolle |
|----------|--------|
| [docs/dev/despaghettification_implementation_input.md](../../docs/dev/despaghettification_implementation_input.md) | Abschnitt **„Letzter Struktur-Scan“** aktualisieren; **Informations-Inputliste** nur ergänzen, wenn sich die fachliche Befundlage ändert (neue oder geänderte **DS-***-Zeilen). |
| [tools/spaghetti_ast_scan.py](../../tools/spaghetti_ast_scan.py) | Kanonische Ausführung der Metriken (Repo-Wurzel = CWD). |
| [docs/state/EXECUTION_GOVERNANCE.md](../../docs/state/EXECUTION_GOVERNANCE.md) | Der reine **Scan** erzeugt **keine** neuen Pre/Post-Artefakte; nur wenn der Auftraggeber ausdrücklich eine **Wave** mit Evidenz will. |
| Lokale Planung / Issues | Falls das Team einen Umsetzungsplan oder Tickets pflegt: Scan-Zahlen dort nur nach Abstimmung spiegeln; **keine** festen absoluten Pfade im Repo-Dokument erforderlich. |

## Nicht tun

- **Nicht** `docs/archive/documentation-consolidation-2026/*` ändern.
- **Keine** Prozent-Scores als „objektive“ Wahrheit verkaufen — höchstens **heuristische** Einordnung in der Scan-Tabelle.
- **Kein** Ersatz für grüne CI: Scan ist **Lesart**, Tests bleiben authoritative.

## Umfang des Python-AST-Laufs (fix)

Diese Verzeichnisse **immer** einbeziehen (Pfade relativ zur Repository-Wurzel):

- `backend/app`
- `world-engine/app`
- `ai_stack`
- `story_runtime_core`
- `tools/mcp_server`
- `administration-tool`

**Ignorieren:** `.state_tmp`, `site/`, `node_modules`, `.venv`, `venv`, `__pycache__` (und alles unterhalb davon).

## Reproduktion: AST-Scan-Skript

**Im Repository vorhanden:** [tools/spaghetti_ast_scan.py](../../tools/spaghetti_ast_scan.py) — bei Änderung der Metrikdefinition **Task-Dokument und Skript gemeinsam** pflegen.

Der folgende Block ist eine **Kopie** der Logik (falls das Skript fehlt oder abweicht):

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

Ausführung von der **Repository-Wurzel**:

```bash
python tools/spaghetti_ast_scan.py
```

## Zusatzchecks (fix)

1. **Duplikat Builtins:** Suche nach `def build_god_of_carnage_solo` in `**/builtins.py` (Backend + World-Engine) — Zustand in Scan-Tabelle kurz erwähnen, solange das für euch ein offenes Builtins-/Drift-Thema ist.
2. **Import-Workarounds (Stichprobe):** unter `backend/app/runtime` nach `TYPE_CHECKING`, `avoid circular`, `circular dependency` greppen — nur qualitativ („weiterhin vorhanden“ / „weniger Treffer“), keine vollständige Graph-Analyse nötig.

## Pflege der Inputliste

In [despaghettification_implementation_input.md](../../docs/dev/despaghettification_implementation_input.md):

1. Abschnitt **„Letzter Struktur-Scan“**: **Datum** und Metriken (**N**, **L₅₀**, **L₁₀₀**, **D₆**, **S**) aus dem Skriptlauf übernehmen; Unterabschnitt **Score *S*** konsistent halten. Längste Funktionen / Top-Nesting nur in der **Skript-Ausgabe** voll aufführen, im Markdown nur das Nötige.
2. **Informations-Inputliste**: neue oder geänderte Strukturthemen als **DS-***-Zeilen; **DS-ID → Workstream**-Tabelle mitpflegen.
3. Optional: **Fortschritt / Arbeitslog** und **`WORKSTREAM_*_STATE.md`** bei einer formalen Wave.

## Ergebnisformat für den Auftraggeber (kurz)

Nach Lauf **3–8 Sätze** + Verweis auf geänderte Markdown-Zeilen: was an Länge/Nesting/Hotspots auffällt und welche **DS-***-Zeilen (falls vorhanden) sich daraus ergeben oder bestätigt werden.
