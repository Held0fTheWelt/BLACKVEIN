# `runtime_diagnostic_snapshot.v1` — Contract (PR-0 Stub)

**Status:** PR-0 envelope stub. Populated by PR-A/B/C.
**Date:** 2026-05-19
**Source code (stub):** [`ai_stack/runtime_diagnostic_snapshot_contracts.py`](../../../ai_stack/runtime_diagnostic_snapshot_contracts.py)
**Owning ADR(s):** [ADR-0057 (Phase-1 amendment)](../../ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md), [ADR-0061 (Draft)](../../ADR/adr-0061-director-pause-mode-for-gathering-interruption.md), [ADR-0062 (composition path)](../../ADR/adr-0062-director-realization-thin-path.md)
**PIV artifact:** [`docs/implementation_logs/pr_0_npc_interactivity_contracts_piv.md`](../../implementation_logs/pr_0_npc_interactivity_contracts_piv.md)
**Roadmap source:** [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md) §3.5

---

## 1. Purpose

`runtime_diagnostic_snapshot.v1` is the **single per-turn diagnostic envelope** that the world-engine UI diagnostic pages read from once PR-A/B/C land. It wraps the four Phase-1 NPC-interactivity contracts plus the existing thin-path evidence so each UI page can read structured fields from one snapshot, rather than each page synthesizing its own view from direct Manager / Ledger queries.

The envelope is **read-only diagnostic**. It does not carry control or mutation fields. It does not own commit / readiness decisions. It mirrors data already produced by the runtime.

## 2. Why one envelope (governance rule)

Without a single envelope:

- Each diagnostic page (`diagnostics.html`, `narrative_systems.html`, `runtime_ledger.html`, `live_runtime.html`, `traces_observability.html`, `history_events.html`, `runtime_status.html`) queries the Manager / Ledger / Langfuse independently and may render half-different views.
- The Operator surface becomes noisy and the question "what was the truth this turn?" admits multiple inconsistent answers.

With a single envelope:

- One contract, one truth. One source for diagnostic UI pages. UI pages slice the snapshot by topic; the underlying data is identical across pages.
- Versionable: `runtime_diagnostic_snapshot.v2` etc. extends the contract without breaking existing UI consumers.
- Testable shape: the envelope keys are listed once in `REQUIRED_ENVELOPE_KEYS` and the four contract placeholder names in `REQUIRED_CONTRACT_PLACEHOLDER_NAMES` (see source).

## 3. Envelope shape (PR-0 stub)

Defined in [`ai_stack/runtime_diagnostic_snapshot_contracts.py`](../../../ai_stack/runtime_diagnostic_snapshot_contracts.py):

| Key | Type (stub) | Source contract / origin | Populated by |
|---|---|---|---|
| `schema_version` | `"runtime_diagnostic_snapshot.v1"` | This contract. | PR-0 (constant). |
| `session_id` | `str \| None` | Session identifier. | PR-A. |
| `turn_number` | `int \| None` | Turn number within the session. | PR-A. |
| `canonical_step_id` | `str \| None` | `session.canonical_step_id`. | PR-A. |
| `visible_block_emitted` | `bool \| None` | Did this turn emit at least one block to `visible_scene_output.blocks`? | PR-A. |
| `resolver_output` | `ResolverOutputPlaceholder` | `free_player_action_resolution.v1` (per ADR-0057 amendment). | PR-A. |
| `director_gathering_state` | `DirectorGatheringStatePlaceholder` | `director_gathering_state.v1` (per ADR-0061 Draft). | PR-C. |
| `canonical_path_hold_effect` | `CanonicalPathHoldEffectPlaceholder` | `canonical_path_hold_effect.v1` (per ADR-0057 amendment). | PR-B. |
| `narrator_consequence_realization` | `NarratorConsequenceRealizationPlaceholder` | `narrator_consequence_realization.v1` (per ADR-0057 amendment). | PR-B. |
| `semantic_capability_consultation_names` | `tuple[str, ...]` | List of semantic capability identifiers consulted by the Director this turn. **Semantic runtime names only.** Pi / Pi-numbered ids are not allowed. | PR-A/B/C. |

The four placeholders each carry a `contract_name` constant and a `payload: dict | None` field. PR-A/B/C either populate `payload` with the structured contract fields or replace the placeholder with a richer dataclass — that decision is part of the implementing PR.

## 4. Vocabulary rules (binding for all consumers)

- **Semantic capability names only.** `semantic_capability_consultation_names` carries strings such as the semantic capability identifiers documented in [`docs/MVPs/capability_matrix_status_and_adr_relations.md`](../../MVPs/capability_matrix_status_and_adr_relations.md) (right column of the index mapping). Pi / Pi-numbered ids must not appear in this field; the gate `tests/gates/test_adr_0039_pi_scope.py::test_production_runtime_vocabulary_has_no_active_pi_control_tokens` enforces this on production code.
- **No UI control / mutation fields.** No "advance pointer", "reset director state", or "set canonical step" buttons. The envelope describes; it does not act.
- **No direct per-page Manager / Ledger queries.** UI pages must read this envelope; if a page needs a field the envelope does not yet expose, the fix is to add the field to the envelope (and version it), not to bypass the envelope.

## 5. Lifecycle

- **PR-0 (this commit):** the stub at `ai_stack/runtime_diagnostic_snapshot_contracts.py` declares the envelope shape and the four contract placeholder names. The stub is **not imported** by any production runtime path. No graph node constructs it. No endpoint serializes it.
- **PR-A:** populates `resolver_output`, `canonical_step_id`, `visible_block_emitted`, `session_id`, `turn_number`, and partial `semantic_capability_consultation_names`. The serialization surface is the existing operator endpoint family established by [ADR-0062](../../ADR/adr-0062-director-realization-thin-path.md) (`GET /api/story/sessions/{session_id}/thin-path-summary`); the envelope nests under the existing payload.
- **PR-B:** populates `canonical_path_hold_effect` and `narrator_consequence_realization`.
- **PR-C:** populates `director_gathering_state`.
- **Phase 2 (ADR-0058 / ADR-0059 / ADR-0060):** either extends `runtime_diagnostic_snapshot.v1` field set (if non-breaking) or introduces `runtime_diagnostic_snapshot.v2` (if breaking). PR-0 leaves room for both.

## 6. Acceptance tests (PR-0 scope)

`tests/test_npc_interactivity_piv_baseline.py` verifies:

- The envelope module imports cleanly.
- `RUNTIME_DIAGNOSTIC_SNAPSHOT_SCHEMA_VERSION == "runtime_diagnostic_snapshot.v1"`.
- `REQUIRED_ENVELOPE_KEYS` contains the keys listed in §3.
- `REQUIRED_CONTRACT_PLACEHOLDER_NAMES` contains exactly the four Phase-1 contract names.
- The envelope dataclass has the placeholder fields wired to the placeholder dataclasses.
- The stub module is not imported by any other production module in `ai_stack/`, `backend/app/`, `world-engine/app/`, `story_runtime_core/`, `tools/mcp_server/` (no side-effects in PR-0).
