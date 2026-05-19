"""Contract / envelope stub for ``runtime_diagnostic_snapshot.v1``.

This module is a **PR-0 stub**: it declares the envelope shape that PR-A,
PR-B, and PR-C of the NPC interactivity roadmap will populate. It does not
implement any runtime behavior, is not wired into any graph node, is not
imported by any production code today, and does not perform any I/O.

The envelope is the single source the existing world-engine UI diagnostic
pages (see roadmap ``NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`` section 3.5)
will read from once PR-A/B/C land. The contract guarantees:

* One source for diagnostic UI pages -- pages must not query Manager or
  RuntimeAspectLedger directly per page.
* No UI control / mutation fields -- this envelope is read-only diagnostic.
* Semantic capability consultation names only -- no Pi / numeric capability
  ids, no module-specific literals.

Authoritative governance:

* `docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference.md`
  (Phase-1 amendment names the four contracts this envelope wraps).
* `docs/ADR/adr-0061-director-pause-mode-for-gathering-interruption.md`
  (Draft -- Director-Pause shape).
* `docs/ADR/adr-0062-director-realization-thin-path.md` (composition path
  that PR-A movement realization rides on).
* `docs/MVPs/npc_interactivity_piv_log.md` (roadmap PIV index).
* `docs/implementation_logs/pr_0_npc_interactivity_contracts_piv.md`
  (PR-0 PIV artifact).

This module is intentionally a small frozen dataclass surface with literal
field names and one schema-version constant. PR-A/B/C extend the dataclass
field set or version the contract to ``.v2`` if the shape needs to evolve.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

RuntimeDiagnosticSnapshotSchemaVersion = Literal["runtime_diagnostic_snapshot.v1"]

RUNTIME_DIAGNOSTIC_SNAPSHOT_SCHEMA_VERSION: RuntimeDiagnosticSnapshotSchemaVersion = (
    "runtime_diagnostic_snapshot.v1"
)


# ---------------------------------------------------------------------------
# Placeholder sub-envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolverOutputPlaceholder:
    """Slot for the per-turn ``free_player_action_resolution.v1`` payload.

    PR-A will populate fields; PR-0 only reserves the slot. No runtime code
    constructs this dataclass.
    """

    contract_name: str = "free_player_action_resolution.v1"
    payload: dict | None = None


@dataclass(frozen=True)
class DirectorGatheringStatePlaceholder:
    """Slot for the per-tick ``director_gathering_state.v1`` snapshot.

    PR-C will populate fields; PR-0 only reserves the slot.
    """

    contract_name: str = "director_gathering_state.v1"
    payload: dict | None = None


@dataclass(frozen=True)
class CanonicalPathHoldEffectPlaceholder:
    """Slot for the ``canonical_path_hold_effect.v1`` field set.

    PR-B will populate fields; PR-0 only reserves the slot.
    """

    contract_name: str = "canonical_path_hold_effect.v1"
    payload: dict | None = None


@dataclass(frozen=True)
class NarratorConsequenceRealizationPlaceholder:
    """Slot for the ``narrator_consequence_realization.v1`` field set.

    PR-B will populate fields; PR-0 only reserves the slot.
    """

    contract_name: str = "narrator_consequence_realization.v1"
    payload: dict | None = None


# ---------------------------------------------------------------------------
# Top-level envelope
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeDiagnosticSnapshotEnvelope:
    """Top-level ``runtime_diagnostic_snapshot.v1`` envelope (stub).

    This is the read-only diagnostic surface for one ``(session_id, turn_number)``
    pair. PR-A/B/C populate the payload fields; PR-0 reserves the keys so the
    contract is stable before implementation begins.

    Forbidden contents (enforced by review):

    * No UI control / mutation fields.
    * No Pi / Pi-numbered capability ids; capability names are semantic
      runtime identifiers populated by PR-A/B/C in ``semantic_capability_consultation_names``.
    * No module-specific literals (actor names, room names, beat names).
    """

    schema_version: RuntimeDiagnosticSnapshotSchemaVersion = (
        RUNTIME_DIAGNOSTIC_SNAPSHOT_SCHEMA_VERSION
    )

    session_id: str | None = None
    turn_number: int | None = None

    canonical_step_id: str | None = None
    visible_block_emitted: bool | None = None

    resolver_output: ResolverOutputPlaceholder = field(
        default_factory=ResolverOutputPlaceholder
    )
    director_gathering_state: DirectorGatheringStatePlaceholder = field(
        default_factory=DirectorGatheringStatePlaceholder
    )
    canonical_path_hold_effect: CanonicalPathHoldEffectPlaceholder = field(
        default_factory=CanonicalPathHoldEffectPlaceholder
    )
    narrator_consequence_realization: NarratorConsequenceRealizationPlaceholder = (
        field(default_factory=NarratorConsequenceRealizationPlaceholder)
    )

    semantic_capability_consultation_names: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Required envelope key tuple (for shape tests)
# ---------------------------------------------------------------------------

REQUIRED_ENVELOPE_KEYS: tuple[str, ...] = (
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
)


REQUIRED_CONTRACT_PLACEHOLDER_NAMES: tuple[str, ...] = (
    "free_player_action_resolution.v1",
    "director_gathering_state.v1",
    "canonical_path_hold_effect.v1",
    "narrator_consequence_realization.v1",
)


__all__ = [
    "RUNTIME_DIAGNOSTIC_SNAPSHOT_SCHEMA_VERSION",
    "RuntimeDiagnosticSnapshotSchemaVersion",
    "ResolverOutputPlaceholder",
    "DirectorGatheringStatePlaceholder",
    "CanonicalPathHoldEffectPlaceholder",
    "NarratorConsequenceRealizationPlaceholder",
    "RuntimeDiagnosticSnapshotEnvelope",
    "REQUIRED_ENVELOPE_KEYS",
    "REQUIRED_CONTRACT_PLACEHOLDER_NAMES",
]
