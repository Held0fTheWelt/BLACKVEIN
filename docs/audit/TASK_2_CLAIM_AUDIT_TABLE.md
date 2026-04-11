# Task 2 — Material Claim Audit Table

This table records materially relevant claims for Task 2 execution control.

Classification set:

- `confirmed`
- `partially_confirmed`
- `outdated_or_contradicted`
- `unverifiable`
- `missing_but_necessary`

Action set:

- `retain`
- `narrow`
- `correct`
- `expand`
- `remove`
- `supplement`

| Claim ID | Document path | Section/locator | Claim summary | Classification | Evidence type | Evidence anchor | Action |
|---|---|---|---|---|---|---|---|
| C001 | `README.md` | services/packages section | world-engine is authoritative live-play runtime host | partially_confirmed | code + config + docs | `world-engine/app/story_runtime/manager.py`; `docker-compose.yml`; `docs/architecture/runtime_authority_decision.md` | narrow |
| C002 | `docs/architecture/runtime_authority_decision.md` | summary authority split | backend governs policy/publishing while world-engine hosts runtime execution | partially_confirmed | code + config | backend content service paths; play-service wiring in `docker-compose.yml` | supplement |
| C003 | `docs/CANONICAL_TURN_CONTRACT_GOC.md` | seam authority sections | commit seam is authority for durable narrative truth | partially_confirmed | cross-stack seam evidence | Task 1B seam controls + runtime manager integration paths | narrow |
| C004 | `docs/VERTICAL_SLICE_CONTRACT_GOC.md` | contract sections | vertical-slice constraints are binding for GoC runtime and governance | partially_confirmed | code references + contract docs | references in `ai_stack/goc_yaml_authority.py`; contract docs | supplement |
| C005 | `docs/audit/gate_summary_matrix.md` | notes | cited `tests/reports/evidence/...` paths represent baseline evidence | unverifiable | tracked-path check | `.gitignore` `/tests/reports`; tracked exceptions only in `tests/reports/*.md` | correct |
| C006 | `docs/rag_task3_source_governance.md` | retrieval policy references | retrieval lane behavior uses path/category rules for module vs published content | partially_confirmed | code + tests | `ai_stack/rag.py`; relevant ai_stack tests | expand |
| C007 | `docs/g9_evaluator_b_external_package/documents/*` | package instructions | this docs tree is active package authority without mirror caveat | outdated_or_contradicted | mirror policy docs | Task 1A Appendix C mirror policy + duplicate `outgoing/**` docs | correct |
| C008 | `docs/archive/superpowers-legacy-execution-2026/plans/*` (formerly `docs/superpowers/plans/*`) | plan narratives | timeline/process artifacts are active durable operational truth | unverifiable | organizational-logic evaluation | process/milestone form; no exclusive operational instruction dependency; **archived 2026-04-10** | remove from active tree (done) |
| C009 | `docs/testing/QUALITY_GATES.md` | release criteria | release gating instructions are audience-neutral and should remain under dev testing root | partially_confirmed | process + audience fit | mixed admin release and dev execution content in file structure | narrow |
| C010 | `docs/security/AUDIT_REPORT.md` | report status statements | latest audit statements are currently valid without temporal scope framing | unverifiable | governance evidence check | report date context and evolving repo state | supplement |

## Missing-but-necessary claims to add during execution

| Claim ID | Destination doc | Needed claim | Why required | Action |
|---|---|---|---|---|
| M001 | curated audience index | explicit non-curated control-surface boundary | prevents AI-control docs from being treated as audience docs | add/supplement |
| M002 | release policy docs | explicit owner for release-gate authority | removes ambiguity between dev testing docs and admin release governance | add/supplement |
| M003 | external package mirror docs | explicit canonical mirror owner declaration | prevents stale mirror divergence | add/supplement |
