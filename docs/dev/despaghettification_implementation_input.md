# Despaghettifizierung — Informations-Inputliste für Umsetzer

Dieses Dokument ist **kein** Teil des eingefrorenen Konsolidierungs-Archivs unter [`docs/archive/documentation-consolidation-2026/`](../archive/documentation-consolidation-2026/). Dort liegen **abgeschlossene** Befunde und Migrationsnachweise (Ledgers, Topic Map, Validierungsreports) — **diese Dateien nicht überschreiben oder „fortschreiben“**.

Hier hingegen liegt **lebendige Arbeitsgrundlage**: strukturelle und Spaghetti-Themen im **Code**, priorisierte Inputzeilen für Task-Umsetzer, Koordinationsregeln und eine **freiwillige** Fortschrittsnotiz. Analog zur Dokumentations-Konsolidierung 2026 gilt: **eine kanonische Wahrheit pro Thema** — hier angewendet auf **Code-Struktur** (weniger Duplikate, klarere Grenzen, kleinere kohärente Module).

**Diese Datei ist Teil der Wellen-Disziplin:** Wer eine **Despaghettifizierungs-Welle** im Code umsetzt (neue Helfer-Module, spürbare AST-/Strukturänderung), **überarbeitet dieselbe Welle auch diese Markdown-Datei** — nicht nur den Code. Konkret: siehe § **„Pflege dieser Datei bei strukturellen Wellen“** unter Koordination. Das ersetzt **nicht** Pre/Post-Artefakte unter `docs/state/artifacts/…` (sie bleiben laut [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md) verbindlich), ergänzt sie aber als **fachliche** Einstiegs- und Prioritätsspur.

## Anbindung an `docs/state/` (Execution Governance, Pre/Post)

Dieses Dokument ist **kein** Ersatz für [`docs/state/EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md), sondern die **fachliche Inputseite** für strukturelle Refactors, die **dieselben** Beweis- und Restart-Regeln nutzen sollen.

| Governance-Baustein | Rolle für Despaghettifizierung |
|---------------------|----------------------------------|
| [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md) | Verbindlich: State-Dokument lesen, **Pre-** und **Post-Artefakte** je Wave, Vergleich Pre→Post, State aus Evidenz aktualisieren (**Completion Gate**). |
| [`WORKSTREAM_INDEX.md`](../state/WORKSTREAM_INDEX.md) | Ordnet **Workstream** → `artifacts/workstreams/<slug>/pre|post/`. |
| [`docs/state/README.md`](../state/README.md) | Einstieg State-Hub. |
| `docs/state/artifacts/repo_governance_rollout/pre|post/` | Optional für **repo-weite** Wellen (z. B. großer Diff über mehrere Pakete); sinnvoll, wenn eine DS-Welle die gleichen Repo-Commands wie der Rollout braucht. |

**Artefakt-Pfade (kanonisch, relativ zu `docs/state/`):**

- Pro betroffenem Workstream: `artifacts/workstreams/<workstream>/pre/` und `…/post/`.
- Slugs wie im Index: `backend_runtime_services`, `ai_stack`, `administration_tool`, `world_engine` (Documentation nur, wenn MkDocs/Nav mitbetroffen ist).

**Namenskonvention für strukturelle Wellen (DS-*):**

- Sitzungs-/Wellenpräfix wie bestehend: `session_YYYYMMDD_…`.
- **DS-ID im Dateinamen**, z. B. `session_YYYYMMDD_DS-001_scope_snapshot.txt`, `session_YYYYMMDD_DS-001_pytest_collect.exit.txt`, `session_YYYYMMDD_DS-001_pre_post_comparison.json` (letzteres liegt typischerweise unter **`post/`**).
- Mindestens **ein** menschenlesbares Artefakt (`.txt`/`.md`) und **bevorzugt** ein maschinenlesbares (`.json`) — wie in der Governance gefordert.

**DS-ID → primärer Workstream (Wo Pre/Post ablegen):**

| ID | Primärer Workstream (`artifacts/workstreams/…`) | Mitbeteiligt (eigene Pre/Post nur bei echtem Scope) |
|----|--------------------------------------------------|------------------------------------------------------|
| — | — | — |

**Neu befüllen:** Pro aktiver **DS-*** eine Zeile (oder Gruppe mit gleichem Primär-Workstream); Slugs wie in [`WORKSTREAM_INDEX.md`](../state/WORKSTREAM_INDEX.md): `backend_runtime_services`, `ai_stack`, `administration_tool`, `world_engine`, `documentation`. Repo-weite Querverifikation ohne Produktcode: optional `artifacts/repo_governance_rollout/pre|post/` (z. B. **DS-REPLAY-G**).

Umsetzer: **Completion Gate** aus `EXECUTION_GOVERNANCE.md` abhaken; im zugehörigen `WORKSTREAM_*_STATE.md` die Welle und die neuen Artefakt-Pfade eintragen. Kreuzungen vermeiden: pro **DS-ID** ein klarer Wellen-Owner; mehrere Workstreams nur mit abgestimmten **getrennten** Artefakt-Sets.

## Anknüpfung an documentation-consolidation-2026

| Archiv-Artefakt | Bezug zur Code-Despaghettifizierung |
|-----------------|-------------------------------------|
| [`TOPIC_CONSOLIDATION_MAP.md`](../archive/documentation-consolidation-2026/TOPIC_CONSOLIDATION_MAP.md) | Themen sind auf **eine** aktive Doku pro Thema gemappt; Code-Refactors sollten **dieselbe** fachliche Kante nicht in zwei parallelen Implementierungen erneut aufspannen (z. B. RAG, MCP, Runtime). |
| [`DURABLE_TRUTH_MIGRATION_LEDGER.md`](../archive/documentation-consolidation-2026/DURABLE_TRUTH_MIGRATION_LEDGER.md) | Vorbild für **nachvollziehbare** Verschiebung statt stiller Drift; Despaghettifizierung: **eine Quelle** für geteilte Bausteine (z. B. Builtins). |
| [`FINAL_DOCUMENTATION_VALIDATION_REPORT.md`](../archive/documentation-consolidation-2026/FINAL_DOCUMENTATION_VALIDATION_REPORT.md) | Abschlusskriterien für einen **Konsolidierungsstrang**; für Code: Tests/CI grün, Verhalten unverändert, Schnittstellen explizit. |

## Koordination — Aufgaben erweitern ohne sich zu kreuzen

1. **Claims:** Vor größeren Refactors die **ID(s)** im Team/Issue/PR nennen (alle **`DS-*`**, die ihr gerade aus der Informations-Inputliste bearbeitet). Pro ID idealerweise **ein** klarer Owner.
2. **Kein Doppel-Track:** Zwei Umsetzer bearbeiten **nicht** dieselbe ID parallel; bei Aufteilung: Unteraufgaben explizit trennen (z. B. DS-003a nur Backend-Wiring, DS-003b nur World-Engine-Import).
3. **Archiv unangetastet:** Befunde aus Code-Arbeit **nicht** in `documentation-consolidation-2026/*.md` spiegeln; stattdessen CHANGELOG, PR-Beschreibung, **`docs/state/`-Artefakte**, **diese Inputliste** (§ *Letzter Struktur-Scan*, befüllte DS-Zeilen, optional § *Fortschritt*) und die zugehörigen **`WORKSTREAM_*_STATE.md`** nutzen.
4. **Schnittstellen zuerst:** Bei Zyklen (Runtime-Cluster) kleine **DTO-/Protokoll-Module** vor großem Verschieben; vermeidet PRs, die halbe `app.runtime` gleichzeitig anfassen.
5. **Messung optional:** AST-/Review-basierte Längen sind **Richtwerte**; Erfolg ist **verständliche** Grenzen + grüne Suites, nicht ein Prozent-Score.

### Pflege dieser Datei bei strukturellen Wellen (mit dem Code mitführen)

Bei jeder relevanten **DS-*/Despaghettifizierungs-Welle** diese Datei **in derselben PR-/Commit-Logik** anpassen (kein reines „Code-only“):

| Was | Inhalt |
|-----|--------|
| **Informations-Inputliste** | Pro **DS-***: Spalten pflegen (*Hinweis / Messidee*, *Richtung*, *Kollisionshinweis*); abgeschlossene Wellen kurz markieren. |
| **§ Letzter Struktur-Scan** | Nach messbarer Änderung: **Haupttabelle** (Stand, **N**, **L₅₀**, **L₁₀₀**, **D₆**, **S**, Zähler) + Unterabschnitt **Score *S***; optional **Zusatzchecks** / **Offene Schwerpunkte**; bei Runtime-Kanten `tools/ds005_runtime_import_check.py`. Ranglisten nur Skriptausgabe. |
| **§ Empfohlene Umsetzungsreihenfolge** | Bei neuer Priorität, Abhängigkeit oder Phase aktualisieren; optional Mermaid. |
| **§ Fortschritt / Arbeitslog** | Optional **eine** neue Zeile: DS-ID(s), Kurzfassung, Gates/Tests, Pre/Post-Pfade (oder „siehe PR“). |
| **DS-ID → Workstream-Tabelle** | Neue oder verschobene **DS-*** hier verorten; Mitbeteiligte Workstreams vermerken. |

**Governance:** `docs/state/artifacts/workstreams/<slug>/pre|post/` und `WORKSTREAM_*_STATE.md` bleiben der **formale** Nachweis; diese Datei ist die **kompakte** Arbeits- und Review-Landkarte.

## Letzter Struktur-Scan (Orientierung, keine Gewähr)

**Zweck:** Eine **befüllbare** Übersicht nach messbaren Läufen — bei größeren Refactors **Datum**, **Haupttabelle**, **Score-Eingaben** und ggf. **Zusatzchecks** / **Offene Schwerpunkte** aktualisieren. Messablauf, Builtins-Grep und Runtime-Stichprobe: [spaghetti-check-task.md](../../doc/tasks/spaghetti-check-task.md). **Ranglisten** und längste Funktionen: nur Ausgabe von `python tools/spaghetti_ast_scan.py` (Repo-Wurzel).

| Feld | Wert (beim Scan-Update anpassen) |
|------|----------------------------------|
| **Stand (Datum)** | **—** |
| Befehl Spaghetti-Scan | `python tools/spaghetti_ast_scan.py` (ROOTS = Spalte *Messumfang*) |
| Messumfang (ROOTS) | `backend/app`, `world-engine/app`, `ai_stack`, `story_runtime_core`, `tools/mcp_server`, `administration-tool` |
| **N** — Funktionen gesamt | **—** |
| **L₅₀** / **L₁₀₀** — Funktionen />50 / />100 AST-Zeilen | **—** / **—** |
| **D₆** — Verschachtelung ≥6 (gesamt) | **—** |
| **S** — heuristischer Gesamt-Score | **—** |
| **Zähler für S** (L₅₀ + 5·L₁₀₀ + 25·D₆) | **—** |
| Zusatzcheck Builtins | *optional:* Grep wie im Task-Dokument — **Trefferzahl** und **Datum**, sonst **—** |
| Zusatzcheck Runtime | *optional:* `python tools/ds005_runtime_import_check.py` — **exit-Code**; bei Auffälligkeit **kurz** (z. B. `TYPE_CHECKING`, Lazy-Imports), sonst **—** |
| **Offene Schwerpunkte** | *nur ausfüllen, wenn nötig:* was Scan/Review nahelegt und **nicht** schon in einer **DS-***-Zeile steht; sonst **—** |

### Score *S* — Eingaben und Berechnung

| Symbol | Bedeutung | Wert |
|--------|-----------|------|
| **N** | Funktionen gesamt | **—** |
| **L₅₀** | />50 AST-Zeilen | **—** |
| **L₁₀₀** | />100 AST-Zeilen | **—** |
| **D₆** | Verschachtelung ≥6 | **—** |

**Formel:** `S = 100 × (L₅₀ + 5·L₁₀₀ + 25·D₆) / N`

**Zähler:** L₅₀ + 5·L₁₀₀ + 25·D₆ — nach Befüllung der Symbole oben ausrechnen und **S** in die Haupttabelle übernehmen.

*Hinweis:* Heuristik mit ±2–3 % Rauschen (siehe Task-Dokument).

## Informations-Inputliste (erweiterbar)

Jede Zeile: **ID**, **Muster**, **Ort**, **Hinweis / Messidee**, **Richtung**, **Kollisionshinweis** (was parallel riskant ist).

| ID | Muster | Ort (typisch) | Hinweis / Messidee | Richtung (Lösungsskizze) | Kollisionshinweis |
|----|--------|---------------|--------------------|---------------------------|-------------------|
| — | — | — | — | — | — |

**Neue Zeilen:** fortlaufende **DS-001**, **DS-002**, … (oder euer ID-Schema); kurz begründen, warum es ein Struktur-/Spaghetti-Thema ist. Nach § *DS-ID → primärer Workstream* die passenden `artifacts/workstreams/<slug>/pre|post/`-Pfade wählen.

## Empfohlene Umsetzungsreihenfolge

Priorisierte **Phasen**, **Reihenfolge** und **Abhängigkeiten** — abgestimmt mit der § **Informations-Inputliste** und [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md). Nach Befüllung optional: Unterabschnitte pro Phase, Mermaid-`flowchart`, Gates je Welle, Kurz-Prioritätenliste.

| Priorität / Phase | DS-ID(s) | Kurzlogik | Workstream (primär) | Anmerkung (Abhängigkeiten, Gates) |
|-------------------|----------|-----------|---------------------|-----------------------------------|
| — | — | — | — | — |

**Neu befüllen:** Zeilen aus der Inputtabelle übernehmen; harte Ketten (z. B. Schnittstellen vor großem Verschieben) explizit machen. Koordination § *Pflege dieser Datei*: bei geänderter Priorität oder neuen **DS-*** diesen Abschnitt und ggf. Mermaid anpassen.

## Fortschritt / Arbeitslog (freiwillig, ergänzend zur Pflicht-Pflege oben)

Umsetzer können hier **kurz** eintragen, was sichtbar vorangeht (für Reviewer und nächste Iteration). **Pflicht** bei strukturellen Wellen bleibt die **Aktualisierung der Inputtabelle, des § Struktur-Scan und — bei Bedarf — dieses Logs** (siehe Koordination § *Pflege dieser Datei*). **Ergänzend** legen neue Wellen **Pre/Post-Dateien** unter `docs/state/artifacts/…` an (siehe `EXECUTION_GOVERNANCE.md`); ältere Session-Artefakte können fehlen, wenn sie bewusst bereinigt wurden — Nachweis dann über Git/CI/PR. Kein Ersatz für Issues/PRs.

| Datum | ID(s) | Kurzbeschreibung | Pre-Artefakte (rel. zu `docs/state/`) | Post-Artefakte (rel. zu `docs/state/`) | State-Dokument(e) aktualisiert | PR / Commit |
|-------|-------|------------------|----------------------------------------|----------------------------------------|------------------------------|-------------|
| — | — | — | — | — | — | — |

**Neue Zeilen:** chronologisch (**neueste oben** empfohlen); **DS-ID(s)**, gelaufene Gates/Tests, Pfade zu Pre/Post wie in [`EXECUTION_GOVERNANCE.md`](../state/EXECUTION_GOVERNANCE.md); bei reinem Scan/Doku-Update kurz vermerken. Längere Historie: Git, PRs, `WORKSTREAM_*_STATE.md`.

## Kanonische technische Lesepfades (nach Refactor)

Nach strukturellen Änderungen an Runtime/AI/RAG/MCP die **aktive** technische Doku abstimmen (nicht das Archiv 2026):

- Runtime / Autorität: [`docs/technical/runtime/runtime-authority-and-state-flow.md`](../technical/runtime/runtime-authority-and-state-flow.md) — Supervisor-Orchestrierung: `supervisor_orchestrate_execute.py` + `supervisor_orchestrate_execute_sections.py`; Subagent-Aufruf: `supervisor_invoke_agent.py` + `supervisor_invoke_agent_sections.py`
- Inspector-Projektion (Backend): `inspector_turn_projection_sections.py` orchestriert; Bausteine in `inspector_turn_projection_sections_{utils,constants,semantic,provenance}.py`
- Admin-Tool-Routen: `administration-tool/route_registration.py` + `route_registration_{proxy,pages,manage,security}.py`
- GoC-Solo-Builtin (Core): `story_runtime_core/goc_solo_builtin_template.py` + `goc_solo_builtin_catalog.py` + `goc_solo_builtin_roles_rooms.py`
- AI / RAG / LangGraph: [`docs/technical/ai/RAG.md`](../technical/ai/RAG.md), [`docs/technical/integration/LangGraph.md`](../technical/integration/LangGraph.md), [`docs/technical/integration/MCP.md`](../technical/integration/MCP.md)
- Dev-Seam-Übersicht: [`docs/dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md`](architecture/ai-stack-rag-langgraph-and-goc-seams.md)

---

*Erstellt als operatives Brückenstück zwischen struktureller Code-Arbeit, dem State-Hub unter [`docs/state/`](../state/README.md) (Pre/Post-Evidenz) und dem abgeschlossenen Dokumentations-Archiv 2026.*
