"""Wave 2 — Actor Truth Preservation: Implementation verification tests.

Verify that:
1. Playability recovery decision includes preserve_actor_lanes when actor lanes approved + prose-only reject
2. Rewrite instruction properly embeds preserve constraint
3. Build_rewrite_instruction handles both preserve and actor-lane-issue branches
"""

from __future__ import annotations

import pytest

from ai_stack.story_runtime_playability import decide_playability_recovery, build_rewrite_instruction


class TestPlayabilityRecoveryPreserveActorLanes:
	"""Verify recover decision includes preserve_actor_lanes when appropriate."""

	def test_preserve_actor_lanes_true_when_approved_lanes_and_empty_fluency_reject(self):
		"""preserve_actor_lanes=True when actor lanes approved + dramatic_effect_reject_empty_fluency."""
		outcome = {
			"status": "rejected",
			"reason": "dramatic_effect_reject_empty_fluency",
		}
		actor_lane_validation = {
			"status": "approved",
			"reason": "",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=actor_lane_validation,
		)
		assert decision.preserve_actor_lanes is True

	def test_preserve_actor_lanes_true_when_approved_lanes_and_short_narrative_reject(self):
		"""preserve_actor_lanes=True when actor lanes approved + dramatic_alignment_narrative_too_short."""
		outcome = {
			"status": "rejected",
			"reason": "dramatic_alignment_narrative_too_short",
		}
		actor_lane_validation = {
			"status": "approved",
			"reason": "",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=actor_lane_validation,
		)
		assert decision.preserve_actor_lanes is True

	def test_preserve_actor_lanes_true_when_approved_lanes_and_empty_output_reject(self):
		"""preserve_actor_lanes=True when actor lanes approved + empty_visible_output."""
		outcome = {
			"status": "rejected",
			"reason": "empty_visible_output",
		}
		actor_lane_validation = {
			"status": "approved",
			"reason": "",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=actor_lane_validation,
		)
		assert decision.preserve_actor_lanes is True

	def test_preserve_actor_lanes_false_when_no_actor_validation(self):
		"""preserve_actor_lanes=False when no actor_lane_validation provided."""
		outcome = {
			"status": "rejected",
			"reason": "dramatic_effect_reject_empty_fluency",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=None,
		)
		assert decision.preserve_actor_lanes is False

	def test_preserve_actor_lanes_false_when_rejected_lanes(self):
		"""preserve_actor_lanes=False when actor lanes rejected."""
		outcome = {
			"status": "rejected",
			"reason": "dramatic_effect_reject_empty_fluency",
		}
		actor_lane_validation = {
			"status": "rejected",
			"reason": "actor_lane_illegal_actor",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=actor_lane_validation,
		)
		assert decision.preserve_actor_lanes is False

	def test_preserve_actor_lanes_false_when_non_prose_reject(self):
		"""preserve_actor_lanes=False when rejection reason is not prose-only."""
		outcome = {
			"status": "rejected",
			"reason": "actor_lane_illegal_actor",
		}
		actor_lane_validation = {
			"status": "approved",
			"reason": "",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=actor_lane_validation,
		)
		assert decision.preserve_actor_lanes is False

	def test_preserve_actor_lanes_false_when_outcome_approved(self):
		"""preserve_actor_lanes=False when outcome status is already approved."""
		outcome = {
			"status": "approved",
			"reason": "goc_default_validator_pass",
		}
		actor_lane_validation = {
			"status": "approved",
			"reason": "",
		}
		decision = decide_playability_recovery(
			turn_number=1,
			attempt_index=1,
			max_attempts=2,
			outcome=outcome,
			generation={"success": True},
			proposed_state_effects=[{"effect_type": "narrative", "description": "test"}],
			actor_lane_validation=actor_lane_validation,
		)
		assert decision.preserve_actor_lanes is False


class TestRewriteInstructionPreservation:
	"""Verify rewrite instruction includes preserve constraint when appropriate."""

	def test_rewrite_instruction_includes_preserve_message_when_preserve_true(self):
		"""Rewrite instruction should include preserve message when preserve_actor_lanes=True."""
		instruction = build_rewrite_instruction(
			["dramatic_effect_reject_empty_fluency"],
			preserve_actor_lanes=True,
		)
		assert "structurally valid" in instruction.lower()
		assert "do not change" in instruction.lower()
		assert "only improve narration_summary" in instruction.lower()

	def test_rewrite_instruction_omits_preserve_when_false(self):
		"""Rewrite instruction should not include preserve message when preserve_actor_lanes=False."""
		instruction = build_rewrite_instruction(
			["dramatic_effect_reject_empty_fluency"],
			preserve_actor_lanes=False,
		)
		assert "do not change" not in instruction

	def test_rewrite_instruction_with_actor_lane_issues_includes_preserve(self):
		"""Preserve message should come before actor-lane feedback."""
		instruction = build_rewrite_instruction(
			["actor_lane_illegal_actor", "dramatic_effect_reject_empty_fluency"],
			preserve_actor_lanes=True,
		)
		assert "do not change" in instruction.lower()
		assert "only improve narration_summary" in instruction.lower()
		assert "actor_lane" in instruction.lower()

	def test_rewrite_instruction_base_structure(self):
		"""Rewrite instruction should contain standard structure requirements."""
		instruction = build_rewrite_instruction(
			["dramatic_effect_reject_empty_fluency"],
			preserve_actor_lanes=False,
		)
		assert "canonical module boundaries" in instruction.lower()
		assert "character reaction" in instruction.lower()

	def test_rewrite_instruction_with_actor_lane_codes_includes_actor_feedback(self):
		"""When actor-lane codes present, should include actor-specific guidance."""
		instruction = build_rewrite_instruction(
			["actor_lane_illegal_actor"],
			allowed_actor_ids=["alice", "bob"],
			preserve_actor_lanes=False,
		)
		assert "actor" in instruction.lower()
		assert "spoken_lines" in instruction.lower()
		assert "alice" in instruction.lower() or "bob" in instruction.lower()


if __name__ == "__main__":
	pytest.main([__file__, "-v"])
