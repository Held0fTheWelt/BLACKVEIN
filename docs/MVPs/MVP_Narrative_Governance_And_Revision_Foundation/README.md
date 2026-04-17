# Narrative Governance & Revision Foundation — Live-Ready Complete Collection

This bundle is the **full, implementation-oriented collection** for the revised Narrative Governance & Revision Foundation.

It incorporates the prior review, the rollback/conflict/validator/state-machine/notification upgrades, and the live-play runtime additions that close the operational gap between **"formally safe"** and **"playable under pressure."**

## What is newly integrated in this complete version

- immutable package history and rollback
- revision conflict detection and explicit resolution
- explicit validator strategy pattern
- formal revision review state machine
- event-driven notification and alerting
- clearer operator journeys in the administration-tool
- research-to-revision expansion for content-aware change proposals
- evaluation coverage and delta-aware quality gates
- **live corrective retry with validation feedback**
- **guaranteed safe fallback responses for live play**
- **runtime health and fallback-rate monitoring**
- **preview session isolation guidance**
- **player affect / emotion detection with enums instead of narrow frustration-only logic**
- **dramatic quality extension seams for emotional continuity, contradiction checking, steering, and branch simulation**
- **database migration strategy for governance tables, indexes, backfill, and compatibility**

## Document map

- `00_executive_overview.md` — condensed architecture intent and foundation decisions
- `01_revised_mvp_spec.md` — revised MVP specification with live-play continuity requirements
- `02_architecture_decisions.md` — index of architecture decisions; **normative text** in [`docs/ADR/README.md`](../../ADR/README.md) / `docs/ADR/adr-*.md`
- `03_data_contracts.md` — canonical data models and enums
- `04_api_catalog.md` — proposed backend and world-engine APIs
- `05_admin_tool_governance_surface.md` — administration-tool information architecture, wireframes, and operator flows
- `06_research_to_revision_suite.md` — research suite expansion into review-bound revision generation
- `07_evaluation_and_quality_gates.md` — evaluation backbone, live metrics, scoring, and coverage
- `08_package_lifecycle_conflicts_and_rollback.md` — immutable package history, preview promotion, conflicts, rollback, isolation
- `09_state_machines_and_notifications.md` — workflow engine and alerting model
- `10_acceptance_criteria_and_open_risks.md` — exit criteria, non-negotiables, and unresolved risks
- `11_repo_touchpoints.md` — repository-aligned implementation touchpoints by service
- `12_live_play_correction_and_fallbacks.md` — corrective retry, validation feedback, fallback content, runtime health
- `13_dramatic_quality_extensions.md` — affect model, emotional state, contradiction guard, steering, preview simulation
- `14_database_migrations.md` — schema additions, indexes, backfill, and backwards-compatibility strategy

## Intended use

This collection is the **freeze candidate** for implementation work.
It is a technical baseline, not a roadmap deck.
It intentionally avoids schedule language and focuses on contracts, flows, guards, and repository seams.

## Scope stance

This is still a foundation MVP, but it is not a narrow runtime-only MVP.
It establishes durable seams for:

- authored content compilation
- constrained runtime execution
- governance review
- research-to-revision workflows
- preview builds and evaluation
- rollback-safe package promotion
- live-play recovery on validation failures
- future dramatic-quality layers
