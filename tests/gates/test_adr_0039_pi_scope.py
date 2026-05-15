"""ADR-0039 coverage for Pi / Π capability tests and verification evidence.

Pi / Π labels may remain in historical test names and fixture metadata, but
ADR-0039 must govern those tests. This gate makes that scope auditable.
"""

from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]

PI_REFERENCE_RE = re.compile(
    r"Π\d+|(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+(?:\b|_)",
    re.IGNORECASE,
)
ACTIVE_PI_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|Π\d+\b",
    re.IGNORECASE,
)
MACHINE_ABSOLUTE_PATH_RE = re.compile(r"(/mnt/[A-Za-z]/|[A-Za-z]:\\|/home/[^`\s)]+)")

PI_TEST_ROOTS = (
    "tests",
    "ai_stack/tests",
    "world-engine/tests",
    "tools/mcp_server/tests",
)

PRODUCTION_SCAN_ROOTS = (
    "ai_stack",
    "backend/app",
    "frontend/app",
    "frontend/static",
    "frontend/templates",
    "story_runtime_core",
    "tools/mcp_server",
    "world-engine/app",
)

PRODUCTION_SUFFIXES = {".py", ".ts", ".js", ".json", ".yaml", ".yml"}

IGNORED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "htmlcov",
    "node_modules",
    "tests",
    "var",
}

ADR0039_PI_TEST_SCOPE = {
    "ai_stack/tests/test_narrative_runtime_agent.py": "Pi7 fixture rows assert against the npc_initiatives contract rather than copied prose.",
    "ai_stack/tests/test_narrative_aspect_contracts.py": "Π12 fixture metadata; assertions derive from semantic policy, classifier output, and contract fields.",
    "ai_stack/tests/test_npc_agency_contracts.py": "Pi7 shared-contract assertions cover schema constants, bounded adapters, and structured fields.",
    "ai_stack/tests/test_npc_agency_long_horizon_claim_readiness.py": "Pi7 readiness assertions separate local bounded evidence from full claim promotion.",
    "ai_stack/tests/test_npc_agency_planner.py": "Pi7 planning assertions cover deterministic contract fields and policy-derived planner output.",
    "ai_stack/tests/test_capability_selector.py": "ADR-0041 selector tests assert legacy Pi-style keys are rejected while semantic capability names drive selection.",
    "ai_stack/tests/test_pi14_silence_negative_space.py": "Π14 contract tests assert schema versions, reason codes, vocabularies, and routing flags.",
    "ai_stack/tests/test_relationship_state_machine.py": "Π27 relationship-state assertions cover schema constants, policy-derived axes, ledger projection, and structured transition fields.",
    "ai_stack/tests/test_semantic_planner_golden_cases.py": "Π14 director-path regression asserts semantic runtime fields and contract constants.",
    "ai_stack/tests/test_wave3_multi_actor_vitality.py": "Pi19/Pi7 wave assertions assert bounded subtext and simulation contract surfaces.",
    "tests/gates/test_table_b_anti_hardcoding_gate.py": "Legacy Pi control ids are scanned as forbidden production control-flow vocabulary.",
    "tools/mcp_server/tests/test_langfuse_verify_tools.py": "Π12 fixture metadata is verified through RuntimeAspectLedger/MCP matrix extraction fields.",
    "world-engine/tests/test_story_runtime_aspect_ledger.py": "Π12 fixture metadata is verified through RuntimeAspectLedger projection fields.",
    "world-engine/tests/test_story_runtime_callback_web.py": "Π17 continuity tests assert schema constants, bounds, graph export, and ledger projection.",
    "world-engine/tests/test_story_runtime_consequence_cascade.py": "Π21 continuity tests assert schema constants, bounds, graph export, and ledger projection.",
}


def _repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _iter_pi_test_files() -> list[str]:
    files: list[str] = []
    for root in PI_TEST_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = _repo_rel(path)
            if path.name.startswith("test_adr0039") or path.name.startswith("test_adr_0039"):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if PI_REFERENCE_RE.search(text):
                files.append(rel)
    return sorted(set(files))


def _iter_production_files() -> list[Path]:
    files: list[Path] = []
    for root in PRODUCTION_SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in PRODUCTION_SUFFIXES:
                continue
            if any(part in IGNORED_PARTS for part in path.parts):
                continue
            files.append(path)
    return files


def test_all_pi_labeled_tests_are_in_adr0039_scope_manifest() -> None:
    discovered = set(_iter_pi_test_files())
    documented = set(ADR0039_PI_TEST_SCOPE)

    assert discovered <= documented, (
        "Pi / Π-labeled tests must be explicitly covered by ADR-0039:\n"
        + "\n".join(sorted(discovered - documented))
    )


def test_adr0039_pi_scope_manifest_entries_are_current_and_meaningful() -> None:
    discovered = set(_iter_pi_test_files())

    assert discovered
    assert set(ADR0039_PI_TEST_SCOPE) <= discovered
    for rel, rationale in ADR0039_PI_TEST_SCOPE.items():
        assert (REPO_ROOT / rel).exists(), rel
        assert "assert" in rationale or "verified" in rationale or "scanned" in rationale


def test_production_runtime_vocabulary_has_no_active_pi_control_tokens() -> None:
    violations: list[str] = []
    for path in _iter_production_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if ACTIVE_PI_TOKEN_RE.search(text):
            violations.append(_repo_rel(path))

    assert not violations, (
        "Production code must use semantic capability names, not active pi-number tokens:\n"
        + "\n".join(sorted(violations))
    )


def test_adr0039_links_current_matrix_and_live_gate_docs() -> None:
    adr = (REPO_ROOT / "docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md").read_text(
        encoding="utf-8"
    )

    assert "capability_matrix_status_and_adr_relations.md" in adr
    assert "capability_matrix_verification_log.md" in adr
    assert "capability_matrix_live_claim_gates.md" in adr
    assert "adr0039_runtime_surface_governance_inventory.md" in adr
    assert "tests/gates/test_adr_0039_pi_scope.py" in adr
    assert "tests/gates/test_adr0039_runtime_surface_governance.py" in adr


def test_current_truth_docs_do_not_embed_machine_local_paths() -> None:
    docs = [
        "docs/ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md",
        "docs/MVPs/capability_matrix_status_and_adr_relations.md",
        "docs/MVPs/capability_matrix_live_claim_gates.md",
    ]
    violations: list[str] = []
    for rel in docs:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        if MACHINE_ABSOLUTE_PATH_RE.search(text):
            violations.append(rel)

    assert not violations, "Current truth docs must stay repo-root portable:\n" + "\n".join(violations)


def test_verification_log_labels_local_absolute_paths_as_local_only() -> None:
    log = (REPO_ROOT / "docs/MVPs/capability_matrix_verification_log.md").read_text(encoding="utf-8")

    assert "machine-local absolute paths" in log
    assert "local environment evidence only" in log
    assert "Do not treat local PASS output as live-provider proof" in log


def test_mcp_projection_verification_declares_local_only_evidence_scope() -> None:
    source = (REPO_ROOT / "tools/mcp_server/tools_registry_handlers_langfuse_verify.py").read_text(
        encoding="utf-8"
    )

    assert '"evidence_scope": "local_pytest"' in source
    assert '"proof_level": "local_only"' in source
    assert '"live_or_staging_evidence": False' in source
    assert '"governance_adr": "ADR-0039"' in source
    assert "Path(config.repo_root)" in source
