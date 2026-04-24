## Implementierungsplan: Administration Tool Readiness Transparency & AI Stack Closure Diagnostics

Ziel: Die Administration Tool UI soll **live und gate-genau** anzeigen, warum AI Stack Release Readiness aktuell `not fully closed` ist. Keine Fake-Diagnostik, keine zweite Readiness-Quelle, keine verdeckten Defaults.

---

# Phase 0 — Current Truth einfrieren

**Ziel:** Vor Änderungen den aktuellen Zustand beweisbar festhalten.

## Aufgaben

1. Aktuelle Readiness-Ausgaben sichern:

   * `GET /api/v1/admin/ai-stack/release-readiness`
   * `GET /api/v1/admin/system-diagnosis?refresh=1`
   * `GET /api/v1/admin/ai/runtime-readiness`
   * `GET /api/v1/admin/runtime/resolved-config`
   * `GET /api/v1/admin/world-engine/control-center`

2. Artifact Stores prüfen:

   * `backend/var/writers_room/reviews/`
   * `backend/var/improvement/recommendations/`
   * `tests/reports/`
   * `tests/reports/evidence/`

3. Aktuelle `not fully closed` Ursache dokumentieren:

   * offene Gate IDs
   * fehlende Evidence
   * hardcoded partial Gates
   * Admin-Surfaces, die diese Details aktuell nicht zeigen

## Erwartetes Ergebnis

Ein Snapshot unter z. B.:

```text
tests/reports/admin_readiness_truth_snapshot.md
tests/reports/evidence/admin_readiness_release_readiness.json
tests/reports/evidence/admin_readiness_system_diagnosis.json
tests/reports/evidence/admin_readiness_runtime_readiness.json
```

---

# Phase 1 — Canonical Readiness Schema erweitern

**Ziel:** Die bestehende Readiness-Quelle bleibt maßgeblich, wird aber diagnostisch vollständig.

## Betroffene Dateien

```text
backend/app/services/ai_stack_release_readiness_area_rows_list.py
backend/app/services/ai_stack_release_readiness_report_sections.py
backend/app/services/ai_stack_release_readiness_signal_extractors.py
backend/app/services/ai_stack_evidence_service.py
backend/app/services/system_diagnosis_service.py
```

## Umsetzung

Jeder Readiness-Gate-Eintrag soll künftig mindestens enthalten:

```json
{
  "gate_id": "writers_room_review_artifacts",
  "gate_name": "Writers-room review artifacts",
  "status": "partial",
  "owner_service": "backend",
  "reason": "No persisted writers-room review artifact was found.",
  "expected_evidence": "At least one backend/var/writers_room/reviews/*.json file with review_state.status.",
  "actual_evidence": "No review artifacts found.",
  "evidence_paths": [
    "backend/var/writers_room/reviews/"
  ],
  "truth_source": "live_file_store",
  "live_or_static": "live",
  "checked_at": "2026-04-24T...",
  "remediation_hint": "Run or create a governed writers-room review and persist the review artifact.",
  "admin_route": "/manage/ai-stack/release-readiness",
  "test_refs": [
    "backend/tests/test_m11_ai_stack_observability.py"
  ]
}
```

## Status-Enum festlegen

```text
ready
partial
blocked
unknown
error
```

## Wichtig

Nicht nur `overall_status` erweitern. Die Gate-Details müssen aus der echten Quelle kommen:

```text
/api/v1/admin/ai-stack/release-readiness
```

Nicht in der UI nachbauen.

---

# Phase 2 — System Diagnosis mit Gate Details verbinden

**Ziel:** `/manage/diagnosis` darf nicht mehr nur generisch `not fully closed` anzeigen.

## Betroffene Datei

```text
backend/app/services/system_diagnosis_service.py
```

## Umsetzung

Der bestehende Check:

```text
ai_stack_release_readiness
```

soll zusätzlich enthalten:

```json
{
  "overall_status": "partial",
  "partial_gate_count": 6,
  "partial_gate_ids": [
    "story_runtime_cross_layer",
    "writers_room_review_artifacts",
    "writers_room_retrieval_evidence_surface",
    "writers_room_langgraph_orchestration_depth",
    "improvement_governance_evidence",
    "improvement_retrieval_evidence_backing"
  ],
  "partial_gates": [...],
  "release_readiness_route": "/api/v1/admin/ai-stack/release-readiness",
  "admin_route": "/manage/ai-stack/release-readiness",
  "source_trace_id": "..."
}
```

## Fehlerverhalten

Wenn Release Readiness nicht geladen werden kann:

```json
{
  "status": "error",
  "message": "AI stack release readiness source could not be loaded.",
  "details": {
    "error": "...",
    "source": "/api/v1/admin/ai-stack/release-readiness"
  }
}
```

Keine stillen Fallbacks.

---

# Phase 3 — Dedicated Administration Tool Page hinzufügen

**Ziel:** Eine echte Admin-Seite für AI Stack Release Readiness.

## Neue Route

```text
/manage/ai-stack/release-readiness
```

## Betroffene Dateien

```text
administration-tool/route_registration_manage_sections.py
administration-tool/templates/manage/base.html
administration-tool/templates/manage/ai_stack_release_readiness.html
administration-tool/static/manage_ai_stack_release_readiness.js
```

## UI-Inhalte

Die Seite soll anzeigen:

1. Overall Status
2. Generated / checked timestamp
3. Live/static/stale marker
4. Gate Matrix
5. Partial/blocked Gate Details
6. Evidence paths
7. Remediation hints
8. Link zur Quelle/API
9. Raw JSON Toggle

## Tabelle

```text
Gate ID
Gate name
Owner service
Status
Reason
Expected evidence
Actual evidence
Evidence path
Live/static
Remediation
```

## Admin-Navigation

Einen neuen Eintrag ergänzen:

```text
AI Stack → Release Readiness
```

oder im bestehenden Governance/Diagnostics-Bereich:

```text
Diagnostics → AI Stack Release Readiness
```

---

# Phase 4 — `/manage/diagnosis` verbessern

**Ziel:** Die bestehende Diagnosis-Seite bleibt nützlich und verlinkt auf Details.

## Betroffene Dateien

```text
administration-tool/templates/manage/diagnosis.html
administration-tool/static/manage_diagnosis.js
```

## Umsetzung

Für den Check `ai_stack_release_readiness`:

* `partial_gate_count` anzeigen
* Gate IDs anzeigen
* Link zu `/manage/ai-stack/release-readiness`
* Details aus `check.details` aufklappbar rendern
* Fehler sichtbar anzeigen, nicht verschlucken

## Wichtig

Aktuell rendert `manage_diagnosis.js` primär:

```text
status
label
message
latency
source
```

Das reicht nicht. `details` muss sichtbar werden.

---

# Phase 5 — Runtime Config Truth ergänzen

**Ziel:** Admin soll unterscheiden können zwischen:

* Backend konfiguriert
* Backend effective config
* World-Engine hat Config geladen
* Story Runtime ist wirklich aktiv
* Play-Service HTTP ist nur technisch erreichbar

## Betroffene Dateien

```text
backend/app/services/system_diagnosis_service.py
backend/app/services/governance_runtime_service.py
backend/app/api/v1/operational_governance_routes.py
world-engine/app/api/http.py
world-engine/app/story_runtime/manager.py
```

## Umsetzung

System Diagnosis soll nicht nur prüfen:

```text
/api/health
/api/health/ready
```

sondern zusätzlich die governte Runtime-Konfiguration:

```text
/api/internal/story/runtime/config-status
```

oder einen Backend-Proxy darauf.

## Erwartete Diagnosefelder

```json
{
  "play_service_http_health": "ok",
  "play_service_ready": "ok",
  "story_runtime_config_loaded": true,
  "story_runtime_active": true,
  "runtime_profile": "...",
  "generation_execution_mode": "...",
  "provider_selection_mode": "...",
  "retrieval_execution_mode": "...",
  "validation_execution_mode": "..."
}
```

---

# Phase 6 — Closure Cockpit sichtbar machen

**Ziel:** Der bereits vorhandene Backend-Endpunkt soll im Admin sichtbar werden.

## Bestehender Backend-Endpunkt

```text
GET /api/v1/admin/ai-stack/closure-cockpit
```

## Neue oder integrierte Admin-Oberfläche

Option A:

```text
/manage/ai-stack/closure-cockpit
```

Option B:

Integriert in:

```text
/manage/ai-stack/release-readiness
```

## Empfehlung

Für MVP: In Release Readiness integrieren.

Später optional eigene Seite.

## Betroffene Dateien

```text
administration-tool/static/manage_ai_stack_release_readiness.js
administration-tool/templates/manage/ai_stack_release_readiness.html
```

---

# Phase 7 — Contract / Schema Drift reparieren

**Ziel:** Producer und Consumer müssen dieselben Felder verwenden.

## Betroffene Producer

```text
backend/app/services/ai_stack_release_readiness_report_sections.py
backend/app/services/ai_stack_release_readiness_area_rows_list.py
backend/app/services/system_diagnosis_service.py
```

## Betroffene Consumer

```text
administration-tool/static/manage_ai_stack_release_readiness.js
administration-tool/static/manage_diagnosis.js
backend/tests/test_system_diagnosis.py
backend/tests/test_m11_ai_stack_observability.py
```

## Regeln

1. `area` darf nicht alleinige Gate-ID bleiben.
2. `gate_id` wird kanonisch.
3. `status` muss enum-konform sein.
4. Missing evidence darf nicht als leerer String versteckt werden.
5. Hardcoded partial Gates müssen als `truth_source: "static_policy"` markiert werden.
6. Live evidence checks müssen als `truth_source: "live_file_store"` oder ähnlich markiert werden.

---

# Phase 8 — Tests ergänzen

## Backend Tests

### 1. Release Readiness Schema Test

Datei:

```text
backend/tests/test_m11_ai_stack_observability.py
```

Prüfen:

* jedes Gate hat `gate_id`
* jedes Gate hat `status`
* jedes Gate hat `reason`
* jedes partial Gate hat `expected_evidence`
* jedes partial Gate hat `actual_evidence`
* jedes partial Gate hat `remediation_hint`
* `overall_status == partial`, wenn mindestens ein Gate partial ist

### 2. System Diagnosis Detail Projection Test

Datei:

```text
backend/tests/test_system_diagnosis.py
```

Prüfen:

* `ai_stack_release_readiness.details.partial_gate_ids` existiert
* partial gate count stimmt
* Details werden nicht verworfen
* `refresh=1` aktualisiert Cache

### 3. Runtime Config Diagnosis Test

Neue oder bestehende Datei:

```text
backend/tests/test_runtime_config_diagnostics.py
```

Prüfen:

* Play-Service health und governed runtime status werden getrennt ausgegeben
* fehlende World-Engine Config wird sichtbar
* skipped checks sind als skipped markiert, nicht als healthy

---

## Administration Tool Tests

### 1. Route Shell Test

Neue Datei:

```text
administration-tool/tests/test_manage_ai_stack_release_readiness.py
```

Prüfen:

* `/manage/ai-stack/release-readiness` lädt
* JS-Datei ist eingebunden
* Mount point existiert
* Navigation enthält den Eintrag

### 2. Diagnosis Shell erweitert

Datei:

```text
administration-tool/tests/test_manage_diagnosis.py
```

Prüfen:

* Diagnosis Page hat Container für Details
* Link zur AI Stack Release Readiness Page existiert

### 3. JS/Browser Smoke Test

Falls vorhandenes Browser-Testsetup existiert:

```text
tests/e2e/test_admin_release_readiness_surface.py
```

Prüfen:

* Admin lädt Seite
* Backend wird via `/_proxy/api/v1/admin/ai-stack/release-readiness` erreicht
* partial Gates erscheinen sichtbar
* generic `not fully closed` erscheint nicht allein ohne Details

---

# Phase 9 — ADRs erstellen

Alle Cross-Service-Änderungen müssen dokumentiert werden.

## Neue ADR-Dateien

```text
docs/ADR/ADR-000X-canonical-ai-stack-release-readiness-source-of-truth.md
docs/ADR/ADR-000X-administration-tool-release-readiness-projection.md
docs/ADR/ADR-000X-ai-stack-readiness-diagnostic-schema.md
docs/ADR/ADR-000X-cross-service-runtime-config-visibility.md
docs/ADR/ADR-000X-closure-cockpit-operator-surface.md
```

## Jede ADR enthält

```text
Status
Context
Decision
Affected services/files
Consequences
Alternatives considered
Validation evidence
Related finding IDs
```

## Beispiel-Finding IDs

```text
RD-001 Source returns areas, system diagnosis drops details
RD-002 Diagnosis UI ignores check details
RD-003 Release-readiness endpoint has no Admin consumer
RD-004 Closure cockpit endpoint has no Admin consumer
RD-005 Stale operator hint path
RD-006 Runtime readiness and release readiness are different concepts
```

---

# Phase 10 — Abschlussbericht aktualisieren

## Neue Reports

```text
tests/reports/ADMIN_TOOL_READINESS_CONNECTIVITY_REPORT.md
tests/reports/AI_STACK_RELEASE_READINESS_CLOSURE_REPORT.md
```

## Inhalt

* vorheriger Zustand
* implementierte Änderungen
* finale Readiness-Ausgabe
* offene Gates, falls vorhanden
* warum sie offen sind
* Admin Screens/Routes
* Testbefehle
* Testergebnisse
* Docker/Compose Ergebnis

---

# Empfohlene Reihenfolge für die Umsetzung

## Sprint 1 — Backend Truth

1. Readiness Gate Schema erweitern.
2. System Diagnosis Details ergänzen.
3. Backend Tests anpassen.
4. Snapshot Report erzeugen.

**Abschlusskriterium:**
Backend kann per API exakt erklären, warum `not fully closed`.

---

## Sprint 2 — Admin Visibility

1. Neue Admin-Seite `/manage/ai-stack/release-readiness`.
2. Diagnosis-Seite erweitern.
3. Closure Cockpit integrieren.
4. Admin Tests ergänzen.

**Abschlusskriterium:**
Operator sieht im Administration Tool dieselbe Wahrheit wie im Backend.

---

## Sprint 3 — Runtime Config Diagnostics

1. Governed Runtime Config Status in Diagnosis aufnehmen.
2. Play-Service health vs Story Runtime active trennen.
3. Tests ergänzen.

**Abschlusskriterium:**
Admin kann sehen, ob Runtime nur erreichbar oder wirklich aktiv/configured ist.

---

## Sprint 4 — ADRs und Closure Proof

1. ADRs schreiben.
2. Reports aktualisieren.
3. Docker Smoke Test ausführen.
4. Browser/Admin Smoke Test ausführen.
5. Finalen Closure Report schreiben.

**Abschlusskriterium:**
Release Readiness ist entweder geschlossen oder nicht geschlossen — aber der Grund ist vollständig sichtbar, gate-genau, evidenzbasiert und im Admin nachvollziehbar.

---

# Definition of Done

Die Implementierung gilt erst als fertig, wenn:

* `/api/v1/admin/ai-stack/release-readiness` Gate-Details liefert.
* `/api/v1/admin/system-diagnosis?refresh=1` dieselben offenen Gate IDs enthält.
* `/manage/diagnosis` nicht mehr nur generisch `not fully closed` zeigt.
* `/manage/ai-stack/release-readiness` existiert.
* Die Admin-Seite live über `/_proxy` Daten vom Backend lädt.
* Jedes offene Gate einen Grund, Evidence-Hinweis und Remediation-Hint zeigt.
* Hardcoded/static Gates als static markiert sind.
* Live Artifact Checks als live markiert sind.
* Missing Evidence sichtbar ist.
* Runtime health und Runtime config truth getrennt dargestellt werden.
* Tests Backend + Admin + Docker/Browser die Verbindung beweisen.
* ADRs unter `docs/ADR/` existieren.
* Abschlussreport unter `tests/reports/` existiert.
