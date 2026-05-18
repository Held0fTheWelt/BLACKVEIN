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

Aktionen — **sowohl Spieler- als auch NPC-Aktionen** — werden entlang **zwei orthogonaler Achsen** klassifiziert, **nicht** an einer „passt zum Kanon"-Achse:

- **Possibility-Achse** — *Ist die Handlung physisch/sinnvoll möglich in der Welt?*
  - Möglich → Aktion wird realisiert. Inferenz von mundanen Objekten erlaubt (Kaffeemaschine in der Küche, Fenster im Wohnzimmer, Mantelhaken im Foyer), solange das Objekt zum Raumtyp gehört.
  - Unmöglich → `needs_clarification` (Superman, durch Wand, neue Räume aus dem Nichts, neue Personen, hidden_evidence-Erfindung).
- **Morality/Legality-Achse** — *Ist die Handlung kriminell/böse?*
  - Akzeptabel → Aktion wird realisiert (auch wenn unhöflich, sozial unbequem, kanon-unpassend).
  - Kriminell/böse → `needs_clarification` mit klärendem Hinweis (Waffe ziehen, Körperverletzung, Mord).

**Aus diesen beiden Achsen folgen die `affordance_status` / `canonical_risk` Felder im Resolution-Output** — *nicht* aus „passt das gerade zum Mandatory-Beat?". Wer im Code `step.mode` oder `current_beat` als Verbotsgrund liest, gehört auf die Don't-Liste.

**Akteurssymmetrie:** Spieler und NPCs unterliegen demselben Aktion-Modell. NPCs sind keine Dialog-Maschinen, die auf den Kanon warten — sie können mundane Eigenaktionen ausführen (in die Küche gehen, etwas suchen, Wasser einschenken, ans Fenster treten, sich hinsetzen, kurz wegschauen). Diese laufen über denselben semantischen Resolution-Pfad (oder den NPC-äquivalenten) wie Spieler-Aktionen und respektieren dieselben Possibility/Morality-Achsen. Im `gathering_paused`-Zustand sind NPCs deshalb nicht stumm — sie sind genauso frei wie der Spieler, ihren Moment zu nutzen.

**Was *nicht* verboten ist** — auch wenn es den Kanon-Fluss stört:

- Wohnung verlassen
- In einen anderen Raum gehen
- Sich mit einem mundanen Objekt beschäftigen
- Schweigen, wegschauen, das Gegenteil von dem tun, was die Anwesenden erwarten

Diese Aktionen lösen einen **Director-Pause-Modus** aus (§3.4), keinen Hold/Block.

### 2.2 Status-Matrix


| Punkt | Beschreibung                                                                                                          | Unit                                                                                              | Live (Browser, Real Stack) |
| ----- | --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------- |
| (a)   | Affordance-Inferenz für mundane Objekte (Possibility-Achse, alltägliche Objekte im plausiblen Raumkontext)            | ✅ grün                                                                                            | offen                      |
| (b)   | Narrator-Konsequenz bei `requires_model_realization: true` → sichtbarer Block                                         | Contract ✅, Realisierung ❓                                                                        | **offen (Baustelle)**      |
| (c)   | `hold_current_step`-Effekt verhindert canonical_step_id-Vorrücken bei mundaner Inferenz                               | ✅ Unit, **abhängig davon, dass `canonical_path_effect: hold_current_step` im Live-Frame ankommt** | **offen (Baustelle)**      |
| (d)   | **Director-Pause-Modus** bei Versammlungs-Unterbrechung — siehe §3.4 (vorher als „social_wait_policy" missverstanden) | Policy formuliert, Director-Mechanik **fehlt**                                                    | **offen (Hauptbaustelle)** |
| (e)   | Morality-Achse (kriminell/böse) → `needs_clarification` ohne Wortliste                                                | ✅ grün                                                                                            | erwartet ok                |


**Konsequenz für Phase 1:** Drei Live-Verifikationen offen — (b), (c), (d). (d) ist der konzeptionell anspruchsvollste, weil er **keinen Hold** auf den Spieler legt, sondern den **Director** in einen anderen Modus schaltet, in dem die Versammlung wartet statt der Spieler.

---

## 3. Phase 1 — Plan: Freie Aktion live verifizieren

> **An den implementierenden Agenten:** Vor jeder Codeänderung semantische Suche auf den genauen Stand (siehe `CLAUDE.md` „Code Discovery First"). Diese Datei ist die Grundlage, nicht der Patch. **Kein** `if x in {literal_set}` als Lösung — Discriminator gehört in Content/Policy, nicht in Code.

### 3.1 Live-Smoke-Tour (kein Mock, echter Stack)

Spielsession lokal hochfahren (`docker-up.py`), Session-Sprache DE, Spielfigur Annette. Nach Veroniques erstem Satz (step 005) folgende DE-Inputs testen, je in einer eigenen Session, und gegen die Erwartung prüfen:


| Input                                             | Erwartung Resolution                                                                            | Erwartung Visible Output                                                                            | Erwartung Canonical-Pointer |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | --------------------------- |
| „Ich schaue aus dem Fenster."                     | mundan-inferiert, `allowed`, `commit_action`                                                    | 1 narrator-Block, lokal-sensorisch, keine neuen Personen/Räume                                      | hält auf 005                |
| „Ich lege meinen Mantel ab."                      | mundan-inferiert, `allowed`, `commit_action`, evtl. `actor_pressure_profile`-Spiegel an Annette | 1 narrator-Block oder 1 actor_action-Block                                                          | hält                        |
| „Ich gehe zum Wohnzimmer und sehe die Tulpen an." | mundan-Bewegung (Schauplatz bleibt)                                                             | 1 narrator-Block, Sensorik der Tulpen aus `content/modules/.../008_living_room_tulips_florist.yaml` | hält                        |
| „Ich verlasse die Wohnung."                       | `social_wait_policy` greift                                                                     | Narrator schreibt **sozialen Hold** (Tür, Blicke, Pause), nicht: Treppenhaus                        | hält                        |
| „Ich ziehe ein Messer."                           | `canonical_risk: high`, `forbidden_scope` semantisch                                            | `needs_clarification` als Souffleuse oder Narrator-Klärung                                          | hält                        |
| „Ich entwickle Superkräfte."                      | gleich                                                                                          | gleich                                                                                              | hält                        |


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
- **Effekt:** Director schaltet in `**gathering_paused`-Zustand**. *Keine Sperre der Spieler-Aktion.* *Keine Hold-Property auf den Step-Pointer.* Stattdessen: ein neuer Director-Modus.

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


| Aktion-Klasse (illustriert mit Beispiel-Input, **nicht für Hardcode**)               | Erwartete Pfad-Eigenschaften                                                                                                                                                                                                               |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Versammlung verlassen — z. B. „Ich verlasse die Wohnung."                            | `target_location ≠ current_scene_id`, `presence_breaks_gathering: true`, Director schaltet auf `gathering_paused = true`, Narrator emittiert *einen* Reaktionsblock (Tür/Versammlung), Step-Pointer und Mandatory-Beat-Konsum unverändert. |
| In Nicht-Versammlungs-Raum wechseln — z. B. „Ich gehe in die Küche."                 | `target_location`-Inferenz auf den anderen Raum; sofern Spieler ∈ `named_characters[current_step]`, bleibt `gathering_paused`; Narrator realisiert die mundane Raum-Sensorik; kein Mandatory-Beat konsumiert.                              |
| Mundane Lokal-Aktion außerhalb der Versammlung — z. B. „Ich mache mir einen Kaffee." | Mundane Objekt-Inferenz (Possibility-Achse, plausibel im Raumtyp), `canon_safety: content_silent_mundane`, Narrator-Konsequenz lokal. **Keine** erzwungene NPC-Reaktion im Versammlungsraum.                                               |
| Rückkehr in Versammlung — z. B. „Ich kehre ins Wohnzimmer zurück."                   | `target_location == current_scene_id_of_step`, `named_characters[current_step]` ist wieder erfüllt, Director löscht `gathering_paused`; Mandatory-Beat-Konsum ist im nächsten LDSS-Turn wieder verfügbar.                                  |


**Anti-Patterns bewusst vermeiden:**

- **Keine** Raum-/Verb-/Aktion-Whitelist.
- **Kein** „can_leave_gathering_now"-Boolean pro Step, das in YAML hardcoded ist. `named_characters` *ist* das Predicate — was sie deklariert, ist die Versammlungsmenge.
- **Kein** Zwang auf NPCs, in der Pause-Phase ständig Reaktions-Blöcke zu produzieren. Stille ist eine gültige NPC-Wahl (in Phase 2 dann motivations-basiert vom Pulse-Scheduler entschieden).
- **Kein** Zwang auf den Spieler, in den Versammlungsraum zurückzukehren. Er darf beliebig lange in der Küche bleiben. Der Kanon wartet.

### 3.5 Live-Verifikation — systematische Diagnose-Erweiterung der world-engine UI

**Entscheidung (2026-05-19, erweitert):** Phase 1 wird live verifiziert über die **systematische Erweiterung der bestehenden Diagnose-Seiten in der world-engine UI**. Nicht ein einzelnes neues Sammelpanel, sondern Erweiterungen dort, wo die jeweilige Information **thematisch hingehört**. Standort: `world-engine/app/web/templates/ui/` — bestehende Seiten: `diagnostics.html`, `live_runtime.html`, `narrative_systems.html`, `runtime_ledger.html`, `traces_observability.html`, `runs_sessions.html`, `runtime_status.html`, `validation_authority.html`, `history_events.html` u. a.

**Prinzip der Erweiterung:** Für jede neue Director-State-Achse, jeden neuen Capability-Compose-Schritt, jede neue Π-Konsultation und jedes neue Pulse-Ereignis gehört ein Diagnose-Feld **dorthin, wo sein thematischer Nachbar schon sitzt** — nicht in ein generisches Sammel-Panel. Bekannte Felder, die heute noch *nirgendwo* diagnostiziert werden und in Phase 1+2 zu ergänzen sind (illustrative Zuordnung, endgültiger Standort beim Implementieren zu entscheiden):

| Wahrscheinlicher Standort                   | Neues Diagnose-Feld                                                                                                                                                                                                                                                                                | Phase-Bezug          |
| ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `diagnostics.html` / `runtime_status.html`  | Aktueller `session.canonical_step_id`; aktiver `canonical_path_effect`; ob `_turn_holds_canonical_path_for_free_player_action` greift                                                                                                                                                              | Phase 1 (c)          |
| `diagnostics.html` / `narrative_systems.html` | Director-State `gathering_paused = {step_id, missing_actor_ids, since_turn}`                                                                                                                                                                                                                       | Phase 1 (d)          |
| `narrative_systems.html`                    | Letzter Resolver-Output `semantic_action.{resolved_target_type, resolved_target_id, canon_safety, canonical_risk, affordance_status, action_commit_policy}`; letzter `narrator_consequence_packet.{source, requires_model_realization}` und ob daraus ein sichtbarer narrator-Block wurde         | Phase 1 (b), 1.d.0   |
| `narrative_systems.html`                    | Souffleuse-Strom mit Funktion (Bewertung/Affekt/Abwägen/…), Charakter-Voice-Profil-ID, Druck-Eskalations-Stufe                                                                                                                                                                                     | Phase 2 §5           |
| `runtime_ledger.html`                       | Neue Aspekt-Reihen aus `RuntimeAspectLedger` für Director-State, social_wait_indicator, Souffleuse-Funktion, off-stage Π27/Π1-Updates                                                                                                                                                              | Phase 1 + Phase 2    |
| `live_runtime.html`                         | Director-Pulse-Trigger pro Tick (Quelle: Spieler-Input / Motivations-Schwelle / State-Change); Cut-In-Ereignisse (Block-Type, Em-Dash vs. skip-to-end); Block-Stream-Bus-Aktivität                                                                                                                | Phase 2 §4.1         |
| `traces_observability.html`                 | Langfuse-Spans für neue Director-Tool-Calls (Souffleuse-Komposition, Motivation-Score, Off-Stage-Generierung); welche Π aus Table B wurden pro Turn konsultiert                                                                                                                                   | Phase 1 + Phase 2    |
| `history_events.html`                       | Off-Stage-Updates (Π27 `relationship_dynamics_events`, Π1 hierarchical-memory Einträge) während Spieler-Abwesenheit                                                                                                                                                                                | Phase 2 §4.4         |

**Was das Panel pro Session live zeigt:**

| Block | Quelle | Zweck |
|-------|--------|-------|
| Aktueller Canonical-Pointer | `session.canonical_step_id` | Wandert er? Bleibt er bei mundaner Aktion auf Step? |
| Director-State | `director_state.gathering_paused = {step_id, missing_actor_ids, since_turn}` | Schaltet `gathering_paused` korrekt? Wann zurück? |
| Letzter Resolver-Output | `semantic_action.{resolved_target_type, resolved_target_id, canon_safety, canonical_risk, affordance_status, action_commit_policy}` | Greift der Possibility/Morality-Pfad? Liefert er bei Bewegung eine `target_location`? |
| Letzter `canonical_path_effect` | aus committed graph_state | Propagiert `hold_current_step` durch? |
| Letzter `narrator_consequence_packet` | `source`, `requires_model_realization`, ob ein sichtbarer narrator-Block daraus wurde | Schließt sich Baustelle (b) live? |
| Souffleuse-Strom (letzte N Blocks) | aus committed blocks-Vertrag | Funktion, Charakter-Voice, Pressure-Eskalations-Stufe (sobald §5 implementiert) |
| Capability-Komposition pro Turn | welche Π aus Table B wurden konsultiert | Macht der Director das, was er soll? (Beobachtung, kein Schalter) |

**Quellen, die das Panel anzapfen kann (bereits existent):**
- `RuntimeAspectLedger` (alle Π-Aspekte werden hier persistiert)
- `operator_diagnostics_routes` (Π42 Capability Matrix Eintrag)
- `operator_turn_history_service` (Π38)
- Langfuse-Traces (Π43)
- `manager.py` Session-State (`session.canonical_step_id`, `narrative_streaming_active`, etc.)

**Wichtig (Entwicklungs-Disziplin):**

- Diagnose-Erweiterungen sind **Inspektion**, nicht **Kontrolle**. Keine Buttons, die Director-State, Π-Aspekte, Pointer oder Resolver-Output manipulieren. Beobachten, nicht eingreifen — Π39 (Operator override) ist eine separate, hier nicht beanspruchte Capability.
- **Pro neuer Sub-Phase wird die zugehörige UI-Erweiterung gleich mit ausgeliefert.** Eine Sub-Phase ohne sichtbare Diagnose gilt nicht als „fertig". Das schließt rückwirkend auch heute schon existierende, aber nicht-diagnostizierte Achsen ein — die Implementierung soll die UI sukzessive nachholen.
- Die Headless-Tests (§3 vorherige Sub-Sektionen) **bleiben** als CI-Regressionsgate erhalten — die UI-Erweiterung ist live-diagnostisches Werkzeug, kein Test-Ersatz.
- UI ist in **DE oder EN** anzeigbar — Display-Sprache der UI, nicht der Session.
- Die obige Zuordnungstabelle ist **Anhalt**, nicht Spezifikation. Die endgültige Verteilung wird beim Implementieren entschieden, basierend darauf, welcher bestehende UI-Bereich die nahestehende thematische Heimat ist.

**Akzeptanz Phase 1 als Ganzes:**

1. Alle fünf Headless-Tests (oben in 3.x aufgelistet) grün.
2. Manueller Browser-Spielcheck über die in §3.1 illustrierten Aktion-Klassen ohne Auffälligkeiten — beobachtet *über* die erweiterten Diagnose-Seiten der world-engine UI (nicht nur die Player-UI).
3. ADR-0057 (canon-safe player freedom) akzeptiert und gemerged.
4. Diagnose-Erweiterungen für die in der Tabelle genannten Felder sind live verfügbar in den jeweiligen world-engine UI-Seiten für eine laufende GoC-Session.

### 3.6 PR-Schnitt und ADR-Plan für Phase 1

**Entscheidung (2026-05-19):** Drei thematische PRs in fixer Reihenfolge plus zwei ADR-Akzeptanzen.

| PR | Inhalt | Sub-Phasen | Tests | Diagnose-Erweiterungen |
|----|--------|------------|-------|-------------------------|
| **PR-A** | **Resolver-Vertrag schließen.** Resolver liefert zuverlässig `resolved_target_type: "location"` + `resolved_target_id` bei Bewegungs-Aktionen — semantisch durch LLM, *kein* Verb-Whitelist. | 1.d.0 | `test_resolver_movement_target_location_live.py` (paraphrasierte DE-Inputs aus verschiedenen Sprachregistern; Assertion auf Pfad-Eigenschaften, nicht Input-Strings) | `narrative_systems.html` |
| **PR-B** | **Live-Effekt-Propagation.** Narrator-Konsequenz bei `requires_model_realization: true` → sichtbarer narrator-Block im Stream; `canonical_path_effect: hold_current_step` propagiert durch graph_state und greift bei `_turn_holds_canonical_path_for_free_player_action`. | (b), (c) | `test_narrator_realization_mundane_inference_live.py`, `test_canonical_path_held_on_free_action_live.py` | `narrative_systems.html`, `runtime_status.html` |
| **PR-C** | **Director-Pause-Modus.** Director-State `gathering_paused`, Vergleichsfunktion `compute_gathering_state`, Beat-Konsum-Gate im LDSS/NPC-Agency-Builder, Narrator-Reaktions-Hook für Pause-Übergang. | 1.d.1, 1.d.2, 1.d.3, 1.d.4 | `test_director_gathering_paused_state_live.py`, `test_director_gathering_paused_recovery_live.py` | `diagnostics.html`, `narrative_systems.html`, `runtime_ledger.html` |

**Reihenfolge ist fix:** PR-A → PR-B → PR-C. Ohne sauberen Resolver-Output (PR-A) bricht PR-B und PR-C im Live-Test mit garbage. PR-C ist die größte Neuentwicklung (Director-State-Achse) und baut auf beide Vorgänger auf.

**ADR-Schnitt:**

- **ADR-0057** (canon-safe player freedom — heute Draft in `docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md`): **Akzeptanz vor PR-A-Merge**. Liefert den Vertragsboden für PR-A und PR-B.
- **ADR-0061 (neu) — „Director-Pause-Modus bei Versammlungs-Unterbrechung":** **mit PR-C zu liefern**. Dokumentiert die `gathering_paused`-State-Achse, die `compute_gathering_state`-Vergleichsfunktion, das Beat-Konsum-Gate und den Narrator-Reaktions-Hook. Eigenständig — *kein* Vorgriff auf ADR-0058 (Phase 2). Phase 1 baut den Discriminator, Phase 2 baut die Pulse-Mechanik darüber.

**Jeder PR ist self-contained verifizierbar:** PR-A grün = Resolver liefert was er soll; PR-B grün = Effekt-Propagation funktioniert; PR-C grün = Director-Pause läuft live. Nach PR-C ist Phase 1 abgeschlossen und Phase 2 (ADR-0058 / ADR-0059 / ADR-0060) darf beginnen.

### 3.7 Was Phase 1 *nicht* tut

- Keine NPC-Pulse-Mechanik. NPCs reagieren in Phase 1 ausschließlich innerhalb des bestehenden Turn-Cycles auf Spieler-Inputs. Vollständige Autonomie/Koexistenz ist Phase 2.
- Keine Änderung am Narrator-Pfad (Turn 0). Bleibt wie ist.
- Keine Pointer-Repair-Logik in `_execute_opening_locked`. Bleibt wie ist.
- Keine Player-seitige UI-Erweiterung. Das Diagnose-Panel sitzt in der world-engine UI (Operator/Inspector-Surface), nicht im Player-Frontend.

---

## 4. Phase 2 — NPC + Story zuschalten (Vorschlag, ADR-pflichtig)

Erst beginnen, wenn Phase 1 live grün ist. Phase 2 ist *kein* Refactor des Bestehenden, sondern eine **neue Achse** über dem Turn-Cycle.

### 4.1 Design-Kernanforderungen aus der Grill-Sitzung

1. **Spieler kann jederzeit eingreifen.** Keine „NPC-Bündel" mehr; kein Warten auf Ruhepunkt-Signal als Voraussetzung für Eingabe.
2. **Blöcke kommen einzeln, nicht im Bündel.** Ein Block pro Tick, mit klarer typewriter-Lieferung.
3. **NPCs handeln aus Motivation, nicht aus Skript-Zwang.** Wenn der Spieler den Raum verlässt, *kann* (Wahrscheinlichkeit aus Pressure-Profile + Interaction-Patterns) ein NPC folgen — oder nicht. NPCs können in der Abwesenheit des Spielers miteinander interagieren (Beispiel: Alain + Annette im Bad). **NPCs haben dieselbe Aktion-Freiheit wie der Spieler** (siehe §2.1 Akteurssymmetrie): sie dürfen mundane Eigenaktionen ausführen (in die Küche gehen, etwas suchen, etwas anschauen, sich hinsetzen, Wasser einschenken), genauso wie der Spieler. NPCs sind nicht „stehende Dialog-Wartepunkte" während Kanon-Pausen — sie sind Akteure mit voller Aktion-Range innerhalb von Possibility × Morality.
4. **Der Director dirigiert den Tick.** Der Pulse ist **kein** externer Engine-Takt, der den Director konsumiert — der Director *ist* die Quelle des Ticks, weil er das gesamte Szenen-Wissen hält (Anwesenheit, Pressure-Profile, Beat-Liste, dramatische Lage, Spieler-Modus). Ticks sind ereignisgetrieben mit Mindest-Cooldown: ein Tick feuert, wenn (Spieler-Input ankommt) ∨ (Motivations-Score eines NPC eine Schwelle überschreitet) ∨ (State-Change wie `gathering_paused`-Übergang). Pro Tick wird *höchstens ein Block* emittiert.
5. **Stille ist eine aktive Director-Anordnung**, keine Lücke. Wenn der Director nichts motiviert, dann tickt nichts — und der Spieler sieht eine ruhige Szene. „Nichts passieren lassen" ist eine gültige, dramaturgisch begründete Wahl, nicht ein Fallback-Verhalten.
6. **Der Director arrangiert über die Capability-Matrix.** Quelle: `docs/MVPs/capability_matrix_status_and_adr_relations.md` Table B. Der Director ist der „Director der Szene"; er konsultiert / komponiert pro Tick aus den implementierten Capabilities (Π1 hierarchical memory, Π7 multi-agent NPC, Π11 scene energy, Π14 silence, Π16 dramatic irony, Π18 pacing rhythm, Π19 subtext, Π22 social pressure, Π27 relationship dynamics, Π31 momentum, u. a.) genau die Mischung, die zur dramatischen Lage passt. Er erfindet **nichts an der Capability-Matrix vorbei** — und nutzt umgekehrt **keine Capability außerhalb ihrer dokumentierten Maturity-Grenze**.
7. **Souffleuse im Modus-Spektrum** (siehe §5): Pressure ist nur ein Modus; in ruhigen Phasen spricht sie in Charakterstimme als „eigenes Ich" des Spielers. Sie duzt den Spieler, weil man sich duzt, wenn man mit sich selbst spricht.
8. **Keine Hardcoding-Lösungen** — Motivation, Folgen-oder-nicht, Block-Auswahl, Tick-Trigger-Logik, Stille-Anordnung, Capability-Komposition: alles semantisch / AI-gestützt / principled-deterministisch.

### 4.2 Subsysteme, die neu / erweitert werden müssen (Skizze)


| Subsystem                     | Zweck                                                                                    | Heute                                                            | Phase 2                                                                                                                                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Director-getriebener Tick** | Pulse für autonome NPC-Initiative — *vom Director emittiert*, nicht vom Engine-Scheduler | nicht vorhanden                                                  | neu: Director ist Quelle der Ticks; er entscheidet Tick-Trigger (Input ∨ Motivations-Schwelle ∨ State-Change) und Stille-Anordnung; Mindest-Cooldown aus `module.yaml.pacing_rhythm`           |
| **Motivation-Score**          | Entscheidet, *ob* ein NPC im Tick handelt                                                | Initiative-Liste wird vom LDSS-Plan eröffnet                     | neu: on-demand-Score (kein Polling) aus Pressure-Profile, Interaction-Pattern, Relationship, dramatischer Lage; AI-gestützte oder principled-deterministische Bewertung — ADR-0059 entscheidet |
| **Block-Stream-Bus**          | Ein Event-Stream für Narrator/Actor/Souffleuse/Spieler-Input                             | Turn-basiert (alle Blöcke eines Turns als Bündel)                | neu: ein Block = ein Event; Spieler-Input ist gleichberechtigtes Event; kein „streaming_active"-Lock mehr                                                                                      |
| **Player-Cut-In-Handling**    | Spieler darf einen NPC-Block unterbrechen                                                | Eingabe puffert via `queue_player_input`, geöffnet bei Ruhepunkt | neu: Block-Type-abhängig — `actor_line` → Em-Dash-Cut, andere Lanes → skip-to-end; danach Director-Pause + NPC-Plan-Re-Evaluation                                                              |
| **NPC-Folge-Entscheidung**    | Folgt NPC dem Spieler? Reagiert? Bleibt?                                                 | nicht modelliert                                                 | neu: semantische Entscheidung pro Tick: aus Relationship, Pressure-Profile, sozialer Lage und Pfad-Kontext                                                                                     |
| **Souffleuse-Modus-Wahl**     | Pressure vs. „eigenes Ich" vs. Stille                                                    | heute: nur Pressure-Cues an Step-Markern                         | neu: Modus aus Lage (Allein/Mit-Charakter/Versammlung) + Spieler-Sprachstil + ADR-0056-Vertrag                                                                                                 |


### 4.3 Verträge, die ADR-pflichtig sind

Phase 2 berührt mehrere Verträge gleichzeitig — vermutlich **drei neue ADRs**:

- **ADR-0058 (Vorschlag): Director-Driven Pulse und Block-Stream-Bus.** Definiert: (i) Director ist die Quelle der Ticks (kein externer Scheduler); (ii) Tick-Trigger-Bedingungen (Spieler-Input ∨ Motivations-Schwelle ∨ State-Change) mit Mindest-Cooldown aus `pacing_rhythm` (Π18); (iii) Stille als aktive Director-Anordnung; (iv) Block-Stream-Bus mit Block-pro-Tick statt Bündel; (v) Player-Cut-In-Semantik (Block-Type-abhängig); (vi) **Capability-Komposition pro Tick** — der Director arrangiert die zu konsultierenden Capabilities aus Table B der Capability-Matrix gemäß dramatischer Lage. Berührt MVP3 (LDSS) und MVP4 (Diagnostik) — beide Verträge bleiben, aber Streaming-Modell wandelt sich von Bündel zu Tick.
- **ADR-0059 (Vorschlag): Semantischer NPC-Motivation-Score (principled-deterministisch, pro NPC).** Konkretisiert (2026-05-19):
  - **Berechnungs-Methode:** principled-deterministische Funktion über strukturierte Capability-Outputs — `score(npc) = f(Π11 scene_energy, Π22 social_pressure, Π27 relationship_axis_pressure für npc, Π31 narrative_momentum, npc_pressure_baseline aus characters/details/actor_pressure_profiles.yaml)`. Kein AI-Judge-Call pro Tick. Inputs sind semantisch erzeugt (alle Π sind implemented bounded contracts); Aggregation ist transparent. Gewichte aus `module.yaml.runtime_intelligence.npc_motivation_score` (neues Modul-Feld), **nicht** hardcoded.
  - **Granularität:** pro NPC eigener Score. Director vergleicht alle anwesenden NPC-Scores pro Tick-Evaluation; der NPC mit dem höchsten Score über Schwelle wird zum Sprecher dieses Ticks. Wenn keiner über Schwelle: Stille (Director-Anordnung).
  - **Schwelle:** `pacing_rhythm`-Cadence-Profil aus `module.yaml.pacing_rhythm` × per-NPC-Modulator aus `actor_pressure_profiles`. Beide Quellen bereits im Content vorhanden; keine Default-Konstante im Code, keine `if npc_id == "alain" then ...`-Modulation.
  - **NPC-Folge-Entscheidung:** *keine* eigene Subsystem-Achse. Die „folgen / lokal reagieren / sprechen / Geste / mundane Eigenaktion / schweigen"-Wahl ist eine **Aktion-Wahl** im Director-Action-Komposit-Tool, das den motivierten NPC dem Tick zuordnet (siehe ADR-0058 Capability-Komposition + ADR-0060 Souffleuse-Komposition als analoge Muster). **Akteurssymmetrie:** NPCs haben dieselbe Aktion-Range wie der Spieler (mundane Bewegung, Objekt-Interaktion, Wahrnehmung) — der Action-Komposit-Pfad respektiert Possibility × Morality (§2.1) und nutzt für mundane NPC-Aktionen denselben semantischen Resolution-Vertrag wie für Spieler-Aktionen. Inputs für die Aktion-Wahl: Π7 long-horizon NPC-Plan, Π27 relationship attachment axis, `interaction_patterns`, `actor_pressure_profiles`, aktuelle Schauplatz-Topologie aus `actor_locations`, Π23 agency_preservation (verhindert Koerzion gegen Spieler-Lane).
  - **Initiative bei mehreren motivierten Akteuren:** Initiative im Rollenspiel-Sinn — *wer ist gerade am schnellsten*. Pro Tick berechnet der Director die Motivation-Scores aller anwesenden NPCs (plus aktuellen Spieler-Input falls vorhanden); **der mit dem höchsten Score hat Initiative für diesen Tick** und ist der Sprecher / Aktor. Initiative ist **kein festgeschriebenes Roster**: sie wechselt von Tick zu Tick, basierend auf der aktuellen Lage. Die zeitliche Sequenz dieser Initiative-Übernahmen ist die Reihenfolge, in der sich die Szene entfaltet. **Der Spieler nimmt Initiative durch Cut-In** (siehe §4.1 Punkt 1 + Cut-In-Semantik in §4.2 Player-Cut-In-Handling) — auch das ist konsistent mit Akteurssymmetrie. **Keine** Reihenfolge-Queue, Roundtable-Logik oder feste Sprecher-Slots — das wäre Bündel-Reproduktion durch die Hintertür.
- **ADR-0060 (Vorschlag): Souffleuse als innere Stimme — Komposition, Druck-Eskalation, Charakter-Wortschatz.** Erweitert ADR-0056 um (a) die Souffleuse als inneren Dialog-Strom mit reicher Funktionsbreite (Bewertung, Selbstkommentar, Fluchen, Abwägen, Erinnerung, Druck, Motivations-Brücke); (b) **semantische Lage-Komposition** statt If-then-Mapping über Table-B-Capabilities — der Director konsultiert Π14/Π11/Π22/Π27/Π19/Π31 als *Werkzeuge*, nicht als *Schalter*, und entscheidet über ein dediziertes Komponier-Tool, *was* die Souffleuse jetzt sagen soll (oder schweigt); (c) Druck-Eskalation als dramaturgische Schleife (Director macht Souffleuse präsenter, wenn der Spieler sich verweigert, als Pendant zu NPC-Aktion); (d) **Charakter-Wortschatz-Treue** über `characters/voices/character_voice_*.yaml`, niemals generisch; (e) Duzen immer (innere Stimme duzt sich); (f) Produktions-Gate über model-graded judge, nicht String-Pattern-Liste.

### 4.4 Off-Stage-NPC-Verhalten ohne Spieler-Beobachtung (Beispiel: Bad-Szene)

**Beispiel-Lage:** Alain und Annette sind im Bad; der Spieler ist im Wohnzimmer oder in der Küche.

**Entscheidung (entspricht Variante (b) der Grill-Sitzung, erweitert):** Der Director generiert *atmosphärische Hinweise* im Spieler-Raum (motivations-getrieben, nicht regelmäßig) **und** darf innerhalb des Kanons **kreativ frei erfinden**, was off-stage geschieht. „Kreativ frei" heißt: andere stimmungs-/beziehungs-kompatible Wendungen sind erlaubt; das Stimmungsregister bleibt aber kohärent (z. B. **nicht** plötzlich heitere Versöhnung in einer Eskalations-Szene; wohl aber stille Verbundenheit, müder Galgenhumor, gegenseitige Erschöpfung etc.).

**Wo die Erfindung verbuchen?** Nicht in einem neuen Freitext-Memo, sondern in den bereits existierenden Capability-Schichten:

- **Π27 Relationship dynamics** (`relationship_state_engine.py`, `RuntimeAspectLedger.relationship_state`): bounded pair-states, axis-states, transition events. Off-Stage-Beziehungs-Updates landen hier als reguläre `relationship_dynamics_events` — bereits validiert, bereits versioniert, bereits über MCP/Langfuse sichtbar. **Keine neue Schicht erfinden.**
- **Π1 Hierarchical memory** (`hierarchical_memory_contracts.py`, `StorySession.hierarchical_memory`): die session-lokale Gedächtnisschicht trägt den off-stage „shared moment". Der User-Hinweis „Gedächtnis ist noch nicht vollständig in NPCs und Interaktionskette integriert" benennt eine bekannte Lücke; Phase 2 schließt diese Lücke spezifisch für off-stage-Updates.
- **Π8 Branching simulation tree** (optional, dort wo sinnvoll): für „was *wäre* denkbar im Bad" kann der Director eine isolierte Simulation laufen lassen, ohne in canonical commit zu schreiben. Anwendungsfall begrenzt — meist reicht direkt eine Π27-/Π1-Eintragung.

**Was der Director arrangiert (Capability-Komposition pro Off-Stage-Tick):**
- **Π14 Silence / negative space** — entscheidet, ob ein atmosphärischer Hinweis *unterdrückt* werden soll (Stille als Anordnung).
- **Π11 Scene energy** + **Π22 Social pressure** — bestimmen, ob die dramatische Lage einen Hinweis rechtfertigt.
- **Π19 Subtext** + **Π16 Dramatic irony** — formen den Hinweis so, dass er Sub-Information trägt, ohne explizit zu werden.
- **Π23 Agency preservation** — schützt: kein NPC-Verhalten off-stage darf die Spieler-Lane koerzieren oder den Spieler zur Rückkehr zwingen.

**Harte Begrenzer:**
1. **Off-Stage-Updates dürfen niemals den Canonical-Path beeinflussen.** Kein Mandatory-Beat-Konsum, keine Step-Pointer-Bewegung, keine canonical `state_changes_committed` aus off-stage.
2. **Stimmungs-/Charakter-Kohärenz** ist Grundbedingung — geprüft durch existierende Validatoren der konsultierten Capabilities (Π10 voice_consistency, Π27 relationship transition validation, Π19 subtext sincerity band).
3. **Keine neuen Personen, Räume, plot-tragende Fakten off-stage.** `forbidden_scope` aus `player_freedom_policy.yaml` gilt für den Director ebenso wie für den Spieler.
4. **Atmosphärischer Hinweis im Spieler-Raum ist ein einziger Block pro Tick** — kein Off-Stage-Stream.

**Anti-Patterns:**
- Keine Enum-Liste „erlaubte off-stage Themen".
- Kein boolescher Flag `bonding_in_bathroom: true`. Stattdessen Π27-Transition-Event.
- Kein „erinnere Off-Stage-Inhalt explizit beim Wiedersehen". Das Capability-Stack (Π1 + Π27) liefert den Kontext implizit — der NPC-Agency-Builder reagiert semantisch.
- Kein Off-Stage-Tick alleine wegen Wall-Clock; nur motivations-getrieben.

**Akzeptanz-Skizze (illustrativ, keine Test-Fixture):** Spieler im Wohnzimmer, Alain+Annette gehen ins Bad. Über mehrere Spieler-Ticks hinweg: 0–2 atmosphärische `narrator`-Blocks im Wohnzimmer (motivations-getrieben). Im Director-State: ein oder mehrere Π27 `relationship_dynamics_events` über das Paar Alain↔Annette + eventuell ein Π1-Eintrag. Beim nächsten direkten Kontakt mit einem der beiden: spürbare semantische Resonanz im NPC-Verhalten (anderes Pressure-Profile, andere Body-Language-Beschreibung), ohne dass canonical_path oder Mandatory-Beats berührt wurden.

### 4.5 Phasen-Eintritts-Kriterium

Phase 2 startet erst, wenn:

- Phase 1 Live-Smoke-Tour (§3.1) komplett grün
- (b), (c), (d) Akzeptanz erfüllt
- Keine Regression in MVP3-Ruhepunkt-Tests (`world-engine/tests/test_mvp3_complete_integration.py`)

---

## 5. Souffleuse — innere Stimme des Spielcharakters

ADR-0056 D3 verbietet bereits Selbstreferenzen („Souffleuse:", „for this role", Identitätsliste). Phase 2 vertieft die Souffleuse von einer „Modus-Wahl mit drei Buckets" zu **einem inneren Dialog-Strom**.

### 5.1 Konzept — was die Souffleuse *ist*

Die Souffleuse ist die **innere Stimme** des Spielcharakters. Menschen sprechen ständig mit sich selbst — bewerten, fluchen, schimpfen mit sich und mit anderen, wägen ab, erinnern sich, spüren Druck. Die Souffleuse trägt genau diesen Strom in das Spiel.

**Funktionen, die die Souffleuse leisten kann (illustrativ, keine Enum-Liste):**

- *Bewertung der Lage* — „Was für ein Arsch.", „Er meint das ernst, oder?"
- *Selbstkommentar / Selbstbeschimpfung* — „Das hättest du nicht sagen sollen.", „Reiß dich zusammen."
- *Fluchen / Affekt-Ausdruck* — „Verdammt.", „Bitte nicht jetzt."
- *Abwägen vor einer Aktion* — „Sag was. Oder lieber nicht. Beobachte erst."
- *Erinnerung* — „Wie damals mit deiner Mutter. Du wirst nicht wieder leise sein."
- *Druck spürbar machen* — körperlich, emotional, ohne Mechanik zu erklären.
- *Motivations-Brücke* — wenn der Director will, dass der Spieler aktiv wird (statt einen NPC zu pushen), **schaltet die Souffleuse aktiver**, teilt mehr von dem mit, was der Charakter gerade denkt/fühlt — bis der Spieler die Motivation findet, selbst zu handeln.

### 5.2 Lage-Discriminator — Komposition statt Mapping

**Entscheidung (entspricht Variante (d), erweitert):** Die Modus-Wahl ist **keine deterministische `if Π14 then silence`-Schichtung** — das wäre eine versteckte Whitelist über Capability-IDs. Stattdessen:

Der Director konsultiert pro Tick die relevanten Capabilities aus Table B (Π14 silence_negative_space, Π11 scene_energy, Π22 social_pressure, Π27 relationship_state, Π19 subtext, Π31 narrative_momentum, plus Lage aus `actor_locations` + `named_characters`), erhält daraus ein **strukturiertes Lagebild**, und entscheidet **semantisch** — durch ein dediziertes Director-Tool — *was* die Souffleuse jetzt sagen soll, *in welcher Tonlage*, *mit welcher Funktion* (Bewertung, Selbstkommentar, Abwägen, Affekt, Motivations-Push) — oder ob sie schweigt.

**Wenn dieses Director-Tool für die semantische Souffleuse-Komposition heute noch nicht existiert, wird es geschaffen** (Phase 2 / ADR-0060). Der Director ist die *Stelle*, an der die Entscheidung fällt; das Tool ist sein Komponist.

### 5.3 Druck-Eskalation als dramaturgische Schleife

Wenn der Spieler sich „verweigert" (keine Eingabe, oder Eingaben, die den Lagedruck weiter aufstauen), darf der Director **mehr Druck erzeugen**:

- Die Souffleuse wird *präsenter* — sie spricht häufiger, deutlicher, dringender.
- Sie teilt **mehr** von den aktuellen Gedanken / Affekten / Erinnerungen des Spielcharakters mit.
- Das ist **dramaturgisch das Pendant zu einer NPC-Handlung**: statt dass Veronique drängt, drängt das eigene Innere des Charakters.
- Sobald der Spieler aktiv wird, lockert der Druck wieder (semantisch, kein Counter-Reset).

Dieser Druck-Loop ist **vom Director arrangiert**, nicht durch einen Timer oder eine `if turns_without_input > N`-Regel.

### 5.4 Wortschatz-Treue — Charakterstimme, nicht generisch

Die Souffleuse spricht **immer im Wortschatz und Register des aktuell gespielten Charakters** — Quelle: `content/modules/god_of_carnage/characters/voices/character_voice_*.yaml`. Spielt der Spieler Alain, klingt die innere Stimme nach Alain (knapp, juristisch-gefärbt, ungeduldig). Spielt er Annette, klingt sie nach Annette (kontrolliert-höflich mit aufsteigender Brüchigkeit). Spielt er Michel, nach Michel. Spielt er Veronique, nach Veronique. **Niemals generisch.** Niemals außenstehend („Du solltest jetzt…"). Immer aus dem Innen.

**Duzen ist immer** — unabhängig vom Charakter. Begründung (User 2026-05-19): „Sie duzt den Spieler, weil man sich duzt, wenn man mit sich selbst spricht."

### 5.5 Anti-Patterns (keine Hardcoding-Lösungen)

- **Keine** Step-Enum-Modus-Mapping (`if step_id == "armed_vs_carrying" then mode=pressure`).
- **Keine** Tonlage-/Funktion-Whitelist (`SOUFFLEUSE_FUNCTIONS = {"evaluate", "curse", ...}`).
- **Keine** Capability-ID-→-Modus-Tabelle im Director-Code (`{Π14: "silence", Π11: "pressure", ...}`). Das Komponieren über Table B ist semantisch, nicht ein Lookup. Capabilities sind *Werkzeuge*, nicht *Regeln*.
- **Keine** Charakter-spezifischen Souffleuse-Vorlagentexte. Charakterstimme wird *generiert* aus `character_voice_*.yaml` + Lage, nicht aus einem Satzbaukasten.
- **Keine** Druck-Eskalation per Schwellen-Counter („nach 3 Turns ohne Eingabe wird Souffleuse lauter"). Eskalation ist Director-Tool-Entscheidung aus dramaturgischer Lage.
- Validator gegen „for this role", „you are…", „Souffleuse:" bleibt als **Smoke-Regression** legitim, ist aber *nicht* das Produktions-Gate. Produktions-Gate ist ein model-graded judge mit Vertrag aus ADR-0056 D3 + ADR-0060 (neu, siehe §4.3).
- Sprachadapter (`story_runtime_core/language_adapter.py`, in dieser Branch angefasst): keine lokalisierten Vorlagentexte als Quelle — EN-Quellfakten → Output-Sprache via Prompt. Charakterstimme über Charakter-Voice-Profil, nicht über Sprachadapter.

---

## 6. Was dieser Plan *nicht* ist

- **Kein Patch.** Keine konkreten Diffs.
- **Kein ADR.** Phase 2 verlangt drei neue ADRs (4.3); Phase 1 verlangt vermutlich keinen neuen ADR, sondern verifiziert / schließt eine bestehende Lücke im Vertrag ADR-0057 (canon-safe player freedom).
- **Keine Pointer-Repair-Aktion** in `_execute_opening_locked` oder in der Modus-Auswahl. Steps 001–005 bleiben wie sie sind.
- **Keine MVP-Verschiebung.** MVP3 (LDSS), MVP4 (Diagnostik) bleiben Voraussetzung; Phase 2 ergänzt deren Streaming-Modell, ersetzt sie nicht.

---

## 7. Offene Fragen für den Autor (vor Phase-2-Start zu beantworten)

1. **Tick-Frequenz:** ~~offen~~ **entschieden (2026-05-19):** Director ist Quelle der Ticks (kein externer Scheduler). Ereignisgetrieben mit Mindest-Cooldown. Stille ist aktive Anordnung. Cooldown-Default aus `module.yaml.pacing_rhythm`.
2. **Spieler-Cut-In-Semantik:** ~~offen~~ **entschieden (2026-05-19):** Block-Type-abhängig.
   - `actor_line` → **abrupter Cut mit sichtbarem Em-Dash** (dramaturgisch wirksame Charakter-Unterbrechung)
   - `narrator` → **skip-to-end** (Welt-Beschreibung wird nicht „unterbrochen", nur schneller fertig)
   - `souffleuse` → **skip-to-end** (Innenstimme unterbricht sich nicht selbst)
   - `actor_action` → **skip-to-end** (begonnene Geste „passiert", ist nicht semantisch unterbrechbar)
   - Director-Pause direkt nach Cut, dann Re-Evaluation des NPC-Plans im Lichte des neuen Spieler-Inputs.
   - Block-Type ist ein Vertragsbegriff aus `visible_scene_output.blocks.v1` — die Unterscheidung lebt im Daten-Modell, nicht in einer Hardcode-Whitelist.
3. **NPC-Autonomie ohne Spieler-Beobachtung:** ~~offen~~ **entschieden (2026-05-19):** Atmosphärische Hinweise im Spieler-Raum (motivations-getrieben), Director darf innerhalb des Kanons kreativ frei erfinden, State-Updates fließen über bereits existierende Capabilities (Π27 Relationship dynamics, Π1 Hierarchical memory, optional Π8 Simulation). Off-Stage berührt nie den Canonical-Path. Siehe §4.4.
4. **Souffleuse-Modus „Eigenes Ich" — Lage-Discriminator:** ~~offen~~ **entschieden (2026-05-19):** Capability-Komposition statt Mapping. Director konsultiert Π14, Π11, Π22, Π27, Π19, Π31 + Lage-Topologie als *Werkzeuge* (nicht If-then-Schalter); ein dediziertes Komponier-Tool entscheidet semantisch, was/ob die Souffleuse spricht. Souffleuse ist **innere Stimme** mit voller Funktionsbreite (Bewertung, Affekt, Abwägen, Erinnerung, Druck, Motivations-Brücke); Wortschatz aus `character_voice_*.yaml`; duzt immer. Druck-Eskalation als Director-getriebene dramaturgische Schleife. Siehe §5.
5. **Phase 1 Live-Verifikation — Tooling:** ~~offen~~ **entschieden (2026-05-19):** **Systematische Erweiterung der bestehenden Diagnose-Seiten** der world-engine UI (`world-engine/app/web/templates/ui/`: `diagnostics.html`, `live_runtime.html`, `narrative_systems.html`, `runtime_ledger.html`, `traces_observability.html`, `history_events.html`, `runtime_status.html` u. a.). Nicht ein einzelnes neues Sammelpanel — jedes neue Diagnose-Feld zieht thematisch in die passende existierende Seite. Speist sich aus `RuntimeAspectLedger`, `operator_diagnostics_routes`, `operator_turn_history_service`, Langfuse-Traces, Session-State. Inspektion, kein Eingriff. Pro Sub-Phase wird die zugehörige UI-Erweiterung gleich mitgeliefert. Headless-Regressionstests bleiben parallel als CI-Gate. Siehe §3.5.

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
14. **`docs/MVPs/capability_matrix_status_and_adr_relations.md`** (Capability-Matrix Table B — Quelle für die vom Director arrangierbaren Capabilities; insbesondere Π1, Π7, Π8, Π11, Π14, Π16, Π18, Π19, Π22, Π23, Π27, Π31)

---

*Überarbeitet am 2026-05-19 nach Grill-Sitzung. Vorgängerstand ersetzt: die dortige Diagnose-Sektion (Hypothesen A/B/C) war auf den falschen „Bug" ausgerichtet — Veronique-Stopp ist gewollter Testpunkt. Sämtliche „if step.mode in {...}"-Vorschläge entfernt: kein Hardcoding (siehe MEMORY: feedback_no_static_gating).*