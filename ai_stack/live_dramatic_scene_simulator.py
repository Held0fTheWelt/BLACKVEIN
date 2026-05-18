"""MVP3 Live Dramatic Scene Simulator (LDSS).

Produces SceneTurnEnvelope.v2 with validated scene blocks from a committed
God of Carnage solo turn. Invoked through the real story.turn.execute path in
world-engine/app/story_runtime/manager.py (_finalize_committed_turn).

Validation order (enforced before commit / before response packaging):
  1. actor_lane_blocks — reject human actor as AI speaker/actor
  2. dramatic_mass     — require at least one visible NPC actor response
  3. narrator_voice    — reject dialogue recap / forced player state / hidden intent
  4. passivity         — require visible NPC actor_line/action/env unless terminal
  5. affordance        — validate object admission tiers

When no real AI adapter has produced player-visible content, this module must
surface an explicit degraded fallback notice. It must not synthesize substitute
story prose.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from ai_stack.runtime_cost_attribution import build_deterministic_phase_cost


# ---------------------------------------------------------------------------
# Block types
# ---------------------------------------------------------------------------

VALID_BLOCK_TYPES: frozenset[str] = frozenset({
    "narrator",
    "actor_line",
    "actor_action",
    "environment_interaction",
    "souffleuse",
    "system_degraded_notice",
})

VISIBLE_NPC_BLOCK_TYPES: frozenset[str] = frozenset({
    "actor_line",
    "actor_action",
    "environment_interaction",
})

# ---------------------------------------------------------------------------
# Affordance tiers
# ---------------------------------------------------------------------------

VALID_AFFORDANCE_TIERS: frozenset[str] = frozenset({
    "canonical",
    "typical",
    "similar_allowed",
})

# ---------------------------------------------------------------------------
# Narrator rejection patterns
# ---------------------------------------------------------------------------

_NARRATOR_DIALOGUE_SUMMARY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(argue|discuss|debate|argue about)\b", re.IGNORECASE),
    re.compile(r"\b(Véronique|Veronique|Alain|Michel|Annette)\s+(and|says?|told|ask)\b", re.IGNORECASE),
    re.compile(r"\bwhile\s+\w+\s+becomes?\s+\b", re.IGNORECASE),
]

_NARRATOR_FORCED_STATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bYou\s+(decide|feel|know|realize|understand|think|believe)\s+that\b", re.IGNORECASE),
    re.compile(r"\bYou\s+(are|were)\s+(right|wrong|ashamed|angry|happy)\b", re.IGNORECASE),
]

_NARRATOR_HIDDEN_INTENT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b\w+\s+(secretly|actually|really|truly)\s+(wants?|plans?|intends?)\b", re.IGNORECASE),
    re.compile(r"\bYou\s+can\s+see\s+through\s+\w+\b", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------

@dataclass
class SceneBlockDelivery:
    mode: str = "typewriter"
    characters_per_second: int = 44
    pause_before_ms: int = 150
    pause_after_ms: int = 650
    skippable: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "characters_per_second": self.characters_per_second,
            "pause_before_ms": self.pause_before_ms,
            "pause_after_ms": self.pause_after_ms,
            "skippable": self.skippable,
        }


@dataclass
class SceneBlock:
    id: str
    block_type: str
    text: str
    speaker_label: str = ""
    actor_id: str | None = None
    target_actor_id: str | None = None
    object_id: str | None = None
    affordance_tier: str | None = None
    delivery: SceneBlockDelivery = field(default_factory=SceneBlockDelivery)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "block_type": self.block_type,
            "speaker_label": self.speaker_label,
            "actor_id": self.actor_id,
            "target_actor_id": self.target_actor_id,
            "text": self.text,
            "delivery": self.delivery.to_dict(),
        }
        if self.object_id is not None:
            d["object_id"] = self.object_id
        if self.affordance_tier is not None:
            d["affordance_tier"] = self.affordance_tier
        return d


@dataclass
class VisibleSceneOutput:
    blocks: list[SceneBlock] = field(default_factory=list)
    contract: str = "visible_scene_output.blocks.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "blocks": [b.to_dict() for b in self.blocks],
        }


@dataclass
class NPCInitiative:
    actor_id: str
    intent: str
    allowed_block_types: list[str]
    target_actor_id: str | None = None
    passivity_risk: str = "low"

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "intent": self.intent,
            "allowed_block_types": list(self.allowed_block_types),
            "target_actor_id": self.target_actor_id,
            "passivity_risk": self.passivity_risk,
        }


@dataclass
class NPCAgencyPlan:
    turn_number: int
    primary_responder_id: str
    secondary_responder_ids: list[str]
    npc_initiatives: list[NPCInitiative] = field(default_factory=list)
    contract: str = "npc_agency_plan.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "turn_number": self.turn_number,
            "primary_responder_id": self.primary_responder_id,
            "secondary_responder_ids": list(self.secondary_responder_ids),
            "npc_initiatives": [i.to_dict() for i in self.npc_initiatives],
        }


@dataclass
class LDSSInput:
    story_session_state: dict[str, Any]
    actor_lane_context: dict[str, Any]
    player_input: str
    admitted_objects: list[dict[str, Any]] = field(default_factory=list)
    contract: str = "ldss_input.v1"
    # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P1: explicit session
    # output language so deterministic LDSS fallback projects language-correct visible text.
    session_output_language: str = "de"
    # Canonical path consumption (Phase 5): when set, the LDSS renders deterministic
    # scene blocks from the canonical step instead of returning a degraded notice.
    canonical_step_id: str | None = None
    canonical_path: Any | None = None  # ai_stack.canonical_path_resolver.CanonicalPath

    @property
    def human_actor_id(self) -> str:
        return str(self.actor_lane_context.get("human_actor_id") or "").strip()

    @property
    def ai_allowed_actor_ids(self) -> list[str]:
        raw = self.actor_lane_context.get("ai_allowed_actor_ids") or []
        return [str(a) for a in raw if str(a).strip()]

    @property
    def ai_forbidden_actor_ids(self) -> list[str]:
        raw = self.actor_lane_context.get("ai_forbidden_actor_ids") or []
        return [str(a) for a in raw if str(a).strip()]

    @property
    def turn_number(self) -> int:
        return int(self.story_session_state.get("turn_number") or 0)

    @property
    def content_module_id(self) -> str:
        return str(self.story_session_state.get("content_module_id") or "").strip()

    @property
    def runtime_profile_id(self) -> str:
        return str(self.story_session_state.get("runtime_profile_id") or "").strip()

    @property
    def selected_player_role(self) -> str:
        return str(self.story_session_state.get("selected_player_role") or "").strip()

    @property
    def current_scene_id(self) -> str:
        return str(self.story_session_state.get("current_scene_id") or "phase_1").strip()


@dataclass
class LDSSOutput:
    visible_scene_output: VisibleSceneOutput
    npc_agency_plan: NPCAgencyPlan | None = None
    decision_count: int = 0
    npc_agency_plan_count: int = 0
    visible_actor_response_present: bool = False
    scene_block_count: int = 0
    ldss_invoked: bool = True
    entrypoint: str = "story.turn.execute"
    input_hash: str = ""
    output_hash: str = ""
    phase_cost: dict[str, Any] = field(default_factory=dict)
    legacy_blob_used: bool = False
    status: str = "approved"
    error_code: str = ""
    error_message: str = ""
    contract: str = "ldss_output.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "status": self.status,
            "error_code": self.error_code,
            "error_message": self.error_message,
            "decision_count": self.decision_count,
            "npc_agency_plan_count": self.npc_agency_plan_count,
            "visible_actor_response_present": self.visible_actor_response_present,
            "scene_block_count": self.scene_block_count,
            "ldss_invoked": self.ldss_invoked,
            "entrypoint": self.entrypoint,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "phase_cost": dict(self.phase_cost),
            "legacy_blob_used": self.legacy_blob_used,
            "visible_scene_output": self.visible_scene_output.to_dict(),
            "npc_agency_plan": self.npc_agency_plan.to_dict() if self.npc_agency_plan else None,
        }


@dataclass
class SceneTurnEnvelopeV2:
    content_module_id: str
    runtime_profile_id: str
    runtime_module_id: str
    selected_player_role: str
    human_actor_id: str
    npc_actor_ids: list[str]
    visible_scene_output: VisibleSceneOutput
    diagnostics: dict[str, Any]
    npc_agency_plan: dict[str, Any] | None = None
    contract: str = "scene_turn_envelope.v2"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "content_module_id": self.content_module_id,
            "runtime_profile_id": self.runtime_profile_id,
            "runtime_module_id": self.runtime_module_id,
            "selected_player_role": self.selected_player_role,
            "human_actor_id": self.human_actor_id,
            "npc_actor_ids": list(self.npc_actor_ids),
            "npc_agency_plan": dict(self.npc_agency_plan) if isinstance(self.npc_agency_plan, dict) else None,
            "visible_scene_output": self.visible_scene_output.to_dict(),
            "diagnostics": dict(self.diagnostics),
        }


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class LDSSValidationResult:
    status: str  # "approved" | "rejected"
    error_code: str | None = None
    message: str | None = None
    block_index: int | None = None
    actor_id: str | None = None

    @property
    def approved(self) -> bool:
        return self.status == "approved"


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def validate_actor_lane_blocks(
    blocks: list[SceneBlock],
    human_actor_id: str,
    *,
    ai_forbidden_actor_ids: list[str] | None = None,
) -> LDSSValidationResult:
    """Reject any block where AI controls the human actor.

    Must be called before commit and before response packaging.
    """
    forbidden = set(ai_forbidden_actor_ids or [human_actor_id])

    for idx, block in enumerate(blocks):
        actor = block.actor_id or ""
        if actor and actor in forbidden:
            return LDSSValidationResult(
                status="rejected",
                error_code="ai_controlled_human_actor",
                message=(
                    f"AI output cannot speak, act, or control the selected human actor {actor!r}. "
                    f"Block type: {block.block_type}"
                ),
                block_index=idx,
                actor_id=actor,
            )

    return LDSSValidationResult(status="approved")


def validate_dramatic_mass(blocks: list[SceneBlock]) -> LDSSValidationResult:
    """At least one visible NPC actor_line, actor_action, or environment_interaction required."""
    for block in blocks:
        if block.block_type in VISIBLE_NPC_BLOCK_TYPES and block.actor_id:
            return LDSSValidationResult(status="approved")
    return LDSSValidationResult(
        status="rejected",
        error_code="dramatic_alignment_insufficient_mass",
        message=(
            "No visible NPC actor response present. "
            "At least one actor_line, actor_action, or environment_interaction must appear."
        ),
    )


def validate_narrator_voice(narrator_text: str) -> LDSSValidationResult:
    """Narrator must be inner perception/orientation only.

    Rejected modes:
    - dialogue_summary: recaps what characters said
    - forced_player_state: tells player how they feel/decide
    - hidden_npc_intent: reveals undisclosed internal motivation
    """
    for pattern in _NARRATOR_DIALOGUE_SUMMARY_PATTERNS:
        if pattern.search(narrator_text):
            return LDSSValidationResult(
                status="rejected",
                error_code="narrator_dialogue_summary_rejected",
                message="Narrator cannot summarize or recap dialogue between characters.",
            )
    for pattern in _NARRATOR_FORCED_STATE_PATTERNS:
        if pattern.search(narrator_text):
            return LDSSValidationResult(
                status="rejected",
                error_code="narrator_forces_player_state",
                message="Narrator cannot force player emotional or decision state.",
            )
    for pattern in _NARRATOR_HIDDEN_INTENT_PATTERNS:
        if pattern.search(narrator_text):
            return LDSSValidationResult(
                status="rejected",
                error_code="narrator_reveals_hidden_intent",
                message="Narrator cannot reveal undisclosed NPC motivations.",
            )
    return LDSSValidationResult(status="approved")


def validate_passivity(blocks: list[SceneBlock]) -> LDSSValidationResult:
    """Require at least one visible NPC actor response (non-terminal turns)."""
    visible_actor_present = any(
        b.block_type in VISIBLE_NPC_BLOCK_TYPES and b.actor_id
        for b in blocks
    )
    if not visible_actor_present:
        return LDSSValidationResult(
            status="rejected",
            error_code="no_visible_actor_response",
            message=(
                "At least one visible NPC actor_line, actor_action, or environment_interaction "
                "must occur unless the turn is explicitly terminal."
            ),
        )
    return LDSSValidationResult(status="approved")


def validate_affordance(
    env_block: SceneBlock,
    admitted_objects: list[dict[str, Any]],
) -> LDSSValidationResult:
    """Validate environment_interaction object admission and affordance tier."""
    object_id = env_block.object_id or ""
    affordance_tier = env_block.affordance_tier or ""

    if not object_id:
        return LDSSValidationResult(
            status="rejected",
            error_code="environment_object_not_admitted",
            message="environment_interaction block missing object_id",
        )

    if affordance_tier not in VALID_AFFORDANCE_TIERS:
        return LDSSValidationResult(
            status="rejected",
            error_code="environment_object_not_admitted",
            message=f"Invalid affordance_tier {affordance_tier!r} for object {object_id!r}",
        )

    admitted_ids = {
        str(o.get("object_id") or "").strip()
        for o in admitted_objects
        if isinstance(o, dict)
    }

    if object_id not in admitted_ids:
        return LDSSValidationResult(
            status="rejected",
            error_code="environment_object_not_admitted",
            message=f"Object {object_id!r} is not in the admitted objects set",
            actor_id=env_block.actor_id,
        )

    return LDSSValidationResult(status="approved")


def validate_similar_allowed_requires_reason(
    env_block: SceneBlock,
    similarity_reason: str | None,
) -> LDSSValidationResult:
    """similar_allowed affordance requires a canonical_similarity_reason."""
    if (env_block.affordance_tier or "") == "similar_allowed" and not (similarity_reason or "").strip():
        return LDSSValidationResult(
            status="rejected",
            error_code="similar_allowed_requires_similarity_reason",
            message=(
                f"similar_allowed affordance for object {env_block.object_id!r} "
                "requires a non-empty canonical_similarity_reason."
            ),
        )
    return LDSSValidationResult(status="approved")


# ---------------------------------------------------------------------------
# Responder candidate validation
# ---------------------------------------------------------------------------

def validate_responder_candidates(
    primary_responder_id: str,
    secondary_responder_ids: list[str],
    human_actor_id: str,
) -> LDSSValidationResult:
    """Human actor must not be in responder candidates."""
    all_responders = [primary_responder_id] + secondary_responder_ids
    for rid in all_responders:
        if rid == human_actor_id:
            return LDSSValidationResult(
                status="rejected",
                error_code="human_actor_selected_as_responder",
                message=f"Human actor {human_actor_id!r} cannot be a responder candidate.",
                actor_id=rid,
            )
    return LDSSValidationResult(status="approved")


# ---------------------------------------------------------------------------
# Explicit degraded fallback
# ---------------------------------------------------------------------------

LDSS_NO_LIVE_VISIBLE_GENERATION = "ldss_no_live_visible_generation"
LDSS_VALIDATION_REJECTED = "ldss_validation_rejected"

_LDSS_DEGRADED_TEXT_BY_LANG: dict[str, str] = {
    "en": (
        "Fallback: LDSS error {error_code}. Live scene generation did not produce canonical visible output. "
        "No substitute story text was committed."
    ),
    "de": (
        "Fallback: LDSS-Fehler {error_code}. Die Live-Szenengenerierung hat keinen kanonischen sichtbaren Output erzeugt. "
        "Es wurde keine Ersatz-Erzählung übernommen."
    ),
}

_LDSS_REJECTED_TEXT_BY_LANG: dict[str, str] = {
    "en": "Fallback: LDSS error {error_code}. Scene generation failed validation. No substitute narration was committed.",
    "de": "Fallback: LDSS-Fehler {error_code}. Die Szenengenerierung ist an der Validierung gescheitert. Es wurde keine Ersatz-Erzählung übernommen.",
}


def _ldss_lang(ldss_input: LDSSInput) -> str:
    return (str(ldss_input.session_output_language or "de").strip().lower()[:2]) or "de"


def _ldss_degraded_text_for(lang: str, error_code: str) -> str:
    template = _LDSS_DEGRADED_TEXT_BY_LANG.get(lang) or _LDSS_DEGRADED_TEXT_BY_LANG["en"]
    return template.format(error_code=error_code)


def _ldss_rejected_text_for(lang: str, error_code: str) -> str:
    template = _LDSS_REJECTED_TEXT_BY_LANG.get(lang) or _LDSS_REJECTED_TEXT_BY_LANG["en"]
    return template.format(error_code=error_code)


def _only_degraded_notice(blocks: list[SceneBlock]) -> bool:
    return bool(blocks) and all(b.block_type == "system_degraded_notice" for b in blocks)


def build_deterministic_ldss_output(ldss_input: LDSSInput) -> LDSSOutput:
    """Return an explicit degraded notice when LDSS has no live generated content.

    This function used to synthesize GoC-specific narrator, role-anchor, room,
    NPC speech, and NPC action prose. That made a fallback path look like canon.
    The fallback is now deliberately non-fictional and language-aware.
    """
    turn = ldss_input.turn_number
    lang = _ldss_lang(ldss_input)
    error_code = LDSS_NO_LIVE_VISIBLE_GENERATION
    error_message = "LDSS deterministic fallback had no live canonical visible generation to commit."
    blocks = [
        SceneBlock(
            id=f"turn-{turn}-degraded",
            block_type="system_degraded_notice",
            speaker_label="System",
            actor_id=None,
            target_actor_id=None,
            text=_ldss_degraded_text_for(lang, error_code),
        )
    ]

    visible_output = VisibleSceneOutput(blocks=blocks)
    input_str = f"{ldss_input.player_input}:{ldss_input.human_actor_id}:{turn}"
    input_hash = f"sha256:mock-{hashlib.sha256(input_str.encode()).hexdigest()[:16]}"
    output_hash = f"sha256:mock-{hashlib.sha256(blocks[0].text.encode()).hexdigest()[:16]}"

    return LDSSOutput(
        visible_scene_output=visible_output,
        npc_agency_plan=None,
        status="degraded_error",
        error_code=error_code,
        error_message=error_message,
        decision_count=0,
        npc_agency_plan_count=0,
        visible_actor_response_present=False,
        scene_block_count=len(blocks),
        ldss_invoked=True,
        entrypoint="story.turn.execute",
        input_hash=input_hash,
        output_hash=output_hash,
        phase_cost=build_deterministic_phase_cost(
            phase="ldss",
            provider="world_engine",
            model="ldss_deterministic",
            status="degraded_no_visible_generation",
            error_code=error_code,
            error_message=error_message,
            scene_block_count=len(blocks),
            visible_actor_response_present=False,
        ),
        legacy_blob_used=False,
    )


# ---------------------------------------------------------------------------
# Canonical-step LDSS output (Phase 5)
# ---------------------------------------------------------------------------

def build_canonical_step_ldss_output(ldss_input: LDSSInput) -> LDSSOutput | None:
    """Render the active canonical step into a deterministic LDSSOutput.

    Returns None when the input does not carry a resolvable canonical step;
    callers fall back to the degraded notice path.
    """
    canonical_path = ldss_input.canonical_path
    step_id = (ldss_input.canonical_step_id or "").strip()
    if not canonical_path or not step_id:
        return None

    # Lazy import keeps live_dramatic_scene_simulator importable without yaml.
    from ai_stack.canonical_step_renderer import render_canonical_step

    rendered = render_canonical_step(
        canonical_path,
        step_id,
        turn_number=ldss_input.turn_number,
        human_actor_id=ldss_input.human_actor_id,
    )
    if rendered is None:
        return None

    blocks = rendered.visible_scene_output.blocks
    input_str = f"{step_id}:{ldss_input.player_input}:{ldss_input.human_actor_id}:{ldss_input.turn_number}"
    input_hash = f"sha256:canon-{hashlib.sha256(input_str.encode()).hexdigest()[:16]}"
    output_seed = "|".join(b.text for b in blocks)
    output_hash = f"sha256:canon-{hashlib.sha256(output_seed.encode()).hexdigest()[:16]}"

    visible_present = any(b.block_type in VISIBLE_NPC_BLOCK_TYPES and b.actor_id for b in blocks)
    phase_cost = build_deterministic_phase_cost(
        phase="ldss",
        provider="world_engine",
        model="ldss_canonical_path",
        status="approved",
        scene_block_count=len(blocks),
        visible_actor_response_present=visible_present,
    )

    return LDSSOutput(
        visible_scene_output=rendered.visible_scene_output,
        npc_agency_plan=rendered.npc_agency_plan,
        status="approved",
        decision_count=len(rendered.forces_response_records) or len(blocks),
        npc_agency_plan_count=1 if rendered.npc_agency_plan else 0,
        visible_actor_response_present=visible_present,
        scene_block_count=len(blocks),
        ldss_invoked=True,
        entrypoint="story.turn.execute",
        input_hash=input_hash,
        output_hash=output_hash,
        phase_cost=phase_cost,
        legacy_blob_used=False,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_ldss(ldss_input: LDSSInput) -> LDSSOutput:
    """Run the Live Dramatic Scene Simulator with Langfuse span tracking.

    Produces validated structured output from a God of Carnage solo turn.
    Uses deterministic output (no external AI call required for tests).

    Validation order:
    1. Build proposal (deterministic)
    2. Validate actor lanes (before commit)
    3. Validate dramatic mass (before commit)
    4. Validate passivity (before commit)
    5. Return validated output

    Returns output with embedded cost/token info for Phase B aggregation.
    """
    # Phase B: Create Langfuse span for LDSS simulation (lazy import).
    try:
        from app.observability.langfuse_adapter import LangfuseAdapter
        adapter = LangfuseAdapter.get_instance()
    except ImportError:
        adapter = None

    ldss_span = None
    if adapter:
        parent_span = adapter.get_active_span()
        if parent_span:
            ldss_span = adapter.create_child_span(
                name="live_dramatic_scene_simulator",
                input={
                    "scene_id": ldss_input.current_scene_id,
                    "turn_number": ldss_input.turn_number,
                    "actor_ids": ldss_input.ai_allowed_actor_ids,
                },
                metadata={
                    "scene_id": ldss_input.current_scene_id,
                    "turn_number": ldss_input.turn_number,
                }
            )

    try:
        canonical_output = build_canonical_step_ldss_output(ldss_input)
        if canonical_output is not None:
            ldss_output = canonical_output

            # Canonical-step output is authored truth; only the actor-lane
            # guard applies (no AI controlling the human). dramatic_mass and
            # passivity assumptions are written for the live-generation
            # fallback path and do not apply to authored narrator-only beats.
            lane_result = validate_actor_lane_blocks(
                ldss_output.visible_scene_output.blocks,
                human_actor_id=ldss_input.human_actor_id,
                ai_forbidden_actor_ids=ldss_input.ai_forbidden_actor_ids,
            )
            if not lane_result.approved:
                if ldss_span:
                    ldss_span.update(
                        output={"status": "rejected", "error": lane_result.error_code},
                        metadata={"validation_failed": True, "error_code": lane_result.error_code},
                    )
                return _build_rejected_ldss_output(
                    ldss_input=ldss_input,
                    error_code=lane_result.error_code or "actor_lane_validation_failed",
                    message=lane_result.message or "Actor lane validation rejected canonical output.",
                )

            if ldss_span:
                ldss_span.update(
                    output={
                        "block_count": len(ldss_output.visible_scene_output.blocks),
                        "decision_count": ldss_output.decision_count,
                        "status": "approved",
                        "source": "canonical_path",
                    },
                    metadata={
                        "block_count": len(ldss_output.visible_scene_output.blocks),
                        "decision_count": ldss_output.decision_count,
                        "canonical_step_id": ldss_input.canonical_step_id,
                        **ldss_output.phase_cost,
                        "phase_cost": dict(ldss_output.phase_cost),
                    },
                )
            return ldss_output

        ldss_output = build_deterministic_ldss_output(ldss_input)

        if _only_degraded_notice(ldss_output.visible_scene_output.blocks):
            if ldss_span:
                ldss_span.update(
                    output={
                        "status": "degraded_error",
                        "error_code": ldss_output.error_code,
                    },
                    metadata={
                        "validation_failed": False,
                        "error_code": ldss_output.error_code,
                        "error_message": ldss_output.error_message,
                        "phase_cost": dict(ldss_output.phase_cost),
                    },
                )
            return ldss_output

        # Validate actor lanes (must run before commit)
        lane_result = validate_actor_lane_blocks(
            ldss_output.visible_scene_output.blocks,
            human_actor_id=ldss_input.human_actor_id,
            ai_forbidden_actor_ids=ldss_input.ai_forbidden_actor_ids,
        )
        if not lane_result.approved:
            # Return degraded output with validation error — do not commit illegal blocks
            if ldss_span:
                ldss_span.update(
                    output={"status": "rejected", "error": lane_result.error_code},
                    metadata={
                        "validation_failed": True,
                        "error_code": lane_result.error_code,
                        "phase_cost": dict(ldss_output.phase_cost),
                    },
                )
            return _build_rejected_ldss_output(
                ldss_input=ldss_input,
                error_code=lane_result.error_code or "actor_lane_validation_failed",
                message=lane_result.message or "Actor lane validation rejected proposal.",
            )

        # Validate dramatic mass (before commit)
        mass_result = validate_dramatic_mass(ldss_output.visible_scene_output.blocks)
        if not mass_result.approved:
            if ldss_span:
                ldss_span.update(
                    output={"status": "rejected", "error": mass_result.error_code},
                    metadata={
                        "validation_failed": True,
                        "error_code": mass_result.error_code,
                        "phase_cost": dict(ldss_output.phase_cost),
                    },
                )
            return _build_rejected_ldss_output(
                ldss_input=ldss_input,
                error_code=mass_result.error_code or "dramatic_alignment_insufficient_mass",
                message=mass_result.message or "Insufficient dramatic mass.",
            )

        # Validate passivity (before commit)
        passivity_result = validate_passivity(ldss_output.visible_scene_output.blocks)
        if not passivity_result.approved:
            if ldss_span:
                ldss_span.update(
                    output={"status": "rejected", "error": passivity_result.error_code},
                    metadata={
                        "validation_failed": True,
                        "error_code": passivity_result.error_code,
                        "phase_cost": dict(ldss_output.phase_cost),
                    },
                )
            return _build_rejected_ldss_output(
                ldss_input=ldss_input,
                error_code=passivity_result.error_code or "no_visible_actor_response",
                message=passivity_result.message or "Passivity validation failed.",
            )

        # Phase B: Update span with LDSS output metrics
        if ldss_span:
            ldss_span.update(
                output={
                    "block_count": len(ldss_output.visible_scene_output.blocks),
                    "decision_count": ldss_output.decision_count,
                    "status": "approved"
                },
                metadata={
                    "block_count": len(ldss_output.visible_scene_output.blocks),
                    "decision_count": ldss_output.decision_count,
                    **ldss_output.phase_cost,
                    "phase_cost": dict(ldss_output.phase_cost),
                },
            )

        return ldss_output

    except Exception as e:
        if ldss_span:
            ldss_span.update(
                output={"error": str(e)},
                metadata={"error": True, "error_type": type(e).__name__}
            )
        raise

    finally:
        if ldss_span:
            ldss_span.end()


def _build_rejected_ldss_output(
    ldss_input: LDSSInput,
    error_code: str,
    message: str,
) -> LDSSOutput:
    """Return a structured rejection output — does not commit illegal state."""
    lang = _ldss_lang(ldss_input)
    visible_error_code = error_code or LDSS_VALIDATION_REJECTED
    error_message = message or "LDSS proposal failed validation."
    degraded_block = SceneBlock(
        id=f"turn-{ldss_input.turn_number}-degraded",
        block_type="system_degraded_notice",
        speaker_label="System",
        text=_ldss_rejected_text_for(lang, visible_error_code),
    )
    return LDSSOutput(
        visible_scene_output=VisibleSceneOutput(blocks=[degraded_block]),
        status="rejected_error",
        error_code=visible_error_code,
        error_message=error_message,
        decision_count=0,
        npc_agency_plan_count=0,
        visible_actor_response_present=False,
        scene_block_count=1,
        ldss_invoked=True,
        phase_cost=build_deterministic_phase_cost(
            phase="ldss",
            provider="world_engine",
            model="ldss_deterministic",
            status="rejected",
            error_code=visible_error_code,
            error_message=error_message,
        ),
        legacy_blob_used=False,
    )


# ---------------------------------------------------------------------------
# Scene turn envelope builder
# ---------------------------------------------------------------------------

def build_scene_turn_envelope_v2(
    *,
    ldss_input: LDSSInput,
    ldss_output: LDSSOutput,
    story_session_id: str = "",
    turn_number: int = 0,
    runtime_module_id: str = "solo_story_runtime",
) -> SceneTurnEnvelopeV2:
    """Build the final SceneTurnEnvelope.v2 from validated LDSS output."""
    ldss_dict = ldss_output.to_dict()
    agency_plan = ldss_output.npc_agency_plan
    ldss_status = ldss_output.status or (
        "degraded_error" if ldss_output.error_code else "evidenced_live_path"
    )

    diagnostics: dict[str, Any] = {
        "live_dramatic_scene_simulator": {
            "status": ldss_status,
            "invoked": ldss_output.ldss_invoked,
            "entrypoint": ldss_output.entrypoint,
            "error_present": bool(ldss_output.error_code),
            "error_code": ldss_output.error_code or None,
            "error_message": ldss_output.error_message or None,
            "decision_count": ldss_output.decision_count,
            "output_contract": "visible_scene_output.blocks.v1",
            "scene_block_count": ldss_output.scene_block_count,
            "visible_actor_response_present": ldss_output.visible_actor_response_present,
            "legacy_blob_used": ldss_output.legacy_blob_used,
            "story_session_id": story_session_id,
            "turn_number": turn_number,
            "input_hash": ldss_output.input_hash,
            "output_hash": ldss_output.output_hash,
        },
        "npc_agency": {
            "primary_responder_id": agency_plan.primary_responder_id if agency_plan else None,
            "secondary_responder_ids": agency_plan.secondary_responder_ids if agency_plan else [],
            "visible_actor_response_present": ldss_output.visible_actor_response_present,
            "npc_agency_plan_count": ldss_output.npc_agency_plan_count,
        },
        "actor_lane_enforcement": {
            "human_actor_id": ldss_input.human_actor_id,
            "ai_allowed_actor_ids": ldss_input.ai_allowed_actor_ids,
            "ai_forbidden_actor_ids": ldss_input.ai_forbidden_actor_ids,
            "validation_ran_before_commit": True,
        },
        "phase_cost": dict(ldss_output.phase_cost),
    }

    return SceneTurnEnvelopeV2(
        content_module_id=ldss_input.content_module_id or "god_of_carnage",
        runtime_profile_id=ldss_input.runtime_profile_id or "god_of_carnage_solo",
        runtime_module_id=runtime_module_id,
        selected_player_role=ldss_input.selected_player_role,
        human_actor_id=ldss_input.human_actor_id,
        npc_actor_ids=list(ldss_input.ai_allowed_actor_ids),
        npc_agency_plan=agency_plan.to_dict() if agency_plan else None,
        visible_scene_output=ldss_output.visible_scene_output,
        diagnostics=diagnostics,
    )


# ---------------------------------------------------------------------------
# Helpers for building LDSSInput from session / graph state
# ---------------------------------------------------------------------------

def build_ldss_input_from_session(
    *,
    session_id: str,
    module_id: str,
    turn_number: int,
    selected_player_role: str,
    human_actor_id: str,
    npc_actor_ids: list[str],
    player_input: str,
    current_scene_id: str = "phase_1",
    runtime_profile_id: str = "god_of_carnage_solo",
    content_module_id: str = "god_of_carnage",
    admitted_objects: list[dict[str, Any]] | None = None,
    session_output_language: str = "de",
    canonical_step_id: str | None = None,
    canonical_path: Any | None = None,
) -> LDSSInput:
    """Build LDSSInput from story session state fields."""
    story_session_state = {
        "contract": "story_session_state.v1",
        "story_session_id": session_id,
        "turn_number": turn_number,
        "content_module_id": content_module_id,
        "runtime_profile_id": runtime_profile_id,
        "runtime_module_id": "solo_story_runtime",
        "current_scene_id": current_scene_id,
        "selected_player_role": selected_player_role,
        "human_actor_id": human_actor_id,
        "npc_actor_ids": npc_actor_ids,
        "visitor_present": False,
        "canonical_step_id": canonical_step_id,
    }
    actor_lane_context = {
        "contract": "actor_lane_context.v1",
        "content_module_id": content_module_id,
        "runtime_profile_id": runtime_profile_id,
        "selected_player_role": selected_player_role,
        "human_actor_id": human_actor_id,
        "actor_lanes": {
            human_actor_id: "human",
            **{npc: "npc" for npc in npc_actor_ids},
        },
        "ai_allowed_actor_ids": sorted(npc_actor_ids),
        "ai_forbidden_actor_ids": [human_actor_id],
    }
    return LDSSInput(
        story_session_state=story_session_state,
        actor_lane_context=actor_lane_context,
        player_input=player_input,
        admitted_objects=admitted_objects or [],
        session_output_language=session_output_language,
        canonical_step_id=canonical_step_id,
        canonical_path=canonical_path,
    )
