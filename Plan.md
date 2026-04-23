Ich habe die MCP-Schicht und die angrenzenden Governance-/Diagnosepfade im hochgeladenen Repository in mehreren Durchgängen geprüft: Struktur, Operations-Inventar, Integrationsseams, Parallelitätsdetektion, Governance, Negativraum und Konsolidierung. Maßgeblich waren dabei vor allem `.mcp.json`, `tools/mcp_server/*`, `ai_stack/mcp_canonical_surface.py`, `ai_stack/mcp_static_catalog.py`, `backend/app/api/v1/session_routes.py`, `backend/app/api/v1/world_engine_console_routes.py`, `backend/app/api/v1/ai_stack_governance_routes.py`, `backend/app/api/v1/mcp_operations_routes.py` sowie `backend/app/services/mcp_operations_service.py`.

## A. Executive Judgment

**Ja: Der bestehende MCP-Server ist eine gute Basis für diese Audit-Layer.**
**Ja: Die Integration sollte innerhalb des bestehenden MCP-Servers erfolgen, nicht als separater Parallel-Server.**
**Der aktuelle Stand ist „teilweise ausreichend“**: stark genug für eine saubere Integration, aber noch nicht vollständig genug für eine echte Architektur-Audit-Layer ohne zusätzliche Analyzer, Findings-Normalisierung und Audit-Ressourcen.

Mein Kernurteil ist:

* Die bestehende MCP-Schicht ist bereits **descriptor-getrieben**, **suite-segmentiert**, **governance-fähig** und **telemetrieangebunden**.
* Genau deshalb wäre ein neuer separater Audit-Server **architektonisch die falsche Richtung**.
* Es fehlt nicht die Grundstruktur, sondern die **domänenspezifische Audit-Logik**:

  * kein normalisiertes Struktur-Findings-Modell,
  * keine dedizierten Architektur-Analyzer,
  * keine Audit-Ressourcen,
  * keine invariantengetriebene Parallelitätsdetektion,
  * keine saubere Cache-/Snapshot-Strategie für Repository-Analysen.

Die sicherste Lösung ist daher:

1. **Core-Analyzer intern ergänzen**,
2. **über den bestehenden MCP-Server exposen**,
3. **an den vorhandenen Operator-/Telemetry-Strang andocken**,
4. **anfangs read-only im bestehenden Admin-Strang**,
5. **keinen neuen Parallel-Control-Plane-Strang eröffnen**.

---

## B. Existing MCP Structure Report

### 1. Wo der MCP-Server lebt

Der MCP-Server lebt im Repository unter:

* `tools/mcp_server/server.py`
* `tools/mcp_server/rpc_method_router.py`
* `tools/mcp_server/tools_registry.py`
* `tools/mcp_server/tools_registry_handlers*.py`
* `tools/mcp_server/resource_prompt_support.py`

Die lokale Startdefinition liegt in:

* `.mcp.json`

Dort ist ein **stdio-basierter MCP-Server** hinterlegt, der per:

* `python -m tools.mcp_server.server`

gestartet wird.

### 2. Architekturstil

Die MCP-Schicht ist **nicht monolithisch**, sondern bereits in klar erkennbare Ebenen getrennt:

* **Canonical descriptor layer**
  `ai_stack/mcp_canonical_surface.py`
* **Static resource/prompt catalog**
  `ai_stack/mcp_static_catalog.py`
* **Transport / JSON-RPC routing**
  `tools/mcp_server/server.py`, `rpc_method_router.py`
* **Tool registry + handler composition**
  `tools/mcp_server/tools_registry.py`, `tools_registry_handlers*.py`
* **Resource / prompt exposure**
  `resource_prompt_support.py`
* **Backend HTTP authority bridge**
  `backend_client.py`
* **Telemetry / operator trace emission**
  `logging_utils.py` plus Backend-Ingest

Das ist genau die Art von Struktur, in die eine Audit-Layer sauber eingebaut werden kann.

### 3. Registrierungsmodell

Der wichtigste Source of Truth ist:

* `ai_stack/mcp_canonical_surface.py`

Dort werden die MCP-Tools über kanonische Deskriptoren definiert. Relevant sind u. a.:

* `McpSuite`
* `McpToolClass`
* `McpOperatingProfile`
* `CANONICAL_MCP_TOOL_DESCRIPTORS`

Diese Deskriptoren tragen bereits:

* Tool-Name
* Suite-Zuordnung
* Tool-Klasse
* Authority-Quelle
* Governance-Sicht
* Implementierungsstatus

Das ist für eine spätere Architektur-Audit-Layer sehr wertvoll, weil die Infrastruktur bereits **explizite Metadaten über Authority und Governance** kennt.

### 4. Unterstützte MCP-Flächen

Der Server exponiert heute bereits drei MCP-Flächen:

* `tools`
* `resources`
* `prompts`

Die Router-Methoden in `rpc_method_router.py` unterstützen:

* `initialize`
* `tools/list`
* `tools/call`
* `resources/list`
* `resources/read`
* `prompts/list`
* `prompts/get`

Das heißt: Die gewünschte Audit-Layer muss nicht auf Tools beschränkt werden. Sie kann sauber als **Kombination aus Tools, Ressourcen und Prompts** aufgebaut werden.

### 5. Suites / Kontrollmodell

Die MCP-Schicht kennt derzeit Suites wie:

* `wos-admin`
* `wos-runtime-read`
* `wos-runtime-control`
* `wos-author`
* `wos-ai`

Zusätzlich existieren bereits:

* Suite-Filter
* Operating Profiles
* Operator-Truth-Aggregation

Das spricht klar dafür, die Audit-Layer **in das bestehende Suite-/Profile-Modell** einzuhängen statt eine neue Nebenlogik zu schaffen.

### 6. Auth / Authorization / Runtime Boundary

Wichtig ist: Der MCP-Server ist lokal/stdio-basiert, aber seine Backend-Zugriffe sind trotzdem abgesichert.

Relevant:

* `backend/app/api/v1/auth.py` mit `require_mcp_service_token`
* `tools/mcp_server/backend_client.py`

Das Muster ist:

* MCP lokal
* Backend-Zugriffe via Bearer/Service-Token
* Admin-Oberflächen separat via Admin/JWT-Mechanik

Das ist eine sinnvolle Boundary. Eine Audit-Layer darf diese nicht unterlaufen.

### 7. Wichtige strukturelle Einschränkung

Die aktuelle MCP-Schicht ist stark als **Control-Plane / Governance-Plane** gebaut, nicht als vollwertiges statisches Architektur-Analyse-Framework.
Sie kann so etwas aber **gut hosten**, solange die neue Audit-Layer:

* read-only startet,
* dieselben Deskriptor-/Registry-Muster nutzt,
* keine eigene Authority erfindet,
* und Findings nicht mit Runtime-Truth verwechselt.

---

## C. Operation Reuse Map

Ich mappe hier die vorhandenen MCP-Operationen auf ihre Wiederverwendbarkeit für eine Architektur-Audit-Layer.

### Direkt wiederverwendbar

#### `wos.mcp.operator_truth`

**Was es liefert:**
Kompakte, kanonische Beschreibung der MCP-Oberfläche und ihrer Governance-/Profilmerkmale.

**Für Audit nützlich:**
Sehr hoch. Das ist einer der wichtigsten Anker für:

* Surface-Honesty-Prüfungen
* Tool-/Suite-Abgleich
* Governance-Truth-Vergleiche
* Detecting “declared vs exposed”

**Status:** Direkt wiederverwendbar.

---

#### `wos.capabilities.catalog`

**Was es liefert:**
Katalogisierte Capability-/Governance-Metadaten.

**Für Audit nützlich:**
Hoch, insbesondere für:

* Inventarbildung
* Supporting-vs-canonical-Flächen
* Scope-/Visibility-Abgleiche
* Prompt-/Tool-/Capability-Zuordnung

**Status:** Direkt wiederverwendbar, eventuell mit kleiner Erweiterung.

---

#### `wos.system.health`

**Was es liefert:**
Health-Sicht auf Backend.

**Für Audit nützlich:**
Mittel. Nicht für Strukturfindings selbst, aber wichtig als:

* Kontextsignal
* Reachability-Indikator
* Live-vs-static-Modusunterscheidung

**Status:** Direkt wiederverwendbar als Kontexttool.

---

#### `wos.session.get`

**Was es liefert:**
Backend-Session-Snapshot.

**Für Audit nützlich:**
Hoch für Runtime-Path- und Truth-Surface-Vergleiche.

**Status:** Direkt wiederverwendbar.

---

#### `wos.session.diag`

**Was es liefert:**
Session-Diagnostics-Bundle.

**Für Audit nützlich:**
Sehr hoch für:

* Validation-vs-commit-Spuren
* Missing evidence chains
* Runtime degradation markers
* State-loss seam analysis

**Status:** Direkt wiederverwendbar.

---

#### `wos.session.state`

**Was es liefert:**
State-Snapshot mit möglicher World-Engine-Proxying-Logik.

**Für Audit nützlich:**
Sehr hoch, gerade weil dieser Pfad selbst potenzielle Authority-Splits zeigt.

**Status:** Direkt wiederverwendbar und selbst Prüfobjekt.

---

#### `wos.session.logs`

**Was es liefert:**
Logs-/Event-Sicht mit Warnhinweisen auf Nicht-Autorität.

**Für Audit nützlich:**
Sehr hoch für Surface-Honesty- und Continuity-Prüfungen.

**Status:** Direkt wiederverwendbar.

---

#### `wos.goc.list_modules`, `wos.goc.get_module`, `wos.content.search`

**Was sie liefern:**
Filesystem-nahe Modul-/Content-Inspektion.

**Für Audit nützlich:**
Hoch für:

* Registry-/Manifest-Vergleiche
* Orphan-Content-Suche
* Duplication-/Scope-Checks
* Canonical-vs-fallback content mapping

**Status:** Direkt wiederverwendbar.

---

### Als Muster wiederverwendbar, aber nicht als direkte Audit-Evidenz

#### `wos.research.explore`

#### `wos.research.validate`

#### `wos.research.bundle.build`

**Was sie liefern:**
Ein bounded research workflow mit Budget-/Review-Posture.

**Für Audit nützlich:**
Nicht als Primärevidenz, aber als **Interaktionsmuster** sehr wertvoll:

* Explore
* Validate
* Bundle

Das ist praktisch exakt die Form, in der auch Architektur-Findings später paketiert werden könnten.

**Status:** Als Workflow-Vorbild wiederverwendbar, nicht als eigentliche Audit-Engine.

---

#### `wos.canon.improvement.preview`

#### `wos.canon.improvement.propose`

**Was sie liefern:**
Verbesserungsvorschläge gegen kanonische Strukturen.

**Für Audit nützlich:**
Phase 1: nein.
Später: vielleicht, wenn aus Findings gezielt Konsolidierungsvorschläge generiert werden.

**Status:** Vorläufig nicht direkt Teil der Audit-Layer.

---

### Für Architektur-Audit nur indirekt relevant

#### `wos.session.create`

#### `wos.session.execute_turn`

Diese sind für strukturelle Audits nicht die erste Wahl. Sie können später für gezielte Live-Probing-Szenarien nützlich sein, aber eine Audit-Layer sollte in Phase 1 **nicht** von Runtime-Mutationen abhängen.

**Status:** Vorläufig nicht zentral.

---

### Wichtig: bestehende Ressourcen

Die vorhandenen Ressourcen sind ebenfalls hoch relevant:

* `wos://system/health`
* `wos://mcp/operator_truth`
* `wos://capabilities/catalog`
* `wos://session/{session_id}`
* `wos://session/{session_id}/diagnostics`
* `wos://session/{session_id}/state`
* `wos://session/{session_id}/logs`
* `wos://content/modules`
* `wos://content/module/{module_id}`

Sie zeigen, dass das System bereits das richtige Muster hat:
**Tool für Aktion / Analyse, Resource für stabil lesbare Sicht.**

Das sollte für Architektur-Findings genauso beibehalten werden.

---

## D. Integration Seam Report

Die saubersten Integrationspunkte sind klar.

### 1. Primärer Code-Seam: canonical surface erweitern

Datei:

* `ai_stack/mcp_canonical_surface.py`

Hier sollte die Audit-Layer **kanonisch verankert** werden, nicht nur implizit im Registry-Code.
Sonst würde genau die Parallelstruktur entstehen, die man eigentlich bekämpfen will.

Empfehlung:

* neue Audit-Tool-Deskriptoren dort definieren,
* Governance-/Authority-Posture explizit mitgeben,
* Suite-Zuordnung explizit halten.

---

### 2. Primärer Registrierungs-Seam: `tools_registry.py`

Datei:

* `tools/mcp_server/tools_registry.py`

Hier wird die Default-Registry aufgebaut.
Das ist der richtige Ort, um die Audit-Layer in den normalen MCP-Lebenszyklus einzuhängen.

Empfehlung:

* keine Sonderregistrierung außerhalb der Registry,
* keine „hidden local tools“,
* keine parallele Initialisierung.

---

### 3. Handler-Kompositions-Seam: `tools_registry_handlers.py`

Dateien:

* `tools_registry_handlers.py`
* `tools_registry_handlers_backend_session.py`
* `tools_registry_handlers_filesystem.py`
* `tools_registry_handlers_governance.py`
* `tools_registry_handlers_research.py`

Das ist der **beste technische Insertion Point**.

Empfehlung:

* eine neue Handler-Familie ergänzen, z. B. logisch in der Art:

  * `tools_registry_handlers_architecture_audit.py`
* von `build_default_mcp_tool_handlers(...)` aus einspeisen
* nicht als Seitenpfad direkt in `server.py`

Damit bleibt der MCP-Server transportseitig dünn und die neue Funktionalität sitzt dort, wo die anderen Domänenfamilien bereits sitzen.

---

### 4. Ressourcen-/Prompt-Seam: `mcp_static_catalog.py` + `resource_prompt_support.py`

Dateien:

* `ai_stack/mcp_static_catalog.py`
* `tools/mcp_server/resource_prompt_support.py`

Das ist der richtige Ort für:

* Audit-Findings-Ressourcen
* Authority-Maps
* Contract-Registry-Sichten
* Prompt-Familien für Architektur-Audits

---

### 5. Backend-Seam für Operator-Surfacing

Dateien:

* `backend/app/api/v1/mcp_operations_routes.py`
* `backend/app/services/mcp_operations_service.py`

Das ist **kein** guter Ort für die Kernanalyse selbst.
Aber es ist ein sehr guter Ort für:

* Aktivitätsübersichten
* Audit-Falllisten
* Bundle-Erzeugung
* spätere Operator-Summary-Surfaces

Die Analyse sollte **nicht** im Backend-Service beginnen.
Sie sollte im MCP-/Analyzer-Core sitzen und nur nachgelagert hier surfacen.

---

### 6. Governance-/Evidence-Seam

Dateien:

* `backend/app/api/v1/ai_stack_governance_routes.py`
* `backend/app/services/ai_stack_evidence_service.py`
* `backend/app/services/inspector_turn_projection_service.py`
* `backend/app/services/inspector_projection_service.py`

Diese Pfade sind extrem wertvoll als **sekundäre Vergleichsflächen**.
Sie sind aber **nicht** der Platz, an dem die Architektur-Audit-Layer selbst entstehen sollte.

Richtige Rolle:

* als Evidence Inputs
* als Cross-Surface Comparator Targets
* als Operator-Surfacing-Targets

---

## E. Required New Capabilities Report

Die bestehende MCP-Struktur ist gut, aber folgende Fähigkeiten fehlen heute noch klar.

### 1. Normalisierte Architektur-Findings

Es gibt derzeit Telemetrie und Diagnostikfälle für MCP-Operationen, aber kein sauberes Modell für strukturelle Repository-Findings.

Es fehlt ein Findings-Schema für Dinge wie:

* authority split
* contract duplication
* orphan lane
* route-family leak
* fallback dishonesty
* surface drift
* state-loss seam
* continuity split

---

### 2. Explizite Invariant-Definitionen

Ohne explizite Invarianten bleibt die Audit-Layer nur ein Haufen Heuristiken.

Es fehlen mindestens Invarianten der Form:

* Single-authority invariant
* Contract singularity invariant
* Surface honesty invariant
* Path continuity invariant
* Validation-to-commit continuity invariant
* Scope honesty invariant
* Supporting-vs-canonical truth invariant

---

### 3. Repository-strukturelle Analyzer

Heute gibt es kein sauberes Analyzer-Paket für:

* Route-Familien-Vergleich
* Contract-/Schema-Duplikationssuche
* Registry-/Manifest-Abgleich
* Fallback-/Default-Erkennung
* Cross-surface truth comparison
* state propagation seam detection

---

### 4. Audit-Ressourcen

Es fehlen read-only Ressourcen wie:

* authority map
* route family map
* contract index
* findings index
* invariants registry
* latest audit snapshot

---

### 5. Cache-/Snapshot-Modell

Repo-weite Strukturprüfung sollte nicht bei jedem Call alles neu scannen, ohne Cache-Konzept.

Es fehlt:

* Snapshot-ID
* Repo-hash/mtime-basierte Invalidierung
* Cache-Scope
* Live-evidence-Anreicherung vs statische Basisanalyse

---

### 6. Prompt-Familien für wiederholbare Audits

Es gibt Workflow-Prompts für Runtime-/Author-/AI-Bundles, aber nicht für Architektur-Audits.

Es fehlen z. B. Prompt-Familien für:

* authority audit
* truth-surface drift audit
* contract duplication audit
* continuity audit
* consolidation planning

---

### 7. Saubere Operator-Surfacing-Strategie

Der MCP Operations Cockpit-Strang kann Aktivität und Diagnostik, aber noch keine saubere strukturelle Audit-Sicht.

Es fehlt:

* klare Unterscheidung zwischen runtime truth und structural findings
* Snapshot-/Repo-Version-Markierung
* Confidence/Severity/Invariant labeling
* Konsolidierungsrichtung als first-class Feld

---

## F. Recommended MCP Audit-Layer Design

## 1. Grunddesign

Die empfohlene Form ist **kein neuer Server**, sondern:

* **Analyzer-Core innerhalb der bestehenden Repository-Architektur**
* **MCP-Exposure über denselben Server**
* **Ressourcen + Tools + Prompts**
* **optionale Backend-Summary-Surfacing**

Die sauberste innere Trennung wäre:

* **Core analyzer package** in einer domänischen Codezone, z. B. bei `ai_stack`
* **MCP adapter layer** in `tools/mcp_server/*`
* **Operator surfacing** nur nachgelagert im Backend/Admin

Damit bleibt klar:

* Analyse-Logik ist Domänenlogik,
* MCP ist Exposition,
* Backend/Admin ist Surfacing,
* nichts davon wird ein zweiter Parallel-Server.

---

## 2. Empfohlene interne Architektur

### Ebene A: Invariants + Findings Model

Zentrale Typen:

* invariant definitions
* finding schema
* finding classes
* severity/confidence model
* evidence reference model
* consolidation direction model

### Ebene B: Static analyzers

Für repository-lokale Analyse:

* route inventory analyzer
* descriptor/catalog analyzer
* contract/schema duplication analyzer
* filesystem/orphan path analyzer
* fallback/default detector
* prompt/tool/resource consistency analyzer

### Ebene C: Live evidence enrichers

Optional zusätzlich:

* backend session evidence comparer
* world-engine console surface comparer
* inspector/governance surface comparer

### Ebene D: Snapshot/cache layer

* repo snapshot identity
* analyzer output cache
* optional enrichment cache
* latest snapshot summary

### Ebene E: MCP exposure

* tools
* resources
* prompts

---

## 3. Empfohlene Tool-Familien

Phase 1 sollte klein und klar bleiben. Meine Empfehlung:

### `wos.arch.audit.inventory`

Liefert strukturierte Inventare zu:

* MCP tools/resources/prompts
* route families
* authority surfaces
* registry declarations
* backend/admin/runtime evidence surfaces

Zweck: Grundlage für alle weiteren Audits.

---

### `wos.arch.audit.findings`

Führt einen gebündelten Architektur-Audit-Durchlauf aus und gibt normalisierte Findings zurück.

Zweck: der eigentliche Einstiegspunkt für AI-Agenten.

---

### `wos.arch.audit.compare_surfaces`

Vergleicht zwei oder mehr Truth-/Evidence-Surfaces, z. B.:

* MCP session state vs backend session route
* backend session route vs world-engine console route
* session diagnostics vs inspector projection

Zweck: truth-surface drift und authority split detection.

---

### `wos.arch.audit.contracts`

Sucht nach parallelen oder duplizierten Verträgen/Schemata/shape definitions.

Zweck: contract singularity.

---

### `wos.arch.audit.trace_path`

Erstellt eine Pfadkarte für einen bestimmten Use Case, z. B.:

* session create
* execute turn
* state read
* diagnostics read
* logs read

Zweck: continuity und state-loss seam detection.

---

### Was ich **nicht** zuerst hinzufügen würde

Nicht in Phase 1:

* write-capable remediation tools
* automatische code changes
* automatische CI-blocking enforcement
* globales AST/call-graph monster framework
* eigener Netzwerk-MCP-Dienst

---

## 4. Empfohlene Ressourcen

Mindestens diese Ressourcen sollten später ergänzt werden:

* `wos://arch-audit/findings/latest`
* `wos://arch-audit/findings/{snapshot_id}`
* `wos://arch-audit/authority-map`
* `wos://arch-audit/contracts`
* `wos://arch-audit/runtime-paths`
* `wos://arch-audit/invariants`

Wichtig: Ressourcen dürfen **keine zweite Wahrheit** erzeugen.
Sie sollten lesbare Sichten auf dieselben Findings/Snapshots sein, die die Tools erzeugen.

---

## 5. Empfohlene Prompts

Nicht viele, aber gute:

* authority audit
* truth-surface drift audit
* continuity/state-loss audit
* contract duplication audit
* consolidation planning prompt

Diese Prompts sollen Workflow-Leitplanken liefern, nicht magische Black-Box-Audits simulieren.

---

## 6. Empfohlenes Findings-Schema

Mindestens diese Felder sind sinnvoll:

* `finding_id`
* `finding_class`
* `subsystem`
* `surface_family`
* `authority_surface_claimed`
* `authority_surface_observed`
* `runtime_stage`
* `issue_class`
* `invariant_id`
* `severity`
* `confidence`
* `impact`
* `evidence`
* `affected_paths`
* `supporting_surfaces`
* `consolidation_direction`
* `recommended_next_step`
* `snapshot_id`

Das ist deutlich wichtiger als exotische Analyzer.

---

## 7. Cache-/Index-Strategie

Empfehlung:

* **Phase 1:** on-demand Analyse + leichter Snapshot-Cache
* Cache-Key über:

  * repo snapshot / file hash / mtime bundle
  * operating profile
  * optional analysis scope
* **kein** schweres Persistenzsystem zuerst
* später optional:

  * vorcomputierte Inventare
  * incremental invalidation
  * persisted bundles für CI / admin

Wichtig: Erst Snapshot-Cache, später eventuell tieferer Index.
Nicht anders herum.

---

## 8. Governance-Surfacing

Die Audit-Layer sollte Ergebnisse anfangs primär surfacen an:

* AI agents via MCP
* Operatoren via bestehende Admin-/Cockpit-Surfaces
* optional Bundles für CI

Aber mit klaren Labels:

* `structural finding`
* `not runtime authority`
* `snapshot-based`
* `confidence`
* `evidence-backed`

---

## G. Parallel-Structure Detection Plan

Hier ist der eigentliche Kern.

## 1. Authority Splits

### Zu prüfende Invariante

Eine Capability darf nicht gleichzeitig mehrere implizite Authority-Pfade haben, ohne das offenzulegen.

### Code-grounded Ansatz

Vergleich von:

* `session_routes.py`
* `world_engine_console_routes.py`
* `ai_stack_governance_routes.py`
* MCP session tools/resources
* inspector projections

Besonders relevant:
`backend/app/api/v1/session_routes.py` zeigt bereits, dass State teils per World-Engine-Proxy, teils via Backend-Fallback geliefert wird. Genau das ist ein klassischer Authority-Split-Kandidat.

### Audit-Methode

* Routenfamilien inventarisieren
* claimed authority je Surface bestimmen
* observed backing path bestimmen
* Warn-/fallback-Marker erkennen
* Findings erzeugen, wenn:

  * mehr als ein Authority-Pfad denselben fachlichen Vertrag beansprucht
  * oder Supporting-Surfaces als primäre Wahrheit erscheinen

---

## 2. Schema / Contract Duplication

### Invariante

Ein fachlicher Vertrag soll einen kanonischen Ursprung haben oder explizit als abgeleitete Sicht markiert sein.

### Audit-Methode

* Tool-/resource-/route payload shapes vergleichen
* identische oder nahezu identische Session-/State-/Diag-Verträge erkennen
* Descriptor-/catalog-/docs-/response-shape drift erkennen
* Cross-file contract index erzeugen

### Praktische Zielklassen

* session snapshot
* diagnostics bundle
* operator truth
* release-readiness / closure / inspector projections
* content/module descriptors

---

## 3. Orphaned Subsystems

### Invariante

Subsysteme mit struktureller Rolle müssen entweder:

* im live path genutzt,
* explizit supporting-only,
* oder klar deprecated sein.

### Audit-Methode

* Registry-/route-/service-/admin UI mapping
* prüfen, ob etwas existiert, aber nirgends referenziert oder surfacet wird
* prüfen, ob etwas im UI existiert, aber keine belastbare Backend-/MCP-Stütze hat
* prüfen, ob etwas im Backend existiert, aber nie in MCP/Operatorflächen landet

---

## 4. Route-family Leaks

### Invariante

Gleiche fachliche Capability soll nicht über mehrere Route-Familien mit divergierender Wahrheit oder Scope auftreten, ohne klare Rollentrennung.

### Audit-Methode

Routen gruppieren nach Capability-Familie, z. B.:

* session state
* diagnostics
* logs
* session control
* governance evidence
* mcp operations diagnostics

Dann prüfen:

* gleiche Funktion, andere Authority?
* gleiche Funktion, anderer Auth-Posture?
* gleiche Funktion, anderer Truth-Level?
* supporting surface als primary missverständlich?

---

## 5. Hidden Defaults / Fallbacks

### Invariante

Fallbacks und Defaults mit Einfluss auf Wahrheit, Runtime-Path oder Operator-Wahrnehmung müssen explizit erkennbar sein.

### Audit-Methode

* scan auf `fallback`, `default`, `degraded`, `proxy`, `warning`, `deprecated`, `if not available`
* insbesondere in:

  * session routes
  * backend services
  * MCP server profile logic
  * operator-truth builders
  * inspector/evidence services

Hier ist der bestehende Code bereits ergiebig:
`session_routes.py` und zugehörige Warnfelder zeigen, dass die Audit-Layer genau diese Übergangsstellen erkennen sollte.

---

## 6. Truth-Surface Mismatch

### Invariante

Wenn zwei Surfaces dieselbe Sache darstellen, muss entweder

* dieselbe Wahrheit gezeigt werden,
* oder die Abweichung explizit markiert werden.

### Audit-Methode

Vergleich von:

* MCP resource `session/state`
* backend session state route
* admin world-engine console state route
* inspector projections
* diagnostics / coverage / provenance surfaces

---

## 7. State-Loss Seams

### Invariante

Zwischen plan → validate → commit → diagnostics → render dürfen relevante Zustandsanteile nicht unmarkiert verloren gehen.

### Audit-Methode

* Pfadkarten aufbauen
* shared identifiers / metadata keys verfolgen
* warnings / unsupported dimensions / missing fields erkennen
* evidence continuity prüfen

Die vorhandenen Inspector-/Evidence-Services sind dafür sehr brauchbare Vergleichsflächen.

---

## H. Consolidation Safety Report

Damit die Audit-Layer nicht selbst eine neue Parallelstruktur wird, braucht sie klare Guardrails.

## 1. Kein neuer MCP-Server

Das wäre der größte Fehler.
Die bestehende MCP-Schicht ist bereits der richtige Kontrollpunkt.

---

## 2. Kein separater „audit truth store“ als neue Primärquelle

Die Audit-Layer darf Findings speichern oder cachen, aber nicht zur neuen Wahrheit über Runtime oder Governance werden.

Sie darf nur sagen:

* was sie beobachtet,
* auf welche Evidenz sie sich stützt,
* mit welcher Confidence sie das tut.

---

## 3. Kein Vermischen von strukturellen Findings mit Live-Runtime-Truth

Im Operator-Surfacing muss glasklar getrennt bleiben:

* Runtime authority
* supporting evidence
* structural analysis
* telemetry/usage traces

---

## 4. Kein versteckter Analyzer außerhalb der kanonischen MCP-Registrierung

Wenn die neue Audit-Familie existiert, muss sie in:

* `mcp_canonical_surface.py`
* `tools_registry.py`
* `mcp_static_catalog.py`

sauber sichtbar sein.
Sonst erzeugt sie genau die versteckte Struktur, die sie aufspüren soll.

---

## 5. Erst read-only, dann mehr

In Phase 1 darf die Audit-Layer nichts mutieren.
Auch keine „halb-automatischen“ Konsolidierungsaktionen.

---

## 6. Kein Überbau über alles ohne Phasenmodell

Nicht zuerst:

* AST + Call graph + persisted graph DB + CI gates + admin cockpit rewrite.

Zuerst:

* canonical integration
* findings model
* inventory + compare + trace
* snapshot resources

---

## I. Phased Integration Recommendation

## Phase 1: Read-only Integration in bestehendem MCP-Server

Ziel:

* vorhandene Serverstruktur wiederverwenden
* keine neue Suite nötig
* keine neue Persistenz nötig

Liefern:

* Audit-Handler-Familie
* Findings-Schema
* `inventory`, `findings`, `compare_surfaces`, `trace_path`
* leichte Snapshot-Caches
* erste Audit-Ressourcen

Empfehlung:

* zunächst unter `wos-admin` einsortieren, nicht sofort neue Suite einführen

---

## Phase 2: Normalisierte Ressourcen + Findings-Snapshots

Ziel:

* stabile, lesbare Audit-Sichten
* wiederholbare Agenten-Workflows

Liefern:

* findings resources
* authority map
* contract index
* invariants resource
* prompt families

---

## Phase 3: Live evidence enrichers und tiefere Parallelitätsdetektion

Ziel:

* Cross-surface-Vergleiche über Runtime-/Inspector-/Governance-Flächen

Liefern:

* backend/world-engine/inspector comparer
* fallback/default detector
* state-loss seam analyzer
* route-family leak classifier

Erst hier lohnt sich mehr Runtime-Nähe.

---

## Phase 4: Operator-/CI-Surfacing

Ziel:

* Ergebnisse sichtbar und prüfbar machen

Liefern:

* Cockpit summary
* audit bundles
* optional CI artifact
* später ggf. threshold-based assertions

Nicht früher.

---

## J. Additional Test / Evidence Recommendations

Bevor man behauptet, die Audit-Layer sei sauber integriert, sollten mindestens diese Nachweise existieren.

### 1. Canonical registration tests

Beweisen, dass alle Audit-Tools/Ressourcen/Prompts:

* in der canonical surface sichtbar sind
* korrekt suite-gefiltert werden
* korrekt öffentlich beschrieben werden

### 2. Read-only posture tests

Beweisen, dass die Audit-Layer keine Runtime mutiert.

### 3. Snapshot/cache invalidation tests

Beweisen, dass Findings nicht aus veralteten Repo-Zuständen stammen.

### 4. Cross-surface comparison tests

Mit bekannten Repository-Beispielen prüfen, dass echte Truth-Splits erkannt werden.

### 5. Golden-fixture tests für Findings

Gezielte Mini-Fixtures mit:

* authority split
* duplicate contract
* orphan path
* hidden fallback
* state-loss seam

### 6. Operator labeling tests

Beweisen, dass Admin-/Cockpit-Surfaces structural findings nicht als runtime authority ausgeben.

### 7. Evidence completeness tests

Beweisen, dass jedes Finding:

* Invariante
* Evidence refs
* severity
* consolidation direction
  trägt.

### 8. Documentation alignment tests

Gerade bei dieser Layer wichtig: docs/code/catalog drift muss erkennbar werden.

---

## K. Final Recommendation

Die empfohlene Integrationsstrategie ist klar:

**Die neue Architektur-Audit-Layer soll innerhalb des bestehenden MCP-Servers als neue read-only Audit-Familie entstehen, gestützt durch einen internen Analyzer-Core und normalisierte Findings-Snapshots.**

### Die ersten Änderungen, die gemacht werden sollten

1. **Findings-Modell und Invarianten definieren**
   Ohne das wird alles zu lose.

2. **Audit-Handler-Familie in die bestehende Registry-Komposition einhängen**
   Nicht am Server vorbei.

3. **Kleine erste Toolmenge einführen**

   * inventory
   * findings
   * compare_surfaces
   * trace_path

4. **Audit-Ressourcen ergänzen**

   * latest findings
   * authority map
   * contracts
   * invariants

5. **Snapshot-/Cache-Modell einführen**

   * leichtgewichtig
   * repo-snapshot-basiert
   * noch keine schwere Persistenz

### Was zunächst verschoben werden sollte

* eigener Audit-Server
* write-capable remediation
* umfassendes AST-/Call-Graph-System
* harte CI-Blocking-Gates
* großer Admin-Umbau

### Warum das der sicherste Weg ist

Weil der bestehende MCP-Server bereits alles mitbringt, was für eine saubere Integration entscheidend ist:

* kanonische Deskriptoren
* Suite-/Governance-Modell
* Tool-/Resource-/Prompt-Muster
* Telemetrie-Anbindung
* Admin-Cockpit-Anschluss
* klare Backend-Boundaries

Die Lücke liegt nicht im Servermodell, sondern in der **fehlenden Architektur-Audit-Domäne**.
Genau diese sollte ergänzt werden — **innerhalb** der vorhandenen Struktur, nicht daneben.

Der wichtigste architektonische Satz für die Umsetzung ist daher:

**Build a new audit domain, not a new audit plane.**

Im nächsten Schritt kann ich daraus direkt einen umsetzungsreifen Masterprompt oder eine saubere `Task.md` für einen Implementierungs-/Audit-Operator ableiten.
