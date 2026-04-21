# Research-and-Canon-Improvement MVP Implementation Summary

## Scope
This implementation realizes the bounded Research-and-Canon-Improvement MVP defined in `docs/ROADMAP_MVP_RESEARCH_AND_CANON_IMPROVEMENT_SYSTEM.md` with deterministic contracts, budget-enforced exploration, structured canon improvement outputs, and review-safe publication posture.

## Implemented modules
- `ai_stack/research_contract.py`
  - canonical owner for status model, contradiction classes, abort reasons, relation enums, issue/proposal taxonomies, legal transitions, and mandatory exploration-budget contract.
- `ai_stack/research_store.py`
  - deterministic persistent structured store for source/anchor/aspect/exploration/claim/issue/proposal/run records.
  - hard referential integrity checks for source/anchor/aspect/node/edge/claim links.
  - governance field hardening (`provenance`, `metadata`, `outputs`, `preview_patch_ref` cannot be semantically empty).
- `ai_stack/research_ingestion.py`
  - deterministic source normalization, operational copyright posture enforcement, segmentation, and anchor creation.
  - segment records now carry `source_id` to enforce source-local aspect extraction.
- `ai_stack/research_perspectives.py`
  - perspective-separated deterministic extraction rules (playwright, director, actor, dramaturg).
- `ai_stack/research_aspect_extraction.py`
  - extraction and persistence of perspective-specific aspect records.
- `ai_stack/research_exploration.py`
  - bounded exploration engine with deterministic branching, pruning, budget accounting, and stable abort semantics.
  - explicit time abort reason (`time_budget_exhausted`) and explicit elapsed wall-time reporting.
- `ai_stack/research_validation.py`
  - canonical owner for promotion decisions, block logic, and contradiction-aware verification flow.
  - promotion requires `kept_for_validation` exploration outcome and known anchor references.
- `ai_stack/canon_improvement_contract.py`
  - canonical issue/proposal mapping contract.
- `ai_stack/canon_improvement_engine.py`
  - deterministic canon issue detection and taxonomy-bound proposal generation.
  - issues/proposals are persisted as review artifacts (`approved_research`) to avoid silent canon adoption semantics.
- `ai_stack/research_langgraph.py`
  - orchestrates six pipeline phases (intake -> extraction -> exploration -> verification -> canon improvement -> review bundle) without owning classification truth.
  - review bundle now includes an explicit populated `aspects` section and computed `review_safe` posture.
  - canon relevance hint is derived deterministically from exploration content, not hardcoded.

## MCP/capability integration
- `ai_stack/capabilities.py`
  - added read-only tools:
    - `wos.research.source.inspect`
    - `wos.research.aspect.extract`
    - `wos.research.claim.list`
    - `wos.research.run.get`
    - `wos.research.exploration.graph`
    - `wos.canon.issue.inspect`
  - added review-bound tools:
    - `wos.research.explore`
    - `wos.research.validate`
    - `wos.research.bundle.build`
    - `wos.canon.improvement.propose`
    - `wos.canon.improvement.preview`
  - capability-level hard budget validation for exploration.
  - exploration audit summary includes compact consumed/effective budget evidence.
- `ai_stack/mcp_canonical_surface.py`
  - canonical MCP descriptors extended for full research/canon MVP tool surface.
- `tools/mcp_server/tools_registry.py`
  - MCP handlers implemented for all new research/canon tools.
  - MCP-level hard budget validation for `wos.research.explore`.

## RAG support extension
- `ai_stack/rag.py`
  - added retrieval domain `research` and aligned profile metadata for deterministic retrieval usage in research workflows.

## Determinism enforcement
- Golden tests are fixture-driven and do not depend on live probabilistic model behavior.
- Deterministic ordering/tie behavior is enforced in:
  - source/aspect ordering,
  - exploration node and edge ID generation,
  - branch traversal order,
  - claim and proposal ordering,
  - bundle section layout.
- Structural outcomes are deterministic under fixed fixture + budget inputs.
- Only wording fields are allowed bounded textual variance.
- Golden A-F tests were strengthened with explicit expected outputs (IDs/shapes/order/statuses) instead of subset-only smoke assertions.

## Review safety
- Review bundle generation is recommendation-only.
- Canon mutation is explicitly blocked in output governance fields.
- No direct canon apply/publish flow is introduced in MVP.
- Inspector comparison rendering enforces a structured turn-to-turn view (mandatory dimension, status/dimensions, row table, and row blocks for nested comparison fields) with full JSON retained as secondary view.
