# Plan: Resolver → Director → Narrator (Thin Path)

**Stand:** 2026-05-19
**Verfasser-Kontext:** Vorlauf-Arbeit zu `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`. Diese Datei beschreibt die *Architektur-Korrektur*, die der freien Aktion zugrunde liegen muss, bevor NPC-Pulse, Director-Pause-Modus oder Co-Existenz drauflegen.
**Live-Reproduktion:** vier Langfuse-Traces vom 2026-05-18/19, Session `104422554784410f92f4178c9299c335`.

---

## 0. Was dieser Plan beantwortet — und wieso

Trace-Evidenz zeigt: das Opening (Veronique-Stopp, Steps 001–005) funktioniert. Sobald der Spieler **frei** handelt („Gehe in die Küche", „Ich gehe ins Bad", „Was finde ich in der Küche?"), bricht der sichtbare Output strukturell zusammen — entweder Englisch-Bleed, leerer Block oder Network Error.

Die Ursache ist **nicht** der Resolver, **nicht** der Content, **nicht** die Übersetzungs-Ingress (alles vorhanden und korrekt befüllt). Die Ursache ist die **Routing-Architektur**: ein Knoten-Schalter zwischen einem deterministischen Short-Path und einem monolithischen `full_pipeline`, beide an der falschen Stelle zuständig.

**User-Anforderung in einem Satz:** Resolver übersetzt + klassifiziert. Director entscheidet kombinatorisch, was passiert. Narrator überbringt. Keine andere Logik dazwischen.

**Kern-Verdikt:** `full_pipeline` ist *als monolithischer Pfad* der Fehler. Sie muss in eine **Capability-Bibliothek** zerlegt werden, aus der der Director per Turn das wählt, was gebraucht wird. Niemand ruft sie noch „als Ganzes" auf.

---

## 1. Trace-Diagnose (verifiziert)

Quelle: vier Trace-JSONs (siehe `\trace-ff646a6c…`, `\trace-fe778b…`, `\trace-d642b3…`, `\trace-9cafc9…`). Session-Sprache: `de`/`de`.

### 1.1 Ablauf je Trace

| Trace | Eingabe | turn_status | Symptom |
|---|---|---|---|
| `ff646a6c…` | session.create | runtime_engine_initialized | Opening fein |
| `fe778b…` (T1) | „Gehe in die Küche" | committed | **Englisch-Bleed**: „A connected domestic service room…" |
| `d642b3…` (T2) | „Was finde ich in der Küche ?" | rejected_recoverable | **Validator-Reject** → kein Output / Netzfehler |
| `9cafc9…` (T3) | „Ich gehe ins Bad" | committed | **Englisch-Bleed**: „A private regrouping space…" |

### 1.2 Mechanik T1/T3 (Englisch-Bleed)

- Router `_route_after_resolve_player_action` (`ai_stack/langgraph_runtime_executor.py:6374-6415`) wählt bei `commit_action`+`allowed/allowed_offscreen/partial` den deterministischen **Short-Path** „authoritative_action_resolution".
- `_authoritative_action_resolution_turn` (`ai_stack/langgraph_runtime_executor.py:6417-6440`) ruft `build_synthetic_generation_for_action_resolution(lang="de", …)`.
- Output stammt aus `narrator_consequence_plan.consequence_text` mit `source: "scene_affordance_detail"` und `requires_model_realization: False`.
- Inhalt kommt aus `entry_sensory_detail.{lang}` im `scene_affordance_model`, Fallback-Kette: `detail.get(lang) or detail.get("de") or detail.get("en") or row.get("description")`.
- `content/modules/god_of_carnage/locations/appartment_vallon/kitchen.yaml:7-10` hat **nur** `description:` auf Englisch, kein `entry_sensory_detail`-Block. → Fallback liefert englischen `description`-Text.
- Keine LLM-Realisierung. `selected_capabilities=[]`, `director_path_mode=None`, `narrator_path_selected=False`. Der Director ist **vollständig umgangen**.
- `visible_language_contract_pass=true` ist eine Lüge des Sprach-Validators, der nicht auf `consequence_text` schaut.

### 1.3 Mechanik T2 (Validator-Reject)

- Eingabe wird als `speech_like` erkannt (Frage) → Router zwingt auf **`full_pipeline`** (`langgraph_runtime_executor.py:6384`).
- Full-Pipeline läuft komplett durch (`route_model → invoke_model → validation → commit`).
- `validate_dramatic_irony_realization` (`ai_stack/dramatic_irony_runtime.py:668-701`) lehnt mit `dramatic_irony_hidden_fact_echo` ab.
- Frontend zeigt Network Error / Degraded Notice.

### 1.4 Was vorhanden ist und funktioniert

- Übersetzungs-Ingress `translate_player_input` (ADR-0054/0055, `langgraph_runtime_executor.py:405-438`).
- Semantische Klassifikation `interpret_input` (Speak/Act-Diskriminierung greift korrekt).
- Resolver `resolve_player_action` (`ai_stack/player_action_resolution.py`) liefert sauberes `player_action_frame` + `affordance_resolution`.
- Zwei grüne Karten `player_input` + `player_input_outcome` in `world-engine/app/story_runtime/manager.py:7615-7671`. Frontend-Renderer in `frontend/tests/test_block_renderer.js:286-293`.
- Vertrag: `docs/ADR/adr-0034-player-facing-narrative-shell-contract.md:32`.

### 1.5 Was *fehlt* (Architektur-Lücke)

- **Director ist im Player-Turn nicht eingebunden.** Heutige Director-Logik (`ai_stack/scene_director_goc.py`) läuft für NPC-Auswahl und Szenen-Direction, *nicht* als Realization-Composer für Spieler-Aktionen.
- **`full_pipeline` ist monolithisch.** Capabilities werden nicht vom Director komponiert, sondern als feste Knoten-Folge konsumiert.
- **Keine direkte Resolver→Director→Narrator-Achse** für mundane Player-Aktionen.

---

## 2. Zielarchitektur

```
Player Input (DE/EN)
   │
   ▼
Resolver  ──  semantic_resolution_planner
   │         · übersetzt nach EN für interne Grundierung (ADR-0054)
   │         · klassifiziert: speech vs action, possibility, kanon_break
   │         · liefert: semantic_action, target, glück_disposition_input
   │         · MUSS richtig sein, darf nicht entscheiden
   ▼
Director  ──  director_realization_composer
   │         · entscheidet kombinatorisch: welche Capabilities für diesen Turn?
   │         · wählt realization_owner ∈ {narrator, actor_line}
   │         · entscheidet Glück (Erfolg/Teilerfolg/Misserfolg) semantisch
   │         · integriert relevante Validatoren VORNE als Entscheidungsinput
   │           (z. B. Wissensstand pro Actor aus dramatic_irony_record),
   │           NICHT als nachgelagerten Reject-Gate
   │         · output: realization_plan.v1
   ▼
Narrator/Actor-Line  ──  realize_via_capabilities
   │         · ruft genau die vom Director gewählten Capabilities
   │         · LLM-Realisierung in session_output_language
   │         · produziert visible_scene_output.blocks
   ▼
Visible Blocks
   · player_input              (verbatim)
   · player_input_outcome      (diegetische Realisierung)
   · narrator / actor_line     (Director-getriebene Realisierung)
```

### 2.1 Was passiert mit `full_pipeline`?

**Zerlegung in Capability-Bibliothek.** Heutige Knoten von `full_pipeline` (`route_model`, `invoke_model`, `validation`, `commit`, …) werden zu **diskreten, vom Director benannt aufrufbaren** Operationen. Es gibt keinen Pfad mehr, der „die ganze Pipeline" als feste Reihenfolge fährt. Der Director-Composer schreibt für jeden Turn eine kleine Liste, was er konkret braucht.

**Konsequenz:** Router-Entscheidung `_route_after_resolve_player_action` (`langgraph_runtime_executor.py:6374-6415`) wird gelöscht. Stattdessen: Resolver-Output geht direkt in `director_compose_realization`, dessen Output fährt dann `realize_via_capabilities`.

### 2.2 Verträge

| Vertrag | Pflichtfelder | Datei |
|---|---|---|
| `semantic_resolution_output.v1` | `semantic_action`, `player_input_kind`, `resolved_target_type/id`, `possibility`, `kanon_break: bool`, `kanon_break_reason: str\|null`, `glück_disposition_input` | `ai_stack/player_action_resolution.py` (Erweiterung) |
| `realization_plan.v1` | `realization_owner ∈ {narrator, actor_line, narrator+actor_line}`, `capabilities_selected: [str]`, `outcome_disposition: {success\|partial\|fail, reason}`, `language_target`, `visibility_constraints: [str]` | neu: `ai_stack/director_realization_composer.py` |
| `kanon_break_check.v1` | nur ein Feld: `is_kanon_break: bool` + `reason: str`. Definition: `is_kanon_break = true` nur wenn die Aktion das **Weiterspielen unmöglich macht** (physisch unmöglich, kriminell/böse, irreversibel verheerend). Reversible Veränderung ≠ Bruch. | Resolver-Output, Director-Konsum |

### 2.3 Was bleibt vom heutigen Stack

- `translate_player_input` (Ingress) — unverändert.
- `interpret_input` — unverändert.
- `resolve_player_action` — erweitert um `kanon_break`-Feld und `glück_disposition_input`, sonst unverändert.
- `_player_input_scene_blocks_for_story_window` (zwei grüne Karten) — unverändert.
- Frontend-Renderer — unverändert.
- ADR-0054/0055/0034 — unverändert.

Was *neu* gebaut wird: `director_realization_composer` + `realize_via_capabilities`.
Was *gelöscht* wird: `_route_after_resolve_player_action`, `_authoritative_action_resolution_turn`, `build_synthetic_generation_for_action_resolution` (für `commit_action+allowed/allowed_offscreen/partial`-Fälle).

---

## 3. Phasenplan

### PR-A — Bewegung über Resolver → Director → Narrator (Phase 1.a)

**Scope:** *Nur* Bewegung. Keine Objekt-Interaktion, keine Sachfragen, kein RAG, keine plausible_inference für Objekte.

**Akzeptanz live (Smoke, lokal über `docker-up.py`, Session DE/DE):**

1. „Gehe in die Küche" → sichtbarer **deutscher** `narrator`-Block, der die Bewegung beschreibt. Kein Englisch-Bleed.
2. „Ich gehe ins Bad" → idem.
3. „Ich gehe zurück ins Wohnzimmer" → idem, mit korrekter Rückkehr-Erwähnung.
4. „Ich schleiche in Richtung Küche" → idem, mit Glück-Färbung durch Director (z. B. „unbemerkt", „beobachtet").
5. „Ich gehe durch die Wand" → `kanon_break=true`, Resolver liefert `needs_clarification`, Director komponiert Klärungsblock (kein Englisch-Bleed, kein Network Error).
6. Beide grüne Karten erscheinen unverändert vor dem `narrator`-Block.

**Eingriffe (verbindlich):**

- [ ] **A-1** Resolver-Output um `kanon_break: bool` + `kanon_break_reason` erweitern. Datei: `ai_stack/player_action_resolution.py`. Definition strikt semantisch (kein Verb-Set, kein Raumset), gegen die Möglichkeit-/Moral-Achsen aus `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md` §2.1.
- [ ] **A-2** Neuer Modul `ai_stack/director_realization_composer.py` mit Funktion `compose_realization_plan(semantic_resolution_output, scene_context, session_languages) -> realization_plan.v1`. Innerhalb: semantische Auswahl (LLM-Call mit kleinem Director-Prompt, der Charakter/Druck/Possibility/kanon_break als Input bekommt). Keine Whitelist.
- [ ] **A-3** Neuer Graph-Knoten `director_compose_realization` in `ai_stack/langgraph_runtime_executor.py`. Edge: `resolve_player_action → director_compose_realization` (statt `_route_after_resolve_player_action`).
- [ ] **A-4** Neuer Graph-Knoten `realize_via_capabilities`. Konsumiert `realization_plan.v1`, ruft für PR-A genau eine Capability: `narrator.location_transition.describe` mit LLM-Realisierung in `session_output_language`.
- [ ] **A-5** Edge `director_compose_realization → realize_via_capabilities → commit`.
- [ ] **A-6** Lösche `_route_after_resolve_player_action` (`langgraph_runtime_executor.py:6374-6415`).
- [ ] **A-7** Lösche `_authoritative_action_resolution_turn` (`langgraph_runtime_executor.py:6417-6440`).
- [ ] **A-8** Lösche/Quarantäne `build_synthetic_generation_for_action_resolution` für `commit_action+allowed/allowed_offscreen/partial`. Falls für `needs_clarification`/`unknown_target` weiter gebraucht: behalten und klar einschränken.
- [ ] **A-9** Tests anpassen (kein Whitelist-Recovery): `ai_stack/tests/test_runtime_authority_aspects.py:497-587` und `ai_stack/tests/test_langgraph_runtime.py:643-660`. Neue Tests gegen `realization_plan.v1`-Eigenschaften, nicht gegen String-Fixtures.
- [ ] **A-10** Live-Smoke gegen die fünf Eingaben oben über `docker-up.py`. Per CLAUDE.md "No Mock Tests for Integration Features".
- [ ] **A-11** Diagnose-Feld `realization_plan` in `narrative_systems.html` ergänzen (per NPC_INTERACTION-Plan §3.5).

**Bewusst NICHT in PR-A:**

- Objekt-Interaktion („Mach das Licht an", „Schau in den Kühlschrank") — kommt in PR-A.2.
- Sachfragen („Was finde ich in der Küche?") — kommt in PR-A.3.
- RAG-Zugriff — kommt in PR-A.2.
- `dramatic_irony_hidden_fact_echo`-Verlagerung zum Director — kommt in PR-A.3 oder PR-B.
- Director-Pause-Modus aus NPC_INTERACTION-Plan §3.4 — kommt in PR-C.
- NPC-Pulse / Phase 2 — viel später.

**Risiken:**

- Tests in `test_runtime_authority_aspects.py`/`test_langgraph_runtime.py` brechen. Müssen umgeschrieben werden, *nicht* als Whitelist wiederhergestellt.
- LLM-Kosten pro Movement-Turn steigen (vorher 0 Token, jetzt ~1 kleiner Call für den Director + 1 für den Narrator). Akzeptiert.
- Wenn der Narrator-LLM down ist, bekommt der Spieler bei mundaner Bewegung einen Network-Error statt Englisch-Bleed. Das ist transparenter — beabsichtigt.

### PR-A.2 — Objekt-Interaktion + RAG + plausible Inferenz (Phase 1.b)

**Scope:** Mundane Interaktion mit benannten und plausibel-inferierten Objekten.

**Akzeptanz live:**

- „Mach das Licht an" → Director komponiert `narrator.environment_interaction` mit Glück-Disposition; kein Englisch-Bleed.
- „Schau in den Kühlschrank" → RAG-Lookup auf `content/modules/god_of_carnage/objects/appartment_vallon/kitchen/refrigerator.yaml`, sichtbarer DE-Output.
- „Hol mir Kekse aus dem Kühlschrank" → plausible_inference (Kekse nicht authored, aber mundan + canon-safe), Director komponiert Glück-Outcome („du findest welche", „nur eine Packung Cracker"), Narrator realisiert.
- „Ich zerschlage das Fenster" → `kanon_break_reason="irreversibel_situationsverändernd"` ODER Glück-Misserfolg via Director (Annette ist kein Hulk). Director entscheidet, ob es ein Bruch oder ein Fehlversuch ist.

**Eingriffe:**

- [ ] **A.2-1** Resolver-Erweiterung: RAG-Hook für mundane Objekte mit `target_resolution_source: ai_semantic_resolution.plausible_inference`. Quelle: `content/modules/<module>/objects/`.
- [ ] **A.2-2** Director-Composer um `outcome_disposition` (Glück) erweitern. Semantisch, charakter-spezifisch (z. B. Annette schlägt keine Fenster ein).
- [ ] **A.2-3** Neue Capability `narrator.environment_interaction` mit Glück-Färbung.
- [ ] **A.2-4** Live-Smoke gegen die vier Eingaben oben.

### PR-A.3 — Sachfragen + Validatoren-Verlagerung (Phase 1.c)

**Scope:** Spieler-Fragen über mundane Inhalte des aktuellen Raums; dramatic_irony-Disziplin als Director-Eingangs-Information statt nachgelagertes Gate.

**Akzeptanz live:**

- „Was finde ich in der Küche?" → DE-Antwort des Narrators aus dem `scene_affordance_model`, keine `hidden_fact_echo`-Ablehnung. Hidden Facts werden gar nicht erst zur Realisierung angeboten.
- „Wer ist hier?" → DE-Antwort über sichtbare Actors.
- „Was hat Alain in der Tasche?" (= Hidden-Fact-Frage) → Director realisiert NICHT als Aussage, sondern als Souffleuse-Hint oder Klärungs-Block. Kein nachgelagerter Reject.

**Eingriffe:**

- [ ] **A.3-1** `dramatic_irony_runtime.py:668-701` `validate_dramatic_irony_realization`: Funktion bleibt, wird aber vom Director vor der Realisierung konsumiert (Wissensstand pro Actor → Director weiß, was er realisieren *darf*).
- [ ] **A.3-2** Director-Composer-Logik erweitern: bei `player_input_kind=question` + Target-Klassifikation entscheidet er, welche Capability greift (Narrator-Auskunft, Souffleuse-Hint, Klärung).
- [ ] **A.3-3** Live-Smoke gegen die drei Eingaben oben.

### PR-B — `full_pipeline`-Zerlegung in Capability-Bibliothek (Phase 1.d)

**Scope:** Strukturelle Auflösung des Monolithen. `route_model`, `invoke_model`, `validation`, `commit` werden zu vom Director komponierbaren Operations. Keine Verhaltensänderung für Spieler, aber strukturelle Vorbedingung für Phase 2 (NPC-Pulse).

### PR-C — Director-Pause-Modus (Phase 2 Foundation)

**Scope:** Implementierung von `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md` §3.4 (Versammlungs-Pause-Modus). Setzt PR-A bis PR-B voraus.

---

## 4. Anti-Patterns (verbindlich)

- **Keine Whitelists/Blacklists.** Weder Verb-Listen noch Raum-Listen noch `if x in {literal_set}`. Discriminator gehört in Content/Resolver-Semantik oder Director-Entscheidung, nicht in Code.
- **Keine Π-IDs als Runtime-Keys.** Verwendung nur als Plan-Label. Runtime/Tests/UI/MCP: ausschließlich semantische Namen (vgl. NPC_INTERACTION-Plan §3.0 Mapping-Tabelle).
- **Keine Mock-Tests für die End-to-End-Integration.** Per CLAUDE.md: integration tests run real code paths; unit tests dürfen mocken.
- **Kein „dirty bypass" der Validatoren.** Sie werden *vorne* eingeplant, nicht hinten umgangen.
- **Keine zweite Quelle für Sprach-Realisierung.** Sichtbarer Text entsteht **nur** durch `realize_via_capabilities` → LLM in `session_output_language`. Kein `description`-Echo.
- **Keine neuen ad-hoc Felder.** Wenn ein neues Datum gebraucht wird, gehört es in einen der drei Verträge aus §2.2.

---

## 5. Test-/Verifikations-Strategie

- **Live-Smoke**: lokaler Stack über `docker-up.py`, manuelle Eingaben über die UI. Die Akzeptanz-Eingaben pro PR sind Smoke-Tests, *keine* Test-Fixtures.
- **Unit-Tests**: gegen `realization_plan.v1`-Eigenschaften und `semantic_resolution_output.v1`-Eigenschaften. Paraphrasierte Inputs aus Sprachregistern (umgangssprachlich/formell/elliptisch), Asserts auf Pfad-Eigenschaften, nie auf Strings.
- **Test-Runner**: `python tests/run_tests.py` (CLAUDE.md-Regel: einziger Runner).
- **Trace-Verifikation**: jeder PR-Abschluss erzeugt drei neue Langfuse-Traces, die die Akzeptanz-Eingaben durchspielen. Pfad-Summary muss `director_path_mode!=None`, `selected_capabilities!=[]`, `generation_attempted=True` zeigen.

---

## 6. Diagnose-Erweiterung (NPC_INTERACTION-Plan §3.5)

Pro Turn im `runtime_diagnostic_snapshot.v1`:

- `semantic_resolution_output` (neuer Vertrag)
- `realization_plan` (neuer Vertrag)
- `capabilities_invoked` (Ist, gegen `realization_plan.capabilities_selected`)
- `kanon_break_check` (`is_kanon_break`, `reason`)
- `outcome_disposition` (Glück: success/partial/fail + reason)

Anzeige-Standort: `narrative_systems.html` (siehe NPC_INTERACTION-Plan §3.5 Standort-Tabelle).

---

## 7. Fortschritt

### PR-A

| # | Schritt | Status | Notiz |
|---|---|---|---|
| A-1 | Resolver-Output: `kanon_break` + `kanon_break_reason` | ✓ done | `story_runtime_core/language_adapter.py:300-302` (Contract), `ai_stack/player_action_resolution.py:200-217` (helper), `:747-757` (Return). `glück_disposition_input` aus Resolver gestrichen — Glück gehört ganz in den Director. |
| A-2 | `ai_stack/director_realization_composer.py` neu | ✓ done | `realization_plan.v1` mit `realization_owner`, `capabilities_selected`, `outcome_disposition`, `language_target`, `visibility_constraints`, `decision_reason`. PR-A deterministisch (Bewegung→Narrator-Location-Transition, kanon_break→Refusal, uncertain→Clarification). Semantischer LLM-Call kommt in PR-A.2/3. |
| A-3 | Graph-Knoten `director_compose_realization` | ✓ done | `langgraph_runtime_executor.py:6383-6400` Methode, `:4869` add_node, `:4900` add_edge |
| A-4 | Graph-Knoten `realize_via_capabilities` | ✓ done | `langgraph_runtime_executor.py:6402-6464` Methode. Baut Narrator-Prompt aus `realization_plan.capabilities_selected[0]`. Reicht `state.model_prompt` an existierendes `route_model`/`invoke_model` weiter. |
| A-5 | Edges `resolve_player_action → composer → realize → route_model` | ✓ done | `langgraph_runtime_executor.py:4900-4902`. Alte conditional_edge nach `resolve_player_action` entfernt. Player-Turns gehen NICHT mehr durch `retrieve_context`/`derive_*`/`assemble_model_context`. Graph kompiliert; bestehende Tests brechen (per A-9). |
| A-6 | Lösche `_route_after_resolve_player_action` | ✓ done | 44 Zeilen entfernt. Methode war nur noch von Tests referenziert (per A-9 angepasst). |
| A-7 | Lösche `_authoritative_action_resolution_turn` | ✓ done | 152 Zeilen entfernt. Auch `graph.add_node`/`add_edge` für den `authoritative_action_resolution`-Knoten entfernt. Import von `build_synthetic_generation_for_action_resolution` entfernt. |
| A-8 | Eingrenze `build_synthetic_generation_for_action_resolution` | ✓ effektiv done | Modul `ai_stack/langgraph_synthetic_action_resolution.py` existiert weiter, wird aber im Player-Turn-Graph nicht mehr aufgerufen. Klärung erzeugt der Director via `_realize_via_capabilities` mit `CAPABILITY_NARRATOR_CLARIFICATION`. |
| A-9 | Tests umschreiben | offen | `test_runtime_authority_aspects.py`, `test_langgraph_runtime.py` |
| A-10 | Live-Smoke (5 Inputs) | offen | `docker-up.py` |
| A-11 | Diagnose-Anzeige `realization_plan` | offen | `narrative_systems.html` |

### PR-A.2

| # | Schritt | Status | Notiz |
|---|---|---|---|
| A.2-1 | RAG-Hook im Resolver | offen | — |
| A.2-2 | Director-Composer + `outcome_disposition` | offen | — |
| A.2-3 | Capability `narrator.environment_interaction` | offen | — |
| A.2-4 | Live-Smoke (4 Inputs) | offen | — |

### PR-A.3

| # | Schritt | Status | Notiz |
|---|---|---|---|
| A.3-1 | `dramatic_irony` als Director-Input | offen | `dramatic_irony_runtime.py` |
| A.3-2 | Composer-Logik für Sachfragen | offen | — |
| A.3-3 | Live-Smoke (3 Inputs) | offen | — |

### PR-B / PR-C

Eröffnet nach Abschluss PR-A.3.

---

## 8. Anhang — Code-Anker (verifiziert 2026-05-19)

| Komponente | Datei:Zeile |
|---|---|
| Translate-Ingress | `ai_stack/langgraph_runtime_executor.py:405-438` |
| Resolver (Player) | `ai_stack/player_action_resolution.py` |
| Router (ZU LÖSCHEN) | `ai_stack/langgraph_runtime_executor.py:6374-6415` |
| Short-Path-Knoten (ZU LÖSCHEN) | `ai_stack/langgraph_runtime_executor.py:6417-6440` |
| Synth-Gen (EINGRENZEN) | `ai_stack/narrator_consequence_contracts.py` (Quelle `build_synthetic_generation_for_action_resolution`) |
| Director (heute) | `ai_stack/scene_director_goc.py` |
| Validator dramatic_irony | `ai_stack/dramatic_irony_runtime.py:668-701` |
| Manager / Story-Runtime | `world-engine/app/story_runtime/manager.py` |
| Zwei grüne Karten | `world-engine/app/story_runtime/manager.py:7615-7671` |
| Frontend Renderer | `frontend/static/play_typewriter_engine.js:216-450`, `frontend/tests/test_block_renderer.js:286-293` |
| ADR Player-Shell | `docs/ADR/adr-0034-player-facing-narrative-shell-contract.md:32` |
| ADR Session-Sprache | `docs/ADR/adr-0054-session-input-language-english-internal-resolution.md`, `adr-0055-semantic-player-input-translation-ingress.md` |
| Anschluss-Plan | `NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md` (§3.4, §3.5) |
