"""Tests for Iteration 3 policy layer: PreCheckLane, metrify enforcement, CLI integration."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from fy_platform.ai.contracts import (
    PolicyDecision, EvidenceLink, PreCheckResult
)


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
