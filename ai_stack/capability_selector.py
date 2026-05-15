"""Deterministic semantic capability selection for ADR-0041.

This module is intentionally local and side-effect free. It selects a bounded
semantic capability subset for one runtime situation and produces
RuntimeAspectLedger-compatible evidence. It does not execute validators, run
judges, mutate runtime state, or make live/staging claims.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Any


CAPABILITY_SELECTOR_SCHEMA_VERSION = "capability_selection.v1"
LOCAL_SELECTION_EVIDENCE_SCOPE = "local_runtime_selection"
LOCAL_SELECTION_PROOF_LEVEL = "local_only"
_NON_LEXICAL_INPUT_KINDS = frozenset({"non_lexical", "silence", "gesture"})
_OPENING_TURN_KINDS = frozenset({"opening", "engine_opening"})
_NPC_TURN_KINDS = frozenset({"npc", "npc_turn"})
_RECOVERY_TURN_KINDS = frozenset(
    {
        "recovery",
        "fallback",
        "fallback_recovery",
        "rejected_recoverable",
        "player_rejected_recoverable",
        "player_graph_exception_playable",
        "graph_exception_playable",
    }
)
_SYSTEM_TURN_KINDS = frozenset({"system_transition"})


class CapabilityMode(str, Enum):
    """Per-turn activation mode for one semantic capability."""

    OFF = "off"
    OBSERVE = "observe"
    ENFORCE = "enforce"
    JUDGE = "judge"


class TurnKind(str, Enum):
    OPENING = "opening"
    PLAYER_INPUT = "player_input"
    NPC_TURN = "npc_turn"
    NARRATOR_BRIDGE = "narrator_bridge"
    RECOVERY = "recovery"
    SYSTEM_TRANSITION = "system_transition"
    HIGH_STAKES_TURN = "high_stakes_turn"


class ActiveActor(str, Enum):
    NARRATOR = "narrator"
    PLAYER = "player"
    NPC = "npc"
    SYSTEM = "system"


class InterpersonalPressure(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ScenePhase(str, Enum):
    OPENING = "opening"
    ESCALATION = "escalation"
    CONFRONTATION = "confrontation"
    AFTERMATH = "aftermath"
    RECOVERY = "recovery"


class LastTurnQuality(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FALLBACK = "fallback"


CAP_NARRATOR_AUTHORITY = "narrator_authority"
CAP_SCENE_ENERGY = "scene_energy"
CAP_ENVIRONMENT_STATE = "environment_state"
CAP_INFORMATION_DISCLOSURE = "information_disclosure"
CAP_VOICE_CONSISTENCY = "voice_consistency"
CAP_THEMATIC_TRACKING = "thematic_tracking"
CAP_CALLBACK_WEB = "callback_web"
CAP_SENSORY_CONTEXT = "sensory_context"
CAP_NPC_AGENCY = "npc_agency"
CAP_PLAYER_INTENT_INFERENCE = "player_intent_inference"
CAP_ACTION_RESOLUTION = "action_resolution"
CAP_CONSEQUENCE_CASCADE = "consequence_cascade"
CAP_LONG_HORIZON_FORECAST = "long_horizon_forecast"
CAP_SILENCE_NEGATIVE_SPACE = "silence_negative_space"
CAP_DRAMATIC_IRONY = "dramatic_irony"

INITIAL_CAPABILITIES: tuple[str, ...] = (
    CAP_NARRATOR_AUTHORITY,
    CAP_SCENE_ENERGY,
    CAP_ENVIRONMENT_STATE,
    CAP_INFORMATION_DISCLOSURE,
    CAP_VOICE_CONSISTENCY,
    CAP_THEMATIC_TRACKING,
    CAP_CALLBACK_WEB,
    CAP_SENSORY_CONTEXT,
    CAP_NPC_AGENCY,
    CAP_PLAYER_INTENT_INFERENCE,
    CAP_ACTION_RESOLUTION,
    CAP_CONSEQUENCE_CASCADE,
    CAP_LONG_HORIZON_FORECAST,
    CAP_SILENCE_NEGATIVE_SPACE,
    CAP_DRAMATIC_IRONY,
)

_ACTIVE_LEGACY_SELECTOR_KEY_RE = re.compile(
    r"(?:Π\d+|(?<![A-Za-z0-9])pi_?\d+(?:\b|_))",
    re.IGNORECASE,
)
_SEMANTIC_CAPABILITY_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _coerce_enum(enum_type: type[Enum], value: Any) -> Enum:
    if isinstance(value, enum_type):
        return value
    text = str(value or "").strip()
    for item in enum_type:
        if item.value == text:
            return item
    allowed = ", ".join(item.value for item in enum_type)
    raise ValueError(f"Unsupported {enum_type.__name__}: {text!r}; expected one of {allowed}")


def _unique(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        name = validate_semantic_capability_name(item)
        if name not in seen:
            seen.add(name)
            ordered.append(name)
    return tuple(ordered)


def validate_semantic_capability_name(name: str) -> str:
    """Return a normalized semantic capability name or raise on legacy keys."""
    text = str(name or "").strip()
    if not text:
        raise ValueError("Capability name must not be empty")
    if _ACTIVE_LEGACY_SELECTOR_KEY_RE.search(text):
        raise ValueError(f"Capability selector keys must be semantic, not legacy labels: {text!r}")
    if not _SEMANTIC_CAPABILITY_NAME_RE.fullmatch(text):
        raise ValueError(f"Capability selector keys must be lowercase semantic identifiers: {text!r}")
    return text


@dataclass(frozen=True)
class TurnSituation:
    """Semantic situation signals consumed by the deterministic selector."""

    turn_kind: TurnKind | str = TurnKind.PLAYER_INPUT
    active_actor: ActiveActor | str = ActiveActor.PLAYER
    player_input_present: bool = False
    npc_decision_required: bool = False
    action_resolution_required: bool = False
    visible_projection_required: bool = False
    interpersonal_pressure: InterpersonalPressure | str = InterpersonalPressure.NONE
    scene_phase: ScenePhase | str = ScenePhase.OPENING
    last_turn_quality: LastTurnQuality | str = LastTurnQuality.HEALTHY
    canonical_scene_seed: bool = False
    non_lexical_input_present: bool = False
    knowledge_gap_present: bool = False
    world_state_change_requested: bool = False
    high_risk_turn: bool = False
    branch_preview_requested: bool = False
    ambiguous_local_validation: bool = False
    promotion_evaluation_requested: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "turn_kind", _coerce_enum(TurnKind, self.turn_kind))
        object.__setattr__(self, "active_actor", _coerce_enum(ActiveActor, self.active_actor))
        object.__setattr__(
            self,
            "interpersonal_pressure",
            _coerce_enum(InterpersonalPressure, self.interpersonal_pressure),
        )
        object.__setattr__(self, "scene_phase", _coerce_enum(ScenePhase, self.scene_phase))
        object.__setattr__(
            self,
            "last_turn_quality",
            _coerce_enum(LastTurnQuality, self.last_turn_quality),
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("turn_kind", "active_actor", "interpersonal_pressure", "scene_phase", "last_turn_quality"):
            value = result.get(key)
            if isinstance(value, Enum):
                result[key] = value.value
        return result


@dataclass(frozen=True)
class CapabilityBudget:
    """Turn-level cost constraints for selected capability behavior."""

    max_enforced_capabilities: int
    allow_llm_judges: bool = False
    allow_heavy_forecast: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_enforced_capabilities", max(0, int(self.max_enforced_capabilities)))
        object.__setattr__(self, "allow_llm_judges", bool(self.allow_llm_judges))
        object.__setattr__(self, "allow_heavy_forecast", bool(self.allow_heavy_forecast))

    def to_projection(self) -> dict[str, Any]:
        return {
            "max_enforced": self.max_enforced_capabilities,
            "llm_judges_allowed": self.allow_llm_judges,
            "heavy_forecast_allowed": self.allow_heavy_forecast,
        }


@dataclass(frozen=True)
class CapabilitySelectionResult:
    """Bounded selector output plus local evidence metadata."""

    situation: TurnSituation
    budget: CapabilityBudget
    enforced: tuple[str, ...] = field(default_factory=tuple)
    observed: tuple[str, ...] = field(default_factory=tuple)
    judged: tuple[str, ...] = field(default_factory=tuple)
    excluded: tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)
    evidence_scope: str = LOCAL_SELECTION_EVIDENCE_SCOPE
    proof_level: str = LOCAL_SELECTION_PROOF_LEVEL
    live_or_staging_evidence: bool = False
    implementation_proof: bool = False
    schema_version: str = CAPABILITY_SELECTOR_SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "enforced", _unique(self.enforced))
        object.__setattr__(self, "observed", _unique(self.observed))
        object.__setattr__(self, "judged", _unique(self.judged))
        object.__setattr__(self, "excluded", _unique(self.excluded))
        object.__setattr__(self, "warnings", tuple(str(item) for item in self.warnings if str(item).strip()))
        object.__setattr__(self, "live_or_staging_evidence", False)
        object.__setattr__(self, "implementation_proof", False)
        object.__setattr__(self, "evidence_scope", LOCAL_SELECTION_EVIDENCE_SCOPE)
        object.__setattr__(self, "proof_level", LOCAL_SELECTION_PROOF_LEVEL)

    @property
    def off(self) -> tuple[str, ...]:
        return self.excluded

    def activation_modes(self) -> dict[str, str]:
        modes = {capability: CapabilityMode.OFF.value for capability in INITIAL_CAPABILITIES}
        for capability in self.observed:
            modes[capability] = CapabilityMode.OBSERVE.value
        for capability in self.enforced:
            modes[capability] = CapabilityMode.ENFORCE.value
        for capability in self.judged:
            if modes.get(capability) != CapabilityMode.ENFORCE.value:
                modes[capability] = CapabilityMode.JUDGE.value
        return modes

    def to_runtime_aspect_projection(self) -> dict[str, Any]:
        """Return a RuntimeAspectLedger-compatible local evidence projection."""
        return {
            "capability_selection": {
                "schema_version": self.schema_version,
                "turn_kind": self.situation.turn_kind.value,
                "active_actor": self.situation.active_actor.value,
                "selected": list(self.enforced),
                "observed_only": list(self.observed),
                "judged": list(self.judged),
                "excluded": list(self.excluded),
                "activation_modes": self.activation_modes(),
                "budget": self.budget.to_projection(),
                "reason": self.reason,
                "warnings": list(self.warnings),
                "evidence_scope": self.evidence_scope,
                "proof_level": self.proof_level,
                "live_or_staging_evidence": self.live_or_staging_evidence,
                "implementation_proof": self.implementation_proof,
                "implemented_by_runtime": False,
                "live_verified": False,
                "staging_verified": False,
                "provider_verified": False,
                "capability_promoted": False,
            }
        }

    def to_ledger_payload(self) -> dict[str, Any]:
        return self.to_runtime_aspect_projection()

    def to_runtime_intelligence_projection(self) -> dict[str, Any]:
        return self.to_runtime_aspect_projection()


def budget_for_situation(situation: TurnSituation) -> CapabilityBudget:
    """Return ADR-0041 initial defaults for one situation."""
    if situation.turn_kind is TurnKind.OPENING:
        return CapabilityBudget(
            max_enforced_capabilities=5,
            allow_llm_judges=False,
            allow_heavy_forecast=False,
        )
    if situation.turn_kind is TurnKind.RECOVERY or situation.last_turn_quality is LastTurnQuality.FALLBACK:
        return CapabilityBudget(
            max_enforced_capabilities=3,
            allow_llm_judges=False,
            allow_heavy_forecast=False,
        )
    if (
        situation.turn_kind is TurnKind.HIGH_STAKES_TURN
        or situation.high_risk_turn
        or situation.branch_preview_requested
    ):
        return CapabilityBudget(
            max_enforced_capabilities=8,
            allow_llm_judges=True,
            allow_heavy_forecast=True,
        )
    if situation.turn_kind is TurnKind.NPC_TURN:
        return CapabilityBudget(
            max_enforced_capabilities=7,
            allow_llm_judges=bool(
                situation.ambiguous_local_validation
                or situation.promotion_evaluation_requested
            ),
            allow_heavy_forecast=False,
        )
    return CapabilityBudget(
        max_enforced_capabilities=6,
        allow_llm_judges=bool(
            situation.ambiguous_local_validation
            or situation.promotion_evaluation_requested
        ),
        allow_heavy_forecast=False,
    )


def derive_turn_situation_from_runtime_context(
    *,
    turn_kind: str | None = None,
    turn_number: int | None = None,
    raw_player_input: str | None = None,
    input_kind: str | None = None,
    active_actor: str | None = None,
    npc_decision_required: bool | None = None,
    action_resolution_required: bool | None = None,
    visible_projection_required: bool | None = None,
    canonical_scene_seed: bool | None = None,
    non_lexical_input_present: bool | None = None,
    knowledge_gap_present: bool | None = None,
    world_state_change_requested: bool | None = None,
) -> tuple[TurnSituation, tuple[str, ...]]:
    """Conservatively derive selector inputs from existing runtime turn context.

    The derivation intentionally maps only clear signals. Unknown high-stakes,
    forecast, judge, live/staging, and promotion signals remain disabled until
    later integration phases provide explicit evidence.
    """
    raw = str(raw_player_input or "")
    kind_text = str(turn_kind or "").strip().lower()
    input_kind_text = str(input_kind or "").strip().lower()
    actor_text = str(active_actor or "").strip().lower()
    warnings: list[str] = []

    try:
        tn = int(turn_number) if turn_number is not None else None
    except (TypeError, ValueError):
        tn = None
        warnings.append("situation_derivation:invalid_turn_number_defaulted")

    player_input_present = bool(raw.strip())
    explicit_non_lexical = bool(non_lexical_input_present)
    derived_non_lexical = input_kind_text in _NON_LEXICAL_INPUT_KINDS
    non_lexical = explicit_non_lexical or derived_non_lexical
    visibility = True if visible_projection_required is None else bool(visible_projection_required)

    opening = kind_text in _OPENING_TURN_KINDS or (
        tn is not None and tn <= 0 and not player_input_present
    )
    if opening:
        return (
            TurnSituation(
                turn_kind=TurnKind.OPENING,
                active_actor=ActiveActor.NARRATOR,
                player_input_present=False,
                npc_decision_required=False,
                action_resolution_required=False,
                visible_projection_required=visibility,
                canonical_scene_seed=True
                if canonical_scene_seed is None
                else bool(canonical_scene_seed),
                non_lexical_input_present=non_lexical,
                knowledge_gap_present=bool(knowledge_gap_present),
                world_state_change_requested=False,
                scene_phase=ScenePhase.OPENING,
            ),
            tuple(warnings),
        )

    npc_turn = (
        actor_text == ActiveActor.NPC.value
        or kind_text in _NPC_TURN_KINDS
        or bool(npc_decision_required)
    )
    if npc_turn:
        return (
            TurnSituation(
                turn_kind=TurnKind.NPC_TURN,
                active_actor=ActiveActor.NPC,
                player_input_present=player_input_present,
                npc_decision_required=True
                if npc_decision_required is None
                else bool(npc_decision_required),
                action_resolution_required=bool(action_resolution_required),
                visible_projection_required=visibility,
                interpersonal_pressure=InterpersonalPressure.HIGH,
                scene_phase=ScenePhase.CONFRONTATION,
                non_lexical_input_present=non_lexical,
                knowledge_gap_present=bool(knowledge_gap_present),
                world_state_change_requested=bool(world_state_change_requested),
            ),
            tuple(warnings),
        )

    if kind_text in _RECOVERY_TURN_KINDS:
        return (
            TurnSituation(
                turn_kind=TurnKind.RECOVERY,
                active_actor=ActiveActor.SYSTEM,
                player_input_present=player_input_present,
                npc_decision_required=False,
                action_resolution_required=False,
                visible_projection_required=visibility,
                scene_phase=ScenePhase.RECOVERY,
                last_turn_quality=LastTurnQuality.FALLBACK,
                non_lexical_input_present=non_lexical,
                knowledge_gap_present=bool(knowledge_gap_present),
                world_state_change_requested=False,
            ),
            tuple(warnings),
        )

    if kind_text in _SYSTEM_TURN_KINDS or actor_text == ActiveActor.SYSTEM.value:
        return (
            TurnSituation(
                turn_kind=TurnKind.SYSTEM_TRANSITION,
                active_actor=ActiveActor.SYSTEM,
                player_input_present=player_input_present,
                npc_decision_required=False,
                action_resolution_required=False,
                visible_projection_required=visibility,
                non_lexical_input_present=non_lexical,
                knowledge_gap_present=bool(knowledge_gap_present),
                world_state_change_requested=False,
            ),
            tuple(warnings),
        )

    known_player_kinds = {"", "player", "player_input"}
    if kind_text not in known_player_kinds:
        warnings.append(f"situation_derivation:unknown_turn_kind:{kind_text}")

    return (
        TurnSituation(
            turn_kind=TurnKind.PLAYER_INPUT,
            active_actor=ActiveActor.PLAYER,
            player_input_present=player_input_present,
            npc_decision_required=False,
            action_resolution_required=bool(action_resolution_required)
            if action_resolution_required is not None
            else player_input_present,
            visible_projection_required=visibility,
            scene_phase=ScenePhase.ESCALATION if player_input_present else ScenePhase.OPENING,
            non_lexical_input_present=non_lexical,
            knowledge_gap_present=bool(knowledge_gap_present),
            world_state_change_requested=bool(world_state_change_requested),
        ),
        tuple(warnings),
    )


def _add_candidate(candidates: list[tuple[str, bool]], capability: str, *, required: bool) -> None:
    name = validate_semantic_capability_name(capability)
    if not any(existing == name for existing, _required in candidates):
        candidates.append((name, required))


def _add_observed(observed: list[str], capability: str) -> None:
    name = validate_semantic_capability_name(capability)
    if name not in observed:
        observed.append(name)


def _cap_enforced_candidates(
    candidates: list[tuple[str, bool]],
    budget: CapabilityBudget,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    warnings: list[str] = []
    ordered = [
        *(capability for capability, required in candidates if required),
        *(capability for capability, required in candidates if not required),
    ]
    selected: list[str] = []
    for capability in ordered:
        if capability in selected:
            continue
        if len(selected) >= budget.max_enforced_capabilities:
            warnings.append(f"budget_dropped:{capability}")
            continue
        selected.append(capability)
    return tuple(selected), tuple(warnings)


def _opening_selection(
    candidates: list[tuple[str, bool]],
    observed: list[str],
) -> str:
    for capability in (
        CAP_NARRATOR_AUTHORITY,
        CAP_SCENE_ENERGY,
        CAP_ENVIRONMENT_STATE,
        CAP_INFORMATION_DISCLOSURE,
        CAP_VOICE_CONSISTENCY,
    ):
        _add_candidate(candidates, capability, required=True)
    for capability in (CAP_THEMATIC_TRACKING, CAP_CALLBACK_WEB, CAP_SENSORY_CONTEXT):
        _add_observed(observed, capability)
    return "Opening scene with narrator-only authority and no player action."


def _player_selection(
    situation: TurnSituation,
    candidates: list[tuple[str, bool]],
    observed: list[str],
) -> str:
    _add_candidate(candidates, CAP_PLAYER_INTENT_INFERENCE, required=True)
    if situation.action_resolution_required:
        _add_candidate(candidates, CAP_ACTION_RESOLUTION, required=True)
    for capability in (CAP_INFORMATION_DISCLOSURE, CAP_VOICE_CONSISTENCY, CAP_SCENE_ENERGY):
        _add_candidate(candidates, capability, required=True)
    for capability in (CAP_ENVIRONMENT_STATE, CAP_THEMATIC_TRACKING, CAP_CALLBACK_WEB):
        _add_observed(observed, capability)
    return "Player input turn with action/intent handling and visible projection."


def _npc_conflict_selection(
    candidates: list[tuple[str, bool]],
    observed: list[str],
) -> str:
    for capability in (
        CAP_NPC_AGENCY,
        CAP_VOICE_CONSISTENCY,
        CAP_SCENE_ENERGY,
        CAP_INFORMATION_DISCLOSURE,
    ):
        _add_candidate(candidates, capability, required=True)
    for capability in (CAP_CALLBACK_WEB, CAP_THEMATIC_TRACKING):
        _add_observed(observed, capability)
    return "NPC conflict turn with NPC decision pressure and visible projection."


def _recovery_selection(candidates: list[tuple[str, bool]], observed: list[str]) -> str:
    for capability in (CAP_NARRATOR_AUTHORITY, CAP_VOICE_CONSISTENCY, CAP_INFORMATION_DISCLOSURE):
        _add_candidate(candidates, capability, required=True)
    _add_observed(observed, CAP_ENVIRONMENT_STATE)
    return "Fallback or recovery turn with small enforced capability set."


def _base_selection(
    situation: TurnSituation,
    candidates: list[tuple[str, bool]],
    observed: list[str],
) -> str:
    if situation.turn_kind is TurnKind.OPENING:
        return _opening_selection(candidates, observed)
    if situation.turn_kind is TurnKind.RECOVERY or situation.last_turn_quality is LastTurnQuality.FALLBACK:
        return _recovery_selection(candidates, observed)
    if situation.turn_kind is TurnKind.NPC_TURN and situation.npc_decision_required:
        return _npc_conflict_selection(candidates, observed)
    return _player_selection(situation, candidates, observed)


def select_capabilities(
    situation: TurnSituation | dict[str, Any] | None = None,
    *,
    budget: CapabilityBudget | None = None,
) -> CapabilitySelectionResult:
    """Select a bounded semantic capability subset for one turn."""
    normalized_situation = (
        TurnSituation(**situation)
        if isinstance(situation, dict)
        else situation
        if isinstance(situation, TurnSituation)
        else TurnSituation()
    )
    effective_budget = budget or budget_for_situation(normalized_situation)
    candidates: list[tuple[str, bool]] = []
    observed: list[str] = []
    reason = _base_selection(normalized_situation, candidates, observed)

    if normalized_situation.non_lexical_input_present:
        _add_candidate(candidates, CAP_SILENCE_NEGATIVE_SPACE, required=True)
    if normalized_situation.knowledge_gap_present:
        _add_observed(observed, CAP_DRAMATIC_IRONY)
    if (
        normalized_situation.world_state_change_requested
        and normalized_situation.action_resolution_required
    ):
        _add_candidate(candidates, CAP_CONSEQUENCE_CASCADE, required=True)
    if effective_budget.allow_heavy_forecast and (
        normalized_situation.turn_kind is TurnKind.HIGH_STAKES_TURN
        or normalized_situation.high_risk_turn
        or normalized_situation.branch_preview_requested
    ):
        _add_candidate(candidates, CAP_LONG_HORIZON_FORECAST, required=False)

    enforced, budget_warnings = _cap_enforced_candidates(candidates, effective_budget)
    observed_tuple = tuple(
        capability
        for capability in _unique(tuple(observed))
        if capability not in enforced
    )

    judged: tuple[str, ...] = ()
    if effective_budget.allow_llm_judges and (
        normalized_situation.ambiguous_local_validation
        or normalized_situation.high_risk_turn
        or normalized_situation.promotion_evaluation_requested
        or normalized_situation.turn_kind is TurnKind.HIGH_STAKES_TURN
    ):
        judged = tuple(
            capability
            for capability in enforced
            if capability in {CAP_VOICE_CONSISTENCY, CAP_NPC_AGENCY, CAP_ACTION_RESOLUTION}
        )[:2]

    selected_or_observed = set(enforced) | set(observed_tuple) | set(judged)
    excluded = tuple(
        capability
        for capability in INITIAL_CAPABILITIES
        if capability not in selected_or_observed
    )
    warnings = [*budget_warnings]
    if not effective_budget.allow_llm_judges:
        warnings.append("llm_judges_disabled_by_budget")
    if not effective_budget.allow_heavy_forecast:
        warnings.append("heavy_forecast_disabled_by_budget")

    return CapabilitySelectionResult(
        situation=normalized_situation,
        budget=effective_budget,
        enforced=enforced,
        observed=observed_tuple,
        judged=judged,
        excluded=excluded,
        reason=reason,
        warnings=tuple(warnings),
    )
