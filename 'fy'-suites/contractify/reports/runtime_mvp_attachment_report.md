# Runtime/MVP Contractify attachment report

Generated from the canonical manifest-backed Contractify audit.

## Outcome

- Canonical tracked audit snapshot: `'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md`
- Local machine audit export: `'fy'-suites/contractify/reports/_local_contract_audit.json` (ephemeral, not tracked)
- Contracts discovered in audit: **60**
- Relations discovered in audit: **310**
- Manual unresolved areas kept explicit: **3**

The runtime/MVP spine remains a **bounded family view** inside the larger canonical audit. Broader ADR-governance additions now contribute to the full audit totals above.

## Precedence / weight handling

- **runtime_authority** (rank 1): Highest-order runtime authority and boundary contracts. These outrank slice detail, implementation observations, and projections when authority clashes are reviewed.
- **slice_normative** (rank 2): Binding MVP / slice contracts and accepted slice-scoped ADRs. These govern GoC behavior beneath the runtime authority layer.
- **implementation_evidence** (rank 3): Observed code surfaces that embody or operationalize contracts but do not replace normative authority.
- **verification_evidence** (rank 4): Test and verification surfaces that support claims about implementation and documented paths.
- **projection_low** (rank 5): Lower-weight audience projections and convenience summaries. Useful for navigation, never equal to runtime authority or slice contracts.

## Runtime/MVP family visibility

- `runtime_authority`: CTR-ADR-0001-RUNTIME-AUTHORITY, CTR-ADR-0002-BACKEND-SESSION-QUARANTINE, CTR-RUNTIME-AUTHORITY-STATE-FLOW, CTR-BACKEND-RUNTIME-CLASSIFICATION, CTR-CANONICAL-RUNTIME-CONTRACT, CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS, CTR-RUNTIME-NARRATIVE-COMMIT, OBS-WE-WS-API, OBS-WE-COMMIT-MODELS, VER-WE-WS-TEST, VER-WE-NARRATIVE-COMMIT-TEST
- `input_turn`: CTR-PLAYER-INPUT-INTERPRETATION, OBS-CORE-INPUT-INTERPRETER, VER-CORE-INPUT-INTERPRETER-TEST
- `goc`: CTR-GOC-VERTICAL-SLICE, CTR-GOC-CANONICAL-TURN, CTR-GOC-GATE-SCORING, VER-GOC-EXPERIENCE-SCORE-CLI-TEST
- `scene_identity`: CTR-ADR-0003-SCENE-IDENTITY, OBS-AI-GOC-SCENE-IDENTITY, OBS-AI-GOC-YAML-AUTHORITY, VER-AI-GOC-SCENE-IDENTITY-TEST
- `publish_rag`: CTR-WRITERS-ROOM-PUBLISHING-FLOW, CTR-RAG-GOVERNANCE, OBS-BE-WRITERS-ROOM-ROUTES, OBS-AI-RAG, VER-BE-WRITERS-ROOM-ROUTES-TEST, VER-AI-RETRIEVAL-GOVERNANCE-SUMMARY-TEST
- `routing_observability`: CTR-AI-STORY-ROUTING-OBSERVATION, OBS-BE-MODEL-ROUTING-CONTRACTS, OBS-BE-OPERATOR-AUDIT, VER-BE-CROSS-SURFACE-OPERATOR-AUDIT-TEST
- `evidence_baseline`: CTR-EVIDENCE-BASELINE-GOVERNANCE, VER-SMOKE-DOCUMENTED-PATHS
- `testing`: CTR-TESTING-ORCHESTRATION, VER-TEST-RUNNER-CLI, VER-SMOKE-DOCUMENTED-PATHS

## Explicit unresolved areas preserved

- `CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT` — Backend transitional session surfaces are now attached and weighted, but the actual retirement timeline remains intentionally unresolved.
  - source: `docs/ADR/adr-0002-backend-session-surface-quarantine.md`
  - source: `docs/technical/architecture/backend-runtime-classification.md`
  - source: `backend/app/api/v1/session_routes.py`
  - source: `backend/app/runtime/session_store.py`
- `CNF-EVIDENCE-BASELINE-CLONE-REPRO` — Audit docs intentionally cite machine-local tests/reports evidence paths while clone reproducibility only guarantees the tracked subset; this boundary must stay explicit in governance review.
  - source: `docs/audit/gate_summary_matrix.md`
  - source: `docs/audit/repo_evidence_index.md`
  - source: `.gitignore`
  - source: `tests/reports`
- `CNF-RUNTIME-SPINE-WRITERS-RAG-OVERLAP` — Writers’ Room workflow and RAG governance intentionally overlap at retrieval/context-pack assembly, but publishing authority and runtime truth remain distinct and should stay explicitly reviewed.
  - source: `docs/technical/content/writers-room-and-publishing-flow.md`
  - source: `docs/technical/ai/RAG.md`
  - source: `backend/app/api/v1/writers_room_routes.py`
  - source: `ai_stack/rag.py`

## Notes

- This report is regenerated from the same canonical manifest-backed run as `CANONICAL_REPO_ROOT_AUDIT.md`.
- Use the canonical audit snapshot for repo-wide totals and this report for the bounded runtime/MVP reading path.
- The broader ADR portfolio is visible in the canonical snapshot ADR-governance section and the ADR investigation state/report surfaces.
