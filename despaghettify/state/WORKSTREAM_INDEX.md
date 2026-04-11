# Workstream Index

Dieses Dokument ist der kanonische Index fuer state-changing Workstreams unter Governance.

## Statusuebersicht

| Workstream | State-Dokument | Pre-Artefakte | Post-Artefakte | Governance-Status |
| --- | --- | --- | --- | --- |
| Backend Runtime and Services | `WORKSTREAM_BACKEND_RUNTIME_AND_SERVICES_STATE.md` | `artifacts/workstreams/backend_runtime_services/pre/` | `artifacts/workstreams/backend_runtime_services/post/` | Governed |
| AI Stack | `WORKSTREAM_AI_STACK_STATE.md` | `artifacts/workstreams/ai_stack/pre/` | `artifacts/workstreams/ai_stack/post/` | Governed |
| Administration Tool | `WORKSTREAM_ADMIN_TOOL_STATE.md` | `artifacts/workstreams/administration_tool/pre/` | `artifacts/workstreams/administration_tool/post/` | Governed |
| Documentation | `WORKSTREAM_DOCUMENTATION_STATE.md` | `artifacts/workstreams/documentation/pre/` | `artifacts/workstreams/documentation/post/` | Governed |
| World Engine | `WORKSTREAM_WORLD_ENGINE_STATE.md` | `artifacts/workstreams/world_engine/pre/` | `artifacts/workstreams/world_engine/post/` | Governed |

Die **Pre/Post-Ordner** sind Zielpfade für künftige Wellen; sie können im Arbeitsbaum **ohne Dateien** existieren, wenn ältere Session-Artefakte bewusst entfernt wurden.

## Repositoryweiter Rollout-Nachweis

- Pre: `artifacts/repo_governance_rollout/pre/`
- Post: `artifacts/repo_governance_rollout/post/`

## Bootstrap-Entscheidungen

- Vorhandene Governance-/Audit-Dokumente unter `docs/audit/`, `docs/audits/` und `audits/` bleiben erhalten.
- `docs/state/` ist der neue kanonische Restart-Anker fuer laufende Ausfuehrungsgouvernanz.
- Historische Claims ohne verlinkte Evidenz gelten nicht als Abschlussbeweis.

## Strukturelle Code-Arbeit (Despaghettifizierung)

Refactors gegen Spaghetti/Modulgrenzen nutzen **dieselben** Pre/Post-Pfade wie die Workstreams oben (pro betroffenem `artifacts/workstreams/<slug>/pre|post/`). Kanonische Arbeitsvorlage (Inputliste, **DS-ID → Workstream**-Tabelle, Umsetzungsreihenfolge, Arbeitslog — derzeit als Templates vorbereitet): [`../dev/despaghettification_implementation_input.md`](../dev/despaghettification_implementation_input.md).
