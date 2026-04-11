# Repository-Wide Execution Governance

## Zweck

Dieses Dokument definiert die verbindliche Governance fuer alle zustandsaendernden Workstreams in `WorldOfShadows`.
Es ergaenzt vorhandene Fach- und Audit-Dokumentation, ersetzt sie aber nicht.

Autoritaetsreihenfolge bei Widerspruch:
1. Repository-Realitaet (Dateien, Code, aktueller Zustand)
2. Objektive Artefakte im Repository
3. Kanonische State-Dokumente unter `docs/state/`
4. Historische Narrative/Chat-Kontext

## Geltungsbereich

Die Governance gilt fuer alle realen state-changing Workstreams, insbesondere:
- Backend Runtime and Services
- AI Stack
- Administration Tool
- Documentation
- World Engine

## Verbindliches Modell pro Workstream

Jeder Workstream muss haben:
1. Ein kanonisches State-Dokument unter `docs/state/`.
2. Ein Pre-Artefakt-Set unter `docs/state/artifacts/workstreams/<workstream>/pre/`.
3. Ein Post-Artefakt-Set unter `docs/state/artifacts/workstreams/<workstream>/post/`.

Mindestens ein Artefakt muss menschenlesbar sein (`.txt`/`.md`), ein maschinenlesbares Artefakt ist bevorzugt (`.json`).

## Completion Gate (nicht verhandelbar)

Ein Wave-, Task- oder Closure-Claim ist nur zulaessig, wenn alle Punkte erfuellt sind:
- Das zugehoerige State-Dokument wurde vor Arbeitsbeginn gelesen.
- Repository-Realitaet wurde frisch inspiziert.
- Pre-Artefakte existieren.
- Ausfuehrungsarbeit wurde gegen den aktuellen Repo-Stand gemacht.
- Post-Artefakte existieren.
- Post gegen Pre ist dokumentiert verglichen.
- State-Dokument wurde aus Evidenz aktualisiert.
- Es bleibt kein unbelegter Abschlussclaim stehen.

## Contradiction Stop Rule

Wenn Repo-Realitaet und bestehende State-/Audit-Narrative widersprechen:
- Stoppen.
- Widerspruch im betroffenen State-Dokument unter "Contradictions/Caveats" erfassen.
- Scope und naechste Schritte neu auf Repo-Realitaet ausrichten.
- Erst dann weiterarbeiten.

## Rollout-Artefakte dieser Governance-Installation

Repositoryweiter Rollout-Nachweis:
- Pre: `docs/state/artifacts/repo_governance_rollout/pre/`
- Post: `docs/state/artifacts/repo_governance_rollout/post/`

Workstreams werden im `WORKSTREAM_INDEX.md` gefuehrt.
