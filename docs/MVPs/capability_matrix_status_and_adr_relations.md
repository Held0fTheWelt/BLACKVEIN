# Capability matrix and ADR relations

Last updated: 2026-05-13

This file serves two purposes:

1. **Gate table** — capabilities from the gated MVP slice × **ADR-001–016** × normative ADR paths (unchanged intent).
2. **Runtime intelligence overlay** — where legacy “Π”-style ideas went in **today’s modules**, maturity labels, and **what is still not a first-class runtime aspect** (beat realization, narrator/NPC authority ledger, dramatic capability selection).

Legacy Π symbols are **not** active feature names in source. Content is distributed across contracts, heuristics, diagnostics, Langfuse traces, and planning docs. Treat Π references as **historical vocabulary** when reading the maturity tables below.

### Gate test oracle policy (cross-cutting)

Promotion and validation are meaningless if gate tests **encode accidental output** instead of declared contracts. **[ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md)** forbids hardcoded literals as the **primary** oracle for gate and promotion-style regression tests; expectations must trace to schema, OpenAPI, canonical authored content ([ADR-0025](../ADR/adr-0025-canonical-authored-content-model.md)), or reviewable baselines. This tightens how we read **[ADR-0008](../ADR/adr-0008-validation-strategy-explicit-configurable.md)** (strategy-specific tests must still be honest) and **[ADR-0009](../ADR/adr-0009-evaluation-is-a-promotion-gate.md)** (evaluation evidence must not be “string-matched theatre”).

**Operational inventory:** [`docs/governance/gate_oracle_tightness_inventory.md`](../governance/gate_oracle_tightness_inventory.md) tracks gate oracle quality (strict vs brittle) and refactor waves. **Staging / live provider credentials:** same document **§10** — use MCP/backend credential retrieval for readiness; never paste or report secrets; `non_mock_generation_pass` and related Langfuse scores stay degraded when credentials are missing. **Wave 1** (rows 1, 5–11, 16, 21, 22): YAML fixtures, canonical title loader, CI YAML oracle, ADR-0033 snippet dedup, MVP4 mock payloads. **Wave 2** (rows 12, 13, 14, 17): LDSS wiring via import + AST; FastAPI route AST + manager surface; narrative gov admin template via `data-testid`, derived proxy URL, and panel JSON keys; `execute_turn` diagnostics via AST + subprocess integration test. See §9 in that document for commands and status.

### Observability authority (non-negotiable split)

```text
Frontend ≠ observability authority
Backend / world-engine + Langfuse = observability authority
```

```text
Frontend stays visually and functionally largely stable.
Backend / world-engine / Langfuse must supply missing system-level observability.
```

The frontend is **not** the observability authority. The current player shell should remain **visually stable** and continue rendering **backend-provided** player-facing story cards. Dramatic observability must be produced by **backend/world-engine runtime records** and **Langfuse spans/scores**. Frontend changes should be limited to **optional presentation** improvements (e.g. card color tuning, readability, typewriter UX) and **displaying backend-provided diagnostics** — not to inferring dramatic correctness.

The frontend is **not** where beat, narrator, NPC, or capability **logic** should originate. It should keep rendering story cards as today.

The **frontend** may at most **display** what the backend already supplies. It must **not** infer or own answers to:

- Was the beat realized?
- Was the NPC allowed to do that?
- Was the narrator responsible?
- Which capability was selected / violated?

Those decisions belong in the **runtime / backend path**, recorded for **Langfuse** (spans, scores, path summaries), then optionally surfaced in the shell. **BeatRealization UI**, **NarratorAuthority UI**, and **dramatic Capability UI** are **not** frontend obligations unless the backend first emits authoritative fields.

**Division of responsibility:** the **frontend** remains the **play surface**; **Langfuse** is the **analysis surface**; the **world-engine** remains **canonical truth**.

**Frontend status (summary):** Implemented as player-facing rendering shell. Keep visually stable. Optional card color/readability improvements are allowed. Runtime intelligence observability belongs to backend/world-engine and Langfuse, not the frontend.

---

## Status legend (gate table)

| Status | Meaning |
|--------|---------|
| `implemented` | Enforced in the gated live-runtime / contract slice. |
| `partially_proven` | Contract or code present; end-to-end proof uneven. |
| `target_state` | Roadmap / not fully closed in the active slice. |

Gate ADR list source: `docs/MVPs/MVP_Live_Runtime_Completion/*.md` and `tests/reports/MVP_Live_Runtime_Completion_IMPLEMENTATION_REPORT.md`.

---

## Extended maturity legend (runtime intelligence overlay)

Use these in **Table B** only. They refine “partial” for narrative/dramatic systems.

| Label | Meaning |
|-------|---------|
| `implemented` | Behavior exists on the live GoC / world-engine path; locators below. |
| `partial` | Real code, but incomplete authority, enforcement, or end-to-end story. |
| `scaffold` | Module or data exists; not clearly wired into the live turn path. |
| `not_wired_to_live_path` | Implemented in tree but not exercised as canonical turn behavior. |
| `not_found_in_source` | No durable locator in this repo (policy / content-only / future). |

---

## Table A — Gated capabilities × ADR (canonical)

| Area | Capability | Contract / anchor (short) | Status | MVP gate ADR(s) | ADR record path(s) |
|------|------------|---------------------------|--------|-----------------|-------------------|
| World-Engine | Authoritative session truth & commit | `commit_seam`, narrative commit | implemented | ADR-004, ADR-005 | [`docs/ADR/adr-0001-runtime-authority-in-world-engine.md`](../ADR/adr-0001-runtime-authority-in-world-engine.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-005-canonical-content-authority.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-005-canonical-content-authority.md); [`docs/ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md`](../ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md) |
| World-Engine | Turn seam pipeline | proposal → validate → commit → render | implemented | ADR-004, ADR-016 | [`docs/ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md`](../ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md); [`docs/ADR/adr-0033-live-runtime-commit-semantics.md`](../ADR/adr-0033-live-runtime-commit-semantics.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md) |
| World-Engine | Turn counter (opening vs player, rollback) | `turn_counter`, turn 0 opening | implemented | ADR-004, ADR-016 | [`docs/ADR/adr-0033-live-runtime-commit-semantics.md`](../ADR/adr-0033-live-runtime-commit-semantics.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md) |
| World-Engine | Beat progression | `BeatProgression`, carry-forward | partially_proven | ADR-007, ADR-011 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-007-minimum-agency-baseline-superseded.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-007-minimum-agency-baseline-superseded.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md) |
| World-Engine | Session lifecycle & content snapshot | session, `content_snapshot` | partially_proven | ADR-001, ADR-002 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-001-experience-identity.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-001-experience-identity.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-002-runtime-profile-resolver.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-002-runtime-profile-resolver.md) |
| World-Engine | Runtime provenance | `runtime_state.v1`, hashes | partially_proven | ADR-001, ADR-002 | Same as previous row |
| World-Engine | Actor lanes | `ActorLaneContext` | implemented | ADR-003, ADR-004 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-003-role-selection-actor-ownership.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-003-role-selection-actor-ownership.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-004-actor-lane-enforcement.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp2-004-actor-lane-enforcement.md) |
| World-Engine | NPC coercion boundary | state delta / validation | implemented | ADR-003, ADR-004 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-003-npc-coercion-state-delta.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp2-003-npc-coercion-state-delta.md) |
| World-Engine | Object admission | `ObjectAdmissionRecord`, tiers | implemented | ADR-015 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-015-environment-affordances.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp2-015-environment-affordances.md) |
| World-Engine | Protected truth / state delta | `StateDeltaBoundary` | implemented | ADR-005 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-005-canonical-content-authority.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-005-canonical-content-authority.md) |
| World-Engine | Continuity carry-forward | `continuity_impacts` | partially_proven | ADR-007, ADR-011 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-007-minimum-agency-baseline-superseded.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-007-minimum-agency-baseline-superseded.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md) |
| World-Engine | Recoverable / playable rejection | recoverable turn path | partially_proven | ADR-004, ADR-008 | [`docs/ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md`](../ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md) — maps to “failure-as-story” *fragment* |
| World-Engine | P0 action resolution evidence (path summary) | `p0_action_resolution_evidence.v1` | partially_proven | ADR-004, ADR-009 | [`world-engine/app/story_runtime/manager.py`](../../world-engine/app/story_runtime/manager.py) (`_build_p0_action_resolution_evidence`); ADR-009 for traceability — **if a static archive lacks this field, compare archive date to checkout** |
| AI | Proposal-only until validation | model vs commit | implemented | ADR-004, ADR-005 | [`docs/ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md`](../ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-005-canonical-content-authority.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-005-canonical-content-authority.md) |
| AI | Evidence-gated capabilities | capability reports | implemented | ADR-006 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-006-evidence-gated-capabilities.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-006-evidence-gated-capabilities.md) |
| AI | Turn graph orchestration | LangGraph executor, seams | implemented | ADR-004, ADR-016 | [`docs/ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md`](../ADR/adr-0004-runtime-model-output-proposal-only-until-validator-approval.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md) |
| AI | Semantic move / interpreted move | `semantic_move_contract`, GoC interpretation | partially_proven | ADR-004, ADR-011 | [`ai_stack/semantic_move_contract.py`](../../ai_stack/semantic_move_contract.py); [`ai_stack/semantic_move_interpretation_goc.py`](../../ai_stack/semantic_move_interpretation_goc.py) |
| AI | Scene director (responder, pacing, silence) | `scene_director_goc`, `scene_plan_contract` | partially_proven | ADR-011, ADR-012 | [`ai_stack/scene_director_goc.py`](../../ai_stack/scene_director_goc.py); [`ai_stack/scene_plan_contract.py`](../../ai_stack/scene_plan_contract.py) |
| AI | Social state / relationship pressure | `social_state_contract`, GoC application | partially_proven | ADR-011 | [`ai_stack/social_state_contract.py`](../../ai_stack/social_state_contract.py); [`ai_stack/social_state_goc.py`](../../ai_stack/social_state_goc.py) |
| AI | Character mind / voice records | `character_mind_contract`, GoC | partially_proven | ADR-011, ADR-013 | [`ai_stack/character_mind_contract.py`](../../ai_stack/character_mind_contract.py); [`ai_stack/character_mind_goc.py`](../../ai_stack/character_mind_goc.py) |
| AI | Player action resolution (stage-1) | `player_action_resolution.py` | partially_proven | ADR-004, ADR-015 | [`ai_stack/player_action_resolution.py`](../../ai_stack/player_action_resolution.py) — not fully authority-equivalent to commit seam |
| AI | GoC turn seams / continuity on commit | `goc_turn_seams` | partially_proven | ADR-004, ADR-011 | [`ai_stack/goc_turn_seams.py`](../../ai_stack/goc_turn_seams.py) |
| AI | Capability registry (technical) | `capabilities.py`, default registry | partially_proven | ADR-006 | [`ai_stack/capabilities.py`](../../ai_stack/capabilities.py); **not** narrator/NPC dramatic capability catalog |
| AI | Validation strategy | configurable validators | partially_proven | ADR-004, ADR-008, ADR-0039 | [`docs/ADR/adr-0008-validation-strategy-explicit-configurable.md`](../ADR/adr-0008-validation-strategy-explicit-configurable.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md); [`docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md`](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) |
| AI | RAG / retrieval governance | runtime retrieval + trace summary | partially_proven | ADR-006 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-006-evidence-gated-capabilities.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-006-evidence-gated-capabilities.md); [`docs/technical/ai/RAG.md`](../technical/ai/RAG.md) |
| AI | Research / bounded AI (off live truth) | review-bound pipelines | partially_proven | ADR-006 | [`docs/MVPs/world_of_shadows_canonical_mvp/16_ai_stack_bounded_research_and_control_plane_support.md`](world_of_shadows_canonical_mvp/16_ai_stack_bounded_research_and_control_plane_support.md) |
| AI | SLM vs LLM stratification (policy) | routing roles | target_state | ADR-006 | [`docs/technical/ai/llm-slm-role-stratification.md`](../technical/ai/llm-slm-role-stratification.md) |
| Narration | LDSS | live dramatic scene simulator | partially_proven | ADR-011, ADR-016 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md) |
| Narration | Narrative runtime agent / streaming | narrator events | target_state | ADR-011, ADR-013 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-013-narrator-inner-voice-contract.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-013-narrator-inner-voice-contract.md) |
| Narration | Structured scene output | `SceneTurnEnvelope.v2`, blocks | partially_proven | ADR-011, ADR-014 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp5-001-modular-block-rendering-architecture.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp5-001-modular-block-rendering-architecture.md) |
| Narration | NPC agency | `NPCAgencyPlan` | target_state | ADR-012 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-012-npc-free-dramatic-agency.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-012-npc-free-dramatic-agency.md) |
| Narration | Passivity guard | visible actor response | implemented | ADR-012 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-012-npc-free-dramatic-agency.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-012-npc-free-dramatic-agency.md) |
| Narration | Narrator inner voice | narrator validation | implemented | ADR-013 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-013-narrator-inner-voice-contract.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-013-narrator-inner-voice-contract.md) |
| Narration | Environment affordances | similar / canonical / typical | implemented | ADR-015 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-015-environment-affordances.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp2-015-environment-affordances.md) |
| Branching / threads | Narrative threads & branching scaffolds | `story_runtime_core/branching`, `narrative_threads*` | partially_proven | ADR-007, ADR-011 | not proven as active future-tree planner on GoC live path |
| Authoring | Writers room pipeline | services + routes | partially_proven | ADR-006, ADR-010 | [`writers-room/`](../../writers-room/); [`backend/app/services/`](../../backend/app/services/) `writers_room_*` |
| Observability | Diagnostics & degradation | normal / degraded / failed | implemented | ADR-008 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md) |
| Observability | Langfuse & traceable decisions | traces, decision IDs | implemented | ADR-009 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-009-langfuse-traceable-decisions.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-009-langfuse-traceable-decisions.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-002-langfuse-integration.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-002-langfuse-integration.md) |
| Observability | Narrative Gov operator surface | health / truth panels | implemented | ADR-010 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-010-narrative-gov-operator-truth-surface.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-010-narrative-gov-operator-truth-surface.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-004-narrative-gov-panels.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-004-narrative-gov-panels.md) |
| World-Engine / Langfuse | Runtime aspect ledger | backend-owned turn aspect record (input, beat, capability, authority, commit, visible realization) | target_state | ADR-009, ADR-010, future aspect ADR | Required so beat, narrator/NPC authority, capability selection, commit, and visible realization are **observable without changing the player shell**. Include Langfuse aspect spans and deterministic scores (e.g. `story.beat.realize`, `beat_realized`, `npc_takeover_absent`) as part of the same target. [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-009-langfuse-traceable-decisions.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-009-langfuse-traceable-decisions.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-010-narrative-gov-operator-truth-surface.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-010-narrative-gov-operator-truth-surface.md) |
| World-Engine / Langfuse | Beat lifecycle observability | BeatState, BeatSelection, BeatRealization, BeatValidation | target_state | ADR-011, ADR-009 | Must be visible in Langfuse and backend diagnostics — **not** inferred by the frontend. [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp3-011-live-dramatic-scene-simulator.md) |
| World-Engine / Langfuse | Narrator/NPC authority observability | expected_owner, actual_owner, npc_takeover_absent, narrator_required_when_expected | target_state | ADR-012, ADR-013, ADR-009 | Must prove whether narrator and NPC lanes behaved correctly. |
| World-Engine / Langfuse | Dramatic capability observability | selected_capabilities, blocked_capabilities, realized_capabilities | target_state | ADR-006, ADR-009 | Must show which player/narrator/NPC capabilities were selected, blocked, or violated. |
| World-Engine / Langfuse | Visible output origin tracking | origin_aspect, origin_beat_id, origin_capability, authority_owner | target_state | ADR-009, ADR-014 | Backend attaches metadata **before** the frontend renders. The frontend may ignore it visually or show it only as passive display. |
| QA / eval | Evaluation pipeline & judges | Langfuse-linked | partially_proven | ADR-006, ADR-009, ADR-0039 | [`ai_stack/evaluation_pipeline.py`](../../ai_stack/evaluation_pipeline.py); [`docs/ADR/adr-0009-evaluation-is-a-promotion-gate.md`](../ADR/adr-0009-evaluation-is-a-promotion-gate.md); [`docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md`](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) |
| Frontend | Player-facing story shell | structured scene blocks, `player_display_text`, typewriter delivery ([`frontend/static/play_block_renderer.js`](../../frontend/static/play_block_renderer.js), [`play_block_display_text.js`](../../frontend/static/play_block_display_text.js), [`play_blocks_orchestrator.js`](../../frontend/static/play_blocks_orchestrator.js), [`play_typewriter_engine.js`](../../frontend/static/play_typewriter_engine.js)) | implemented | ADR-014, ADR-0034 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp5-001-modular-block-rendering-architecture.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp5-001-modular-block-rendering-architecture.md); [`docs/ADR/adr-0034-player-facing-narrative-shell-contract.md`](../ADR/adr-0034-player-facing-narrative-shell-contract.md) — Stay visually/functionally close to the current shell; render backend-provided cards; **not** the authority for beat, narrator/NPC, capability, or aspect observability. |
| Frontend | Card styling / visual polish | card colors, emphasis, readable lane styling | partially_proven | ADR-014, ADR-0034 | Cosmetic improvements allowed; must **not** change runtime authority or infer dramatic correctness. |
| Frontend | Optional diagnostics display | backend-provided diagnostics only | partially_proven | ADR-008, ADR-010 | May display fields the backend sends; must **not** compute beat realization, narrator ownership, NPC authority, or capability correctness in the client. [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-008-diagnostics-degradation-semantics.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp4-010-narrative-gov-operator-truth-surface.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp4-010-narrative-gov-operator-truth-surface.md) |
| Operations | Operational gates | docker-up, `tests/run_tests.py`, CI | implemented | ADR-016, ADR-0039 | [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp1-016-operational-gates.md); [`docs/ADR/MVP_Live_Runtime_Completion/adr-mvp2-016-operational-gates.md`](../ADR/MVP_Live_Runtime_Completion/adr-mvp2-016-operational-gates.md); [`docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md`](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) |
| Properties | Session / world-state schema (tiers) | MVP bundle contracts | partially_proven | ADR-001–ADR-005 | [`docs/ADR/adr-0025-canonical-authored-content-model.md`](../ADR/adr-0025-canonical-authored-content-model.md) |
| Properties | Narrative package / revision / evaluation | governance data model | target_state | ADR-006, ADR-010 | [`docs/ADR/adr-0007-revision-conflicts-explicit-governance-objects.md`](../ADR/adr-0007-revision-conflicts-explicit-governance-objects.md); [`docs/ADR/adr-0009-evaluation-is-a-promotion-gate.md`](../ADR/adr-0009-evaluation-is-a-promotion-gate.md) |

**ADR-016:** Two accepted files (`adr-mvp1-016`, `adr-mvp2-016`) — one logical gate.

Redirect: [`ADR_GATED_IMPLEMENTATION_LOCK_MAP.md`](ADR_GATED_IMPLEMENTATION_LOCK_MAP.md) → this file.

### Supplement — player shell display only (non-authoritative)

These are **implemented or partial in the repo** as **display / diagnostics**, not as runtime proof of beat realization, authority, or capability correctness (see **Observability authority**). They support the **Player-facing story shell** and **Optional diagnostics** rows above; this list is for **source locators** only.

| Surface | Role | Evidence (indicative) | Maturity |
|---------|------|----------------------|----------|
| Structured blocks + `player_display_text` | Player-visible rendering; `data-block-type`, actor/speaker attributes, diagnostics vs player-visible separation | [`frontend/static/play_block_renderer.js`](../../frontend/static/play_block_renderer.js), [`play_block_display_text.js`](../../frontend/static/play_block_display_text.js) | implemented (render) |
| Typewriter / slice queue | Single active typewriter, deferred mount of later slices | [`play_blocks_orchestrator.js`](../../frontend/static/play_blocks_orchestrator.js), [`play_typewriter_engine.js`](../../frontend/static/play_typewriter_engine.js) | implemented |
| Runtime status / passivity / vitality | Operator-oriented summaries (quality, degradation, passivity, vitality) — does not explain *why* a beat or authority failed | [`frontend/app/routes_play.py`](../../frontend/app/routes_play.py), [`frontend/templates/session_shell.html`](../../frontend/templates/session_shell.html) | partial (display) |
| Dramatic context whitelist | Shows a bounded set of dramatic fields (`scene_function`, `pacing_mode`, `silence_mode`, retrieval, thread pressure, social continuity, `beat_id`, …) when backend supplies them | `_DRAMATIC_CONTEXT_DISPLAY_SPECS` in [`routes_play.py`](../../frontend/app/routes_play.py) | partial (display) |
| Beat labels on blocks | `beat_id`, `narration_beat`, `data-narration-beat` can surface — **no** `BeatRealization` / `beat_realized` semantics in the shell | [`routes_play.py`](../../frontend/app/routes_play.py), [`play_block_renderer.js`](../../frontend/static/play_block_renderer.js), [`frontend/tests/test_block_renderer.js`](../../frontend/tests/test_block_renderer.js) | partial (label only) |

There is **no** frontend-centric Runtime Aspect Ledger UI, narrator/NPC authority contract display, or dramatic capability matrix until **backend + Langfuse** emit those fields (Table A: **World-Engine / Langfuse** `target_state` rows).

### Frontend evolution boundaries (allowed vs forbidden)

**May improve (UX only, no new authority):**

- More stable typewriter sequencing
- Clearer errors on recoverable turns
- Cleaner reveal-all behavior
- No duplicate cards; no name-only empty cards
- Better colors per card type; better narrator/NPC/player lane readability

**Must not:**

- Implement beat system logic in the frontend
- Derive NPC authority in the frontend
- Decide capability selection in the frontend
- Replace Langfuse evidence with UI inference (`visible text → frontend decides correctness`)

---

## Trace exports vs static archives

Langfuse / API path summaries may include fields that a **given** `current_repo.zip` or older checkout does not yet contain (or the opposite: source ahead of export schema). **Always pair trace timestamp with git SHA.**

Example in **this** repository: `p0_action_resolution_evidence` is built in [`world-engine/app/story_runtime/manager.py`](../../world-engine/app/story_runtime/manager.py) and asserted in [`world-engine/tests/test_story_runtime_api.py`](../../world-engine/tests/test_story_runtime_api.py). If an archive shows the field in traces but not in source, the archive is stale relative to that trace (or traces were produced from a different branch).

**Gap:** Dramatic aspects do **not** need to originate in the frontend. They **must** originate in backend/world-engine runtime records and Langfuse spans/scores. The frontend may render backend-provided metadata, but it must **not** be responsible for *determining* beat realization, narrator/NPC authority, or capability correctness. Today, those aspects are **not** consistently first-class in Langfuse or path summaries either — observability for *narrative* enforcement still lags *validation* outcomes (`approved`, boundary flags).

### Observability data flow (target)

**Correct:**

```text
World-Engine decides
→ backend delivers blocks + optional metadata
→ Langfuse stores aspect spans/scores
→ frontend renders as today (optional display of backend fields)
```

**Incorrect:**

```text
frontend interprets visible text
→ frontend decides whether beat/NPC/narrator/capability was correct
```

(Equivalent extended chain: runtime decision → aspect record → validation/commit consumes record → visible output carries origin metadata → Langfuse span + score → optional frontend display.)

### Target model (illustrative JSON)

Illustrative shape for `turn_aspect_ledger` (not implemented as a single object today):

```json
{
  "turn_aspect_ledger": {
    "beat": {
      "selected": "domestic_disruption",
      "realized": false,
      "failure_reason": "not_visible_in_scene_blocks"
    },
    "narrator_authority": {
      "required": true,
      "expected_owner": "narrator",
      "actual_owner": "npc",
      "status": "failed"
    },
    "npc_authority": {
      "policy": "social_reaction_only",
      "npc_takeover_detected": true,
      "offending_actor_id": "veronique"
    },
    "capability_selection": {
      "selected_capabilities": [
        "player.object_interaction.attempt",
        "narrator.physical_consequence"
      ],
      "blocked_capabilities": [
        "npc.execute_player_action"
      ],
      "realized_capabilities": [
        "npc.execute_player_action"
      ],
      "status": "failed"
    },
    "visible_projection": {
      "blocks_have_origin_aspect": true,
      "lost_required_narrator_block": false
    }
  }
}
```

The frontend may display this **if** the API exposes it; **Langfuse and the backend must prove it.**

---

## Table B — Legacy Π themes → today’s surfaces (maturity)

Π labels are **index only**; read the “Today’s surface” and “Maturity” columns as authoritative.

| Π (index) | Theme (short) | Today’s surface (primary) | Maturity | Notes |
|-----------|---------------|---------------------------|----------|--------|
| Π1 | Hierarchical memory | `manager.py`, `narrative_threads*`, RAG store, social/mind records | partial | Session + threads + RAG; not a single 12-domain AI memory selector. |
| Π2 | Graph workflow | `ai_stack/langgraph_runtime_executor.py` | implemented | interpret → action resolve → RAG → director → model → validate → commit → render. |
| Π3 | Advanced RAG | `ai_stack/rag*.py`, hybrid / embeddings | implemented | Stronger than lexical-only reference scaffolds. |
| Π4 | MCP | `tools/mcp_server/`, `ai_stack/mcp_*` | partial | Ops / Langfuse verify; not a full runtime boundary for all game systems. |
| Π5 | “Modern AI” meta-reasoning | LangGraph + retry + judges | partial | No dedicated ToT/Reflexion *engine* as product. |
| Π6 | Governance | `live_runtime_commit_semantics.py`, `governed_runtime.py`, `manager.py` | partial | Truth/commit strong; beat/narrator/NPC *aspect* governance weak. |
| Π7 | Multi-agent NPC | `scene_director_goc.py`, `character_mind_goc.py`, telemetry | partial | Responder selection; not full multi-agent simulation. |
| Π8 | Contingency / future trees | `story_runtime_core/branching/*`, threads | scaffold | Data/scaffold; not active future-tree planner on live GoC path. |
| Π9 | Context synthesis | `rag_context_pack_*`, `_assemble_model_context` | partial | Assembly ≠ full “synthesis” engine. |
| Π10 | Voice consistency | content + `character_mind_goc.py`, eval | partial | Records/judges; weak enforcement loop. |
| Π11 | Scene energy | `build_pacing_and_silence`, `scene_plan_contract` | partial | No `SceneEnergy` system type. |
| Π12 | Thematic tracking | content / YAML hints | not_found_in_source | No theme tracker in code. |
| Π13 | Intent inference | `input_interpreter.py`, `semantic_move_interpretation_goc.py` | partial | Heuristic / rule-heavy. |
| Π14 | Silence / negative space | `build_pacing_and_silence`, `semantic_move_contract` | partial | Signals exist; not full dramatic capability. |
| Π15 | Environmental story | visible render, opening, scene guidance | partial | No place-system. |
| Π16 | Dramatic irony | social/mind (indirect) | partial | Weak / indirect. |
| Π17 | Callback web | threads, `continuity_impacts`, branching | partial | No callback index *engine*. |
| Π18 | Pacing rhythm | scene director + plan | partial | Pacing yes; rhythm engine no. |
| Π19 | Subtext | semantic move + director | partial | Pressure/tactics; no surface-vs-intent model. |
| Π20 | Mystery rationing | — | not_found_in_source | |
| Π21 | Consequence cascade | `goc_turn_seams` continuity, branching consequences | partial | Facts without full cascade engine visibility. |
| Π22 | Tension calibration | social state, director, dramatic gates | partial | Bands, not continuous metric. |
| Π23 | Agency preservation | `goc_turn_seams`, actor lane, `manager.py` | partial → strong on human lane | Narrator/NPC authority aspects weaker. |
| Π24 | Improvisational coherence | dramatic validation | partial | No yes-and system. |
| Π25 | Meta-awareness | meta input handling | partial | Recognition only. |
| Π26 | Sensory layering | prompts / content | not_found_in_source | |
| Π27 | Relationship dynamics | `social_state_goc.py`, mind, director | partial | No NPC↔NPC simulation. |
| Π28 | Time manipulation | — | not_found_in_source | |
| Π29 | Surprise budget | content hints | not_found_in_source | |
| Π30 | Failure-as-story | recoverable rejection in `manager.py` | partial | Playable rejection exists; not full no-dead-end system. |
| Π31 | Momentum | dramatic gates, alignment | partial | |
| Π32 | Genre awareness | GoC content / prompts | partial | |
| Π33 | Symbolic resonance | — | not_found_in_source | |
| Π34 | Active listening | interpreter, command resolution | partial | Heuristics, not NLU “listening”. |
| Π35 | Tonal consistency | eval, judges, voice | partial | Drift monitor not hard runtime loop. |
| Π36–Π46 | Platform (authoring, analytics, replay, god mode, A/B, VCS, QA, cost, multi-author, assets, profiling) | writers-room, Langfuse, MCP, governance routes, improvement routes | partial | See Table A rows for authoring/obs/eval. |

---

## Constructs still missing as first-class runtime (debugging pain)

Responsibility for closing these gaps is **backend / world-engine + Langfuse**, not the player shell (see **Observability authority** above).

These names are **not** centralized in source today; they explain why traces can look “legal” while dramatic intent is opaque:

- `BeatState`, `BeatCandidate`, `BeatSelection`, `BeatTransition`, `BeatRealization`, `BeatValidation`
- `NarratorAuthorityContract`, `NpcAuthorityContract`, `npc_takeover_absent`, `narrator_required_when_expected`
- `PlayerRuntimeCapability`, `NarratorRuntimeCapability`, `NpcRuntimeCapability`, `CapabilitySelection`, `CapabilityRealization`, `CapabilityViolation`
- `RuntimeAspectLedger` / `turn_aspect_ledger` (single place tying **selected** beat/capability/authority → **visible** blocks)

**What exists instead (fragments):** `semantic_move`, `scene_function`, `pacing_mode`, `silence_brevity_decision`, `selected_responder_set`, `character_mind_records`, `social_state_record`, `dramatic_effect_gate`, `visible_output_bundle`, `p0_action_resolution_evidence`.

---

## Suggested next implementation locus (non-normative)

If ADRs are added later for aspect observability, candidate integration points:

- [`ai_stack/langgraph_runtime_executor.py`](../../ai_stack/langgraph_runtime_executor.py)
- [`world-engine/app/story_runtime/manager.py`](../../world-engine/app/story_runtime/manager.py)
- [`ai_stack/goc_turn_seams.py`](../../ai_stack/goc_turn_seams.py)

Pair with **Langfuse spans / deterministic aspect scores** so exports do not drift from enforceable runtime state.

---

## Reference package (external)

Normative **five-layer target** and **reference scaffold** (v21) live under `D:\MVP\mvp\` — see `mvp/docs/03_FIVE_LAYER_EXECUTION_ARCHITECTURE.md` and `mvp/reference_scaffold/wos_mvp/`. That tree is **not** the live `D:\WorldOfShadows` runtime; use it for lineage and demos, not production authority.
