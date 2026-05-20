# NPC Interactivity Roadmap — PIV Index

**Status:** Living document
**Created:** 2026-05-19
**Last refreshed:** 2026-05-20 (Phase 2 documentation pass — ADR-0058/0059/0060 aligned with implemented Stages A–M)
**Roadmap source:** [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md)
**Reviewer rule:** False or invented `file:line` references in any linked PIV artifact are reject-worthy. Every claim about runtime structure must trace to a verified source location at the time the PIV was written.

---

## 1. Purpose

This index tracks the **Phase Implementation Verification (PIV)** artifacts produced for each PR on the NPC Interactivity roadmap. A PIV artifact captures, **before code is written**, the consumer scan, the existing-path probe, the live-smoke feasibility probe, anti-dead-end checkpoints, the `file:line` references to all anchors the PR will touch or extend, and the list of paths that must remain untouched.

The PIV log is the bridge between the roadmap plan (which is dramaturgical and architectural) and the implementation PR (which must execute against verified reality). It is **not** a duplicate of the plan — it is the record that "we looked at the actual code on the day before we wrote the PR" and what we found.

## 2. Roadmap structure (high-level)

The roadmap defines Phase 1 (free player action + Director-Pause) and Phase 2 (Director-driven pulse, Block-Stream-Bus, Souffleuse inner voice). Each phase has thematically ordered PRs. PR-0 is the **contracts + verification preamble** that lets PR-A/PR-B/PR-C proceed against a stable specification.

| Phase | PR | Theme | Status | PIV artifact |
|-------|----|-------|--------|--------------|
| 1 | **PR-0** | Runtime contracts + PIV baseline + diagnostic snapshot envelope | **Draft (this commit)** | [`pr_0_npc_interactivity_contracts_piv.md`](../implementation_logs/pr_0_npc_interactivity_contracts_piv.md) |
| 1 | **PR-A** | Resolver-Contract closure (`free_player_action_resolution.v1`, `resolved_target_type: "location"` for movement) | **Draft (this commit)** | [`pr_a_resolver_contract_closure_piv.md`](../implementation_logs/pr_a_resolver_contract_closure_piv.md) |
| 1 | **PR-B** | Live-effect propagation (`narrator_consequence_realization.v1`, `canonical_path_hold_effect.v1`) | **Draft (this commit)** | [`pr_b_live_effect_propagation_piv.md`](../implementation_logs/pr_b_live_effect_propagation_piv.md) |
| 1 | **PR-C** | Director-Pause mode (`director_gathering_state.v1`, `compute_gathering_state`, beat-consumption gate, narrator reaction hook) | **Draft** | [`pr_c_director_pause_mode_piv.md`](../implementation_logs/pr_c_director_pause_mode_piv.md) |
| 2 | ADR-0058 / Pulse-MVP | Director-driven tick + Block-Stream-Bus (Stages A–M + Completion Pass) | **Shipped** — see [`phase_2_director_pulse_status.md`](phase_2_director_pulse_status.md) | [`phase_2_director_pulse_status.md`](phase_2_director_pulse_status.md) |
| 2 | ADR-0059 | Motivation-Score (per-NPC, principled-deterministic; Stage-F three-tier source classification) | **Shipped** — see [`phase_2_director_pulse_status.md`](phase_2_director_pulse_status.md) | [`phase_2_director_pulse_status.md`](phase_2_director_pulse_status.md) |
| 2 | ADR-0060 | Souffleuse inner-voice composition + Stage M NPC follow-up dispatcher | **Shipped** (Souffleuse contract surface + Stage M template/semantic dispatcher with closed-enum safety gates) — see [`phase_2_director_pulse_status.md`](phase_2_director_pulse_status.md). Live Director-composed Souffleuse pressure-escalation blocks and production semantic-provider wiring remain Future Work (§5.2). | [`phase_2_director_pulse_status.md`](phase_2_director_pulse_status.md) |

## 3. PIV artifact requirements

Every PIV artifact under [`docs/implementation_logs/`](../implementation_logs/) must include the following sections. The list is enforced by gate test `tests/test_npc_interactivity_piv_baseline.py::test_pr_0_piv_artifact_required_sections` for PR-0; future PRs may add their own PIV gate.

1. **Consumer scan** — list of every production file that today consumes the contracts this PR will introduce or extend (`grep` / semantic-search anchors with `file:line`).
2. **Existing-path probe** — what code path runs today for the action class this PR targets, with verified `file:line` anchors.
3. **Live-smoke feasibility probe** — what evidence exists (or does not yet exist) that the proposed change can be observed in a live session (Langfuse spans, runtime aspect ledger rows, operator endpoints, UI surfaces).
4. **Anti-dead-end checkpoints** — what failure modes were considered, and how the PR will surface them as observable runtime evidence (not silent fallbacks).
5. **File:line references** — every anchor cited in the plan **re-verified** at the time the PIV is written. Discrepancies between plan-file references and current truth must be recorded explicitly.
6. **What existing paths will be extended later** — explicit list of files the PR will _not_ touch in its current scope but will extend in a subsequent PR (forward declaration of follow-up scope).
7. **What must not be touched in PR-0 (or this PR)** — the negative scope: paths whose semantics this PR pledges to leave unchanged.

## 4. Capability-name vocabulary discipline

PIV artifacts and the ADRs they reference use **semantic capability names** (e.g. `npc_agency`, `scene_energy`, `social_pressure`, `relationship_state`, `pacing_rhythm`, `silence_negative_space`, `voice_consistency`, `narrative_momentum`, `subtext`, `dramatic_irony`, `hierarchical_memory`, `agency_preservation`, `branching_simulation`). Π / Pi labels remain index-only in the [Capability Matrix](capability_matrix_status_and_adr_relations.md); they must not appear as active runtime keys, contract identifiers, MCP payload fields, Langfuse score names, or UI routing keys.

This is the same vocabulary discipline enforced by [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) and the production scans in `tests/gates/test_adr_0039_pi_scope.py` and `tests/gates/test_table_b_anti_hardcoding_gate.py`.

## 5. Related governance

- [`capability_matrix_status_and_adr_relations.md`](capability_matrix_status_and_adr_relations.md) — current capability truth map and ADR ownership.
- [`capability_matrix_live_claim_gates.md`](capability_matrix_live_claim_gates.md) — promotion rules; live/staging/Langfuse/MCP claim gates.
- [`capability_matrix_verification_log.md`](capability_matrix_verification_log.md) — dated verification runs and limitations.
- [ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) — gate-test oracle policy.
- [ADR-0057](../ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md) — canon-safe player freedom contract surface (Phase 1 amendment lives here).
- [ADR-0061 (Draft)](../ADR/adr-0061-director-pause-mode-for-gathering-interruption.md) — Director-Pause mode contract (delivered with PR-C).
- [ADR-0062](../ADR/adr-0062-director-realization-thin-path.md) — Resolver → Director → Narrator thin path; PR-A movement realization rides on this composition path.

## 6. Update protocol

When a PR opens against this roadmap:

1. Create a PIV artifact under `docs/implementation_logs/` with the required sections.
2. Add a row to the table in §2 with status `Draft` and a link to the artifact.
3. When the PR merges, change the status to `Merged` and record the merge SHA in the PIV artifact's footer.
4. When a subsequent PR invalidates a verification claim from an older PIV, the older artifact must be amended with a `Superseded by` note rather than rewritten silently.
