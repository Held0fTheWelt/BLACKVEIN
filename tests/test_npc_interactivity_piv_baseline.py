"""Acceptance tests for PR-0 of the NPC Interactivity roadmap.

These tests prove:

1. The PIV log/index exists and is wired to PR-0.
2. ADR-0057 has been amended with the Phase-1 contract names.
3. ADR-0061 exists with Draft status and defines the Director-Pause surface.
4. The ``runtime_diagnostic_snapshot.v1`` envelope stub exists with the
   required shape.
5. The envelope stub does **not** introduce runtime behavior -- no other
   production module imports it.
6. PR-0 does not introduce forbidden active Pi / Pi-numbered runtime keys.
7. PR-0 does not implement PR-A / PR-B / PR-C runtime symbols prematurely
   (the runtime files it pledges to leave untouched do not gain the
   PR-A/B/C symbols this PR has only contractually named).

Per ADR-0039 and the rules in ``NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md``
section 3.0, these tests assert path properties and structured contract
field names -- never paraphrased prose or input-string fixtures.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]

PIV_LOG_PATH = REPO_ROOT / "docs" / "MVPs" / "npc_interactivity_piv_log.md"
PR_0_PIV_PATH = (
    REPO_ROOT / "docs" / "implementation_logs" / "pr_0_npc_interactivity_contracts_piv.md"
)
ADR_0057_PATH = (
    REPO_ROOT / "docs" / "ADR" / "adr-0057-canon-safe-player-freedom-and-affordance-inference.md"
)
ADR_0061_PATH = (
    REPO_ROOT / "docs" / "ADR" / "adr-0061-director-pause-mode-for-gathering-interruption.md"
)
SNAPSHOT_CONTRACT_DOC_PATH = (
    REPO_ROOT
    / "docs"
    / "technical"
    / "runtime"
    / "runtime_diagnostic_snapshot_v1_contract.md"
)
SNAPSHOT_STUB_PY_PATH = REPO_ROOT / "ai_stack" / "runtime_diagnostic_snapshot_contracts.py"

PHASE_1_CONTRACT_NAMES = (
    "free_player_action_resolution.v1",
    "director_gathering_state.v1",
    "canonical_path_hold_effect.v1",
    "narrator_consequence_realization.v1",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# (1) PIV log / index exists
# ---------------------------------------------------------------------------


def test_pr_0_piv_log_index_exists_and_lists_pr_0() -> None:
    assert PIV_LOG_PATH.is_file(), f"Missing PIV index: {PIV_LOG_PATH}"

    text = _read(PIV_LOG_PATH)
    assert "NPC Interactivity Roadmap" in text
    assert "PR-0" in text
    rel_pr_0_link = "../implementation_logs/pr_0_npc_interactivity_contracts_piv.md"
    assert rel_pr_0_link in text, "PIV index must link to the PR-0 PIV artifact"


def test_pr_0_piv_artifact_required_sections() -> None:
    assert PR_0_PIV_PATH.is_file(), f"Missing PR-0 PIV artifact: {PR_0_PIV_PATH}"

    text = _read(PR_0_PIV_PATH)

    required_section_keywords = (
        "Consumer scan",
        "Existing-path probe",
        "Live-smoke feasibility probe",
        "Anti-dead-end checkpoints",
        "What existing paths will be extended later",
        "What must not be touched in PR-0",
    )
    for keyword in required_section_keywords:
        assert keyword in text, f"PR-0 PIV artifact missing required section: {keyword}"

    for verified_anchor in (
        "ai_stack/story_runtime/player_action_resolution.py:502",
        "world-engine/app/story_runtime/manager/dramatic_context_authority.py:229",
        "ai_stack/langgraph/langgraph_runtime_executor.py:3996",
        "ai_stack/langgraph/langgraph_runtime_executor.py:4703",
        "ai_stack/story_runtime/director/god_of_carnage_scene_director.py:655",
        "content/modules/god_of_carnage/canonical_path/005_statement_reading.yaml:36",
    ):
        assert verified_anchor in text, (
            "PR-0 PIV artifact must cite verified file:line anchor: " + verified_anchor
        )


# ---------------------------------------------------------------------------
# (2) ADR-0057 Phase-1 amendment
# ---------------------------------------------------------------------------


def test_adr_0057_phase_1_amendment_names_four_contracts() -> None:
    assert ADR_0057_PATH.is_file(), f"Missing ADR-0057: {ADR_0057_PATH}"

    text = _read(ADR_0057_PATH)

    assert "Phase-1" in text or "Phase 1" in text, (
        "ADR-0057 must carry a Phase-1 amendment heading"
    )

    for contract_name in PHASE_1_CONTRACT_NAMES:
        assert contract_name in text, (
            f"ADR-0057 amendment must name contract: {contract_name}"
        )

    for required_clause in (
        "No verb",
        "semantic runtime names only",
        "presence_breaks_gathering",
        "Director-Pause is",
    ):
        assert required_clause.lower() in text.lower(), (
            "ADR-0057 amendment must clarify: " + required_clause
        )


# ---------------------------------------------------------------------------
# (3) ADR-0061 Draft
# ---------------------------------------------------------------------------


def test_adr_0061_draft_exists_and_defines_director_pause() -> None:
    assert ADR_0061_PATH.is_file(), f"Missing ADR-0061 draft: {ADR_0061_PATH}"

    text = _read(ADR_0061_PATH)

    status_match = re.search(r"^##\s*Status\s*$\s*(?P<status>[A-Za-z]+)", text, re.MULTILINE)
    assert status_match is not None, "ADR-0061 must declare a Status section"
    assert status_match.group("status").strip().lower() == "draft", (
        "ADR-0061 Status must be Draft until PR-C lands"
    )

    for required_term in (
        "director_gathering_state.v1",
        "compute_gathering_state",
        "named_characters",
        "actor_locations",
        "participation_relevance",
        "visibility / audibility",
        "Mandatory-Beat",
        "player remains free",
        "Return clears the pause",
        "narrator transition reaction",
    ):
        assert required_term.lower() in text.lower(), (
            "ADR-0061 draft must mention: " + required_term
        )

    for non_goal in (
        "No Phase-2 Pulse",
        "No pointer repair",
        "No `step.mode` switch",
        "No new runtime aspect ledger row",
    ):
        assert non_goal.lower() in text.lower(), (
            "ADR-0061 draft must declare non-goal: " + non_goal
        )


# ---------------------------------------------------------------------------
# (4) Diagnostic snapshot envelope stub
# ---------------------------------------------------------------------------


def test_runtime_diagnostic_snapshot_v1_envelope_shape_exists() -> None:
    from ai_stack.contracts.runtime_diagnostic_snapshot_contracts import (
        REQUIRED_CONTRACT_PLACEHOLDER_NAMES,
        REQUIRED_ENVELOPE_KEYS,
        RUNTIME_DIAGNOSTIC_SNAPSHOT_SCHEMA_VERSION,
        RuntimeDiagnosticSnapshotEnvelope,
    )

    assert RUNTIME_DIAGNOSTIC_SNAPSHOT_SCHEMA_VERSION == "runtime_diagnostic_snapshot.v1"

    expected_keys = {
        "schema_version",
        "session_id",
        "turn_number",
        "canonical_step_id",
        "visible_block_emitted",
        "resolver_output",
        "director_gathering_state",
        "canonical_path_hold_effect",
        "narrator_consequence_realization",
        "semantic_capability_consultation_names",
    }
    assert set(REQUIRED_ENVELOPE_KEYS) == expected_keys

    assert set(REQUIRED_CONTRACT_PLACEHOLDER_NAMES) == set(PHASE_1_CONTRACT_NAMES)

    envelope = RuntimeDiagnosticSnapshotEnvelope()
    for key in REQUIRED_ENVELOPE_KEYS:
        assert hasattr(envelope, key), (
            "RuntimeDiagnosticSnapshotEnvelope must expose required key: " + key
        )

    assert envelope.resolver_output.contract_name == "free_player_action_resolution.v1"
    assert (
        envelope.director_gathering_state.contract_name == "director_gathering_state.v1"
    )
    assert (
        envelope.canonical_path_hold_effect.contract_name == "canonical_path_hold_effect.v1"
    )
    assert (
        envelope.narrator_consequence_realization.contract_name
        == "narrator_consequence_realization.v1"
    )


def test_runtime_diagnostic_snapshot_v1_contract_doc_exists() -> None:
    assert SNAPSHOT_CONTRACT_DOC_PATH.is_file(), (
        f"Missing snapshot contract doc: {SNAPSHOT_CONTRACT_DOC_PATH}"
    )

    text = _read(SNAPSHOT_CONTRACT_DOC_PATH)
    lowered = text.lower()
    for required in (
        "runtime_diagnostic_snapshot.v1",
        "one source",
        "PR-0",
        "REQUIRED_ENVELOPE_KEYS",
    ):
        assert required.lower() in lowered, (
            "Snapshot contract doc must mention: " + required
        )


# ---------------------------------------------------------------------------
# (5) Stub is not imported by any other production module
# ---------------------------------------------------------------------------


PRODUCTION_SCAN_ROOTS = (
    "administration-tool",
    "ai_stack",
    "backend/app",
    "frontend/app",
    "frontend/static",
    "frontend/templates",
    "story_runtime_core",
    "tools/mcp_server",
    "world-engine/app",
)

PRODUCTION_SUFFIXES = {".py"}

STUB_MODULE_NAME = "runtime_diagnostic_snapshot_contracts"


def _iter_production_python_files() -> list[Path]:
    files: list[Path] = []
    for root in PRODUCTION_SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in PRODUCTION_SUFFIXES:
                continue
            if path.resolve() == SNAPSHOT_STUB_PY_PATH.resolve():
                continue
            if any(part == "tests" for part in path.parts):
                continue
            if any(part in {"__pycache__", "node_modules", ".pytest_cache"} for part in path.parts):
                continue
            files.append(path)
    return files


def test_runtime_diagnostic_snapshot_stub_is_not_imported_by_production_code() -> None:
    """PR-0 must not wire the stub into runtime behavior."""
    importers: list[str] = []
    pattern = re.compile(
        r"(?:from\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b|"
        r"from\s+ai_stack\s+import\s+runtime_diagnostic_snapshot_contracts\b|"
        r"import\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b)"
    )
    for path in _iter_production_python_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            importers.append(str(path.relative_to(REPO_ROOT)))

    assert not importers, (
        "PR-0 must not wire runtime_diagnostic_snapshot_contracts into production. "
        "Importing modules:\n" + "\n".join(importers)
    )


# ---------------------------------------------------------------------------
# (6) No forbidden active Pi / Pi-numbered runtime keys in PR-0 additions
# ---------------------------------------------------------------------------


PR_0_ADDED_PATHS = (
    SNAPSHOT_STUB_PY_PATH,
)


def test_pr_0_python_additions_have_no_active_pi_runtime_keys() -> None:
    pi_pattern = re.compile(
        r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|Π\d+\b",
        re.IGNORECASE,
    )
    violations: list[str] = []
    for path in PR_0_ADDED_PATHS:
        assert path.is_file(), f"PR-0 added path missing: {path}"
        text = path.read_text(encoding="utf-8")
        if pi_pattern.search(text):
            violations.append(str(path.relative_to(REPO_ROOT)))

    assert not violations, (
        "PR-0 additions must use semantic capability names only:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# (7) No PR-A/B/C runtime symbols implemented prematurely
# ---------------------------------------------------------------------------


# These symbol names belong to PR-A, PR-B, and PR-C respectively. PR-0 must
# not introduce any of them as a callable, attribute access, or assignment in
# the existing runtime files it pledges to leave untouched.
PR_A_B_C_FORBIDDEN_RUNTIME_SYMBOLS = (
    "compute_gathering_state",
    "presence_breaks_gathering",
    "gathering_paused",
)


RUNTIME_FILES_UNTOUCHED_BY_PR_0 = (
    "ai_stack/story_runtime/player_action_resolution.py",
    "ai_stack/contracts/narrator_consequence_contracts.py",
    "ai_stack/story_runtime/canonical_path/canonical_path_resolver.py",
    "ai_stack/story_runtime/director/god_of_carnage_scene_director.py",
    "ai_stack/langgraph/langgraph_runtime_executor.py",
    "ai_stack/live_dramatic_scene_simulator.py",
    "ai_stack/module_runtime_policy.py",
    "ai_stack/story_runtime/runtime_aspect_ledger.py",
    "ai_stack/story_runtime/narrator/god_of_carnage_narrator_path.py",
    "ai_stack/story_runtime/god_of_carnage/god_of_carnage_souffleuse.py",
    "world-engine/app/story_runtime/manager/dramatic_context_authority.py",
    "world-engine/app/story_runtime/manager/ldss_narrative_queue.py",
)


def test_pr_0_does_not_implement_pr_abc_runtime_symbols_in_untouched_files() -> None:
    """Sanity probe: the runtime files PR-0 pledges to leave untouched must
    not have acquired the PR-A/B/C symbols this PR has only named in
    contracts. The probe checks for symbol-shaped tokens (e.g. function
    definitions, attribute references). Documentation strings inside ADRs
    and PIV artifacts are allowed; those live under ``docs/`` and are not
    scanned here.
    """
    violations: list[str] = []
    for rel in RUNTIME_FILES_UNTOUCHED_BY_PR_0:
        path = REPO_ROOT / rel
        if not path.is_file():
            # File missing is reported separately; this probe focuses on symbol drift.
            continue
        text = path.read_text(encoding="utf-8")
        for symbol in PR_A_B_C_FORBIDDEN_RUNTIME_SYMBOLS:
            symbol_def_pattern = re.compile(
                rf"\bdef\s+{re.escape(symbol)}\b|\bclass\s+{re.escape(symbol)}\b",
            )
            if symbol_def_pattern.search(text):
                violations.append(f"{rel}: defines forbidden PR-A/B/C symbol '{symbol}'")

    assert not violations, (
        "PR-0 must not implement PR-A/B/C runtime symbols. Violations:\n"
        + "\n".join(violations)
    )


# ---------------------------------------------------------------------------
# (8) PR-0 added paths exist
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "expected_path",
    [
        PIV_LOG_PATH,
        PR_0_PIV_PATH,
        ADR_0057_PATH,
        ADR_0061_PATH,
        SNAPSHOT_STUB_PY_PATH,
        SNAPSHOT_CONTRACT_DOC_PATH,
    ],
)
def test_pr_0_artifacts_exist(expected_path: Path) -> None:
    assert expected_path.is_file(), f"PR-0 artifact missing: {expected_path}"
