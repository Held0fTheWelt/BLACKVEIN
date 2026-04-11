# Workstream State: Backend Runtime and Services

## Current Objective

Backend-Runtime- und Service-Änderungen unter [`EXECUTION_GOVERNANCE.md`](EXECUTION_GOVERNANCE.md) führen. Strukturelle Refactors: [`docs/dev/despaghettification_implementation_input.md`](../dev/despaghettification_implementation_input.md) (Inputliste, Struktur-Scan, optional Arbeitslog). Orientierungszahlen und Hotspots nur dort pflegen, nicht hier duplizieren.

## Current Repository Status

- Typischer Scope: `backend/app/runtime`, `backend/app/services`, `backend/app/api/v1`, zugehörige Tests.
- Nach der nächsten **Wave**: Scope-Snapshot unter `artifacts/workstreams/backend_runtime_services/pre/` ablegen (siehe Namenskonvention in der Inputliste).

## Hotspot / Target Status

- — *(bei Bedarf nach Review/Scan kurz benennen.)*

## Last Completed Wave/Session

- — *(Datum, **DS-ID(s)**, Kurzfassung; Links zu `pre|post`-Artefakten relativ zu `docs/state/`.)*

## Pre-Work Baseline Reference

Kanonisches Muster (Dateien erst anlegen, wenn eine Wave läuft):

- `artifacts/workstreams/backend_runtime_services/pre/git_status_scope.txt` *(optional)*
- `artifacts/workstreams/backend_runtime_services/pre/session_YYYYMMDD_DS-xxx_*` *(Claim, Snapshot, Collect, … — siehe Governance)*

## Post-Work Verification Reference

- `artifacts/workstreams/backend_runtime_services/post/session_YYYYMMDD_DS-xxx_*`
- Pre→Post-Vergleich und `pre_post_comparison.json` wo gefordert.

## Known Blockers

- —

## Next Recommended Wave

- Nächste **DS-*-Zeile** aus der Informations-Inputliste; Claim **DS-ID + Owner** vor größeren Änderungen.

## Contradictions / Caveats

- Abschlussclaims nur mit verlinkten, versionierten Artefakten; fehlende alte Pfade ersetzen nicht Git-Historie oder CI.
