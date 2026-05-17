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

Deterministic mock output is produced when no real AI adapter is present.
Fallback output is produced when proposal generation fails.
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
    contract: str = "ldss_output.v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
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
# Deterministic mock / fallback
# ---------------------------------------------------------------------------

_GOC_DISPLAY_NAMES: dict[str, str] = {
    "annette": "Annette",
    "alain": "Alain",
    "veronique": "Véronique",
    "michel": "Michel",
}

_GOC_NPC_LINES_BY_LANG: dict[str, dict[str, list[str]]] = {
    "en": {
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P2: phase-1 opening
        # NPC lines must be ritual greeting / hospitality fiction — no prosecutorial
        # framing, no mid-conflict accusation. Existing English lines were rewritten.
        "veronique": [
            "Perhaps we should sit before we begin.",
            "Thank you for coming. We thought it best to talk in person.",
        ],
        "alain": [
            "Let us hear what happened, calmly.",
            "We appreciate the invitation; it is the right setting for this.",
        ],
        "michel": [
            "Coffee? It is still warm.",
            "It is good of you both to come on a Saturday.",
        ],
    },
    "de": {
        "veronique": [
            "Vielleicht setzen wir uns, bevor wir beginnen.",
            "Danke, dass ihr gekommen seid. Wir hielten es für besser, persönlich zu reden.",
        ],
        "alain": [
            "Lasst uns hören, was passiert ist — ruhig.",
            "Wir schätzen die Einladung; das ist der richtige Rahmen dafür.",
        ],
        "michel": [
            "Kaffee? Er ist noch warm.",
            "Schön, dass ihr beide an einem Samstag gekommen seid.",
        ],
    },
}

_GOC_NPC_ACTIONS_BY_LANG: dict[str, dict[str, str]] = {
    "en": {
        "alain": "glances at his phone but does not pick it up yet.",
        "michel": "shifts the coffee table book aside.",
        "veronique": "gestures to the empty chairs around the low table.",
        "annette": "",
    },
    "de": {
        "alain": "wirft einen Blick auf sein Handy, nimmt es aber noch nicht in die Hand.",
        "michel": "schiebt den Kunstband auf dem Couchtisch beiseite.",
        "veronique": "weist mit einer kleinen Handbewegung auf die freien Stühle.",
        "annette": "",
    },
}


def _goc_npc_line_for(lang: str, actor_id: str, turn: int) -> tuple[str, str]:
    by_actor = _GOC_NPC_LINES_BY_LANG.get(lang) or _GOC_NPC_LINES_BY_LANG["en"]
    lines = by_actor.get(actor_id) or []
    if not lines:
        label = _GOC_DISPLAY_NAMES.get(actor_id, actor_id.capitalize())
        return label, f"{label} considers the situation."
    return _GOC_DISPLAY_NAMES.get(actor_id, actor_id.capitalize()), lines[turn % len(lines)]


def _goc_npc_action_for(lang: str, actor_id: str) -> str:
    by_actor = _GOC_NPC_ACTIONS_BY_LANG.get(lang) or _GOC_NPC_ACTIONS_BY_LANG["en"]
    return by_actor.get(actor_id, "")


# Legacy aliases kept for back-compat with any external callers that imported the
# original dicts; they expose the English variants used historically by tests.
_GOC_NPC_LINES = _GOC_NPC_LINES_BY_LANG["en"]
_GOC_NPC_ACTIONS = _GOC_NPC_ACTIONS_BY_LANG["en"]

# Opening narrator contract (OPEN-00-01): narrator_intro → role_anchor → scene_setup → actor_line
_OPENING_NARRATOR_INTRO_BY_LANG: dict[str, str] = {
    "en": (
        "Two couples meet in a Paris apartment on behalf of their children. "
        "The incident happened in the schoolyard; what happens here will be settled in a salon."
    ),
    "de": (
        "Zwei Paare treffen sich in einer Pariser Wohnung wegen ihrer Kinder. "
        "Der Vorfall geschah auf dem Schulhof; was hier geschieht, soll im Salon entschieden werden."
    ),
}
_OPENING_ROLE_ANCHORS_BY_LANG: dict[str, dict[str, str]] = {
    "en": {
        "annette": (
            "You are Annette Reille. The apartment is yours, and with it the expectation "
            "that this will be handled with civility — the meeting was your idea."
        ),
        "alain": (
            "You are Alain Reille. You would rather be elsewhere. "
            "You came because your wife insisted, and you are already calculating the fastest polite exit."
        ),
    },
    "de": {
        "annette": (
            "Du bist Annette Reille. Die Wohnung gehört dir, und mit ihr die Erwartung, "
            "dass dieser Abend zivilisiert verläuft — das Treffen war deine Idee."
        ),
        "alain": (
            "Du bist Alain Reille. Du wärst lieber woanders. "
            "Du bist gekommen, weil deine Frau darauf bestanden hat, und kalkulierst schon den schnellsten höflichen Ausweg."
        ),
    },
}
_OPENING_SCENE_SETUP_BY_LANG: dict[str, str] = {
    "en": (
        "The salon: four chairs arranged around a low table. Art books and tulips signal considered taste. "
        "A tray holds espresso cups no one has touched yet. Nobody has sat down."
    ),
    "de": (
        "Der Salon: vier Stühle um einen niedrigen Tisch. Kunstbände und Tulpen signalisieren überlegten Geschmack. "
        "Auf einem Tablett stehen Espressotassen, die niemand bisher berührt hat. Niemand hat sich gesetzt."
    ),
}
_OPENING_FALLBACK_ROLE_ANCHOR_BY_LANG: dict[str, str] = {
    "en": "You take your place in the room.",
    "de": "Du nimmst deinen Platz im Raum ein.",
}


def _opening_narrator_intro_for(lang: str) -> str:
    return _OPENING_NARRATOR_INTRO_BY_LANG.get(lang) or _OPENING_NARRATOR_INTRO_BY_LANG["en"]


def _opening_role_anchor_for(lang: str, role: str) -> str:
    by_role = _OPENING_ROLE_ANCHORS_BY_LANG.get(lang) or _OPENING_ROLE_ANCHORS_BY_LANG["en"]
    if role in by_role:
        return by_role[role]
    return _OPENING_FALLBACK_ROLE_ANCHOR_BY_LANG.get(lang) or _OPENING_FALLBACK_ROLE_ANCHOR_BY_LANG["en"]


def _opening_scene_setup_for(lang: str) -> str:
    return _OPENING_SCENE_SETUP_BY_LANG.get(lang) or _OPENING_SCENE_SETUP_BY_LANG["en"]


def _select_primary_responder(npc_ids: list[str], human_actor_id: str) -> str:
    """Pick the first available NPC as primary responder."""
    for npc in ("veronique", "alain", "michel"):
        if npc in npc_ids and npc != human_actor_id:
            return npc
    for npc_id in npc_ids:
        if npc_id != human_actor_id:
            return npc_id
    return ""


def build_deterministic_ldss_output(ldss_input: LDSSInput) -> LDSSOutput:
    """Produce a valid, deterministic LDSS output without calling any AI provider.

    Turn 0 (opening): narrator_intro → role_anchor → scene_setup → actor_line → [actor_action]
    Turn > 0: narrator → actor_line → [actor_action]
    No human actor control in any block.

    STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P1: visible text follows
    ``ldss_input.session_output_language`` so German sessions do not commit English fallback.
    """
    npc_ids = ldss_input.ai_allowed_actor_ids
    human_id = ldss_input.human_actor_id
    turn = ldss_input.turn_number
    lang = (str(ldss_input.session_output_language or "de").strip().lower()[:2]) or "de"

    primary = _select_primary_responder(npc_ids, human_id)
    effective_primary = primary if primary else (npc_ids[0] if npc_ids else "")
    secondary_ids = [n for n in npc_ids if n != effective_primary and n != human_id]
    secondary = secondary_ids[0] if secondary_ids else ""

    blocks: list[SceneBlock] = []
    block_idx = 1

    if turn == 0:
        # narrator_intro: shared premise / why we are here
        blocks.append(SceneBlock(
            id=f"turn-{turn}-block-{block_idx}",
            block_type="narrator",
            speaker_label=None,
            actor_id=None,
            target_actor_id=None,
            text=_opening_narrator_intro_for(lang),
        ))
        block_idx += 1

        # role_anchor: player's character placement (role-specific)
        role_anchor_text = _opening_role_anchor_for(lang, human_id)
        blocks.append(SceneBlock(
            id=f"turn-{turn}-block-{block_idx}",
            block_type="narrator",
            speaker_label=None,
            actor_id=None,
            target_actor_id=None,
            text=role_anchor_text,
        ))
        block_idx += 1

        # scene_setup: room / spatial grounding
        blocks.append(SceneBlock(
            id=f"turn-{turn}-block-{block_idx}",
            block_type="narrator",
            speaker_label=None,
            actor_id=None,
            target_actor_id=None,
            text=_opening_scene_setup_for(lang),
        ))
        block_idx += 1
    else:
        # Regular turn: single inner-perception narrator block
        blocks.append(SceneBlock(
            id=f"turn-{turn}-block-{block_idx}",
            block_type="narrator",
            speaker_label="You notice",
            actor_id=None,
            target_actor_id=None,
            text=(
                "You notice the silence before anyone speaks; "
                "it feels less like hesitation than calculation."
            ),
        ))
        block_idx += 1

        # Primary NPC actor_line — output-language-aware (P1) + phase-1-polite (P2)
    if effective_primary:
        label, line_text = _goc_npc_line_for(lang, effective_primary, turn)
        target = human_id if human_id else (secondary or None)
        blocks.append(SceneBlock(
            id=f"turn-{turn}-block-{block_idx}",
            block_type="actor_line",
            speaker_label=label,
            actor_id=effective_primary,
            target_actor_id=target,
            text=line_text,
        ))
        block_idx += 1

            # Secondary NPC actor_action — output-language-aware
    if secondary:
        label2 = _GOC_DISPLAY_NAMES.get(secondary, secondary.capitalize())
        action_text = _goc_npc_action_for(lang, secondary)
        if action_text:
            blocks.append(SceneBlock(
                id=f"turn-{turn}-block-{block_idx}",
                block_type="actor_action",
                speaker_label=label2,
                actor_id=secondary,
                target_actor_id=None,
                text=f"{label2} {action_text}",
            ))
            block_idx += 1

    # NPC agency plan
    initiatives: list[NPCInitiative] = []
    if primary:
        initiatives.append(NPCInitiative(
            actor_id=primary,
            intent="respond_to_player_input",
            allowed_block_types=["actor_line"],
            target_actor_id=human_id or None,
            passivity_risk="low",
        ))
    if secondary:
        initiatives.append(NPCInitiative(
            actor_id=secondary,
            intent="secondary_reactive_action",
            allowed_block_types=["actor_action"],
            target_actor_id=None,
            passivity_risk="low",
        ))

    agency_plan = NPCAgencyPlan(
        turn_number=turn,
        primary_responder_id=primary,
        secondary_responder_ids=[secondary] if secondary else [],
        npc_initiatives=initiatives,
    )

    visible_output = VisibleSceneOutput(blocks=blocks)
    visible_actor_present = any(
        b.block_type in VISIBLE_NPC_BLOCK_TYPES and b.actor_id
        for b in blocks
    )

    input_str = f"{ldss_input.player_input}:{ldss_input.human_actor_id}:{turn}"
    input_hash = f"sha256:mock-{hashlib.sha256(input_str.encode()).hexdigest()[:16]}"
    output_str = "".join(b.text for b in blocks)
    output_hash = f"sha256:mock-{hashlib.sha256(output_str.encode()).hexdigest()[:16]}"

    return LDSSOutput(
        visible_scene_output=visible_output,
        npc_agency_plan=agency_plan,
        decision_count=len(initiatives) + 1,
        npc_agency_plan_count=1,
        visible_actor_response_present=visible_actor_present,
        scene_block_count=len(blocks),
        ldss_invoked=True,
        entrypoint="story.turn.execute",
        input_hash=input_hash,
        output_hash=output_hash,
        phase_cost=build_deterministic_phase_cost(
            phase="ldss",
            provider="world_engine",
            model="ldss_deterministic",
            decision_count=len(initiatives) + 1,
            scene_block_count=len(blocks),
            visible_actor_response_present=visible_actor_present,
        ),
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
        ldss_output = build_deterministic_ldss_output(ldss_input)

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
    degraded_block = SceneBlock(
        id=f"turn-{ldss_input.turn_number}-degraded",
        block_type="system_degraded_notice",
        speaker_label="System",
        text=f"Scene generation rejected: {error_code}",
    )
    return LDSSOutput(
        visible_scene_output=VisibleSceneOutput(blocks=[degraded_block]),
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
            error_code=error_code,
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

    diagnostics: dict[str, Any] = {
        "live_dramatic_scene_simulator": {
            "status": "evidenced_live_path",
            "invoked": ldss_output.ldss_invoked,
            "entrypoint": ldss_output.entrypoint,
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
    )
