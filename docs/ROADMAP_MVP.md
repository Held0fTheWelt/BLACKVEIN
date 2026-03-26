# Roadmap MVP — World of Shadows

## Zweck

Dieses Dokument beschreibt die präzise MVP-Roadmap für den ersten spielbaren Vertical Slice von **World of Shadows**.  
Der MVP soll zeigen, dass die **World Engine** mit einem **dynamischen, aber kontrollierten AI-Story-Kern** ein formales Content-Modul laden, fortschreiben, validieren, visualisieren und diagnostisch nachvollziehbar machen kann.

Der erste Referenzinhalt ist:

- **1 Content-Modul:** *God of Carnage*
- **1 spielbarer Lauf**
- **1 benutzbare UI**
- **1 kontrollierter AI-Story-Loop**
- **1 belastbare Grundlage für weitere Module**

---

## Leitidee des MVP

Der MVP ist **kein freies Story-Sandbox-System**, sondern ein **eng geführter, formal abgesicherter AI-Story-Vertical-Slice**.

Die Kernlogik lautet:

- **Content** definiert den dramaturgischen Möglichkeitsraum.
- **AI** erzeugt Deutungen, Reaktionsimpulse und Vorschläge.
- **Engine** validiert, entscheidet und schreibt kanonische Zustände fort.
- **UI** macht Story, Zustand, Entscheidungen und Fehler sichtbar.

---

## MVP-Zielbild

Am Ende von W4 existiert ein System, das:

1. das Modul **God of Carnage** formal laden kann,
2. eine Session starten kann,
3. Szenen und Zustände fortschreiben kann,
4. AI-Ausgaben strukturiert entgegennehmen kann,
5. unzulässige AI-Vorschläge verwerfen kann,
6. Zustandsänderungen explizit loggt,
7. den Verlauf in einer UI sichtbar macht,
8. Entwicklung, Debugging und Vorführung unterstützt.

---

## Was der MVP ist

Der MVP umfasst:

- ein formal definiertes Content-Modulformat
- ein vollständiges Referenzmodul für **God of Carnage**
- eine World Engine mit:
  - Session-State
  - Turn-State
  - Event-Log
  - State-Deltas
  - Regel- und Validierungsschicht
- einen AI-Story-Loop mit kontrollierten Outputs
- eine UI für:
  - Session-Start
  - Szenenanzeige
  - Figurenstatus
  - Konfliktentwicklung
  - Turn-Ausführung
  - Debug-/Diagnoseansicht
- Tests für Contracts, Content, Runtime, AI-Integration und End-to-End-Flows

---

## Was **nicht** Teil des MVP ist

Diese Punkte gehören ausdrücklich **nicht** zum MVP:

- generisches Autoren-Tool für beliebige Storymodule
- offenes Multi-Modul-Ökosystem
- freie Lore-Erfindung durch die AI
- autonome AI mit Schreibrechten auf Kanon
- unbegrenzte freie Figuren- oder Szenenerzeugung
- echtes großes Multi-Agent-System als Pflichtbestandteil
- aufwendige Präsentations-/Cinematic-Features vor funktionaler Stabilität
- komplexe Player-Choice-Ökonomie außerhalb des Kernloops
- breite Content-Welle über *God of Carnage* hinaus
- Scope-Erweiterungen, die nicht direkt zur MVP-Funktion nötig sind

---

## Systemgrenzen

### World Engine

Die World Engine ist zuständig für:

- kanonische Zustände
- Zustandsübergänge
- Regelprüfung
- Validierung
- Delta-Anwendung
- Session-Fortschritt
- Fehlerbehandlung
- Logging
- Reproduzierbarkeit

Die Engine ist die **autoritative Instanz**.

### AI

Die AI ist zuständig für:

- Szenendeutung
- Konfliktinterpretation
- Trigger-Erkennung
- Reaktionsimpulse
- Vorschläge für zulässige Zustandsänderungen
- dramaturgische Konfliktbewegung innerhalb definierter Grenzen

Die AI ist **nicht autoritativ**.  
Sie darf nur **strukturierte Vorschläge** machen.

### UI

Die UI ist zuständig für:

- Sichtbarkeit
- Bedienung
- Diagnose
- Verlaufseinsicht
- Debug-Unterstützung

Die UI trifft keine Kanon-Entscheidungen.

### Content

Das Content-Modul definiert:

- Figuren
- Beziehungen
- Szenen
- Übergänge
- Trigger
- Eskalationsachsen
- Endzustände
- Regie-/Interpretationsräume

Content liefert den **formal erlaubten Möglichkeitsraum**.

---

## Grundsatz: Autorität und Kontrolle

Der zentrale Satz des MVP lautet:

> **Die AI darf kreativ sein, aber nie souverän. Die Engine bleibt souverän, aber nie blind.**

Daraus folgen diese Regeln:

- AI setzt niemals selbst Wahrheit.
- AI darf keine Fakten außerhalb des Contracts erzeugen.
- AI darf nur definierte Aktionstypen verwenden.
- AI darf nur erlaubte Zustandsfelder beeinflussen.
- Die Engine validiert jede AI-Ausgabe.
- Nur die Engine committed kanonische Zustandsänderungen.

---

## Zielstruktur der Deliverables

```text
docs/
  roadmap_mvp.md
  mvp_definition.md
  god_of_carnage_module_contract.md
  ai_story_contract.md
  session_runtime_contract.md

schemas/
  content_module.schema.json
  ai_story_output.schema.json
  session_state.schema.json
  state_delta.schema.json

content/
  modules/
    god_of_carnage/
      module.yaml
      characters.yaml
      relationships.yaml
      scenes.yaml
      transitions.yaml
      triggers.yaml
      endings.yaml
      direction/
        system_prompt.md
        scene_guidance.yaml
        character_voice.yaml

engine/
  content/
  session/
  story/

ai/
  adapters/
  prompts/
  validators/
  roles/

ui/
  routes/
  templates/
  static/

tests/
  contracts/
  content/
  engine/
  ai/
  ui/
  e2e/
```

---

# W0 — Fundament schärfen und MVP-Vertrag festziehen

## Ziel

Den bestehenden Stand so ordnen, dass die nächsten Wellen nicht in Architekturdrift, Sonderlogik oder unklaren Zuständigkeiten enden.

## Ergebnis von W0

Am Ende von W0 ist glasklar:

- was der MVP genau ist
- was nicht Teil des MVP ist
- wo Engine, AI, Content und UI jeweils beginnen und enden
- welches God-of-Carnage-Modulformat gilt
- welche AI-Ausgaben zulässig sind
- wie Session, Turn, Delta und Logging strukturiert sind
- welche Ziel-Ordnerstruktur gilt

## Arbeitspakete

### 1. MVP-Definition festschreiben

Festlegen:

- 1 Story-Modul: **God of Carnage**
- 1 spielbarer Lauf
- 1 UI zur Bedienung und Diagnose
- AI als dynamischer Kern, aber kontrolliert

### 2. Systemgrenzen definieren

Abgrenzung zwischen:

- World Engine
- AI
- UI
- Content

### 3. Content-Contract definieren

Struktur definieren für:

- Figuren
- Beziehungen
- Szenen
- Übergänge
- Trigger
- Eskalationsachsen
- Endzustände
- Interventionspunkte

### 4. AI-Contract definieren

Festlegen:

- strukturierte Outputs
- erlaubte Aktionstypen
- verbotene Änderungen
- Pflichtfelder
- Validierungsregeln

### 5. Session-Contract definieren

Definieren:

- Session-State
- Turn-State
- Event-Log
- State-Delta
- AI-Decision-Log

### 6. Fehler- und Guard-Klassen definieren

Mindestens:

- schema invalid
- forbidden mutation
- unknown reference
- illegal scene jump
- unsupported trigger
- canon conflict
- partial AI output
- empty AI response
- timeout / backend failure

### 7. Repo-/Ordnerstruktur festziehen

Keine Vermischung von:

- Content
- Engine
- Runtime
- UI
- AI-spezifischer Logik

## Deliverables

- `docs/mvp_definition.md`
- `docs/god_of_carnage_module_contract.md`
- `docs/ai_story_contract.md`
- `docs/session_runtime_contract.md`
- erste Ziel-Ordnerstruktur
- `schemas/`-Grundgerüst
- Testskelett für Contracts

## Akzeptanzkriterien

- Für alle Beteiligten ist klar, was in W1–W4 gebaut wird.
- Kein zentraler Bereich ist mehr implizit.
- Ein AI-Output kann formal gegen ein Schema geprüft werden.
- Das Content-Modul hat eine definierte Zielstruktur.
- Die Autorität der Engine ist explizit festgeschrieben.

## Gate für W1

W1 beginnt erst, wenn:

- Kernbegriffe definiert sind
- Contracts dokumentiert sind
- erste Schemas existieren
- Zielstruktur festgelegt ist
- Testskelett vorhanden ist

---

# W1 — God of Carnage als echtes Content-Modul

## Ziel

*God of Carnage* nicht als lose Idee, sondern als formales, maschinenlesbares, testbares Modul modellieren.

## Ergebnis von W1

Das Stück ist als erstes Referenz-Content-Modul vorhanden und kann von der Engine geladen werden.

## Arbeitspakete

### 1. Modulstruktur aufbauen

Definieren und anlegen:

- `module.yaml/json`
- `characters`
- `relationships`
- `scenes`
- `transitions`
- `triggers`
- `endings`
- Prompt-/Regie-Bausteine

### 2. Figuren modellieren

Mindestens:

- Véronique
- Michel
- Annette
- Alain

Mit klaren formalen Eigenschaften, Rollen, Grundhaltungen und relevanten Spannungsmerkmalen.

### 3. Beziehungsachsen definieren

Mindestens:

- Ehepartner intern
- Gastgeber vs. Gäste
- moralische vs. pragmatische Haltungen
- latente Dominanz-/Abwertungsachsen

### 4. Szenenstruktur modellieren

Mindestens:

- höflicher Anfang
- moralische Verhandlung
- Lagerbildung / Umschläge
- emotionale Entgleisung
- Kontrollverlust / Eskalation

### 5. Trigger definieren

Mindestens:

- Widerspruch
- Bloßstellung
- Relativierung
- Entschuldigung / Nicht-Entschuldigung
- Zynismus
- Flucht in Nebenhandlungen

### 6. Eskalationslogik definieren

Mindestens:

- individuelle Eskalation
- Beziehungsinstabilität
- Gesprächszerfall
- Koalitionswechsel

### 7. End- und Umschlagbedingungen definieren

Mindestens:

- Abbruch
- offene Implosion
- temporäre Beruhigung
- toxische Scheinlösung

### 8. Content-Validierung bauen

Prüfen:

- Referenzen vollständig
- keine toten Übergänge
- keine unzulässigen Trigger
- Enden erreichbar
- keine Sonderlogik nötig

## Deliverables

- vollständiges `god_of_carnage`-Modul
- Modul-Loader
- Content-Validator
- Content-Tests
- Dokumentation des Moduls

## Akzeptanzkriterien

- Das Modul ist vollständig ladbar.
- Alle Figuren, Szenen und Trigger sind strukturell konsistent.
- Mindestens ein vollständiger Story-Lauf ist als erlaubter Graph modelliert.
- Das Modul kann ohne Sonderlogik von der Engine eingelesen werden.

## Gate für W2

W2 beginnt erst, wenn:

- das Modul stabil geladen wird
- Referenzen valide sind
- mindestens ein Lauf formal möglich ist
- keine hardcodierte Sonderbehandlung nötig ist

---

# W2 — Dynamischen AI-Story-Kern in die World Engine einziehen

## Ziel

Die Engine soll nicht nur Zustände speichern, sondern mit einer fortgeschrittenen dynamischen AI eine Szene wirklich fortschreiben können.

## Ergebnis von W2

Ein erster AI-gestützter Story-Loop läuft mit kontrollierter Dynamik.

## W2-Unterwellen

---

## W2.0 — Story-Loop-Skelett

### Ziel

Den kompletten Kontrollpfad ohne kreative Abhängigkeit schließen.

### Arbeitspakete

- Session starten
- Modul laden
- Szene aktivieren
- State aufbereiten
- Dummy-/Mock-AI-Output einspeisen
- Output validieren
- Deltas anwenden
- Event-Log schreiben
- nächste Situation ableiten

### Akzeptanz

- Ein kompletter Turn läuft technisch durch.
- Die Kontrollkette ist testbar.
- Fehlerpfade sind sichtbar.

---

## W2.1 — Echter AI-Adapter mit strukturiertem Output

### Ziel

Ein Modell liefert formal prüfbare Story-Vorschläge.

### Arbeitspakete

- AI-Adapter anbinden
- feste Promptstruktur
- strikt strukturiertes JSON-Output
- Parsing + Schema-Check
- keine unkontrollierte Wahrheitssetzung über Freitext

### Pflichtbestandteile eines AI-Outputs

- `scene_interpretation`
- `detected_triggers`
- `proposed_state_deltas`
- `dialogue_impulses`
- `conflict_vector`
- optional `confidence` / `uncertainty`

### Akzeptanz

- Mehrere Turns sind möglich.
- Outputs bleiben formal validierbar.
- Fehlerhafte Antworten werden erkannt.

---

## W2.2 — Guard- und Validierungsschicht

### Ziel

Die AI darf keine unzulässigen Änderungen einschmuggeln.

### Arbeitspakete

- erlaubte Aktionstypen whitelisten
- Figuren- und Szenenreferenzen prüfen
- Trigger nur aus erlaubter Menge
- keine neuen Fakten
- keine unzulässigen Zustandsfelder
- keine illegalen Szenensprünge
- Endzustände nur unter gültigen Bedingungen

### Akzeptanz

- Fehlerhafte AI-Outputs werden verworfen oder reduziert übernommen.
- Die Engine bleibt stabil.
- Verwerfungen werden geloggt.

---

## W2.3 — Memory und Kontextlogik

### Ziel

Dynamik ohne Kontextdrift.

### Arbeitspakete

- kurzfristiger Turn-Kontext
- Session-Historie
- verdichtete Verlaufszusammenfassung
- relevante Beziehungsachsen
- modulare Lore-/Regie-Kontextzufuhr

### Akzeptanz

- Längere Sessions bleiben kohärent.
- Eskalationsmuster bleiben nachvollziehbar.
- Kontext bleibt kontrollierbar.

---

## W2.4 — Interne Rollenlogik

### Ziel

Bessere Qualität durch saubere innere Aufgabenverteilung.

### Rollen

- **Interpreter** — Was passiert gerade?
- **Director** — Welche Konfliktbewegung passt jetzt?
- **Responder** — Welche konkrete Reaktion folgt daraus?

### Akzeptanz

- Interpretation, Konfliktdynamik und Reaktion sind sauberer getrennt.
- Diagnose wird klarer.
- Die Rollenlogik bleibt MVP-kompatibel.

---

## W2.5 — Recovery und Stabilitätsmodus

### Ziel

Ein Lauf darf nicht an einer schlechten AI-Antwort sterben.

### Arbeitspakete

- Retry-Regeln
- Reduced-context retry
- Fallback-Modus
- sichere No-op-/Safe-Turn-Strategie
- letzter gültiger Zustand bleibt erhalten
- degradierter, aber laufender Session-Modus

### Akzeptanz

- Ungültige AI-Ausgaben brechen den Lauf nicht.
- Recovery ist nachvollziehbar.
- Die Session bleibt debugbar.

---

## Gesamtdeliverables von W2

- `story_loop`
- AI-Adapter
- AI-Output-Schemas
- Validator
- Session-State-Modell
- Event-/Delta-Logging
- AI-Loop-Tests

## Gesamtakzeptanz für W2

- Eine Session kann von Start bis zu mehreren Turns laufen.
- Die AI erzeugt dynamisch unterschiedliche Reaktionen innerhalb der Regeln.
- Ungültige AI-Ausgaben brechen den Lauf nicht.
- Zustandsänderungen sind nachvollziehbar gespeichert.
- Die Engine bleibt Herr des Kanons.

## Gate für W3

W3 beginnt erst, wenn:

- Sessions stabil über mehrere Turns laufen
- AI-Output formal validiert wird
- Fehlerfälle kontrolliert abgefangen werden
- Deltas explizit gespeichert werden
- Engine-Autorität nicht unterlaufen wird

---

# W3 — Spielbare UI mit Diagnose- und Kontrolltiefe

## Ziel

Der MVP soll benutzbar werden: nicht bloß über Tests, sondern über eine echte Oberfläche.

## Ergebnis von W3

Eine erste UI erlaubt, *God of Carnage* zu starten, Eingaben zu machen und die dynamische Entwicklung sichtbar zu verfolgen.

## Arbeitspakete

### 1. Session-Start-Ansicht

- neues Spiel starten
- Modul auswählen
- Session laden

### 2. Szenenansicht

- aktuelle Szene
- situative Beschreibung
- Gesprächslage

### 3. Figuren-Panel

- emotionale Lage
- Haltung
- Eskalationsstand
- Beziehungsverschiebungen

### 4. Konflikt-/Spannungspanel

- dominante Achsen
- aktuelle Eskalation
- Umschlagsrisiken

### 5. Interaktionspanel

- Spieler-/Operator-Eingabe
- nächster Turn
- AI ausführen

### 6. Verlaufsansicht

- Turn-Historie
- wichtige Ereignisse
- Zustandswechsel

### 7. Debug-/Diagnosepanel

- AI-Output roh/strukturiert
- Validierungsentscheidungen
- übernommene vs. verworfene Änderungen
- aktive Trigger / Regeln

### 8. API-Endpunkte

Mindestens:

- Session starten
- Session abrufen
- Turn ausführen
- Logs abrufen
- State abrufen

## Deliverables

- spielbare Jinja-/Web-UI
- API-Endpunkte
- UI-Smoke-Tests
- Debug-Ansichten

## Akzeptanzkriterien

- Ein Benutzer kann ohne Codeeingriff einen Lauf starten.
- Der Verlauf ist sichtbar.
- Die AI-Reaktionen sind sichtbar.
- Die Zustandsänderungen sind nachvollziehbar.
- Debug-Informationen helfen tatsächlich bei Entwicklung und Test.

## Gate für W4

W4 beginnt erst, wenn:

- Session-Start ohne Codeeingriff funktioniert
- Story-Verlauf sichtbar ist
- Debug-Daten brauchbar sind
- die UI den Kernloop zuverlässig bedienen kann

---

# W4 — MVP-Härtung, Qualität, erste echte Erlebnisfassung

## Ziel

Aus dem technisch laufenden Prototypen einen belastbaren MVP machen, der nicht nur irgendwie funktioniert, sondern als erster echter Vertical Slice vorzeigbar ist.

## Ergebnis von W4

*God of Carnage* läuft als stabiler, nachvollziehbarer, dynamischer AI-MVP.

## Arbeitspakete

### 1. Systemtests / End-to-End-Tests

- Session-Start bis Ende
- typische Eskalationspfade
- Fehlerpfade
- Recovery-Verhalten

### 2. Balancing / Feintuning

- Eskalation nicht zu flach
- Eskalation nicht chaotisch
- Koalitionswechsel nachvollziehbar
- Figuren bleiben charaktertreu

### 3. AI-Qualitätsverbesserung

- bessere Promptstruktur
- bessere Kontextselektion
- sauberere Validierung
- stabilere Antworten

### 4. Session-Persistenz härten

- Speichern / Laden
- Wiederaufnahme
- reproduzierbare Diagnostik

### 5. UI-Nutzbarkeit verbessern

- klarerer Storyfluss
- bessere Sichtbarkeit von Regie-/AI-Entscheidungen
- bessere Entwicklerdiagnose

### 6. MVP-Abgrenzung prüfen

- kein Scope-Creep
- nur MVP-notwendige Ergänzungen

### 7. Vorführung / Demo-Skript

- definierter Vorführlauf
- definierte Testläufe
- definierte Failure-Cases

## Deliverables

- gehärteter MVP
- End-to-End-Testpaket
- Demo-Dokumentation
- klare Definition „bereit für nächste Content-Welle“

## Akzeptanzkriterien

- Mehrere Sessions laufen stabil.
- Die AI wirkt dynamisch, aber nicht beliebig.
- Der Story-Lauf ist nachvollziehbar und debugbar.
- Der MVP ist intern präsentierbar.
- Der MVP ist als Grundlage für weitere Module brauchbar.

---

# Reproduzierbarkeit und Diagnostik

Zur belastbaren Analyse und späteren Weiterentwicklung muss jeder Lauf diagnostisch nachvollziehbar sein.

## Pflicht-Metadaten pro Session

- `session_id`
- `module_id`
- `module_version`
- `contract_version`
- `prompt_version`
- `ai_backend`
- `ai_model`
- optional `seed`
- Zeitstempel

## Pflicht-Logs

- Event-Log
- AI-Decision-Log
- Validation-Log
- State-Delta-Log
- Recovery-/Fallback-Log

---

# Qualitätsgrundsätze

## 1. Keine implizite Wahrheit

Alles Zentrale muss entweder:

- im Content definiert,
- im Contract beschrieben,
- oder im State explizit gespeichert sein.

## 2. Keine Sonderlogik für God of Carnage

Das erste Modul ist Referenzmodul, kein Ausnahmefall.

## 3. Kein freier AI-Kanon

AI darf Bedeutung vorschlagen, aber keine neue Weltordnung setzen.

## 4. Validierung vor Anwendung

Jeder AI-Vorschlag wird geprüft, bevor er den State verändert.

## 5. Diagnose ist Pflicht, nicht Bonus

Ein MVP ohne nachvollziehbare Diagnose ist für dieses Projekt unzureichend.

---

# Die Wellenlogik in einem Satz

- **W0 = Vertrag**
- **W1 = Inhalt**
- **W2 = dynamischer AI-Kern**
- **W3 = Spielbarkeit**
- **W4 = Härtung und MVP-Reife**

---

# Was am Ende von W4 konkret existiert

Dann existieren:

- ein echtes **God-of-Carnage-Content-Modul**
- eine **World Engine**, die Story-Zustände mit AI-Unterstützung fortschreibt
- ein kontrollierter **AI-Story-Loop**
- eine **spielbare UI**
- sichtbare **Diagnose- und Validierungslogik**
- reproduzierbare **Session- und Delta-Logs**
- ein erster vorzeigbarer **AI-Story-MVP**
- eine belastbare Basis für weitere Module nach demselben Muster

---

# Zentrale Priorität

Die kritischste Welle ist **W2**.

Dort entscheidet sich, ob das System:

- nur eine hübsch verpackte Zustandsmaschine wird,
- oder wirklich einen fortgeschrittenen, kontrollierten AI-Story-Kern erhält.

Darum gilt:

> **W2 wird nicht als ein Block umgesetzt, sondern in klaren Unterwellen mit harten Gates.**
