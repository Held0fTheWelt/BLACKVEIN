# Modular Runtime Intelligence / Π6 Implementation Report

Last updated: 2026-05-14

## Summary

Π6 governance is implemented for the modular runtime-intelligence contract. The
runtime core now consumes generic `ModuleRuntimePolicy` fields, persists a
per-turn `RuntimeAspectLedger`, validates beat/capability/authority/visible
projection evidence before canonical commit, and exposes deterministic evidence
to diagnostics, Langfuse, MCP, and backend projection surfaces.

The implementation remains deliberately module-neutral. God of Carnage provides
content-driven policy through module files; generic runtime code must not
hardcode GoC actor names, locations, phase names, beat ids, sample prose, fixed
visible-card counts, or frontend-derived correctness rules.

## Implemented Capability-Matrix Rows

| Row | Status | Notes |
|---|---|---|
| Π1 Hierarchical memory | implemented session-local | Policy-driven, bounded, committed-turn-only memory tiers; no durable cross-session memory yet. |
| Π6 Governance | implemented | Modular runtime governance for live truth, route family, aspect ledger, beat/capability/authority/visible projection, Langfuse, and MCP evidence. |
| Runtime aspect ledger | partially_proven | Local proof exists; staging proof remains environment-dependent. |
| Beat lifecycle observability | partially_proven | Selected/realized/failure fields exist in ledger and scores; staging proof remains pending. |
| Narrator/NPC authority observability | partially_proven | Policy-driven expectation/fulfillment/takeover evidence exists; staging proof remains pending. |
| Visible output origin tracking | partially_proven | Origin metadata and folding preservation are gate-covered locally; staging proof remains pending. |

## Generic Contracts Added Or Upgraded

- `RuntimeAspectLedger`
- `BeatState`, `BeatCandidate`, `BeatSelection`, `BeatRealization`, `BeatValidation`
- `NarratorAuthorityContract`, `NpcAuthorityContract`, `PlayerAgencyContract`
- `DramaticCapabilitySelection`, `DramaticCapabilityRealization`
- `VisibleBlockOrigin`
- `ModuleRuntimePolicy.runtime_governance_policy`
- Hierarchical memory contracts and ledger aspect fields

All structures are intended to remain JSON-safe for canonical turn records,
diagnostics envelopes, path summaries, Langfuse metadata, backend projection,
and MCP normalized evidence. They must not carry secrets, raw prompts, or large
RAG payloads.

## Module Policy Mapping

God of Carnage maps content into generic policy fields:

- `module.yaml/runtime_intelligence` → `ModuleRuntimePolicy.runtime_governance_policy`
- `memory_policy.yaml` → `ModuleRuntimePolicy.memory_policy`
- `phase_beat_policy.yaml` and `knowledge/opening_scene_sequence.yaml` → phase/beat/opening policy
- `knowledge/hard_forbidden_rules.yaml` → hard-forbidden and recovery policy
- `apartment_layout.yaml`, `apartment_objects.yaml`, and `locale/scene_affordances.yaml` → location/object/affordance policy
- `actor_pressure_profiles.yaml` → actor pressure profile data for scene planning

Runtime algorithms consume the generic policy shape. GoC-specific values may
appear as data values, never as required generic schema keys.

## Runtime Behavior

The turn path now records:

- player input kind, semantic move, action frame, affordance resolution, and
  local-context transition
- candidate and selected beat, selection source, expected visible functions,
  realization evidence, and failure reason
- selected, required, blocked, realized, and violated dramatic capabilities
- narrator requirement, expected owner, actual owner evidence, fulfillment, and
  failure reason
- NPC participation policy, actual actors, takeover detection, offending blocks,
  and pass/fail status
- player-agency violations, if any
- visible block origin metadata and folded-origin preservation evidence
- commit status, degraded/recoverable/fallback signals, and committed-result
  truth
- hierarchical memory write/project status, bounded context, and uncommitted
  write guards

Projection failures that drop required beat/narrator/capability evidence are
blocked or recovered before canonical commit according to module policy.

## Langfuse And MCP Evidence

Runtime aspect spans include:

- `story.aspect.input`
- `story.beat.state`
- `story.beat.select`
- `story.beat.realize`
- `story.authority.narrator`
- `story.authority.npc`
- `story.capability.select`
- `story.capability.realize`
- `story.visible.project`
- `story.commit.apply`
- `story.turn.aspect_summary`
- `story.memory.write`
- `story.memory.project`

Deterministic evidence includes:

- `turn_aspect_ledger_present`
- `beat_selected`
- `beat_realized`
- `narrator_required_when_expected`
- `npc_takeover_absent`
- `capability_selection_present`
- `selected_capabilities_realized`
- `visible_block_origin_present`
- `required_visible_origin_preserved`
- `visible_projection_contract_pass`
- `hierarchical_memory_contract_pass`

MCP verification reads backend/world-engine ledger data and Langfuse scores. It
must not infer correctness from visible prose and must not treat fallback,
mock, or degraded generation as healthy runtime evidence.

## Verification Commands

Recorded local verification:

- `python -m pytest tests/gates/test_adr_live_runtime_commit_semantics_gate.py tests/gates/test_table_b_anti_hardcoding_gate.py -q` → 10 passed.
- `python -m pytest ai_stack/tests/test_runtime_authority_aspects.py ai_stack/tests/test_module_runtime_policy.py ai_stack/tests/test_langgraph_runtime.py ai_stack/tests/test_action_resolution_interact_fallback.py -q` → 38 passed.
- `PYTHONPATH=/mnt/d/WorldOfShadows:/mnt/d/WorldOfShadows/world-engine python -m pytest world-engine/tests/test_story_runtime_aspect_ledger.py world-engine/tests/test_live_story_runtime_governance.py world-engine/tests/test_authority_version_and_route_family_truth.py world-engine/tests/test_story_runtime_narrative_commit.py -q` → 50 passed.
- `python tests/run_tests.py --suite story_runtime_core --quick` → 156 passed.
- `python tests/run_tests.py --suite ai_stack --quick` → 1565 passed, 1 skipped.
- `python -m pytest tools/mcp_server/tests/test_langfuse_verify_tools.py -q` → 29 passed.

Backend full-suite snapshot during parallel Quality Lab work:

- `python -m pytest backend/tests -q` → 4390 passed, 2 skipped, 3 failed.
- The failures were 401 responses in forum/M11 observability tests during a
  moving worktree and are not currently classified as Π6 blockers.

## Anti-Hardcoding Audit

Allowed module-specific literals:

- GoC content files under `content/modules/god_of_carnage/`
- GoC-specific fixture and mapping tests
- explicit module-id constants or compatibility shims with documented scope

Disallowed locations:

- generic runtime contracts
- generic validators
- generic scene-director algorithms
- generic authority/capability algorithms
- frontend authority logic
- MCP generic extraction logic

The implementation gate uses the Table B anti-hardcoding test to prevent
example-shaped or GoC-literal oracles from becoming generic runtime behavior.

## Remaining Target-State Items

- Fresh staging session proof with provider-ready, non-fallback generation.
- Durable cross-session memory store and module policy for long-term memory.
- Broader non-GoC module exercise of the same generic policy contracts.
- Full backend-suite re-run after parallel Quality Lab/Auth work settles.

## Matrix Label Changes

- Table B `Π6 Governance`: `implemented`.
- Table B `Π1 Hierarchical memory`: `implemented session-local`.
- Table A runtime aspect rows remain `partially_proven` where the local code
  and test proof exists but fresh staging evidence is still pending.
