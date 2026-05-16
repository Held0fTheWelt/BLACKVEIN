# Local Langfuse Judge Transfer Bundle

- Schema: `wos_langfuse_judge_transfer_bundle.v1`
- Environment: `local`
- Evidence scope: `local_langfuse`
- Proof level: `local_only`
- Live/staging evidence: `False`
- Judge count: `25`

## Bootstrap Steps

1. Start local Langfuse with `python docker-up.py up`.
2. Open `http://localhost:3000` and create/open the local project.
3. Add judge provider credentials in Project Settings -> LLM Connections.
4. For each judge below, create an LLM-as-a-Judge evaluator targeting Observations.
5. Use the JSON bundle for the exact prompt, categories, and local filters.

Local judge scores are qualitative diagnostics only; they do not change Commit, Readiness, or `validation_outcome`.

## Judges

### 1. `opening_experience_judge`

- Scope: `opening_generation`
- Categories: `excellent, acceptable, weak, invalid`
- Observation name: `story.model.generation`
- Trace name: `world-engine.session.create`
- Environment filter: `local`
- Repair card: `OPEN-EXP-01`

### 2. `role_anchor_quality_judge`

- Scope: `opening_generation`
- Categories: `clear, partial, missing, wrong_role`
- Observation name: `story.model.generation`
- Trace name: `world-engine.session.create`
- Environment filter: `local`
- Repair card: `OPEN-ROLE-01`

### 3. `theatrical_style_judge`

- Scope: `opening_generation`
- Categories: `theatrical, serviceable, flat, bad`
- Observation name: `story.model.generation`
- Trace name: `world-engine.session.create`
- Environment filter: `local`
- Repair card: `OPEN-STYLE-01`

### 4. `actor_lane_narrative_violation_judge`

- Scope: `opening_generation`
- Categories: `no_violation, possible_violation, clear_violation`
- Observation name: `story.model.generation`
- Trace name: `world-engine.session.create`
- Environment filter: `local`
- Repair card: `OPEN-ACTORLANE-01`

### 5. `rag_context_usefulness_judge`

- Scope: `opening_generation`
- Categories: `strong_use, some_use, unused, misused`
- Observation name: `story.model.generation`
- Trace name: `world-engine.session.create`
- Environment filter: `local`
- Repair card: `OPEN-RAG-01`

### 6. `player_action_intent_judge`

- Scope: `turn_generation`
- Categories: `correct_intent, minor_mismatch, wrong_intent, invalid_takeover`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-INTENT-01`

### 7. `narrator_npc_boundary_judge`

- Scope: `turn_generation`
- Categories: `clean_boundary, minor_blur, npc_narrates_action, severe_boundary_violation`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-NPCBOUNDARY-01`

### 8. `visible_card_cleanliness_judge`

- Scope: `turn_generation`
- Categories: `clean, minor_artifacts, messy, broken_cards`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-CARD-01`

### 9. `turn_relevance_judge`

- Scope: `turn_generation`
- Categories: `directly_relevant, broadly_relevant, weakly_related, irrelevant_or_wrong`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-RELEVANCE-01`

### 10. `language_consistency_judge`

- Scope: `turn_generation`
- Categories: `consistent, minor_drift, mixed_language, wrong_language`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-LANG-01`

### 11. `dramatic_pacing_judge`

- Scope: `turn_generation`
- Categories: `strong_pacing, acceptable_pacing, weak_pacing, broken_pacing`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-PACING-01`

### 12. `goc_tone_fidelity_judge`

- Scope: `turn_generation`
- Categories: `strong_fidelity, acceptable_fidelity, generic_tone, wrong_tone`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-GOC-TONE-01`

### 13. `player_action_resolution_judge`

- Scope: `turn_generation`
- Categories: `resolved_well, partially_resolved, misresolved, not_resolved`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-ACTION-RESOLUTION-01`

### 14. `blocked_action_playability_judge`

- Scope: `turn_generation`
- Categories: `playable_block, acceptable_clarification, unclear_block, technical_failure`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-BLOCKED-PLAY-01`

### 15. `affordance_plausibility_judge`

- Scope: `turn_generation`
- Categories: `plausible, acceptable_inference, questionable, implausible`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-AFFORDANCE-01`

### 16. `npc_reaction_appropriateness_judge`

- Scope: `turn_generation`
- Categories: `appropriate_reaction, minor_overreaction, unnecessary_commentary, npc_takes_over`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-NPC-REACTION-01`

### 17. `runtime_aspect_integrity_judge`

- Scope: `turn_generation`
- Categories: `complete, mostly_complete, incomplete, missing, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `RUNTIME-ASPECT-EVIDENCE-01`

### 18. `narrator_authority_judge`

- Scope: `turn_generation`
- Categories: `fulfilled, mostly_fulfilled, partial_or_ambiguous, violated, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `AUTH-NARRATOR-01`

### 19. `npc_authority_violation_judge`

- Scope: `turn_generation`
- Categories: `no_violation, minor_blur, ambiguous_violation, clear_violation, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `AUTH-NPC-01`

### 20. `dramatic_capability_realization_judge`

- Scope: `turn_generation`
- Categories: `realized_correctly, mostly_realized, partially_realized, violated_or_missing, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `CAP-REALIZE-01`

### 21. `beat_realization_judge`

- Scope: `turn_generation`
- Categories: `strong_realization, serviceable_realization, weak_realization, not_realized, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `BEAT-REALIZE-01`

### 22. `recoverable_outcome_quality_judge`

- Scope: `turn_generation`
- Categories: `playable_recovery, acceptable_recovery, weak_recovery, failed_recovery, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `RECOVERY-OUTCOME-01`

### 23. `visible_origin_consistency_judge`

- Scope: `turn_generation`
- Categories: `consistent, mostly_consistent, inconsistent_or_incomplete, contradictory, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `VISIBLE-ORIGIN-01`

### 24. `relationship_pressure_judge`

- Scope: `turn_generation`
- Categories: `strong_pressure, serviceable_pressure, weak_pressure, missing_or_wrong, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `RELATION-PRESSURE-01`

### 25. `player_turn_playability_judge`

- Scope: `turn_generation`
- Categories: `playable, mostly_playable, weakly_playable, unplayable, not_applicable, insufficient_evidence`
- Observation name: `story.model.generation`
- Trace name: `world-engine.turn.execute`
- Environment filter: `local`
- Repair card: `TURN-PLAYABILITY-01`
