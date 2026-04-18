from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

WORKSPACE_CONTRACT_VERSION = 'fy.workspace-contract.v2'
COMMAND_ENVELOPE_SCHEMA_VERSION = 'fy.command-envelope.v4'
COMMAND_ENVELOPE_COMPATIBILITY = {
    'current': COMMAND_ENVELOPE_SCHEMA_VERSION,
    'supported_read_versions': ['fy.command-envelope.v3', 'fy.command-envelope.v4'],
    'supported_write_versions': [COMMAND_ENVELOPE_SCHEMA_VERSION],
}
MANIFEST_COMPATIBILITY = {
    'current_manifest_version': 1,
    'supported_manifest_versions': [1],
    'compat_mode': 'autark-outbound',
}
STORAGE_SCHEMA_VERSIONS = {
    'registry': 2,
    'semantic_index': 2,
}
PRODUCTION_READINESS_SCHEMA_VERSION = 'fy.production-readiness.v2'
OBSERVABILITY_SCHEMA_VERSION = 'fy.observability.v2'
RELEASE_MANAGEMENT_FILES = [
    'CHANGELOG.md',
    'docs/platform/BACKWARD_COMPATIBILITY.md',
    'docs/platform/DEPRECATION_POLICY.md',
    'docs/platform/SUPPORT_POLICY.md',
    'docs/platform/RELEASE_POLICY.md',
    'docs/platform/UPGRADE_AND_ROLLBACK.md',
]


# fy v2 Transition IR — Minimal typed objects for platform evolution
# Used to model contracts, findings, and decisions across suite lanes


@dataclass
class EvidenceLink:
    """Reference to evidence from a suite run or analysis."""
    suite: str
    run_id: str
    artifact_path: str
    artifact_type: str  # e.g., 'audit_result', 'wave_plan', 'contract'


@dataclass
class Contract:
    """A discovered contract (API, behavior, interface)."""
    contract_id: str
    name: str
    contract_type: str  # e.g., 'openapi', 'python-interface', 'schema'
    suite: str
    evidence: EvidenceLink
    metadata: dict = field(default_factory=dict)


@dataclass
class ContractProjection:
    """How a contract appears in a specific suite's analysis."""
    contract_id: str
    suite: str
    status: str  # e.g., 'discovered', 'verified', 'drifted'
    coverage: float  # 0.0 to 1.0
    metadata: dict = field(default_factory=dict)


@dataclass
class TestObligation:
    """A test requirement derived from audits."""
    obligation_id: str
    title: str
    test_type: str  # e.g., 'unit', 'integration', 'compatibility'
    severity: str  # e.g., 'high', 'medium', 'low'
    suite: str
    evidence: EvidenceLink
    metadata: dict = field(default_factory=dict)

    __test__ = False  # Prevent pytest from treating this as a test class


@dataclass
class DocumentationObligation:
    """A documentation requirement derived from audits."""
    obligation_id: str
    title: str
    doc_type: str  # e.g., 'api', 'architecture', 'guide'
    audience: str  # e.g., 'developer', 'operator', 'admin'
    severity: str  # e.g., 'high', 'medium', 'low'
    suite: str
    evidence: EvidenceLink
    metadata: dict = field(default_factory=dict)


@dataclass
class SecurityRisk:
    """A security finding from audits."""
    risk_id: str
    title: str
    risk_type: str  # e.g., 'injection', 'auth', 'crypto', 'idor'
    severity: str  # e.g., 'critical', 'high', 'medium', 'low'
    suite: str
    evidence: EvidenceLink
    remediation_hint: str = ''
    metadata: dict = field(default_factory=dict)


@dataclass
class StructureFinding:
    """A structural issue found by despaghettify or similar."""
    finding_id: str
    title: str
    finding_type: str  # e.g., 'spike_file', 'spike_function', 'wrapper_proliferation', 'low_cohesion'
    severity: str  # e.g., 'high', 'medium', 'low'
    path: str  # file or module path
    scope: str | None = None  # e.g., function name for function spikes
    suite: str = 'despaghettify'
    evidence: EvidenceLink | None = None
    remediation_hint: str = ''
    metadata: dict = field(default_factory=dict)


@dataclass
class DecisionRecord:
    """A decision made during platform evolution."""
    decision_id: str
    title: str
    decision_type: str  # e.g., 'extract', 'consolidate', 'deprecate', 'stabilize'
    status: str  # e.g., 'proposed', 'approved', 'implemented', 'superseded'
    rationale: str
    related_findings: list[str] = field(default_factory=list)  # finding IDs
    related_contracts: list[str] = field(default_factory=list)  # contract IDs
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)


@dataclass
class PolicyDecision:
    """A decision made by policy enforcement gates.

    Unlike DecisionRecord (which tracks platform evolution), PolicyDecision
    is specific to governance enforcement (cost gates, validation rules, etc.).
    """
    policy_id: str
    rule_name: str  # e.g., 'file_size_limit', 'token_budget', 'model_availability'
    decision: str  # 'allow', 'deny', or 'escalate'
    evidence: str  # Brief description of why this decision was made
    evidence_link: EvidenceLink | None = None  # Optional link to supporting artifacts
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)

    __test__ = False  # Prevent pytest from treating this as a test class


@dataclass
class PreCheckResult:
    """Result of pre-check validation (input to PreCheckLane.validate()).

    PreCheckResult accumulates violations before work begins.
    """
    target: str  # Path or identifier being validated
    mode: str  # e.g., 'policy-check', 'cost-check', 'full'
    is_valid: bool  # True if no violations
    violations: list[PolicyDecision] = field(default_factory=list)  # List of policy violations
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)
