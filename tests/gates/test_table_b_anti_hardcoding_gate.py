"""Table B anti-hardcoding gate.

The Table B runtime aspect layer must remain content-driven. This gate prevents
new God-of-Carnage-specific literals or Table-B-specific control IDs from
leaking into generic production code. Existing legacy seams are documented here
as explicit debt so the allowlist is visible and cannot grow accidentally.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]

SOURCE_SUFFIXES = {
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".ts",
    ".yaml",
    ".yml",
}

SCAN_ROOTS = (
    "ai_stack",
    "backend/app",
    "frontend/app",
    "frontend/static",
    "frontend/templates",
    "story_runtime_core",
    "tools/mcp_server",
    "world-engine/app",
)

IGNORED_PATH_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    "__pycache__",
    "htmlcov",
    "node_modules",
    "tests",
    "var",
}

IGNORED_PATH_PREFIXES = (
    "ai_stack/tests/",
    "backend/tests/",
    "frontend/tests/",
    "tools/mcp_server/tests/",
    "world-engine/tests/",
)


@dataclass(frozen=True)
class ForbiddenPattern:
    label: str
    regex: re.Pattern[str]


MODULE_SPECIFIC_PATTERNS = (
    ForbiddenPattern("module_id.god_of_carnage", re.compile(r"\bgod_of_carnage(?:_solo)?\b", re.IGNORECASE)),
    ForbiddenPattern("actor.annette", re.compile(r"\bannette\b", re.IGNORECASE)),
    ForbiddenPattern("actor.alain", re.compile(r"\balain\b", re.IGNORECASE)),
    ForbiddenPattern("actor.veronique", re.compile(r"\bv[ée]ronique\b", re.IGNORECASE)),
    ForbiddenPattern("actor.michel", re.compile(r"\bmichel\b", re.IGNORECASE)),
    ForbiddenPattern("actor.ferdinand", re.compile(r"\bferdinand\b", re.IGNORECASE)),
    ForbiddenPattern("actor.bruno", re.compile(r"\bbruno\b", re.IGNORECASE)),
    ForbiddenPattern("location.bathroom", re.compile(r"\bbathroom\b", re.IGNORECASE)),
    ForbiddenPattern("location.kitchen", re.compile(r"\bkitchen\b", re.IGNORECASE)),
    ForbiddenPattern("location.living_room", re.compile(r"\bliving_room\b", re.IGNORECASE)),
    ForbiddenPattern("location.vallon_living_room", re.compile(r"\bvallon_living_room\b", re.IGNORECASE)),
    ForbiddenPattern("phase.phase_1", re.compile(r"\bphase_1\b", re.IGNORECASE)),
    ForbiddenPattern("beat.ritual_civility", re.compile(r"\britual_civility\b", re.IGNORECASE)),
)

REAUDITED_TABLE_B_CONTROL_IDS = tuple(range(1, 14))

LEGACY_TABLE_B_CONTROL_ID_PATTERNS = tuple(
    ForbiddenPattern(
        f"table_b.pi_{index}",
        re.compile(rf"\bpi_0?{index}\b|Π{index}\b", re.IGNORECASE),
    )
    for index in REAUDITED_TABLE_B_CONTROL_IDS
) + (
    ForbiddenPattern("table_b.pi_21", re.compile(r"\bpi_21\b|Π21\b", re.IGNORECASE)),
    ForbiddenPattern("table_b.pi_22", re.compile(r"\bpi_22\b|Π22\b", re.IGNORECASE)),
    ForbiddenPattern("table_b.pi_24", re.compile(r"\bpi_24\b|Π24\b", re.IGNORECASE)),
)

TABLE_B_CONTROL_PATTERNS = (
    *LEGACY_TABLE_B_CONTROL_ID_PATTERNS,
    ForbiddenPattern("table_b.tension_calibration", re.compile(r"\btension_calibration\b", re.IGNORECASE)),
    ForbiddenPattern("table_b.failure_as_story", re.compile(r"\bfailure_as_story\b", re.IGNORECASE)),
    ForbiddenPattern("table_b.symbolic_resonance", re.compile(r"\bsymbolic_resonance\b", re.IGNORECASE)),
    ForbiddenPattern("table_b.mystery_rationing", re.compile(r"\bmystery_rationing\b", re.IGNORECASE)),
    ForbiddenPattern("table_b.surprise_budget", re.compile(r"\bsurprise_budget\b", re.IGNORECASE)),
)

SCENE_ENERGY_RUNTIME_ASPECT_PATTERN = ForbiddenPattern(
    "runtime_aspect.scene_energy",
    re.compile(r"\bscene_energy\b", re.IGNORECASE),
)
INFORMATION_DISCLOSURE_RUNTIME_ASPECT_PATTERN = ForbiddenPattern(
    "runtime_aspect.information_disclosure",
    re.compile(r"\binformation_disclosure\b", re.IGNORECASE),
)
PACING_RHYTHM_RUNTIME_ASPECT_PATTERN = ForbiddenPattern(
    "runtime_aspect.pacing_rhythm",
    re.compile(r"\bpacing_rhythm\b", re.IGNORECASE),
)
CONSEQUENCE_CASCADE_RUNTIME_ASPECT_PATTERN = ForbiddenPattern(
    "runtime_aspect.consequence_cascade",
    re.compile(r"\bconsequence_cascade\b", re.IGNORECASE),
)
IMPROVISATIONAL_COHERENCE_RUNTIME_ASPECT_PATTERN = ForbiddenPattern(
    "runtime_aspect.improvisational_coherence",
    re.compile(r"\bimprovisational_coherence\b", re.IGNORECASE),
)

SCENE_ENERGY_CANONICAL_SURFACES = {
    "ai_stack/langgraph_runtime_executor.py",
    "ai_stack/langgraph_runtime_package_output_dramatic_review.py",
    "ai_stack/langgraph_runtime_package_output_sections.py",
    "ai_stack/langgraph_runtime_state.py",
    "ai_stack/module_runtime_policy.py",
    "ai_stack/runtime_aspect_ledger.py",
    "ai_stack/scene_energy_contracts.py",
    "ai_stack/scene_energy_engine.py",
    "ai_stack/story_runtime_playability.py",
    "backend/app/services/inspector_turn_projection_sections_assembly_filled.py",
    "tools/mcp_server/tools_registry_handlers_langfuse_verify.py",
    "world-engine/app/story_runtime/commit_models.py",
    "world-engine/app/story_runtime/manager.py",
}

INFORMATION_DISCLOSURE_CANONICAL_SURFACES = {
    "ai_stack/information_disclosure_contracts.py",
    "ai_stack/information_disclosure_engine.py",
    "ai_stack/langgraph_runtime_executor.py",
    "ai_stack/langgraph_runtime_state.py",
    "ai_stack/module_runtime_policy.py",
    "ai_stack/runtime_aspect_ledger.py",
    "tools/mcp_server/tools_registry_handlers_langfuse_verify.py",
    "world-engine/app/story_runtime/manager.py",
}

PACING_RHYTHM_CANONICAL_SURFACES = {
    "ai_stack/langgraph_runtime_executor.py",
    "ai_stack/langgraph_runtime_package_output_dramatic_review.py",
    "ai_stack/langgraph_runtime_package_output_sections.py",
    "ai_stack/langgraph_runtime_state.py",
    "ai_stack/module_runtime_policy.py",
    "ai_stack/pacing_rhythm_contracts.py",
    "ai_stack/pacing_rhythm_engine.py",
    "ai_stack/runtime_aspect_ledger.py",
    "ai_stack/story_runtime_playability.py",
    "tools/mcp_server/tools_registry_handlers_langfuse_verify.py",
    "world-engine/app/story_runtime/commit_models.py",
    "world-engine/app/story_runtime/manager.py",
}

CONSEQUENCE_CASCADE_CANONICAL_SURFACES = {
    "ai_stack/consequence_cascade_contracts.py",
    "ai_stack/langgraph_runtime_executor.py",
    "ai_stack/langgraph_runtime_state.py",
    "ai_stack/module_runtime_policy.py",
    "ai_stack/runtime_aspect_ledger.py",
    "story_runtime_core/consequences/__init__.py",
    "story_runtime_core/consequences/consequence_cascade.py",
    "tools/mcp_server/tools_registry_handlers_langfuse_verify.py",
    "world-engine/app/api/http.py",
    "world-engine/app/config.py",
    "world-engine/app/main.py",
    "world-engine/app/story_runtime/consequence_cascade_store.py",
    "world-engine/app/story_runtime/manager.py",
}

IMPROVISATIONAL_COHERENCE_CANONICAL_SURFACES = {
    "ai_stack/improvisational_coherence_contracts.py",
    "ai_stack/improvisational_coherence_engine.py",
    "ai_stack/langgraph_runtime_executor.py",
    "ai_stack/langgraph_runtime_state.py",
    "ai_stack/module_runtime_policy.py",
    "ai_stack/runtime_aspect_ledger.py",
    "tools/mcp_server/tools_registry_handlers_langfuse_verify.py",
    "world-engine/app/story_runtime/manager.py",
}


# These are not exemptions for new Table B work. They document current
# module-specific legacy seams that must be modularized before Table B rows can
# honestly move beyond partial/proven status.
KNOWN_MODULE_LITERAL_DEBT: dict[str, str] = {
    "ai_stack/canonical_prompt_catalog.py": "Legacy prompt catalog embeds GoC host/guest footing.",
    "ai_stack/diagnostics_envelope.py": "Legacy diagnostics defaults still use the GoC live profile.",
    "ai_stack/langchain_integration/bridges.py": "Schema descriptions include GoC-flavored examples.",
    "ai_stack/live_dramatic_scene_simulator.py": "LDSS fallback/opening data is still GoC-specific.",
    "ai_stack/narrative_runtime_agent.py": "Narrator validation examples still mention GoC actors.",
    "ai_stack/narrator_consequence_contracts.py": "Local context fallback still names a GoC location.",
    "ai_stack/opening_shape_normalizer.py": "Opening-shape compatibility shim still names GoC.",
    "ai_stack/research_fixtures.py": "Research fixture data is intentionally GoC-specific.",
    "ai_stack/visible_narrative_contract.py": "Visible sanitizer still has GoC actor fallback tokens.",
    "backend/app/api/v1/game_routes.py": "Play handoff compatibility still knows the GoC solo profile.",
    "backend/app/api/v1/narrative_governance_routes.py": "Narrative governance defaults still use GoC.",
    "backend/app/api/v1/session_routes.py": "Legacy session bootstrap examples still use GoC.",
    "backend/app/content/builtins.py": "Built-in content registry exposes the GoC profile.",
    "backend/app/content/module_loader.py": "Template-to-module compatibility maps GoC solo.",
    "backend/app/content/module_service.py": "Content service doc examples still use GoC.",
    "backend/app/models/game_experience_template.py": "Seed-template compatibility still knows GoC solo.",
    "backend/app/observability/langfuse_adapter.py": "Observability docstring example still uses GoC.",
    "backend/app/runtime/engine.py": "Legacy mini-engine still uses fixed room flags.",
    "backend/app/runtime/npc_behaviors.py": "Legacy mini-engine NPC behavior is GoC-specific.",
    "backend/app/runtime/runtime_models.py": "Runtime model docstring example still uses GoC.",
    "backend/app/runtime/session_start.py": "Session-start docstring example still uses GoC.",
    "backend/app/services/game_content_service.py": "Game content service still maps the GoC solo seed.",
    "frontend/app/routes_play.py": "Play launcher still validates GoC role/profile locally.",
    "frontend/templates/session_start.html": "Play launcher still renders GoC role choices locally.",
    "story_runtime_core/builtin_experience_templates.py": "Built-in template registry includes GoC compatibility.",
    "story_runtime_core/content_locale.py": "Locale fallback still defaults to GoC.",
    "story_runtime_core/goc_solo_builtin_catalog.py": "GoC-specific built-in compatibility catalog.",
    "story_runtime_core/goc_solo_builtin_catalog_actions.py": "GoC-specific built-in compatibility actions.",
    "story_runtime_core/goc_solo_builtin_roles_rooms.py": "GoC-specific built-in compatibility roles/rooms.",
    "story_runtime_core/goc_solo_builtin_template.py": "GoC-specific built-in compatibility template.",
    "world-engine/app/api/http.py": "World-engine HTTP compatibility still knows GoC solo.",
    "world-engine/app/content/builtins.py": "World-engine built-in content registry exposes GoC.",
    "world-engine/app/runtime/actor_lane.py": "Actor-lane helper still defaults a GoC phase id.",
    "world-engine/app/runtime/engine.py": "Legacy mini-engine still uses fixed room flags.",
    "world-engine/app/runtime/npc_behaviors.py": "Legacy mini-engine NPC behavior is GoC-specific.",
    "world-engine/app/runtime/profiles.py": "Runtime profile resolver currently supports GoC solo.",
    "world-engine/app/story_runtime/module_turn_hooks.py": "Explicit GoC compatibility shim.",
    "world-engine/app/story_runtime_shell_readout.py": "Shell readout still contains GoC-specific pressure prose.",
}


def _repo_rel(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _known_module_literal_debt_reason(rel: str) -> str | None:
    if rel in KNOWN_MODULE_LITERAL_DEBT:
        return KNOWN_MODULE_LITERAL_DEBT[rel]
    filename = Path(rel).name
    if rel.startswith("ai_stack/goc_") or (
        rel.startswith("ai_stack/") and filename.endswith("_goc.py")
    ):
        return "GoC-specific ai_stack module; generic Table B code must not depend on it."
    if rel.startswith("story_runtime_core/goc_solo_"):
        return "GoC-specific built-in compatibility module."
    return None


def _iter_source_files() -> Iterable[Path]:
    for root in SCAN_ROOTS:
        base = REPO_ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel = _repo_rel(path)
            if path.suffix not in SOURCE_SUFFIXES:
                continue
            if path.name == "README.md":
                continue
            if any(part in IGNORED_PATH_PARTS for part in path.parts):
                continue
            if any(rel.startswith(prefix) for prefix in IGNORED_PATH_PREFIXES):
                continue
            yield path


def _matches(path: Path, patterns: tuple[ForbiddenPattern, ...]) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    hits: list[str] = []
    for pattern in patterns:
        if pattern.regex.search(text):
            hits.append(pattern.label)
    return hits


def test_table_b_control_ids_do_not_drive_production_code() -> None:
    """Table B IDs must remain policy data, not runtime branching literals."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        hits = _matches(path, TABLE_B_CONTROL_PATTERNS)
        if hits:
            violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, "Table B control literals leaked into production code:\n" + "\n".join(violations)


def test_reaudited_table_b_control_id_guard_covers_pi1_through_pi13() -> None:
    """The Π1-Π13 re-audit must stay represented in this production scan."""
    labels = {pattern.label for pattern in LEGACY_TABLE_B_CONTROL_ID_PATTERNS}
    expected = {f"table_b.pi_{index}" for index in REAUDITED_TABLE_B_CONTROL_IDS}

    assert expected.issubset(labels)


def test_scene_energy_runtime_aspect_is_limited_to_canonical_surfaces() -> None:
    """Scene energy is now a contract aspect, not a legacy Table B shortcut."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        if rel in SCENE_ENERGY_CANONICAL_SURFACES:
            continue
        hits = _matches(path, (SCENE_ENERGY_RUNTIME_ASPECT_PATTERN,))
        if hits:
            violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, (
        "scene_energy appeared outside reviewed canonical aspect surfaces. "
        "Add a contract/policy-backed surface or remove the shortcut literal:\n"
        + "\n".join(violations)
    )


def test_information_disclosure_runtime_aspect_is_limited_to_canonical_surfaces() -> None:
    """Information disclosure is a contract aspect, not a Table B shortcut."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        if rel in INFORMATION_DISCLOSURE_CANONICAL_SURFACES:
            continue
        hits = _matches(path, (INFORMATION_DISCLOSURE_RUNTIME_ASPECT_PATTERN,))
        if hits:
            violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, (
        "information_disclosure appeared outside reviewed canonical aspect surfaces. "
        "Add a contract/policy-backed surface or remove the shortcut literal:\n"
        + "\n".join(violations)
    )


def test_pacing_rhythm_runtime_aspect_is_limited_to_canonical_surfaces() -> None:
    """Pacing rhythm is a contract aspect, not a Table B shortcut."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        if rel in PACING_RHYTHM_CANONICAL_SURFACES:
            continue
        hits = _matches(path, (PACING_RHYTHM_RUNTIME_ASPECT_PATTERN,))
        if hits:
            violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, (
        "pacing_rhythm appeared outside reviewed canonical aspect surfaces. "
        "Add a contract/policy-backed surface or remove the shortcut literal:\n"
        + "\n".join(violations)
    )


def test_consequence_cascade_runtime_aspect_is_limited_to_canonical_surfaces() -> None:
    """Consequence cascade is a contract aspect, not a Table B shortcut."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        if rel in CONSEQUENCE_CASCADE_CANONICAL_SURFACES:
            continue
        hits = _matches(path, (CONSEQUENCE_CASCADE_RUNTIME_ASPECT_PATTERN,))
        if hits:
            violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, (
        "consequence_cascade appeared outside reviewed canonical aspect surfaces. "
        "Add a contract/policy-backed surface or remove the shortcut literal:\n"
        + "\n".join(violations)
    )


def test_improvisational_coherence_runtime_aspect_is_limited_to_canonical_surfaces() -> None:
    """Improvisational coherence is a contract aspect, not a Table B shortcut."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        if rel in IMPROVISATIONAL_COHERENCE_CANONICAL_SURFACES:
            continue
        hits = _matches(path, (IMPROVISATIONAL_COHERENCE_RUNTIME_ASPECT_PATTERN,))
        if hits:
            violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, (
        "improvisational_coherence appeared outside reviewed canonical aspect surfaces. "
        "Add a contract/policy-backed surface or remove the shortcut literal:\n"
        + "\n".join(violations)
    )


def test_module_specific_literals_stay_inside_documented_compatibility_debt() -> None:
    """New generic runtime code must not acquire GoC actor/location/phase literals."""
    violations: list[str] = []
    for path in _iter_source_files():
        rel = _repo_rel(path)
        hits = _matches(path, MODULE_SPECIFIC_PATTERNS)
        if not hits:
            continue
        if _known_module_literal_debt_reason(rel):
            continue
        violations.append(f"{rel}: {', '.join(hits)}")

    assert not violations, (
        "Module-specific literals appeared outside documented compatibility debt. "
        "Move module data to content/policy or add a reviewed compatibility-shim reason:\n"
        + "\n".join(violations)
    )


def test_known_module_literal_debt_allowlist_is_still_current() -> None:
    """The debt allowlist must not silently keep dead paths or empty rationales."""
    stale_paths = [
        rel
        for rel in KNOWN_MODULE_LITERAL_DEBT
        if not (REPO_ROOT / rel).exists()
    ]
    empty_reasons = [
        rel
        for rel, reason in KNOWN_MODULE_LITERAL_DEBT.items()
        if not reason.strip()
    ]

    assert not stale_paths, "Remove stale anti-hardcoding debt allowlist paths:\n" + "\n".join(stale_paths)
    assert not empty_reasons, "Every anti-hardcoding debt allowlist path needs a reason:\n" + "\n".join(empty_reasons)
