"""Tests for fy v2 foundation pass: platform CLI, lanes, IR, and core-thinning."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from contractify.adapter.service import ContractifyAdapter
from fy_platform.ai.contracts import (
    Contract, ContractProjection, TestObligation, DocumentationObligation,
    SecurityRisk, StructureFinding, EvidenceLink, DecisionRecord
)
from fy_platform.ai.lanes import (
    InspectLane, GovernLane, GenerateLane, VerifyLane, StructureLane
)
from fy_platform.ai.run_helpers import RunLifecycleHelper, PayloadBundleHelper
from fy_platform.tools import platform_cli


class TestFyV2TransitionIR:
    """Test fy v2 transition IR objects."""

    def test_evidence_link_creation(self):
        """Evidence link can be created and serialized."""
        link = EvidenceLink(
            suite='contractify',
            run_id='run-123',
            artifact_path='runs/contractify/audit.json',
            artifact_type='audit_result',
        )
        assert link.suite == 'contractify'
        assert link.run_id == 'run-123'

    def test_contract_creation(self):
        """Contract can be created with evidence."""
        link = EvidenceLink('contractify', 'run-1', 'path/to/audit', 'audit_result')
        contract = Contract(
            contract_id='contract-1',
            name='User API',
            contract_type='openapi',
            suite='contractify',
            evidence=link,
            metadata={'openapi_version': '3.0.0'},
        )
        assert contract.contract_id == 'contract-1'
        assert contract.suite == 'contractify'

    def test_structure_finding_creation(self):
        """Structure finding can be created."""
        finding = StructureFinding(
            finding_id='finding-1',
            title='File too large',
            finding_type='spike_file',
            severity='high',
            path='fy_platform/ai/base_adapter.py',
            suite='despaghettify',
            remediation_hint='Extract mechanical responsibilities',
        )
        assert finding.finding_id == 'finding-1'
        assert finding.severity == 'high'

    def test_decision_record_creation(self):
        """Decision record tracks platform evolution."""
        decision = DecisionRecord(
            decision_id='decision-1',
            title='Extract run lifecycle helpers',
            decision_type='extract',
            status='implemented',
            rationale='Reduce base_adapter concentration',
            related_findings=['finding-1'],
        )
        assert decision.decision_id == 'decision-1'
        assert decision.status == 'implemented'
        assert decision.related_findings == ['finding-1']


class TestExplicitLanes:
    """Test explicit lane runtime."""

    def test_inspect_lane_creation(self):
        """Inspect lane can be instantiated."""
        lane = InspectLane()
        assert lane.adapter is None

    def test_inspect_lane_with_adapter(self):
        """Inspect lane can accept an adapter."""
        adapter = ContractifyAdapter()
        lane = InspectLane(adapter)
        assert lane.adapter is not None
        assert lane.adapter.suite == 'contractify'

    def test_inspect_lane_analyze(self):
        """Inspect lane can run analysis."""
        lane = InspectLane()
        result = lane.analyze(Path('.'), mode='standard')
        assert 'target' in result
        assert 'mode' in result
        assert result['mode'] == 'standard'

    def test_govern_lane_creation(self):
        """Govern lane can be instantiated."""
        lane = GovernLane()
        assert lane.adapter is None
        assert lane.violations == []

    def test_govern_lane_check_readiness(self):
        """Govern lane can check readiness."""
        lane = GovernLane()
        result = lane.check_readiness(mode='release')
        assert 'ready' in result or 'mode' in result

    def test_generate_lane_creation(self):
        """Generate lane can be instantiated."""
        lane = GenerateLane()
        assert lane.contracts == []
        assert lane.obligations == []

    def test_generate_lane_register_contract(self):
        """Generate lane can register contracts."""
        lane = GenerateLane()
        link = EvidenceLink('test', 'run-1', 'path', 'audit')
        contract = Contract('c1', 'API', 'openapi', 'test', link)
        lane.register_contract(contract)
        assert len(lane.get_contracts()) == 1

    def test_verify_lane_creation(self):
        """Verify lane can be instantiated."""
        lane = VerifyLane()
        assert lane.risks == []
        assert lane.errors == []

    def test_verify_lane_validate(self):
        """Verify lane can validate targets."""
        lane = VerifyLane()
        result = lane.validate(None, mode='strict')
        assert 'valid' in result or 'mode' in result

    def test_structure_lane_creation(self):
        """Structure lane can be instantiated."""
        lane = StructureLane()
        assert lane.findings == []
        assert lane.decisions == []

    def test_structure_lane_analyze(self):
        """Structure lane can analyze structure."""
        lane = StructureLane()
        result = lane.analyze(Path('.'), mode='standard')
        assert 'target' in result
        assert 'mode' in result


class TestPlatformCLI:
    """Test fy v2 platform CLI shell."""

    def test_analyze_contract(self):
        """fy analyze --mode contract works."""
        result = platform_cli.main(['analyze', '--mode', 'contract', '--format', 'json'])
        assert result == 0

    def test_analyze_docs(self):
        """fy analyze --mode docs works."""
        result = platform_cli.main(['analyze', '--mode', 'docs', '--format', 'json'])
        assert result == 0

    def test_analyze_structure(self):
        """fy analyze --mode structure works."""
        result = platform_cli.main(['analyze', '--mode', 'structure', '--format', 'json'])
        assert result == 0

    def test_govern_release(self):
        """fy govern --mode release works."""
        result = platform_cli.main(['govern', '--mode', 'release', '--format', 'json'])
        assert result == 0

    def test_inspect_structure(self):
        """fy inspect --mode structure works."""
        result = platform_cli.main(['inspect', '--mode', 'structure', '--format', 'json'])
        assert result == 0

    def test_repair_plan_structure(self):
        """fy repair-plan --mode structure works."""
        result = platform_cli.main(['repair-plan', '--mode', 'structure', '--format', 'json'])
        assert result == 0

    def test_platform_cli_help(self):
        """fy --help works (exits with SystemExit)."""
        with pytest.raises(SystemExit) as exc_info:
            platform_cli.main(['--help'])
        assert exc_info.value.code == 0

    def test_platform_cli_unknown_mode(self):
        """fy analyze --mode invalid fails gracefully."""
        # argparse calls sys.exit on error
        with pytest.raises(SystemExit) as exc_info:
            platform_cli.main(['analyze', '--mode', 'invalid', '--format', 'json'])
        # Exit code 2 is argparse's standard error code
        assert exc_info.value.code == 2


class TestCoreThinnningWave:
    """Test first core-thinning wave extraction."""

    def test_run_lifecycle_helper_exists(self):
        """RunLifecycleHelper module exists and imports."""
        from fy_platform.ai.run_helpers import RunLifecycleHelper
        assert RunLifecycleHelper is not None

    def test_payload_bundle_helper_exists(self):
        """PayloadBundleHelper module exists and imports."""
        from fy_platform.ai.run_helpers import PayloadBundleHelper
        assert PayloadBundleHelper is not None

    def test_base_adapter_uses_helpers(self):
        """BaseAdapter delegates to extracted helpers."""
        adapter = ContractifyAdapter()
        # Verify helpers are initialized
        assert hasattr(adapter, '_run_lifecycle')
        assert hasattr(adapter, '_bundle_helper')
        assert adapter._run_lifecycle is not None
        assert adapter._bundle_helper is not None

    def test_base_adapter_reduced(self):
        """base_adapter.py is smaller after extraction."""
        base_path = Path(__file__).parent.parent / 'ai' / 'base_adapter.py'
        lines = len(base_path.read_text(encoding='utf-8').splitlines())
        # Should be < 700 (was originally exactly 700)
        assert lines < 700, f'base_adapter.py is {lines} lines (should be < 700)'


class TestDespaghettifyTransitionMode:
    """Test despaghettify transition stabilization."""

    def test_despaghettify_can_audit_platform(self):
        """Despaghettify has audit_platform_evolution method."""
        from despaghettify.adapter.service import DespaghettifyAdapter
        adapter = DespaghettifyAdapter()
        assert hasattr(adapter, 'audit_platform_evolution')
        assert callable(adapter.audit_platform_evolution)

    def test_legacy_suite_cli_compat(self):
        """Legacy suite CLI (ai_suite_cli) still works."""
        from fy_platform.tools import ai_suite_cli
        # Verify legacy CLI is importable and functional
        assert hasattr(ai_suite_cli, 'main')
        assert callable(ai_suite_cli.main)
        # Basic invocation
        result = ai_suite_cli.main(['contractify', 'explain', '--format', 'json'])
        assert result == 0


class TestLegacyCompatibility:
    """Test that new platform layer doesn't break existing suites."""

    def test_contractify_still_works(self):
        """Contractify adapter still works with extracted helpers."""
        adapter = ContractifyAdapter()
        # Should initialize without error
        assert adapter.suite == 'contractify'
        assert adapter.root is not None
        # Should have extracted helpers
        assert adapter._run_lifecycle is not None
        assert adapter._bundle_helper is not None

    def test_inspect_command_works(self):
        """Suite inspect command still works."""
        adapter = ContractifyAdapter()
        result = adapter.inspect()
        assert 'ok' in result
        assert 'suite' in result


class TestPlatformMode:
    """Test that platform-mode features work alongside suite-mode."""

    def test_lane_and_adapter_coexist(self):
        """Lanes and adapters work together."""
        adapter = ContractifyAdapter()
        lane = InspectLane(adapter)
        assert lane.adapter.suite == 'contractify'

    def test_ir_used_in_lane(self):
        """IR objects are used in lane operations."""
        lane = GenerateLane()
        link = EvidenceLink('test', 'run-1', 'path', 'type')
        contract = Contract('c1', 'Test', 'openapi', 'test', link)
        lane.register_contract(contract)
        contracts = lane.get_contracts()
        assert len(contracts) == 1
        assert isinstance(contracts[0], Contract)
