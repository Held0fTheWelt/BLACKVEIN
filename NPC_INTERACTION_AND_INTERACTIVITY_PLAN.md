# Plan: Freie Aktion → NPC-Zuschaltung → Block-Pulse
**Stand:** 2026-05-19 (überarbeitet nach Grill-Sitzung)
**Modul im Fokus:** `content/modules/god_of_carnage/`
**Verfasser-Kontext:** Vorbereitend für Review/Implementierung durch weitere K.I. Alle Codeverweise mit `file_path:line_number`. Diese Datei ist **kein Implementierungs-PR**, sondern Lagebericht + Phasen-Plan + Klärungsfragen.

---

## 0. Was dieser Plan beantwortet — und was sich geändert hat

**User-Anforderung in einem Satz:** Der Spieler soll sich nach Veroniques Eröffnungssatz natürlich-sprachlich frei bewegen können (Phase 1) und danach mit NPCs koexistieren, die aus eigener Motivation auf eigenem Pulse handeln (Phase 2) — alles **semantisch und/oder principled-deterministisch**, ohne Whitelists, Blacklists oder hardcoded `if x in {...}`-Schalter.

**Korrekturen gegenüber den vorherigen Plan-Versionen:**

1. **Veronique-Stopp ist kein Bug.** Steps 001–005 sind als Testpunkt gewollt: Prologue → wer ist der Spieler / warum ist er hier → ab da beginnt das eigentliche Spiel. Ein „Pointer-Repair" oder „narrator_path→npc_speak-Modus-Switch anhand von `step.mode`-Enums" ist **nicht** der nächste Schritt — er würde gegen die No-Hardcoding-Regel verstoßen.
2. **Phasen-Reihenfolge ist fix:** Erst freie Aktion live verifizieren, *dann* NPCs zuschalten. Beides muss am Ende **koexistieren** (kein turn-taking, kein „Spieler wartet auf NPC-Bündel").
3. **Pulse/Beat als Engine-Mechanik existiert noch nicht.** „beat" ist heute nur Content-Konzept (mandatory_beats, optional_micro_beats, beat_library). Phase 2 braucht eine neue Pulse-Achse — das ist eine ADR-Entscheidung, kein Refactor.
4. **Der Kanon darf den Spieler nicht einsperren.** Verboten ist *ausschließlich*, was **physisch unmöglich** oder **kriminell/böse** ist. „Wohnung verlassen während Versammlung" ist **keine** Policy-Verletzung — es ist ein **Trigger** für einen Director-Pause-Modus, in dem die Versammlung wartet, NPCs menschlich reagieren, und der Spieler frei agieren darf (Kaffee in der Küche, Fenster, etc.) ohne Kanon-Bruch. Siehe §3.4.

---

## 1. Bestehende Architektur — verifizierter Stand (gekürzt)

Faktentreue Bestandsaufnahme; nur die heute relevanten Anker.

### 1.1 Canonical Path
- Source of truth: `content/modules/god_of_carnage/canonical_path/001…038*.yaml`
- Resolver: `ai_stack/canonical_path_resolver.py:104-205`
- 38 Steps, `opening_001_parc_montsouris_edge` … `opening_038_handoff_or_terminal` (`ai_stack/tests/test_canonical_path_resolver.py:54-65`)
- Steps 001–003: `narrator_only_prologue`; 004: `narrator_perception_transition`; 005: `scripted_mandatory_dialog` (**Veronique liest** — gewollter Testpunkt); 006: `scripted_with_player_window`.

### 1.2 Narrator-Pfad / Opening (Turn 0)
- Aufbau: `ai_stack/goc_narrator_path.py:417-499`
- Manager-Projektion: `world-engine/app/story_runtime/manager.py:10370+` setzt `director_path_mode="narrator_path"` und `narrator_path.canonical_step_ids` (Mehrzahl). Turn 0 läuft an LDSS vorbei (`manager.py:7152, 7159, 7393, 7400` — Selektor an `turn_number==0`).
- **Bewusst so gewollt.** Diese Stelle nicht „reparieren".

### 1.3 Souffleuse-Lane
- Vertrag: `docs/ADR/adr-0056-souffleuse-player-guidance-lane.md` (Accepted, 2026-05-18, in dieser Branch erneut bearbeitet).
- Block-Konstruktion: `ai_stack/goc_souffleuse.py:390-444` — `block_type: "souffleuse"`, `visible_lane: "player_hint"`, `commit_impact: "ui_guidance_only"`.
- Output-Realisierung DE/EN: `manager.py:9777-9817` `_souffleuse_output_prompt()` — übersetzt EN-Quellfakten in die Output-Sprache, **niemals via lokalisierter Vorlagen**.

### 1.4 Director / Scene-Planner
- NPC-Auswahl: `ai_stack/scene_director_goc.py:911-943` `_build_responder_set()`
- NPC-Agency-Projektion: `ai_stack/langgraph_runtime_executor.py:4276-4335` `_build_npc_agency_plan_projection()`
- Vertrag „Director ist advisory, kein Wahrheits-Autor": `docs/ADR/adr-0053-bounded-semantic-scene-planner.md`
- Charaktermaterial: `characters/definitions/*.yaml`, `characters/details/{actor_pressure_profiles,interaction_patterns,relationships}.yaml`, `characters/voices/character_voice_*.yaml`

### 1.5 Freie Spieleraktion (aktuelle Branch, uncommitted)
- Policy-Datei: `content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml`
  - `canonical_path_control.default_for_free_player_action: hold_current_step`
  - `social_wait_policy` (semantisch formuliert: Soziale Pause statt Plot-Vorrücken)
  - `plausible_affordance_inference.allowed_scope` / `forbidden_scope` als semantische Kategorien (nicht als Wortlisten)
- Modul-Schalter: `content/modules/god_of_carnage/module.yaml:183-188` `runtime_intelligence.player_freedom`
- Runtime-Aufnahme: `ai_stack/module_runtime_policy.py:327-417`
- Resolution: `ai_stack/player_action_resolution.py` (modifiziert) — `ai_semantic_resolution.plausible_inference` mit `canon_safety`, `canonical_risk`
- Narrator-Konsequenz (mundan-inferiert): `ai_stack/narrator_consequence_contracts.py` (modifiziert) — `source: ai_semantic_plausible_inference`, `requires_model_realization: True`
- Canonical-Anker: `ai_stack/langgraph_runtime_executor.py:4681-4718` Block `canonical_path_control` (Vertrag: committed player movement/perception/wait/object-interaction darf den Pfad **nicht** vorrücken)
- Hold-Mechanik: `manager.py:8703-8717` `_turn_holds_canonical_path_for_free_player_action()`

### 1.6 Block-Output und Streaming
- Vertrag `visible_scene_output.blocks.v1` mit `block_type ∈ {narrator, actor_line, actor_action, environment_interaction, souffleuse, system_degraded_notice}` und `delivery.typewriter`-Profil — `docs/MVPs/MVP_Live_Runtime_Completion/03_live_dramatic_scene_simulator.md:516-575`
- Frontend: `frontend/static/play_typewriter_engine.js:216-450` — Block-für-Block, Skip/RevealAll, Accessibility
- Ruhepunkt: `_check_ruhepunkt_signal` (`manager.py:8777+`) — heute „remaining NPC initiatives == 0"
- Eingabe-Puffer: `manager.queue_player_input(session_id, …)`

### 1.7 Was es heute *nicht* gibt
- **Engine-Pulse / Tick-System:** NPCs handeln im aktuellen Code ausschließlich innerhalb eines `run_ldss`-getriebenen Player-Turns. Es existiert kein autonomer Takt, der NPCs unabhängig vom Spieler-Input bewegt. → für Phase 2 ist das ein neuer Subsystem-Entwurf.
- **Block-Streaming pro Tick:** Heute werden alle Blöcke eines Turns als Bündel produziert, dann gestreamt. Der Pulse-Vorschlag in Phase 2 erfordert Block-Emit pro Tick, damit der Spieler jederzeit reinschneiden kann.

---

## 2. Status der freien Aktion (Phase 1 — laufend)

### 2.1 Zwei Klassifikations-Achsen — keine Kanon-Konformitäts-Achse

Spieler-Aktionen werden entlang **zwei orthogonaler Achsen** klassifiziert, **nicht** an einer „passt zum Kanon"-Achse:

- **Possibility-Achse** — *Ist die Handlung physisch/sinnvoll möglich in der Welt?*
  - Möglich → Aktion wird realisiert. Inferenz von mundanen Objekten erlaubt (Kaffeemaschine in der Küche, Fenster im Wohnzimmer, Mantelhaken im Foyer), solange das Objekt zum Raumtyp gehört.
  - Unmöglich → `needs_clarification` (Superman, durch Wand, neue Räume aus dem Nichts, neue Personen, hidden_evidence-Erfindung).
- **Morality/Legality-Achse** — *Ist die Handlung kriminell/böse?*
  - Akzeptabel → Aktion wird realisiert (auch wenn unhöflich, sozial unbequem, kanon-unpassend).
  - Kriminell/böse → `needs_clarification` mit klärendem Hinweis (Waffe ziehen, Körperverletzung, Mord).

**Aus diesen beiden Achsen folgen die `affordance_status` / `canonical_risk` Felder im Resolution-Output** — *nicht* aus „passt das gerade zum Mandatory-Beat?". Wer im Code `step.mode` oder `current_beat` als Verbotsgrund liest, gehört auf die Don't-Liste.

**Was *nicht* verboten ist** — auch wenn es den Kanon-Fluss stört:
- Wohnung verlassen
- In einen anderen Raum gehen
- Sich mit einem mundanen Objekt beschäftigen
- Schweigen, wegschauen, das Gegenteil von dem tun, was die Anwesenden erwarten

Diese Aktionen lösen einen **Director-Pause-Modus** aus (§3.4), keinen Hold/Block.

### 2.2 Status-Matrix

| Punkt | Beschreibung | Unit | Live (Browser, Real Stack) |
|-------|--------------|------|---------------------------|
| (a) | Affordance-Inferenz für mundane Objekte (Possibility-Achse, alltägliche Objekte im plausiblen Raumkontext) | ✅ grün | offen |
| (b) | Narrator-Konsequenz bei `requires_model_realization: true` → sichtbarer Block | Contract ✅, Realisierung ❓ | **offen (Baustelle)** |
| (c) | `hold_current_step`-Effekt verhindert canonical_step_id-Vorrücken bei mundaner Inferenz | ✅ Unit, **abhängig davon, dass `canonical_path_effect: hold_current_step` im Live-Frame ankommt** | **offen (Baustelle)** |
| (d) | **Director-Pause-Modus** bei Versammlungs-Unterbrechung — siehe §3.4 (vorher als „social_wait_policy" missverstanden) | Policy formuliert, Director-Mechanik **fehlt** | **offen (Hauptbaustelle)** |
| (e) | Morality-Achse (kriminell/böse) → `needs_clarification` ohne Wortliste | ✅ grün | erwartet ok |

**Konsequenz für Phase 1:** Drei Live-Verifikationen offen — (b), (c), (d). (d) ist der konzeptionell anspruchsvollste, weil er **keinen Hold** auf den Spieler legt, sondern den **Director** in einen anderen Modus schaltet, in dem die Versammlung wartet statt der Spieler.

---

## 3. Phase 1 — Plan: Freie Aktion live verifizieren

> **An den implementierenden Agenten:** Vor jeder Codeänderung semantische Suche auf den genauen Stand (siehe `CLAUDE.md` „Code Discovery First"). Diese Datei ist die Grundlage, nicht der Patch. **Kein** `if x in {literal_set}` als Lösung — Discriminator gehört in Content/Policy, nicht in Code.

### 3.1 Live-Smoke-Tour (kein Mock, echter Stack)

Spielsession lokal hochfahren (`docker-up.py`), Session-Sprache DE, Spielfigur Annette. Nach Veroniques erstem Satz (step 005) folgende DE-Inputs testen, je in einer eigenen Session, und gegen die Erwartung prüfen:

| Input | Erwartung Resolution | Erwartung Visible Output | Erwartung Canonical-Pointer |
|-------|----------------------|--------------------------|------------------------------|
| „Ich schaue aus dem Fenster." | mundan-inferiert, `allowed`, `commit_action` | 1 narrator-Block, lokal-sensorisch, keine neuen Personen/Räume | hält auf 005 |
| „Ich lege meinen Mantel ab." | mundan-inferiert, `allowed`, `commit_action`, evtl. `actor_pressure_profile`-Spiegel an Annette | 1 narrator-Block oder 1 actor_action-Block | hält |
| „Ich gehe zum Wohnzimmer und sehe die Tulpen an." | mundan-Bewegung (Schauplatz bleibt) | 1 narrator-Block, Sensorik der Tulpen aus `content/modules/.../008_living_room_tulips_florist.yaml` | hält |
| „Ich verlasse die Wohnung." | `social_wait_policy` greift | Narrator schreibt **sozialen Hold** (Tür, Blicke, Pause), nicht: Treppenhaus | hält |
| „Ich ziehe ein Messer." | `canonical_risk: high`, `forbidden_scope` semantisch | `needs_clarification` als Souffleuse oder Narrator-Klärung | hält |
| „Ich entwickle Superkräfte." | gleich | gleich | hält |

> **Wichtig — Beispiele sind keine Implementierungs-Spezifikation.** Die obigen Inputs sind *dramaturgische Illustrationen* dessen, was die semantischen Pfade leisten sollen. Sie dürfen **nicht** als Test-Fixtures gegen exakte Strings, als Verb-Liste oder als `if input in {...}`-Pattern in den Runtime-Code übernommen werden. Tests gegen diese Pfade müssen *generierte* oder *paraphrasierte* Eingaben benutzen und auf **Pfad-Eigenschaften** (`affordance_status`, `canonical_risk`, `target_location`-Bildung) prüfen, nicht auf den Eingabestring.

**Beobachtungspunkte im Code:**
- Resolution: `ai_stack/player_action_resolution.py` — `resolve_player_action()` Rückgabe inspizieren (Langfuse-Trace, oder lokal stdout instrumentieren)
- Narrator-Konsequenz: `ai_stack/narrator_consequence_contracts.py` — `source`-Feld und `requires_model_realization` im commit-Frame
- Hold-Wirkung: `manager.py:8703-8717` — `_turn_holds_canonical_path_for_free_player_action(graph_state)` muss `True` zurückgeben → Pointer rückt nicht.

**Akzeptanz Phase 1:** Alle sechs Smoke-Inputs erzeugen sichtbares, kanon-sicheres Verhalten *und* der Canonical-Pointer bleibt auf 005.

### 3.2 Baustelle (b) — Live-Narrator-Block für mundane Inferenz

Frage: Wenn `ai_semantic_resolution.plausible_inference` einen mundanen `commit_action` erzeugt und `narrator_consequence_packet` `requires_model_realization: true` setzt — wird der Live-Graph daraus zuverlässig **einen sichtbaren `narrator`-Block** erzeugen, der im `visible_scene_output.blocks` landet?

**Was zu verifizieren ist (semantische Suche, dann Live-Smoke):**
1. Wer im Graph konsumiert `narrator_consequence_packet` mit `source: ai_semantic_plausible_inference`? (Anker: `ai_stack/narrator_consequence_contracts.py` Konsumenten suchen.)
2. Wird der Block dann auch in den committed `blocks`-Vertrag geschrieben — oder fällt er irgendwo wegen fehlendem `actor_response_present` aus dem Vertrag?
3. Existieren Validator-/Judge-Gates, die hier *fälschlich* greifen, weil sie Actor-Sprache erwarten?

**Akzeptanz (b):** Live-Test: ein mundaner Input erzeugt im Stream einen sichtbaren `narrator`-Block mit Inhalt, der weder neue Personen/Räume noch plot-tragende Fakten enthält (Validator in `narrator_consequence_contracts.py` greift bereits, dort prüfen).

**Anti-Pattern bewusst vermeiden:** **kein** „if status == 'mundane_inferred' then force-emit narrator block" als Hardcode. Stattdessen den vorhandenen Vertrag prüfen und die fehlende Brücke im Graph identifizieren — die Lücke muss content-/contract-getrieben geschlossen werden.

### 3.3 Baustelle (c) — `hold_current_step`-Effekt erreicht den Live-Frame

`_turn_holds_canonical_path_for_free_player_action(graph_state)` (manager.py:8703-8717) liest den Hold-Signal aus dem `graph_state`. Frage: **Wer schreibt diesen Effekt rein?** Vermutlich der `commit_state`-Pfad nach `resolve_player_action`. Wenn `canon_safety in {content_silent_mundane, non_load_bearing, reversible_local_detail}`, muss der Effect `canonical_path_effect: hold_current_step` propagiert werden.

**Akzeptanz (c):** Im Live-Smoke aus 3.1 zeigt der Trace, dass nach jedem mundanen Input `canonical_path_effect: hold_current_step` im `graph_state` steht und `_turn_holds_canonical_path_for_free_player_action` deshalb `True` zurückgibt — *durchgängig*, nicht nur zufällig.

**Anti-Pattern:** **kein** statisches „if actor == player and verb in MOVEMENT_VERBS then hold". Die semantische Resolution liefert `canon_safety`; der Commit-Pfad muss diese Information *weitergeben*, nicht erneut raten.

### 3.4 Baustelle (d) — Director-Pause-Modus bei Versammlungs-Unterbrechung

**Konzeptioneller Reset gegenüber früheren Plan-Versionen:** Das ist *kein* Spieler-Hold. Der Spieler darf die Wohnung verlassen, in die Küche gehen, Kaffee machen, am Fenster stehen — alles ohne Kanon-Verletzung. Was passiert, ist eine **Director-Modus-Umschaltung**, in der die *Versammlung* wartet, nicht der *Spieler*.

**Discriminator (Hybrid, Stufe 1):**
- **Quelle:** `named_characters` pro Step (in jedem Step deklariert, z. B. `canonical_path/005_…yaml:36`).
- **Bedingung:** Spielercharakter ∈ `named_characters[current_step]` **und** semantische Aktion-Klassifikation produziert `target_location ≠ current_scene_id` (oder allgemeiner: `presence_breaks_gathering: true`).
- **Effekt:** Director schaltet in **`gathering_paused`-Zustand**. *Keine Sperre der Spieler-Aktion.* *Keine Hold-Property auf den Step-Pointer.* Stattdessen: ein neuer Director-Modus.

**Verhalten im `gathering_paused`-Modus:**
1. **Spieler ist frei.** Jede mögliche & moralisch ok Aktion wird normal ausgeführt — Kaffee machen, Fenster, Mantel, Bewegung. Aktion läuft über denselben ai_semantic_resolution-Pfad wie sonst.
2. **NPCs konsumieren keine Mandatory-Beats** des aktuellen Steps. Der Step-Pointer wartet (nicht weil „verboten", sondern weil die Bedingung — „named_characters anwesend" — gerade nicht erfüllt ist).
3. **Director darf NPCs menschlich reagieren lassen** (eine kurze Reaktionsgeste auf die Spieler-Aktion: „Veronique hält im Lesen inne", „Michel wechselt einen Blick mit Alain"). Diese Reaktionen sind **nicht erzwungen** — der Director entscheidet ob/wann, basierend auf Pressure-Profile und Interaction-Patterns. In Phase 1 (vor Pulse-Mechanik) reicht **ein** zusammenfassender Narrator-Block.
4. **NPCs sind nicht gezwungen weiterzureden.** In Phase 2 (mit Pulse) können sie aus eigener Motivation Mikro-Interaktionen führen, aber kein Mandatory-Beat-Konsum.
5. **Rückkehr aus dem `gathering_paused`-Modus:** Sobald `named_characters[current_step] ⊆ aktuelle Schauplatz-Präsenz` wieder erfüllt ist (Spieler kehrt in den Versammlungsraum zurück), schaltet der Director zurück. Der Kanon-Fluss läuft weiter.

**Entscheidung — Verantwortungs-Trennung (entspricht Variante (a)):**

Der Discriminator wohnt **im Director**, gefüttert aus dem *physischen* Resolver-Output. Resolver = „was bedeutet die Aktion in der Welt?" (Ziel-Location, Possibility, Morality). Director = „was bedeutet das für die Story-Mechanik?" (gathering_paused, Beat-Konsum, NPC-Reaktion). Der Resolver bekommt **keine** Versammlungs-Kenntnis.

**Sub-Phasen für (d):**

- **1.d.0 — Resolver-Vertrag schließen (Vorbedingung).** Der semantische Resolution-Pfad muss bei jeder als Bewegung klassifizierten Aktion **zuverlässig** `resolved_target_type: "location"` + `resolved_target_id: <room_id>` produzieren. Die Klassifikation passiert *semantisch* durch den LLM-Prompt, **nicht** über eine Verb-Whitelist im Code. Wenn der Resolver unsicher ist, gibt er `affordance_status: unknown_target` zurück (Klärungsweg), niemals einen stillen `null`-Fallback. Tests müssen paraphrasierte Bewegungs-Eingaben aus verschiedenen Sprachregistern abdecken (umgangssprachlich, formell, elliptisch) und auf Pfad-Eigenschaften prüfen — keine String-Fixtures.

- **1.d.1 — Director-State-Achse einführen.** Reines Datenfeld pro Session: `director_state.gathering_paused = { step_id, missing_actor_ids, since_turn } | None`. Anker: `ai_stack/scene_director_goc.py`. Kein Enum-Set, kein Modus-Diagramm.

- **1.d.2 — Reine Vergleichsfunktion im Director.** `compute_gathering_state(actor_locations, current_step_named_characters, current_step_scene_id) -> { paused: bool, missing: [actor_ids] }`. Datenquelle für `actor_locations`: `ai_stack/environment_state_contracts.py` (existiert) plus `runtime_world`. Keine Listen, keine Verben — reiner Mengen-Vergleich auf `actor_locations` gegen `named_characters` + `scene_id`.

- **1.d.3 — Beat-Konsum-Gate im LDSS/NPC-Agency-Builder.** Wenn `gathering_paused`, werden **keine** Mandatory-Beats konsumiert. Anker: `ai_stack/live_dramatic_scene_simulator.py`. Der Builder fragt den Director-State und überspringt den Konsum — eine Bedingung, kein Schalter-Schwall.

- **1.d.4 — Narrator-Reaktions-Hook für den Pause-Übergang.** Beim Wechsel `gathering_paused: false → true` darf der Narrator *einen* Reaktionsblock emittieren („die Versammlung hält inne"), Inhalt content-geleitet aus `characters/details/actor_pressure_profiles.yaml` und `interaction_patterns.yaml`. **Kein** hardcoded Textbaustein. In Phase 1 reicht ein zusammenfassender Block; pro-NPC-Reaktion wartet auf Phase 2 (Pulse).

**Akzeptanz-Voraussetzung der Stufen-Reihenfolge:** 1.d.0 muss live grün sein, bevor 1.d.1–1.d.4 sinnvoll testbar sind. Wenn der Resolver-Output unsicher ist, schlägt jede Director-Logik durch — der Discriminator-Pfad fängt dann garbage. Erst Resolver-Vertrag schließen, dann Director-Mechanik anbauen.

**Akzeptanz (d) Phase 1, minimale Stufe — illustrative Szenarien, keine Test-Fixtures:**

> Die folgende Tabelle skizziert das *erwartete Verhalten an typischen Stellen im Aktion-Raum*. Die linken Spalten sind **keine** Eingabe-Werte für Pattern-Matching, **keine** Test-Strings und **keine** Verb-/Phrasen-Whitelist. Sie zeigen vier qualitativ unterschiedliche Klassen von Spieler-Aktion (Versammlung verlassen / in anderen Raum wechseln / mundane Lokal-Aktion ausführen / in Versammlung zurückkehren), damit nachvollziehbar wird, wie die Pfade *funktional* greifen sollen. Tests müssen die jeweilige Klasse mit **mehreren generierten Paraphrasen** treffen und auf Pfad-Eigenschaften prüfen.

| Aktion-Klasse (illustriert mit Beispiel-Input, **nicht für Hardcode**) | Erwartete Pfad-Eigenschaften |
|-----------------------------------------------------------------------|------------------------------|
| Versammlung verlassen — z. B. „Ich verlasse die Wohnung." | `target_location ≠ current_scene_id`, `presence_breaks_gathering: true`, Director schaltet auf `gathering_paused = true`, Narrator emittiert *einen* Reaktionsblock (Tür/Versammlung), Step-Pointer und Mandatory-Beat-Konsum unverändert. |
| In Nicht-Versammlungs-Raum wechseln — z. B. „Ich gehe in die Küche." | `target_location`-Inferenz auf den anderen Raum; sofern Spieler ∈ `named_characters[current_step]`, bleibt `gathering_paused`; Narrator realisiert die mundane Raum-Sensorik; kein Mandatory-Beat konsumiert. |
| Mundane Lokal-Aktion außerhalb der Versammlung — z. B. „Ich mache mir einen Kaffee." | Mundane Objekt-Inferenz (Possibility-Achse, plausibel im Raumtyp), `canon_safety: content_silent_mundane`, Narrator-Konsequenz lokal. **Keine** erzwungene NPC-Reaktion im Versammlungsraum. |
| Rückkehr in Versammlung — z. B. „Ich kehre ins Wohnzimmer zurück." | `target_location == current_scene_id_of_step`, `named_characters[current_step]` ist wieder erfüllt, Director löscht `gathering_paused`; Mandatory-Beat-Konsum ist im nächsten LDSS-Turn wieder verfügbar. |

**Anti-Patterns bewusst vermeiden:**
- **Keine** Raum-/Verb-/Aktion-Whitelist.
- **Kein** „can_leave_gathering_now"-Boolean pro Step, das in YAML hardcoded ist. `named_characters` *ist* das Predicate — was sie deklariert, ist die Versammlungsmenge.
- **Kein** Zwang auf NPCs, in der Pause-Phase ständig Reaktions-Blöcke zu produzieren. Stille ist eine gültige NPC-Wahl (in Phase 2 dann motivations-basiert vom Pulse-Scheduler entschieden).
- **Kein** Zwang auf den Spieler, in den Versammlungsraum zurückzukehren. Er darf beliebig lange in der Küche bleiben. Der Kanon wartet.

### 3.5 Was Phase 1 *nicht* tut
- Keine NPC-Pulse-Mechanik. NPCs reagieren in Phase 1 ausschließlich innerhalb des bestehenden Turn-Cycles auf Spieler-Inputs. Vollständige Autonomie/Koexistenz ist Phase 2.
- Keine Änderung am Narrator-Pfad (Turn 0). Bleibt wie ist.
- Keine Pointer-Repair-Logik in `_execute_opening_locked`. Bleibt wie ist.

---

## 4. Phase 2 — NPC + Story zuschalten (Vorschlag, ADR-pflichtig)

Erst beginnen, wenn Phase 1 live grün ist. Phase 2 ist *kein* Refactor des Bestehenden, sondern eine **neue Achse** über dem Turn-Cycle.

### 4.1 Design-Kernanforderungen aus der Grill-Sitzung

1. **Spieler kann jederzeit eingreifen.** Keine „NPC-Bündel" mehr; kein Warten auf Ruhepunkt-Signal als Voraussetzung für Eingabe.
2. **Blöcke kommen einzeln, nicht im Bündel.** Ein Block pro Tick, mit klarer typewriter-Lieferung.
3. **NPCs handeln aus Motivation, nicht aus Skript-Zwang.** Wenn der Spieler den Raum verlässt, *kann* (Wahrscheinlichkeit aus Pressure-Profile + Interaction-Patterns) ein NPC folgen — oder nicht. NPCs können in der Abwesenheit des Spielers miteinander interagieren (Beispiel: Alain + Annette im Bad).
4. **Pulse/Beat als Engine-Taktgeber.** Tick rhythmisiert die Welt; ein Block kann pro Tick emittiert werden; der Spieler-Input ist ein gleichwertiges Event im selben Stream.
5. **Souffleuse im Modus-Spektrum** (siehe §5): Pressure ist nur ein Modus; in ruhigen Phasen spricht sie in Charakterstimme als „eigenes Ich" des Spielers.
6. **Keine Hardcoding-Lösungen** — Motivation, Folgen-oder-nicht, Block-Auswahl: alles semantisch / AI-gestützt / principled-deterministisch.

### 4.2 Subsysteme, die neu / erweitert werden müssen (Skizze)

| Subsystem | Zweck | Heute | Phase 2 |
|-----------|-------|-------|---------|
| **Tick-Scheduler** | Pulse für autonome NPC-Initiative | nicht vorhanden | neu: emittiert Tick-Events; jedes Tick fragt den Director nach max. einem neuen NPC-Block, sofern Motivation > Schwelle |
| **Motivation-Score** | Entscheidet, *ob* ein NPC im Tick handelt | Initiative-Liste wird vom LDSS-Plan eröffnet | neu: kontinuierlicher Score aus Pressure-Profile, Interaction-Pattern, Relationship, dramatischer Lage; AI-gestützte Bewertung pro Tick |
| **Block-Stream-Bus** | Ein Event-Stream für Narrator/Actor/Souffleuse/Spieler-Input | Turn-basiert (alle Blöcke eines Turns als Bündel) | neu: ein Block = ein Event; Spieler-Input ist gleichberechtigtes Event; kein „streaming_active"-Lock mehr |
| **Player-Cut-In-Handling** | Spieler darf einen NPC-Block unterbrechen | Eingabe puffert via `queue_player_input`, geöffnet bei Ruhepunkt | neu: Eingabe wird sofort gegen den aktiven NPC-Plan gespiegelt; Director kann den NPC-Plan revidieren (Block droppen, anpassen, neue Initiative bilden) |
| **NPC-Folge-Entscheidung** | Folgt NPC dem Spieler? Reagiert? Bleibt? | nicht modelliert | neu: semantische Entscheidung pro Tick: aus Relationship, Pressure-Profile, sozialer Lage und Pfad-Kontext |
| **Souffleuse-Modus-Wahl** | Pressure vs. „eigenes Ich" vs. Stille | heute: nur Pressure-Cues an Step-Markern | neu: Modus aus Lage (Allein/Mit-Charakter/Versammlung) + Spieler-Sprachstil + ADR-0056-Vertrag |

### 4.3 Verträge, die ADR-pflichtig sind

Phase 2 berührt mehrere Verträge gleichzeitig — vermutlich **drei neue ADRs**:

- **ADR-0058 (Vorschlag): Engine-Pulse und Tick-Driven NPC-Initiative.** Definiert Tick-Schema, Block-Stream-Bus, Player-Cut-In. Berührt MVP3 (LDSS), MVP4 (Diagnostik) — beide Verträge bleiben, aber Streaming-Modell wandelt sich von Bündel zu Tick.
- **ADR-0059 (Vorschlag): Semantischer NPC-Motivation-Score und Folge-Entscheidung.** Definiert, wie aus Content-Material (`actor_pressure_profiles`, `interaction_patterns`, `relationships`) + dramatischer Lage eine Per-Tick-Entscheidung wird, ohne Whitelists. Verlangt mindestens einen prinzipien-deterministischen Pfad (Score-Aggregation) und einen AI-gestützten Pfad (Judge), die Quervalidierung machen.
- **ADR-0060 (Vorschlag): Souffleuse-Modus-Spektrum.** Erweitert ADR-0056 um „eigenes Ich"-Modus; spezifiziert, **wie** der Modus bestimmt wird (semantisch, nicht Step-Enum), und **welche** Validatoren greifen (model-graded judge, *keine* String-Pattern als Produktions-Gate).

### 4.4 Phasen-Eintritts-Kriterium

Phase 2 startet erst, wenn:
- Phase 1 Live-Smoke-Tour (§3.1) komplett grün
- (b), (c), (d) Akzeptanz erfüllt
- Keine Regression in MVP3-Ruhepunkt-Tests (`world-engine/tests/test_mvp3_complete_integration.py`)

---

## 5. Souffleuse — Modus-Spektrum

ADR-0056 D3 verbietet bereits Selbstreferenzen („Souffleuse:", „for this role", Identitätsliste). Phase 2 erweitert die Modus-Achse:

| Modus | Trigger (semantisch) | Stimme | Beispiel |
|-------|----------------------|--------|----------|
| **Pressure** (bestehend) | Step-Marker `souffleuse_cues.*` + dramatische Engstelle | Director-/Beobachter-Ton, kondensiert | step 006 `armed_word_role_pressure` |
| **Eigenes Ich** (neu, Phase 2) | Spieler ist *alleine* in einem Raum **oder** mit nur einem Charakter in vertrauter Lage; ruhige Phase ohne Mandatory-Beat-Druck | **Spielerfigur duzt sich selbst** in Charakterstimme (`character_voice_*.yaml`); innere Wahrnehmung, kein Spielmechanik-Hint | „Du atmest flach. Annettes Geduld kostet dich, das weißt du." |
| **Stille** | Spieler bewegt sich gerade aktiv / spricht / unterbricht | kein Souffleuse-Block | — |

**Wichtig (keine Hardcoding):**
- Modus-Wahl ist **semantisch** aus Lage, nicht aus Step-Enum.
- Validator gegen „for this role", „you are…", „Souffleuse:" bleibt als **Smoke-Regression** legitim, ist aber *nicht* das Produktions-Gate. Produktions-Gate ist ein model-graded judge mit Vertrag aus ADR-0056 D3 + ADR-0060 (neu).
- Sprachadapter (`story_runtime_core/language_adapter.py`, in dieser Branch angefasst): keine lokalisierten Vorlagentexte als Quelle — EN-Quellfakten → Output-Sprache via Prompt.

---

## 6. Was dieser Plan *nicht* ist

- **Kein Patch.** Keine konkreten Diffs.
- **Kein ADR.** Phase 2 verlangt drei neue ADRs (4.3); Phase 1 verlangt vermutlich keinen neuen ADR, sondern verifiziert / schließt eine bestehende Lücke im Vertrag ADR-0057 (canon-safe player freedom).
- **Keine Pointer-Repair-Aktion** in `_execute_opening_locked` oder in der Modus-Auswahl. Steps 001–005 bleiben wie sie sind.
- **Keine MVP-Verschiebung.** MVP3 (LDSS), MVP4 (Diagnostik) bleiben Voraussetzung; Phase 2 ergänzt deren Streaming-Modell, ersetzt sie nicht.

---

## 7. Offene Fragen für den Autor (vor Phase-2-Start zu beantworten)

1. **Tick-Frequenz:** Pulse-Cadence — fester Tick (z. B. alle 2–4 s) oder ereignisgetrieben (NPC-Motivation überschreitet Schwelle)? Mein Vorschlag: ereignisgetrieben mit Mindest-Cooldown, damit der Stream nicht ratternd wird.
2. **Spieler-Cut-In-Semantik:** Wenn der Spieler einen NPC-Block unterbricht — wird der laufende Block *zu Ende gerendert* (typewriter), aber der nächste pausiert, oder *abgebrochen*? Mein Vorschlag: zu Ende rendern, danach pausieren, neuen NPC-Plan re-evaluieren.
3. **NPC-Autonomie ohne Spieler-Beobachtung:** Wenn Alain + Annette im Bad sind und der Spieler im Wohnzimmer — sollen die Bad-Interaktionen *narrativ angedeutet* werden (Geräusche, Stille, gedämpfte Stimmen), oder unsichtbar bleiben? Mein Vorschlag: andeuten, niemals wörtlich transkribieren, solange der Spieler nicht hingeht.
4. **Souffleuse-Modus „Eigenes Ich" — Lage-Discriminator:** Welche Content-Metadaten zeigen „ruhige Phase" an? Mein Vorschlag: semantische Ableitung aus Anwesenheits-Topologie + aktueller Beat-Liste + Pressure-Score, **nicht** Step-Enum.
5. **Phase 1 Live-Verifikation — Tooling:** Reicht manueller Browser-Smoke + Langfuse-Trace-Inspektion, oder soll ein Headless-Integrationstest (real Stack, kein Mock) zusätzlich entstehen? Mein Vorschlag: beides — Browser-Smoke für (d) und manuelle Auge-am-Output-Prüfung, Headless für (b) und (c).

---

## 8. Referenz-Stack (in Lesereihenfolge)

1. `CLAUDE.md` (Discipline)
2. `docs/architecture/god_of_carnage_current_contract.md`
3. `docs/ADR/adr-0056-souffleuse-player-guidance-lane.md`
4. `docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md` (Branch-Draft)
5. `docs/ADR/adr-0053-bounded-semantic-scene-planner.md`
6. `docs/ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md`
7. `docs/MVPs/MVP_Live_Runtime_Completion/IMPLEMENTATION_PLAN_NARRATIVE_RUNTIME_AGENT.md`
8. `content/modules/god_of_carnage/module.yaml`
9. `content/modules/god_of_carnage/knowledge/player_freedom_policy.yaml`
10. `content/modules/god_of_carnage/canonical_path/004_*.yaml`, `005_*.yaml`, `006_*.yaml`
11. `ai_stack/canonical_path_resolver.py`, `ai_stack/goc_narrator_path.py`, `ai_stack/goc_souffleuse.py`, `ai_stack/scene_director_goc.py`, `ai_stack/player_action_resolution.py`, `ai_stack/narrator_consequence_contracts.py`, `ai_stack/module_runtime_policy.py`
12. `world-engine/app/story_runtime/manager.py` (heiße Zonen: 7123–7172, 8703–8731, 9777–9817, 10370–10440)
13. `frontend/static/play_typewriter_engine.js`

---

*Überarbeitet am 2026-05-19 nach Grill-Sitzung. Vorgängerstand ersetzt: die dortige Diagnose-Sektion (Hypothesen A/B/C) war auf den falschen „Bug" ausgerichtet — Veronique-Stopp ist gewollter Testpunkt. Sämtliche „if step.mode in {...}"-Vorschläge entfernt: kein Hardcoding (siehe MEMORY: feedback_no_static_gating).*
