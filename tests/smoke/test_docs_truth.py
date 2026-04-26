"""Docs truth tests: verify active docs do not contain forbidden legacy content.

These tests inspect active documentation paths and fail on prohibited patterns.
They are not mere file existence checks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_ACTIVE_DOC_PATHS = [
    _REPO_ROOT / "docs" / "architecture",
    _REPO_ROOT / "docs" / "testing",
    _REPO_ROOT / "docs" / "ADR",
    _REPO_ROOT / "docs" / "admin",
]


def _collect_active_docs() -> list[Path]:
    """Collect all .md files under active documentation paths (excluding archive)."""
    docs: list[Path] = []
    for base in _ACTIVE_DOC_PATHS:
        if not base.exists():
            continue
        for f in base.rglob("*.md"):
            if "archive" in f.parts:
                continue
            docs.append(f)
    return docs


class TestActiveDocsForbiddenContent:
    """Active documentation must not contain forbidden legacy content."""

    def test_active_docs_do_not_describe_visitor_as_valid_actor(self):
        """Active docs must not instruct that 'visitor' is a valid live actor."""
        forbidden_phrases = [
            "visitor is a valid",
            "visitor as a role",
            "visitor actor",
            "visitor participant",
            "visitor lane",
            "add visitor",
            "create visitor",
        ]
        violations: list[str] = []
        for doc_path in _collect_active_docs():
            content = doc_path.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in forbidden_phrases:
                if phrase in content:
                    violations.append(f"{doc_path.name}: contains '{phrase}'")

        assert not violations, (
            "Active docs contain forbidden visitor-as-valid-actor guidance:\n"
            + "\n".join(violations)
        )

    def test_active_docs_do_not_describe_goc_solo_as_canonical_content(self):
        """Active docs must not describe god_of_carnage_solo as a canonical content module."""
        forbidden_phrases = [
            "god_of_carnage_solo is canonical",
            "god_of_carnage_solo as content",
            "canonical module: god_of_carnage_solo",
            "module_id: god_of_carnage_solo",
        ]
        violations: list[str] = []
        for doc_path in _collect_active_docs():
            content = doc_path.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in forbidden_phrases:
                if phrase in content:
                    violations.append(f"{doc_path.name}: contains '{phrase}'")

        assert not violations, (
            "Active docs describe god_of_carnage_solo as canonical content:\n"
            + "\n".join(violations)
        )

    def test_active_docs_do_not_cite_stale_reports_as_gate_proof(self):
        """Active docs must not cite stale PASS reports as current gate evidence."""
        forbidden_phrases = [
            "GOC_MVP2_SOURCE_LOCATOR",
            "GOC_MVP3_SOURCE_LOCATOR",
            "GOC_MVP4_SOURCE_LOCATOR",
            "MVP1_SOURCE_LOCATOR",
            "MVP2_SOURCE_LOCATOR",
            "MVP3_SOURCE_LOCATOR",
            "MVP4_SOURCE_LOCATOR",
            "GOC_PHASE5_FINAL_MVP_CLOSURE",
        ]
        violations: list[str] = []
        for doc_path in _collect_active_docs():
            content = doc_path.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in forbidden_phrases:
                if phrase in content:
                    violations.append(f"{doc_path.name}: references stale report '{phrase}'")

        assert not violations, (
            "Active docs cite stale reports as gate evidence:\n"
            + "\n".join(violations)
        )

    def test_active_docs_do_not_describe_builtin_as_production_truth(self):
        """Active docs must not describe built-in/demo content as canonical production proof."""
        forbidden_phrases = [
            "builtin is canonical",
            "built-in content is production",
            "demo content is canonical",
            "builtin template is canonical",
        ]
        violations: list[str] = []
        for doc_path in _collect_active_docs():
            content = doc_path.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in forbidden_phrases:
                if phrase in content:
                    violations.append(f"{doc_path.name}: contains '{phrase}'")

        assert not violations, (
            "Active docs describe built-in content as production truth:\n"
            + "\n".join(violations)
        )


class TestActiveDocsRequiredContracts:
    """Active documentation must include current contracts."""

    def test_service_boundaries_doc_exists(self):
        """docs/architecture/current_service_boundaries.md must exist and be substantial."""
        path = _REPO_ROOT / "docs" / "architecture" / "current_service_boundaries.md"
        assert path.exists(), f"current_service_boundaries.md not found at {path}"
        assert path.stat().st_size > 500, "current_service_boundaries.md is too small"

    def test_god_of_carnage_contract_exists(self):
        """docs/architecture/god_of_carnage_current_contract.md must exist and be substantial."""
        path = _REPO_ROOT / "docs" / "architecture" / "god_of_carnage_current_contract.md"
        assert path.exists(), f"god_of_carnage_current_contract.md not found at {path}"
        assert path.stat().st_size > 500, "god_of_carnage_current_contract.md is too small"

    def test_runtime_profile_vs_content_contract_exists(self):
        """docs/architecture/runtime_profile_vs_content_contract.md must exist."""
        path = _REPO_ROOT / "docs" / "architecture" / "runtime_profile_vs_content_contract.md"
        assert path.exists(), f"runtime_profile_vs_content_contract.md not found at {path}"
        assert path.stat().st_size > 500, "runtime_profile_vs_content_contract.md is too small"

    def test_observability_traceability_contract_exists(self):
        """docs/architecture/observability_traceability_contract.md must exist."""
        path = _REPO_ROOT / "docs" / "architecture" / "observability_traceability_contract.md"
        assert path.exists(), f"observability_traceability_contract.md not found at {path}"
        assert path.stat().st_size > 500, "observability_traceability_contract.md is too small"

    def test_test_suite_contract_exists(self):
        """docs/testing/TEST_SUITE_CONTRACT.md must exist."""
        path = _REPO_ROOT / "docs" / "testing" / "TEST_SUITE_CONTRACT.md"
        assert path.exists(), f"TEST_SUITE_CONTRACT.md not found at {path}"
        assert path.stat().st_size > 500, "TEST_SUITE_CONTRACT.md is too small"

    def test_visitor_prohibition_is_documented(self):
        """The visitor prohibition must be stated in active architecture docs."""
        goc_contract = _REPO_ROOT / "docs" / "architecture" / "god_of_carnage_current_contract.md"
        assert goc_contract.exists()
        content = goc_contract.read_text(encoding="utf-8")
        assert "visitor" in content.lower(), "GoC contract must document the visitor prohibition"
        assert "FORBIDDEN" in content or "prohibited" in content.lower(), (
            "GoC contract must explicitly prohibit visitor"
        )

    def test_canonical_runner_documented(self):
        """The canonical runner path must be stated in the test suite contract."""
        contract = _REPO_ROOT / "docs" / "testing" / "TEST_SUITE_CONTRACT.md"
        assert contract.exists()
        content = contract.read_text(encoding="utf-8")
        assert "tests/run_tests.py" in content, (
            "TEST_SUITE_CONTRACT.md must document tests/run_tests.py as canonical runner"
        )

    def test_no_root_runner_mentioned_as_canonical(self):
        """Active testing docs must not mention run-test.py as canonical."""
        forbidden = "run-test.py"
        for doc_path in _collect_active_docs():
            content = doc_path.read_text(encoding="utf-8", errors="replace")
            # Allow mentions in historical context only; forbidden as "canonical" instruction
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if forbidden in line and any(
                    kw in line.lower()
                    for kw in ["canonical", "use this", "run with", "invoke with", "entry point"]
                ):
                    pytest.fail(
                        f"{doc_path.name}:{i+1}: mentions run-test.py as canonical runner: {line.strip()}"
                    )
