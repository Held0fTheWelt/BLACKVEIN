"""Tests for Iteration 3 policy layer: PreCheckLane, metrify enforcement, CLI integration."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from fy_platform.ai.contracts import (
    PolicyDecision, EvidenceLink, PreCheckResult
)
from fy_platform.ai.lanes import PreCheckLane, GovernLane
from metrify.adapter.service import MetrifyAdapter


class TestPolicyLayerIR:
    """Test policy layer IR objects."""

    def test_policy_decision_creation(self):
        """PolicyDecision can be created and tracks enforcement decisions."""
        decision = PolicyDecision(
            policy_id='policy-file-size',
            rule_name='file_size_limit',
            decision='deny',
            evidence='File exceeds 10MB limit: repository.tar.gz is 15MB',
            metadata={'limit_mb': 10, 'actual_mb': 15},
        )
        assert decision.policy_id == 'policy-file-size'
        assert decision.decision == 'deny'
        assert decision.rule_name == 'file_size_limit'

    def test_policy_decision_with_evidence_link(self):
        """PolicyDecision can link to evidence artifacts."""
        link = EvidenceLink(
            suite='metrify',
            run_id='metrify-run-1',
            artifact_path='runs/metrify/cost-check.json',
            artifact_type='cost_check',
        )
        decision = PolicyDecision(
            policy_id='policy-token-budget',
            rule_name='token_budget',
            decision='escalate',
            evidence='Token budget exceeded; escalating to admin review',
            evidence_link=link,
        )
        assert decision.evidence_link == link
        assert decision.decision == 'escalate'

    def test_precheck_result_creation(self):
        """PreCheckResult accumulates violations."""
        violation_1 = PolicyDecision(
            policy_id='policy-file-size',
            rule_name='file_size_limit',
            decision='deny',
            evidence='File too large',
        )
        violation_2 = PolicyDecision(
            policy_id='policy-token-budget',
            rule_name='token_budget',
            decision='deny',
            evidence='Token budget exceeded',
        )
        result = PreCheckResult(
            target='repo.tar.gz',
            mode='policy-check',
            is_valid=False,
            violations=[violation_1, violation_2],
        )
        assert result.target == 'repo.tar.gz'
        assert result.is_valid is False
        assert len(result.violations) == 2
        assert all(v.decision == 'deny' for v in result.violations)


class TestPreCheckLane:
    """Test PreCheckLane validation and rule registration."""

    def test_precheck_lane_creation(self):
        """PreCheckLane can be created."""
        lane = PreCheckLane()
        assert lane.rules == {}
        assert lane.violations == []

    def test_register_rule(self):
        """Rules can be registered."""
        lane = PreCheckLane()

        def check_foo(target: Path, mode: str) -> PolicyDecision | None:
            return None

        lane.register_rule('foo_rule', check_foo)
        assert 'foo_rule' in lane.rules

    def test_validate_with_missing_target(self):
        """Validation fails if target does not exist."""
        lane = PreCheckLane()
        result = lane.validate(Path('/nonexistent'), mode='policy-check')
        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0].rule_name == 'target_exists'

    def test_validate_with_custom_rule(self):
        """Custom rules are checked during validation."""
        lane = PreCheckLane()

        def check_forbidden(target: Path, mode: str) -> PolicyDecision | None:
            if target.name == 'forbidden.txt':
                return PolicyDecision(
                    policy_id='policy-forbidden',
                    rule_name='forbidden_names',
                    decision='deny',
                    evidence='Filename matches forbidden pattern',
                )
            return None

        lane.register_rule('forbidden_names', check_forbidden)

        with tempfile.TemporaryDirectory() as tmpdir:
            forbidden_path = Path(tmpdir) / 'forbidden.txt'
            forbidden_path.write_text('test')
            result = lane.validate(forbidden_path, mode='policy-check')
            assert result.is_valid is False
            assert any(v.rule_name == 'forbidden_names' for v in result.violations)

    def test_validate_with_valid_target(self):
        """Validation passes for valid targets."""
        lane = PreCheckLane()
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / 'test.txt'
            target.write_text('test data')
            result = lane.validate(target, mode='policy-check')
            assert result.is_valid is True
            assert len(result.violations) == 0

    def test_validate_with_cost_check_mode(self):
        """cost-check mode skips builtin rules."""
        lane = PreCheckLane()
        with tempfile.TemporaryDirectory() as tmpdir:
            result = lane.validate(Path(tmpdir), mode='cost-check')
            assert result.is_valid is True  # Directory without file size limit


class TestMetrifyEnforcement:
    """Test metrify enforcement gates."""

    def test_metrify_enforce_budget_allow(self):
        """enforce_budget returns allow decision for valid budget."""
        adapter = MetrifyAdapter()
        result = adapter.enforce_budget(
            suite='contractify',
            run_budget={'tokens': 50_000, 'cost_usd': 5.0},
        )
        assert result['decision'] == 'allow'
        assert result['suite'] == 'contractify'

    def test_metrify_enforce_budget_default(self):
        """enforce_budget uses defaults when budget not provided."""
        adapter = MetrifyAdapter()
        result = adapter.enforce_budget(suite='docify')
        assert result['decision'] == 'allow'
        assert 'run_budget' in result
        assert 'policy_ids' in result


class TestGovernLanePolicyIntegration:
    """Test GovernLane integration with policy checks."""

    def test_govern_lane_has_precheck_lane(self):
        """GovernLane owns a PreCheckLane instance."""
        lane = GovernLane()
        assert isinstance(lane.precheck_lane, PreCheckLane)

    def test_govern_lane_records_policy_decisions(self):
        """GovernLane can record policy decisions."""
        lane = GovernLane()
        decision = PolicyDecision(
            policy_id='policy-test',
            rule_name='test_rule',
            decision='allow',
            evidence='Test evidence',
        )
        lane.record_policy_decision(decision)
        assert len(lane.get_policy_decisions()) == 1
        assert lane.get_policy_decisions()[0].policy_id == 'policy-test'
