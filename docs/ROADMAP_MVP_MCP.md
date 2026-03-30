# MCP Roadmap · World of Shadows (Ist-Stand kompatibel)

Diese Roadmap beschreibt die Schritte, um **MCP (Model Context Protocol)** in das aktuelle System zu integrieren – in der Reihenfolge **A → B → C**:
- **A:** Operator-/Dev-Tooling (out-of-band, read-only)
- **B:** MCP im AI-Pfad (in-loop, guarded, zuerst read-only/preview)
- **C:** Supervisor + Subagents (echte Orchestrierung, Policies, Hardening)

> Leitprinzip: **Guard/Validation bleibt Gesetz**. MCP/AI darf den autoritativen State nicht umgehen.

---

## M0 — Rahmen & Architekturentscheidungen (Pflicht)

**Ziel:** MCP so einführen, dass es in eurem Setup (lokal + PythonAnywhere) real nutzbar ist.

### Tasks
1. **Host festlegen (wer ruft MCP auf?)**
   - A: IDE/Operator-Tools (lokal)  
   - B/C: Backend-AI-Host (Adapter-Pfad)
2. **Transport wählen**
   - **stdio** (lokal, schnell, simpel) für A
   - **HTTP/Streamable** (Service/Netz) falls später nötig
3. **Security-Baseline**
   - Start: **read-only Tools**
   - keine State-Writes ohne Guard/Policy
4. **Tool-Namensschema + Versioning**
   - `wos.goc.*`, `wos.session.*`, `wos.guard.*`, `wos.content.*`
5. **Deployment-Entscheidung**
   - MCP Server lokal (Operator) spricht remote mit Backend via HTTPS  
   - oder Sidecar im gleichen Netz wie Backend (später Docker)

### Akzeptanzkriterien
- Dokument **„MCP Contract v0“** existiert (Tools, Inputs/Outputs, Auth, Limits)
- Transportentscheidung ist fix (mindestens für A)

---

## A1 — MCP als Operator-/Dev-Tooling (Out-of-Band)

**Ziel:** Sofortiger Nutzen ohne Änderung am God-of-Carnage Turn-Loop.

### A1.1 MCP Server Skeleton
- Neues Modul/Repo z. B. `tools/mcp_server/`
- Implementiert:
  - `tools/list`
  - `tools/call`
  - Logging: Request-ID, `tool_name`, Duration, Status

### A1.2 Read-Only Tools (v0) für God of Carnage
**Empfohlene Tool-Liste (10–12 Tools):**
1. `wos.goc.list_modules()` → verfügbare Module/IDs  
2. `wos.goc.get_module(module_id)` → Metadaten, entry scene  
3. `wos.session.list_active()` → aktive Sessions (In-Memory)  
4. `wos.session.get(session_id)` → scene_id, turn_counter, flags snapshot  
5. `wos.session.get_history(session_id)` → letzte N turns  
6. `wos.guard.explain_last(session_id)` → letzte Guard/Validation  
7. `wos.guard.preview_transition(session_id, target_scene_id)` → allow/deny + Gründe  
8. `wos.guard.preview_delta(session_id, delta)` → allow/deny + Gründe  
9. `wos.content.search(query)` → Content-Suche (Scenes/Beats/Texts)  
10. `wos.system.health()` → backend reachable, version, mode  
11. (optional) `wos.session.export_bundle(session_id)` → Diagnostics bundle  
12. (optional) `wos.content.get_scene(module_id, scene_id)` → Scene-Definition

**Implementationsvarianten:**
- **Empfohlen (remote-first):** MCP Tools rufen **Backend HTTP Endpoints** auf (authentifiziert).
- Alternativ: MCP Server importiert Backend-Python direkt (nur sinnvoll in gleicher Runtime/Env).

### A1.3 Backend: minimale Read-Endpoints (falls nötig)
Wenn Daten noch nicht über bestehende APIs zugänglich sind:
- `GET /api/session/<id>/snapshot`
- `GET /api/session/<id>/history?limit=N`
- `GET /api/session/<id>/guard/last`
- `GET /api/module/<id>`
- `GET /api/content/search?q=...`

### Akzeptanzkriterien
- MCP Tools funktionieren gegen PythonAnywhere oder lokal
- Operator kann Sessions live inspizieren (scene/state/history/guard)
- Keine Änderung am Turn-Flow erforderlich

---

## A2 — Observability & Reproduzierbarkeit (Vorbereitung für B/C)

**Ziel:** Alles bleibt erklärbar und regressions-testbar.

### Tasks
- Einheitliche **Trace-ID**: Session-ID, Turn-ID, Request-ID
- Strukturierte Logs:
  - Tool Calls: name, args-hash, response-hash, duration, status
- Optional: Diagnostics Export (Bundle)

### Akzeptanzkriterien
- Ein Turn ist reproduzierbar/erklärbar („Warum reject?“)
- Tool Calls sind im Debug nachvollziehbar

---

## B1 — MCP im AI-Pfad: Context Enrichment (in-loop, read-only)

**Ziel:** AI (wenn aktiviert) bekommt über MCP den richtigen Kontext, bevor Output erzeugt wird.

### Tasks
1. **AI-Mode kontrolliert aktivierbar machen**
   - z. B. `execution_mode="ai"` via config/admin, nicht hidden
2. **Preflight Context über MCP**
   - allowed actions, scene constraints, flags, history
3. Kontext in **strukturierter Form** in `AdapterRequest`
4. Guard bleibt unverändert: AI schlägt vor, Guard entscheidet

### Akzeptanzkriterien
- AI-Turn läuft ohne Write-Tools
- Tool Calls geloggt
- Guard-Verhalten identisch wie zuvor (nur bessere Inputs)

---

## B2 — MCP Tool-Loop (optional)

**Ziel:** Modell kann Tools anfordern; Host führt aus; Modell finalisiert.

### Tasks
- Whitelist erlaubter Tools je Turn
- Max Tool Calls/Turn (z. B. 3–5), Timeouts, Retries
- Tool-Transcript in Debug Panel

### Akzeptanzkriterien
- Keine Endlosschleifen
- Deterministische Limits greifen
- Debuggability: “welches Tool beeinflusste welches Output?”

---

## B3 — Guarded Preview (kein Write)

**Ziel:** AI kann Deltas vorschlagen und per MCP previewen, aber nicht anwenden.

### Tasks
- `wos.guard.preview_delta(...)` als zentraler Loop
- Adapter nutzt Preview-Feedback zur Korrektur

### Akzeptanzkriterien
- Guard-Reject-Rate sinkt ohne Safety-Verlust
- State bleibt weiterhin autoritativ im Backend/Guard

---

## C1 — Agent Registry + Supervisor Layer (echte Subagents)

**Ziel:** Supervisor/Subagents werden real (Routing, mehrere Calls, Konsolidierung).

### Tasks
1. **Agent Registry (Konfig + Runtime)**
   - agent_id, role, allowed tools, budgets, model selection, status
2. **Supervisor Orchestrator**
   - Plan → Execute → Merge → Finalize
3. Ergebnisformat kompatibel zu aktuellem Turn-Contract

### Akzeptanzkriterien
- Subagents sind echte Aufrufe (nicht nur Textsektionen)
- Tool-Policies pro Agent (MCP whitelist) greifen
- Konsolidierung ist nachvollziehbar (why/trace)

---

## C2 — Production Hardening

**Ziel:** Agentik wird betreibbar.

### Tasks
- Budgets pro Turn (Zeit, Tokens, Toolcalls)
- Fallbacks / Degrade gracefully
- Caching (Content reads, allowed actions, etc.)
- Audit: wer rief welche Tools auf?

### Akzeptanzkriterien
- Stabiler Betrieb, keine Agentenexplosion
- Turn bleibt innerhalb definierter Limits

---

## Empfohlene Reihenfolge

**A1 → A2 → B1 → (B2/B3 optional) → C1 → C2**

---

## Grobe Aufwandsskala (realistische Größenordnung)

- **A1:** 1–3 Tage (Skeleton + ~10 Tools)  
- **A2:** 1–2 Tage (Tracing + Logs + Export)  
- **B1:** 2–5 Tage (AI-Pfad + Preflight + Tests)  
- **B2/B3:** 3–8 Tage (Tool loop + Limits + Diagnostics)  
- **C1:** 1–3 Wochen (Registry + Supervisor + Subagents + Tests)  
- **C2:** 1–2 Wochen (Policies, caching, failover, audit)

---

## Kurz-Checkliste (DoD)

- [ ] MCP Server läuft lokal (stdio) und kann Backend remote ansprechen  
- [ ] `wos.goc.*` Tools liefern belastbare Session-/Content-Infos  
- [ ] Guard Preview Tools existieren (`preview_delta`, `preview_transition`)  
- [ ] Tracing/Logs machen Turns reproduzierbar  
- [ ] AI-Pfad nutzt MCP read-only, Guard bleibt Gesetz  
- [ ] (optional) Tool-loop ist limitiert + auditierbar  
- [ ] Supervisor/Subagents erst nach stabiler A/B Basis
