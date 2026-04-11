# Execution State Hub

Dieser Ordner ist die kanonische Restart-Schicht fuer zustandsaendernde Ausfuehrungsarbeit im Repository.

Kernprinzip:
- State-Dokumente sichern Kontinuitaet.
- Artefakte sichern Beweise.
- Abschlussclaims sind nur gueltig, wenn Pre- und Post-Artefakte verlinkt und vergleichbar sind.

Hinweis: `artifacts/workstreams/…/pre|post/` kann zwischen Wellen **leer** sein (z. B. nach Bereinigung). Neue strukturelle Wellen legen die Session-Dateien dort wieder an; fehlende alte Pfade ersetzen **nicht** Git-Historie, CI oder Tests.

Kanonische Einstiegspunkte:
- `EXECUTION_GOVERNANCE.md`
- `WORKSTREAM_INDEX.md`

Strukturelle Code-Refactors (Spaghetti / Modulgrenzen) mit denselben Pre/Post-Pfaden: [`../dev/despaghettification_implementation_input.md`](../dev/despaghettification_implementation_input.md).
