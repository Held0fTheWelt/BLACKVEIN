"""Frozen controlled vocabulary for the God of Carnage MVP vertical slice.

Authoritative definitions: docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md §5,
docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md §6–§7,
docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md §1 and §7.
"""

from __future__ import annotations

from functools import lru_cache
from typing import FrozenSet, Literal, TypeVar
import unicodedata

# --- Scene function (VERTICAL_SLICE_CONTRACT_GOC.md §5) ---
SceneFunction = Literal[
    "establish_pressure",
    "escalate_conflict",
    "probe_motive",
    "repair_or_stabilize",
    "withhold_or_evade",
    "reveal_surface",
    "redirect_blame",
    "scene_pivot",
]

SCENE_FUNCTIONS: FrozenSet[str] = frozenset(
    {
        "establish_pressure",
        "escalate_conflict",
        "probe_motive",
        "repair_or_stabilize",
        "withhold_or_evade",
        "reveal_surface",
        "redirect_blame",
        "scene_pivot",
    }
)

# --- Pacing (VERTICAL_SLICE_CONTRACT_GOC.md §5) ---
PacingMode = Literal["standard", "compressed", "thin_edge", "containment", "multi_pressure"]

PACING_MODES: FrozenSet[str] = frozenset(
    {"standard", "compressed", "thin_edge", "containment", "multi_pressure"}
)

# --- Silence / brevity mode (VERTICAL_SLICE_CONTRACT_GOC.md §5) ---
SilenceBrevityMode = Literal["normal", "brief", "withheld", "expanded"]

SILENCE_BREVITY_MODES: FrozenSet[str] = frozenset({"normal", "brief", "withheld", "expanded"})

# --- Continuity class (VERTICAL_SLICE_CONTRACT_GOC.md §5) ---
ContinuityClass = Literal[
    "situational_pressure",
    "dignity_injury",
    "alliance_shift",
    "revealed_fact",
    "refused_cooperation",
    "blame_pressure",
    "repair_attempt",
    "silent_carry",
]

CONTINUITY_CLASSES: FrozenSet[str] = frozenset(
    {
        "situational_pressure",
        "dignity_injury",
        "alliance_shift",
        "revealed_fact",
        "refused_cooperation",
        "blame_pressure",
        "repair_attempt",
        "silent_carry",
    }
)

# Severity rank for CANONICAL_TURN_CONTRACT_GOC.md §3.5 (highest first).
CONTINUITY_CLASS_SEVERITY_ORDER: tuple[str, ...] = (
    "revealed_fact",
    "dignity_injury",
    "alliance_shift",
    "blame_pressure",
    "situational_pressure",
    "repair_attempt",
    "refused_cooperation",
    "silent_carry",
)

# --- Visibility class (VERTICAL_SLICE_CONTRACT_GOC.md §5) ---
VisibilityClass = Literal["truth_aligned", "bounded_ambiguity", "non_factual_staging"]

VISIBILITY_CLASSES: FrozenSet[str] = frozenset({"truth_aligned", "bounded_ambiguity", "non_factual_staging"})

# --- Failure class (VERTICAL_SLICE_CONTRACT_GOC.md §5) ---
FailureClass = Literal[
    "scope_breach",
    "validation_reject",
    "model_fallback",
    "graph_error",
    "missing_scene_director",
    "missing_validation_path",
    "missing_commit_path",
    "continuity_inconsistency",
]

FAILURE_CLASSES: FrozenSet[str] = frozenset(
    {
        "scope_breach",
        "validation_reject",
        "model_fallback",
        "graph_error",
        "missing_scene_director",
        "missing_validation_path",
        "missing_commit_path",
        "continuity_inconsistency",
    }
)

# --- Transition pattern (CANONICAL_TURN_CONTRACT_GOC.md §6.1, §7.2) ---
TransitionPattern = Literal["hard", "soft", "carry_forward", "diagnostics_only"]

TRANSITION_PATTERNS: FrozenSet[str] = frozenset({"hard", "soft", "carry_forward", "diagnostics_only"})

# --- Gate families (GATE_SCORING_POLICY_GOC.md §1.1) ---
GateFamily = Literal["slice_boundary", "turn_integrity", "dramatic_quality", "diagnostic_sufficiency"]

GATE_FAMILIES: FrozenSet[str] = frozenset(
    {"slice_boundary", "turn_integrity", "dramatic_quality", "diagnostic_sufficiency"}
)

# Canonical module id for the vertical slice (VERTICAL_SLICE_CONTRACT_GOC.md §2.1).
GOC_MODULE_ID = "god_of_carnage"


def _fold_actor_ref(value: str) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


@lru_cache(maxsize=1)
def _goc_actor_alias_index() -> dict[str, tuple[str, FrozenSet[str]]]:
    """Content-derived actor aliases keyed by folded runtime reference."""
    try:
        from ai_stack.god_of_carnage_yaml_authority import goc_actor_identity_index

        identity_index = goc_actor_identity_index()
    except Exception:
        return {}

    alias_index: dict[str, tuple[str, FrozenSet[str]]] = {}
    for actor_id, row in identity_index.items():
        canonical_actor_id = str(actor_id or "").strip()
        if not canonical_actor_id or not isinstance(row, dict):
            continue
        aliases: set[str] = {canonical_actor_id}
        for key in ("actor_id", "character_key", "name", "first_name"):
            raw = str(row.get(key) or "").strip()
            if raw:
                aliases.update({raw, raw.lower(), _fold_actor_ref(raw)})
        group = frozenset(alias for alias in aliases if alias)
        for alias in group:
            folded = _fold_actor_ref(alias)
            if folded:
                alias_index[folded] = (canonical_actor_id, group)
    return alias_index


def canonicalize_goc_actor_id(actor_id: str) -> str:
    aid = str(actor_id or "").strip()
    if not aid:
        return ""
    alias_entry = _goc_actor_alias_index().get(_fold_actor_ref(aid))
    if alias_entry:
        return alias_entry[0]
    return aid


def expand_goc_actor_id_aliases(actor_id: str) -> FrozenSet[str]:
    aid = str(actor_id or "").strip()
    if not aid:
        return frozenset()
    alias_entry = _goc_actor_alias_index().get(_fold_actor_ref(aid))
    if alias_entry:
        return frozenset({aid, *alias_entry[1]})
    return frozenset({aid})

# Director fields that the proposal model must not overwrite (CANONICAL_TURN_CONTRACT_GOC.md §3.6).
DIRECTOR_IMMUTABLE_FIELDS: FrozenSet[str] = frozenset(
    {
        "selected_scene_function",
        "selected_responder_set",
        "pacing_mode",
        "silence_brevity_decision",
    }
)

_T = TypeVar("_T", bound=str)


def _in_set(value: str, allowed: FrozenSet[str]) -> bool:
    """Describe what ``_in_set`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
        allowed: ``allowed`` (FrozenSet[str]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return value in allowed


def assert_scene_function(value: str) -> str:
    """``assert_scene_function`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if value not in SCENE_FUNCTIONS:
        raise ValueError(f"Invalid scene_function label: {value!r}")
    return value


def assert_pacing_mode(value: str) -> str:
    """``assert_pacing_mode`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if value not in PACING_MODES:
        raise ValueError(f"Invalid pacing_mode label: {value!r}")
    return value


def assert_silence_brevity_mode(value: str) -> str:
    """Describe what ``assert_silence_brevity_mode`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if value not in SILENCE_BREVITY_MODES:
        raise ValueError(f"Invalid silence_brevity mode: {value!r}")
    return value


def assert_transition_pattern(value: str) -> str:
    """Describe what ``assert_transition_pattern`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if value not in TRANSITION_PATTERNS:
        raise ValueError(f"Invalid transition_pattern label: {value!r}")
    return value
