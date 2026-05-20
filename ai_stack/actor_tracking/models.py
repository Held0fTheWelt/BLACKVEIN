"""W5 Actor Situation Tracker — closed enums and record models.

See ADR-0063 (``docs/ADR/adr-0063-w5-actor-situation-tracker.md``).

All enum *values* are ``lower_snake_case`` strings (Python member names may be
``UPPER_CASE``). Records are frozen dataclasses with ``to_dict`` / ``from_dict``
helpers and stable ``schema_version`` strings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


W5_FACT_SCHEMA_VERSION = "w5_fact.v1"
W5_SNAPSHOT_SCHEMA_VERSION = "w5_snapshot.v1"
W5_PROJECTION_SCHEMA_VERSION = "w5_projection.v1"


class W5Dimension(str, Enum):
    WHO = "who"
    WHERE = "where"
    WHAT = "what"
    HOW = "how"
    WHY = "why"


class W5TruthLevel(str, Enum):
    CANONICAL = "canonical"
    OBSERVED = "observed"
    DECLARED = "declared"
    DIRECTOR_ASSIGNED = "director_assigned"
    INFERRED = "inferred"
    PROJECTED = "projected"


class W5Source(str, Enum):
    CANONICAL_CONTENT = "canonical_content"
    COMMITTED_ACTION = "committed_action"
    PARTICIPANT_STATE_MOVE = "participant_state_move"
    FREE_PLAYER_ACTION_RESOLUTION = "free_player_action_resolution"
    DIRECTOR_GATHERING_STATE = "director_gathering_state"
    DIRECTOR_COMPOSITION = "director_composition"
    NPC_AGENCY_SIMULATION = "npc_agency_simulation"
    CHARACTER_MIND_RECORD = "character_mind_record"
    SENSORY_CONTEXT_ENGINE = "sensory_context_engine"
    SOUFFLEUSE = "souffleuse"
    NARRATOR_COMPOSITION = "narrator_composition"
    ADMIN_OVERRIDE = "admin_override"


class W5VisibilityScope(str, Enum):
    PUBLIC = "public"
    PRIVATE_TO_ACTOR = "private_to_actor"
    GM_ONLY = "gm_only"
    DIRECTOR_ONLY = "director_only"


class W5FactStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    SUPERSEDED = "superseded"
    CONTRADICTED = "contradicted"
    RESOLVED = "resolved"
    PENDING_VALIDATION = "pending_validation"


class W5FreshnessStatus(str, Enum):
    FRESH = "fresh"
    AGING = "aging"
    STALE = "stale"


class W5ActorType(str, Enum):
    HUMAN = "human"
    NPC = "npc"
    NARRATOR = "narrator"


class W5ProjectionConsumer(str, Enum):
    NARRATOR = "narrator"
    NPC = "npc"
    DIRECTOR = "director"
    PLAYER_SHELL = "player_shell"
    ADMIN = "admin"
    DIAGNOSTICS = "diagnostics"


class W5ActionState(str, Enum):
    STARTING = "starting"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    STALE = "stale"


class W5ConflictResolutionStatus(str, Enum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"
    PENDING_DIRECTOR = "pending_director"


class W5ValidationFailureCode(str, Enum):
    W5_ACTOR_NOT_PRESENT = "w5_actor_not_present"
    W5_LOCATION_CONTINUITY_BREAK = "w5_location_continuity_break"
    W5_PERCEPTION_BREAK = "w5_perception_break"
    W5_ACTION_CONTINUITY_BREAK = "w5_action_continuity_break"
    W5_UNRESOLVED_CONFLICT = "w5_unresolved_conflict"


_DIMENSION_VALUES = frozenset(d.value for d in W5Dimension)
_TRUTH_VALUES = frozenset(t.value for t in W5TruthLevel)
_SOURCE_VALUES = frozenset(s.value for s in W5Source)
_VISIBILITY_VALUES = frozenset(v.value for v in W5VisibilityScope)
_FACT_STATUS_VALUES = frozenset(s.value for s in W5FactStatus)
_FRESHNESS_VALUES = frozenset(f.value for f in W5FreshnessStatus)
_ACTOR_TYPE_VALUES = frozenset(a.value for a in W5ActorType)
_CONSUMER_VALUES = frozenset(c.value for c in W5ProjectionConsumer)
_CONFLICT_RES_VALUES = frozenset(c.value for c in W5ConflictResolutionStatus)


# Centralized policy hook for why.* truth-level admissibility. Phase 2 keeps the
# Phase 1 rule (OBSERVED why.* is forbidden) so the W5 record stays the pure
# observation lane. A future engine-owned Why-commit ADR can relax this in one
# place without rewriting W5Fact construction everywhere.
_WHY_ADMITTED_TRUTH_LEVELS: frozenset[W5TruthLevel] = frozenset(
    {
        W5TruthLevel.INFERRED,
        W5TruthLevel.CANONICAL,
        W5TruthLevel.DECLARED,
        W5TruthLevel.DIRECTOR_ASSIGNED,
    }
)


def why_truth_level_is_admitted(truth_level: W5TruthLevel) -> bool:
    """Return True if ``truth_level`` is currently legal for a ``why.*`` fact.

    Single source of truth for the rule that OBSERVED why.* is forbidden in
    Phase 1 / Phase 2. A future engine-owned Why-commit ADR can relax this
    here without touching W5Fact or the extractor.
    """

    return truth_level in _WHY_ADMITTED_TRUTH_LEVELS


def _coerce_enum(value: Any, enum_cls: type[Enum], field_name: str) -> Enum:
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError as exc:
            raise ValueError(
                f"invalid {field_name} value {value!r} for {enum_cls.__name__}"
            ) from exc
    raise ValueError(
        f"invalid {field_name} value {value!r} for {enum_cls.__name__}"
    )


def _enum_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    return value


@dataclass(frozen=True)
class W5Fact:
    fact_id: str
    actor_id: str
    dimension: W5Dimension
    key: str
    value: Any
    source: W5Source
    truth_level: W5TruthLevel
    valid_from_turn: int
    last_confirmed_turn: int
    visibility: W5VisibilityScope
    status: W5FactStatus
    schema_version: str = W5_FACT_SCHEMA_VERSION
    source_event_id: str | None = None
    confidence: float = 1.0
    valid_until_turn: int | None = None
    actor_knowledge_scope: tuple[str, ...] = field(default_factory=tuple)
    superseded_by_fact_id: str | None = None
    contradicted_by_fact_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.fact_id, str) or not self.fact_id.strip():
            raise ValueError("W5Fact.fact_id must be a non-empty string")
        if self.schema_version != W5_FACT_SCHEMA_VERSION:
            raise ValueError(
                f"W5Fact.schema_version must be {W5_FACT_SCHEMA_VERSION!r}"
            )
        if not isinstance(self.actor_id, str) or not self.actor_id.strip():
            raise ValueError("W5Fact.actor_id must be a non-empty string")
        if self.dimension.value not in _DIMENSION_VALUES:
            raise ValueError(f"W5Fact.dimension invalid: {self.dimension!r}")
        if self.truth_level.value not in _TRUTH_VALUES:
            raise ValueError(f"W5Fact.truth_level invalid: {self.truth_level!r}")
        if self.source.value not in _SOURCE_VALUES:
            raise ValueError(f"W5Fact.source invalid: {self.source!r}")
        if self.visibility.value not in _VISIBILITY_VALUES:
            raise ValueError(f"W5Fact.visibility invalid: {self.visibility!r}")
        if self.status.value not in _FACT_STATUS_VALUES:
            raise ValueError(f"W5Fact.status invalid: {self.status!r}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                f"W5Fact.confidence must be in [0.0, 1.0]; got {self.confidence!r}"
            )
        if self.truth_level is W5TruthLevel.PROJECTED:
            raise ValueError(
                "W5Fact.truth_level must not be 'projected'; "
                "projected values belong in W5Projection"
            )
        if self.dimension is W5Dimension.WHY and not why_truth_level_is_admitted(
            self.truth_level
        ):
            raise ValueError(
                "W5Fact why.* must use a truth_level admitted by "
                "why_truth_level_is_admitted; OBSERVED why.* is forbidden in "
                "Phase 1/Phase 2 and only a future engine-owned Why-commit ADR "
                "may relax this in the central policy."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fact_id": self.fact_id,
            "actor_id": self.actor_id,
            "dimension": self.dimension.value,
            "key": self.key,
            "value": self.value,
            "source": self.source.value,
            "source_event_id": self.source_event_id,
            "truth_level": self.truth_level.value,
            "confidence": float(self.confidence),
            "valid_from_turn": int(self.valid_from_turn),
            "valid_until_turn": (
                None if self.valid_until_turn is None else int(self.valid_until_turn)
            ),
            "last_confirmed_turn": int(self.last_confirmed_turn),
            "visibility": self.visibility.value,
            "actor_knowledge_scope": list(self.actor_knowledge_scope),
            "status": self.status.value,
            "superseded_by_fact_id": self.superseded_by_fact_id,
            "contradicted_by_fact_id": self.contradicted_by_fact_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "W5Fact":
        return cls(
            schema_version=str(data.get("schema_version", W5_FACT_SCHEMA_VERSION)),
            fact_id=str(data["fact_id"]),
            actor_id=str(data["actor_id"]),
            dimension=_coerce_enum(data["dimension"], W5Dimension, "dimension"),  # type: ignore[arg-type]
            key=str(data["key"]),
            value=data.get("value"),
            source=_coerce_enum(data["source"], W5Source, "source"),  # type: ignore[arg-type]
            source_event_id=(
                None if data.get("source_event_id") is None else str(data["source_event_id"])
            ),
            truth_level=_coerce_enum(data["truth_level"], W5TruthLevel, "truth_level"),  # type: ignore[arg-type]
            confidence=float(data.get("confidence", 1.0)),
            valid_from_turn=int(data["valid_from_turn"]),
            valid_until_turn=(
                None if data.get("valid_until_turn") is None else int(data["valid_until_turn"])
            ),
            last_confirmed_turn=int(data["last_confirmed_turn"]),
            visibility=_coerce_enum(data["visibility"], W5VisibilityScope, "visibility"),  # type: ignore[arg-type]
            actor_knowledge_scope=tuple(str(a) for a in (data.get("actor_knowledge_scope") or [])),
            status=_coerce_enum(data["status"], W5FactStatus, "status"),  # type: ignore[arg-type]
            superseded_by_fact_id=(
                None
                if data.get("superseded_by_fact_id") is None
                else str(data["superseded_by_fact_id"])
            ),
            contradicted_by_fact_id=(
                None
                if data.get("contradicted_by_fact_id") is None
                else str(data["contradicted_by_fact_id"])
            ),
        )


@dataclass(frozen=True)
class W5ActorSituation:
    actor_id: str
    actor_type: W5ActorType
    freshness_status: W5FreshnessStatus
    last_confirmed_turn: int
    actor_role_in_scene: str | None = None
    involvement_type: str | None = None
    where: tuple[W5Fact, ...] = field(default_factory=tuple)
    what: tuple[W5Fact, ...] = field(default_factory=tuple)
    how: tuple[W5Fact, ...] = field(default_factory=tuple)
    why: tuple[W5Fact, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type.value,
            "actor_role_in_scene": self.actor_role_in_scene,
            "involvement_type": self.involvement_type,
            "where": [f.to_dict() for f in self.where],
            "what": [f.to_dict() for f in self.what],
            "how": [f.to_dict() for f in self.how],
            "why": [f.to_dict() for f in self.why],
            "freshness_status": self.freshness_status.value,
            "last_confirmed_turn": int(self.last_confirmed_turn),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "W5ActorSituation":
        return cls(
            actor_id=str(data["actor_id"]),
            actor_type=_coerce_enum(data["actor_type"], W5ActorType, "actor_type"),  # type: ignore[arg-type]
            actor_role_in_scene=(
                None
                if data.get("actor_role_in_scene") is None
                else str(data["actor_role_in_scene"])
            ),
            involvement_type=(
                None
                if data.get("involvement_type") is None
                else str(data["involvement_type"])
            ),
            where=tuple(W5Fact.from_dict(d) for d in (data.get("where") or [])),
            what=tuple(W5Fact.from_dict(d) for d in (data.get("what") or [])),
            how=tuple(W5Fact.from_dict(d) for d in (data.get("how") or [])),
            why=tuple(W5Fact.from_dict(d) for d in (data.get("why") or [])),
            freshness_status=_coerce_enum(
                data["freshness_status"], W5FreshnessStatus, "freshness_status"
            ),  # type: ignore[arg-type]
            last_confirmed_turn=int(data["last_confirmed_turn"]),
        )


@dataclass(frozen=True)
class W5Conflict:
    conflict_id: str
    actor_id: str
    dimension: W5Dimension
    competing_fact_ids: tuple[str, ...]
    resolution_status: W5ConflictResolutionStatus
    resolver_source: W5Source | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "actor_id": self.actor_id,
            "dimension": self.dimension.value,
            "competing_fact_ids": list(self.competing_fact_ids),
            "resolution_status": self.resolution_status.value,
            "resolver_source": _enum_value(self.resolver_source),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "W5Conflict":
        resolver_raw = data.get("resolver_source")
        resolver = (
            None
            if resolver_raw is None
            else _coerce_enum(resolver_raw, W5Source, "resolver_source")
        )
        return cls(
            conflict_id=str(data["conflict_id"]),
            actor_id=str(data["actor_id"]),
            dimension=_coerce_enum(data["dimension"], W5Dimension, "dimension"),  # type: ignore[arg-type]
            competing_fact_ids=tuple(str(x) for x in (data.get("competing_fact_ids") or [])),
            resolution_status=_coerce_enum(
                data["resolution_status"],
                W5ConflictResolutionStatus,
                "resolution_status",
            ),  # type: ignore[arg-type]
            resolver_source=resolver,  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class W5Snapshot:
    snapshot_id: str
    story_session_id: str
    turn_number: int
    created_at: str
    actors: dict[str, W5ActorSituation] = field(default_factory=dict)
    conflicts: tuple[W5Conflict, ...] = field(default_factory=tuple)
    derived_from_event_ids: tuple[str, ...] = field(default_factory=tuple)
    schema_version: str = W5_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != W5_SNAPSHOT_SCHEMA_VERSION:
            raise ValueError(
                f"W5Snapshot.schema_version must be {W5_SNAPSHOT_SCHEMA_VERSION!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "snapshot_id": self.snapshot_id,
            "story_session_id": self.story_session_id,
            "turn_number": int(self.turn_number),
            "actors": {aid: sit.to_dict() for aid, sit in self.actors.items()},
            "conflicts": [c.to_dict() for c in self.conflicts],
            "derived_from_event_ids": list(self.derived_from_event_ids),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "W5Snapshot":
        actors_raw = data.get("actors") or {}
        actors = {
            str(aid): W5ActorSituation.from_dict(sit) for aid, sit in actors_raw.items()
        }
        return cls(
            schema_version=str(data.get("schema_version", W5_SNAPSHOT_SCHEMA_VERSION)),
            snapshot_id=str(data["snapshot_id"]),
            story_session_id=str(data["story_session_id"]),
            turn_number=int(data["turn_number"]),
            actors=actors,
            conflicts=tuple(W5Conflict.from_dict(d) for d in (data.get("conflicts") or [])),
            derived_from_event_ids=tuple(
                str(x) for x in (data.get("derived_from_event_ids") or [])
            ),
            created_at=str(data.get("created_at") or ""),
        )


@dataclass(frozen=True)
class W5Projection:
    target_consumer: W5ProjectionConsumer
    who_summary: dict[str, Any] = field(default_factory=dict)
    where_summary: dict[str, Any] = field(default_factory=dict)
    what_summary: dict[str, Any] = field(default_factory=dict)
    how_summary: dict[str, Any] = field(default_factory=dict)
    why_summary: dict[str, Any] = field(default_factory=dict)
    source_attribution: dict[str, str] = field(default_factory=dict)
    truth_attribution: dict[str, str] = field(default_factory=dict)
    actor_id: str | None = None
    schema_version: str = W5_PROJECTION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != W5_PROJECTION_SCHEMA_VERSION:
            raise ValueError(
                f"W5Projection.schema_version must be {W5_PROJECTION_SCHEMA_VERSION!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "target_consumer": self.target_consumer.value,
            "actor_id": self.actor_id,
            "who_summary": dict(self.who_summary),
            "where_summary": dict(self.where_summary),
            "what_summary": dict(self.what_summary),
            "how_summary": dict(self.how_summary),
            "why_summary": dict(self.why_summary),
            "source_attribution": dict(self.source_attribution),
            "truth_attribution": dict(self.truth_attribution),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "W5Projection":
        return cls(
            schema_version=str(data.get("schema_version", W5_PROJECTION_SCHEMA_VERSION)),
            target_consumer=_coerce_enum(
                data["target_consumer"], W5ProjectionConsumer, "target_consumer"
            ),  # type: ignore[arg-type]
            actor_id=(None if data.get("actor_id") is None else str(data["actor_id"])),
            who_summary=dict(data.get("who_summary") or {}),
            where_summary=dict(data.get("where_summary") or {}),
            what_summary=dict(data.get("what_summary") or {}),
            how_summary=dict(data.get("how_summary") or {}),
            why_summary=dict(data.get("why_summary") or {}),
            source_attribution=dict(data.get("source_attribution") or {}),
            truth_attribution=dict(data.get("truth_attribution") or {}),
        )
