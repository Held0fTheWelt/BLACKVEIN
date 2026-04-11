# Despaghettify

Zentraler Ort für den **Despaghettifizierungs-** und **Struktur-/Spaghetti-Check-Zyklus** (neben `docs/state/` für Execution Governance).

| Datei | Rolle |
|-------|--------|
| [`despaghettification_implementation_input.md`](despaghettification_implementation_input.md) | Kanonische **Inputliste**, DS-Koordination, Struktur-Scan-Tabelle, Umsetzungsreihenfolge, Arbeitslog (Templates). |
| [`spaghetti-check-task.md`](spaghetti-check-task.md) | Reproduzierbarer **AST-/Spaghetti-Check**; Pflege des § *Letzter Struktur-Scan* in der Inputliste. |

**Werkzeuge** (bleiben unter `tools/`): `spaghetti_ast_scan.py`, `ds005_runtime_import_check.py`.

**Governance / Pre–Post:** [`docs/state/README.md`](../docs/state/README.md), [`docs/state/EXECUTION_GOVERNANCE.md`](../docs/state/EXECUTION_GOVERNANCE.md).
