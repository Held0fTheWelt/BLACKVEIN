"""Canonical WoS Langfuse LLM-as-a-Judge (categorical) evaluator catalog.

Single source of truth for judge ordering, matrix columns, repair cards, issue
routing, and (where documented) full Langfuse evaluator payloads. Deterministic
runtime gates must never be derived from or overridden by these evaluators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Literal

EvaluatorKind = Literal["llm_as_a_judge"]
EvaluatorScope = Literal["opening_generation", "turn_generation", "session_lifecycle"]
ScoreType = Literal["categorical"]

# Qualitative-only warning reused in previews and the primary turn-resolution judge prompt.
_QUALITATIVE_ONLY_SENTINEL: Final[str] = "This is a qualitative review signal only."

GATE_OVERRIDE_WARNING: Final[str] = (
    "This WoS LLM-as-a-Judge evaluator is qualitative-only and must not override "
    "deterministic runtime gates (ADR-0033 live runtime commit semantics, "
    "actor_lane_safety_pass, fallback_absent, non_mock_generation_pass, "
    "visible_output_present, usage_present, rag_context_attached, "
    "live_runtime_contract_pass, live_opening_contract_pass, can_execute, "
    "runtime_session_ready, opening_generation_status)."
)

# Do not attach categorical judges to LDSS/mock/deterministic-fallback generations when
# Langfuse metadata negation is available; otherwise rely on GENERATION + story.model.generation.
LLM_JUDGE_ADAPTER_EXCLUSION_HINTS: Final[tuple[str, ...]] = (
    "ldss_fallback",
    "mock",
    "ldss_deterministic",
)

LLM_JUDGE_ADAPTER_EXCLUSION_NOTE: Final[str] = (
    "Avoid scoring LDSS fallback or mock paths: exclude adapter metadata in "
    f"{', '.join(LLM_JUDGE_ADAPTER_EXCLUSION_HINTS)} when Langfuse supports negation. "
    "If negation is unavailable, GENERATION + observation name story.model.generation is "
    "the practical filter (repo does not emit that observation for those adapters)."
)

# Langfuse UI-style lists (evaluator attachment wizard).
OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS: Final[dict[str, Any]] = {
    "Type": ["GENERATION"],
    "Name": ["story.model.generation"],
    "Trace Name": ["world-engine.session.create"],
    "Environment": ["live"],
}

TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS: Final[dict[str, Any]] = {
    "Type": ["GENERATION"],
    "Name": ["story.model.generation"],
    "Trace Name": ["backend.turn.execute"],
    "Environment": ["live"],
}

# Compact operator templates (snake_case single values) for docs / MCP.
LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE: Final[dict[str, Any]] = {
    "observation_type": "GENERATION",
    "observation_name": "story.model.generation",
    "trace_name": "world-engine.session.create",
    "environment": "live",
    "metadata": {
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "turn_kind": "opening",
        "opening_turn": True,
        "turn_number": 0,
    },
    "legacy_trace_names_for_search_only": ["world-engine.session.create"],
}

LANGFUSE_TURN_GENERATION_FILTER_BUNDLE: Final[dict[str, Any]] = {
    "observation_type": "GENERATION",
    "observation_name": "story.model.generation",
    "trace_name": "backend.turn.execute",
    "environment": "live",
    "metadata": {
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "opening_turn": False,
    },
    "legacy_trace_names": ["world-engine.turn.execute"],
}

TURN_JUDGE_OPTIONAL_METADATA_HINT: Final[str] = (
    "If the Langfuse UI supports numeric trace metadata filters, prefer turn_number > 0 "
    "in addition to Trace Name backend.turn.execute and opening_turn=false; otherwise omit."
)


def langfuse_evaluator_filter_templates() -> dict[str, Any]:
    """Shared Langfuse filter bundles for MCP catalog (opening vs turn judge groups)."""
    return {
        "opening_generation": dict(LANGFUSE_OPENING_GENERATION_FILTER_BUNDLE),
        "turn_generation": dict(LANGFUSE_TURN_GENERATION_FILTER_BUNDLE),
    }


@dataclass(frozen=True)
class LangfuseCategoricalEvaluatorSpec:
    """Typed specification for a categorical Langfuse LLM-as-a-Judge evaluator."""

    name: str
    description: str
    kind: EvaluatorKind
    scope: EvaluatorScope
    score_type: ScoreType
    categories: tuple[str, ...]
    allow_multiple_matches: bool
    prompt: str
    score_reasoning_prompt: str
    category_selection_prompt: str
    qualitative_only: bool
    runtime_gate: bool
    replaces_deterministic_gates: bool
    applies_to: tuple[str, ...]
    required_input_fields: tuple[str, ...]
    issue_categories: frozenset[str]
    repair_card: str
    matrix_column_key: str
    display_short: str
    langfuse_observation_filters: dict[str, Any] = field(default_factory=dict)
    trace_metadata_filters: dict[str, Any] = field(default_factory=dict)
    legacy_trace_names: tuple[str, ...] = ()


def _opening_trace_meta() -> dict[str, Any]:
    return {
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "turn_kind": "opening",
        "opening_turn": True,
        "turn_number": 0,
    }


def _turn_trace_meta() -> dict[str, Any]:
    return {
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "opening_turn": False,
    }


def _stub_prompt_preamble() -> str:
    return (
        f"{_QUALITATIVE_ONLY_SENTINEL} Do not replace deterministic runtime gates, "
        "validators, or commit semantics.\n\n"
        "Full rubric text for this evaluator may be maintained in Langfuse; this "
        "catalog entry carries structured metadata for MCP operators and CI.\n\n"
        "Generation input:\n{{input}}\n\nGeneration output:\n{{output}}\n\n"
        "Observation metadata:\n{{metadata}}\n"
    )


def _stub_reasoning_prompt() -> str:
    return (
        "Explain briefly why the chosen category best matches the generation, "
        "referencing input, output, and metadata."
    )


def _stub_category_prompt(*, categories_csv: str) -> str:
    return f"Choose exactly one category: {categories_csv}."


_ORDER_NAMES: tuple[str, ...] = (
    "opening_experience_judge",
    "role_anchor_quality_judge",
    "theatrical_style_judge",
    "actor_lane_narrative_violation_judge",
    "rag_context_usefulness_judge",
    "player_action_intent_judge",
    "narrator_npc_boundary_judge",
    "visible_card_cleanliness_judge",
    "turn_relevance_judge",
    "language_consistency_judge",
    "dramatic_pacing_judge",
    "goc_tone_fidelity_judge",
    "player_action_resolution_judge",
    "blocked_action_playability_judge",
    "affordance_plausibility_judge",
    "npc_reaction_appropriateness_judge",
)

_SPECS_BY_NAME: dict[str, LangfuseCategoricalEvaluatorSpec] = {
    "opening_experience_judge": LangfuseCategoricalEvaluatorSpec(
        name="opening_experience_judge",
        description="First-impression quality of the live opening generation.",
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("excellent", "acceptable", "weak", "invalid"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="excellent, acceptable, weak, invalid"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "live_ui", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak", "invalid"}),
        repair_card="OPEN-EXP-01",
        matrix_column_key="opening_judge_category",
        display_short="opening experience",
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "role_anchor_quality_judge": LangfuseCategoricalEvaluatorSpec(
        name="role_anchor_quality_judge",
        description="Quality and presence of the player role anchor in the opening.",
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("strong_anchor", "adequate_anchor", "weak_anchor", "missing_anchor"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="strong_anchor, adequate_anchor, weak_anchor, missing_anchor"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "role_anchor", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak_anchor", "missing_anchor"}),
        repair_card="OPEN-ROLE-01",
        matrix_column_key="role_anchor_category",
        display_short="role anchor",
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "theatrical_style_judge": LangfuseCategoricalEvaluatorSpec(
        name="theatrical_style_judge",
        description="Theatrical style fidelity for the opening narration.",
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("alive_style", "acceptable", "flat", "broken_style"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="alive_style, acceptable, flat, broken_style"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "theatrical_style", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"flat", "broken_style"}),
        repair_card="OPEN-STYLE-01",
        matrix_column_key="style_category",
        display_short="theatrical style",
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "actor_lane_narrative_violation_judge": LangfuseCategoricalEvaluatorSpec(
        name="actor_lane_narrative_violation_judge",
        description="Narrative-level actor-lane concerns in the opening.",
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("no_concern", "possible_violation", "clear_violation"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="no_concern, possible_violation, clear_violation"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "actor_lane", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"possible_violation", "clear_violation"}),
        repair_card="OPEN-ACTORLANE-01",
        matrix_column_key="actor_lane_judge_category",
        display_short="actor-lane judge",
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "rag_context_usefulness_judge": LangfuseCategoricalEvaluatorSpec(
        name="rag_context_usefulness_judge",
        description="Usefulness of RAG context in the opening generation.",
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("strong_use", "weak_use", "no_or_bad_use"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="strong_use, weak_use, no_or_bad_use"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "rag", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak_use", "no_or_bad_use"}),
        repair_card="OPEN-RAG-01",
        matrix_column_key="rag_use_category",
        display_short="RAG use",
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "player_action_intent_judge": LangfuseCategoricalEvaluatorSpec(
        name="player_action_intent_judge",
        description="Whether player intent is respected vs hijacked in turn output.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("correct_intent", "wrong_intent", "invalid_takeover"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="correct_intent, wrong_intent, invalid_takeover"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "player_action", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"wrong_intent", "invalid_takeover"}),
        repair_card="TURN-INTENT-01",
        matrix_column_key="player_action_intent_category",
        display_short="player action intent",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "narrator_npc_boundary_judge": LangfuseCategoricalEvaluatorSpec(
        name="narrator_npc_boundary_judge",
        description="Narrator vs NPC boundary hygiene on the turn.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("healthy_boundary", "npc_narrates_action", "severe_boundary_violation"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="healthy_boundary, npc_narrates_action, severe_boundary_violation"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "narrator_npc", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"npc_narrates_action", "severe_boundary_violation"}),
        repair_card="TURN-NPCBOUNDARY-01",
        matrix_column_key="narrator_npc_boundary_category",
        display_short="narrator/NPC boundary",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "visible_card_cleanliness_judge": LangfuseCategoricalEvaluatorSpec(
        name="visible_card_cleanliness_judge",
        description="Visible card / projection cleanliness on the turn.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("clean", "messy", "broken_cards"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(categories_csv="clean, messy, broken_cards"),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"messy", "broken_cards"}),
        repair_card="TURN-CARD-01",
        matrix_column_key="visible_card_cleanliness_category",
        display_short="visible card cleanliness",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "turn_relevance_judge": LangfuseCategoricalEvaluatorSpec(
        name="turn_relevance_judge",
        description="Relevance of model output to the current turn context.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("strongly_related", "weakly_related", "irrelevant_or_wrong"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="strongly_related, weakly_related, irrelevant_or_wrong"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weakly_related", "irrelevant_or_wrong"}),
        repair_card="TURN-RELEVANCE-01",
        matrix_column_key="turn_relevance_category",
        display_short="turn relevance",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "language_consistency_judge": LangfuseCategoricalEvaluatorSpec(
        name="language_consistency_judge",
        description="Language consistency vs configured player/locale expectations.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("consistent", "mixed_language", "wrong_language"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="consistent, mixed_language, wrong_language"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"mixed_language", "wrong_language"}),
        repair_card="TURN-LANG-01",
        matrix_column_key="language_consistency_category",
        display_short="language consistency",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "dramatic_pacing_judge": LangfuseCategoricalEvaluatorSpec(
        name="dramatic_pacing_judge",
        description="Dramatic pacing of the visible turn output.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("effective_pacing", "weak_pacing", "broken_pacing"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="effective_pacing, weak_pacing, broken_pacing"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak_pacing", "broken_pacing"}),
        repair_card="TURN-PACING-01",
        matrix_column_key="dramatic_pacing_category",
        display_short="dramatic pacing",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "goc_tone_fidelity_judge": LangfuseCategoricalEvaluatorSpec(
        name="goc_tone_fidelity_judge",
        description="God of Carnage tonal fidelity in turn output.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("on_tone", "generic_tone", "wrong_tone"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(categories_csv="on_tone, generic_tone, wrong_tone"),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "goc", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"generic_tone", "wrong_tone"}),
        repair_card="TURN-GOC-TONE-01",
        matrix_column_key="goc_tone_fidelity_category",
        display_short="GoC tone fidelity",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "player_action_resolution_judge": LangfuseCategoricalEvaluatorSpec(
        name="player_action_resolution_judge",
        description=(
            "Evaluates whether a free player action was resolved correctly in an "
            "interactive World of Shadows turn."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("resolved_well", "partially_resolved", "misresolved", "not_resolved"),
        allow_multiple_matches=False,
        prompt=(
            "You are evaluating whether a free player action was resolved correctly in an "
            "interactive World of Shadows turn.\n\n"
            f"{_QUALITATIVE_ONLY_SENTINEL} Do not replace deterministic action-resolution, "
            "actor-lane, or runtime gates.\n\n"
            "Generation input:\n{{input}}\n\n"
            "Generation output:\n{{output}}\n\n"
            "Observation metadata:\n{{metadata}}\n\n"
            "Your task:\n"
            "Judge whether the player's input was resolved as the correct kind of in-world "
            "action, perception, movement, speech, or mixed move.\n\n"
            "Pay attention to:\n"
            '- whether movement such as "Gehe ins Bad" becomes an actual movement/action, '
            "not quoted speech\n"
            '- whether perception such as "Schau aus dem Fenster" leads to a '
            "perceptual/narrator consequence\n"
            "- whether speech/questions remain speech/questions\n"
            "- whether mixed input preserves both action and speech\n"
            "- whether the selected human actor owns the action\n"
            "- whether NPCs incorrectly explain or perform the player's action\n"
            "- whether the visible result is playable and follows the player's intent\n\n"
            "Rubric:\n\n"
            "resolved_well:\n"
            "The player action is clearly and correctly resolved. The selected player character "
            "performs or attempts the intended action, and the visible output follows naturally.\n\n"
            "partially_resolved:\n"
            "The action is mostly understood, but the result is incomplete, slightly awkward, "
            "too generic, or missing part of the intended consequence.\n\n"
            "misresolved:\n"
            "The system interprets the input as the wrong action type, wrong target, wrong "
            "actor, or wrong narrative function, but some relation to the input remains.\n\n"
            "not_resolved:\n"
            "The action is not resolved at all, is ignored, becomes technical failure text, or "
            "is replaced by unrelated NPC/narrator output."
        ),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the player action resolution. "
            "Mention the player's apparent intent, how it was rendered, and whether the "
            "selected player character actually performed or attempted the intended action."
        ),
        category_selection_prompt=(
            "Choose exactly one category: resolved_well, partially_resolved, misresolved, or "
            "not_resolved. Select not_resolved when the player action is ignored, turned into "
            "technical failure text, or not represented in the visible output."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=(
            "interactive_turn",
            "player_action",
            "visible_output",
            "story.model.generation",
        ),
        required_input_fields=(
            "input",
            "output",
            "metadata",
            "metadata.selected_human_actor",
            "metadata.human_actor_id",
            "metadata.actor_lane_validation",
            "metadata.player_input_kind",
            "metadata.semantic_move_kind",
            "metadata.visible_output_present",
            "metadata.adapter",
            "metadata.final_adapter",
            "metadata.fallback_reason",
        ),
        issue_categories=frozenset({"partially_resolved", "misresolved", "not_resolved"}),
        repair_card="TURN-ACTION-RESOLUTION-01",
        matrix_column_key="player_action_resolution_category",
        display_short="player action resolution",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "blocked_action_playability_judge": LangfuseCategoricalEvaluatorSpec(
        name="blocked_action_playability_judge",
        description="Playability and clarity when an action is blocked.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("clear_block", "unclear_block", "technical_failure"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="clear_block, unclear_block, technical_failure"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "blocked_action", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"unclear_block", "technical_failure"}),
        repair_card="TURN-BLOCKED-PLAY-01",
        matrix_column_key="blocked_action_playability_category",
        display_short="blocked action playability",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "affordance_plausibility_judge": LangfuseCategoricalEvaluatorSpec(
        name="affordance_plausibility_judge",
        description="Plausibility of affordances invoked on the turn.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("plausible", "questionable", "implausible"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="plausible, questionable, implausible"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "affordance", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"questionable", "implausible"}),
        repair_card="TURN-AFFORDANCE-01",
        matrix_column_key="affordance_plausibility_category",
        display_short="affordance plausibility",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
    "npc_reaction_appropriateness_judge": LangfuseCategoricalEvaluatorSpec(
        name="npc_reaction_appropriateness_judge",
        description="Appropriateness of NPC reactions relative to player agency.",
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("appropriate", "unnecessary_commentary", "npc_takes_over"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=_stub_reasoning_prompt(),
        category_selection_prompt=_stub_category_prompt(
            categories_csv="appropriate, unnecessary_commentary, npc_takes_over"
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "npc", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"unnecessary_commentary", "npc_takes_over"}),
        repair_card="TURN-NPC-REACTION-01",
        matrix_column_key="npc_reaction_appropriateness_category",
        display_short="NPC reaction appropriateness",
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=("world-engine.turn.execute",),
    ),
}


ORDERED_CATEGORICAL_EVALUATORS: tuple[LangfuseCategoricalEvaluatorSpec, ...] = tuple(
    _SPECS_BY_NAME[n] for n in _ORDER_NAMES
)

WOS_CATEGORICAL_JUDGES_ORDER: tuple[str, ...] = tuple(s.name for s in ORDERED_CATEGORICAL_EVALUATORS)

WOS_JUDGE_ISSUE_CATEGORIES: dict[str, frozenset[str]] = {
    s.name: s.issue_categories for s in ORDERED_CATEGORICAL_EVALUATORS
}

JUDGE_TO_REPAIR_CARD: dict[str, str] = {s.name: s.repair_card for s in ORDERED_CATEGORICAL_EVALUATORS}

MATRIX_JUDGE_COLUMN_KEYS: dict[str, str] = {s.name: s.matrix_column_key for s in ORDERED_CATEGORICAL_EVALUATORS}

JUDGE_DISPLAY_SHORT: dict[str, str] = {s.name: s.display_short for s in ORDERED_CATEGORICAL_EVALUATORS}

LEGACY_JUDGE_ISSUE_TOKENS: frozenset[str] = frozenset().union(
    *WOS_JUDGE_ISSUE_CATEGORIES.values(),
    frozenset(
        {
            "bad",
            "missing",
            "wrong_role",
            "unused",
            "misused",
            "partial",
        }
    ),
)


def all_categorical_evaluator_specs() -> tuple[LangfuseCategoricalEvaluatorSpec, ...]:
    return ORDERED_CATEGORICAL_EVALUATORS


def get_categorical_evaluator_spec(name: str) -> LangfuseCategoricalEvaluatorSpec | None:
    return _SPECS_BY_NAME.get(name)


def evaluator_spec_to_public_dict(
    spec: LangfuseCategoricalEvaluatorSpec,
    *,
    include_prompts: bool,
) -> dict[str, Any]:
    """Serialize evaluator for MCP catalog/get; optionally strip large prompt bodies."""
    base: dict[str, Any] = {
        "name": spec.name,
        "description": spec.description,
        "kind": spec.kind,
        "scope": spec.scope,
        "score_type": spec.score_type,
        "categories": list(spec.categories),
        "allow_multiple_matches": spec.allow_multiple_matches,
        "qualitative_only": spec.qualitative_only,
        "runtime_gate": spec.runtime_gate,
        "replaces_deterministic_gates": spec.replaces_deterministic_gates,
        "applies_to": list(spec.applies_to),
        "required_input_fields": list(spec.required_input_fields),
        "issue_categories": sorted(spec.issue_categories),
        "repair_card": spec.repair_card,
        "matrix_column_key": spec.matrix_column_key,
        "display_short": spec.display_short,
        "langfuse_observation_filters": dict(spec.langfuse_observation_filters),
        "trace_metadata_filters": dict(spec.trace_metadata_filters),
        "legacy_trace_names": list(spec.legacy_trace_names),
        "langfuse_filter_group": spec.scope,
        "recommended_adapter_exclusions_if_metadata_negation_supported": list(LLM_JUDGE_ADAPTER_EXCLUSION_HINTS),
        "adapter_exclusion_operator_note": LLM_JUDGE_ADAPTER_EXCLUSION_NOTE,
    }
    if spec.scope == "turn_generation":
        base["optional_trace_metadata_hint"] = TURN_JUDGE_OPTIONAL_METADATA_HINT
    if include_prompts:
        base["prompt"] = spec.prompt
        base["score_reasoning_prompt"] = spec.score_reasoning_prompt
        base["category_selection_prompt"] = spec.category_selection_prompt
    else:
        base["prompt"] = None
        base["score_reasoning_prompt"] = None
        base["category_selection_prompt"] = None
        base["prompt_omitted"] = True
    return base


def build_langfuse_sync_preview_payload(name: str) -> dict[str, Any] | None:
    """Deterministic Langfuse evaluator configuration preview (no API calls)."""
    spec = get_categorical_evaluator_spec(name)
    if spec is None:
        return None
    out: dict[str, Any] = {
        "name": spec.name,
        "score_type": spec.score_type,
        "categories": list(spec.categories),
        "allow_multiple_matches": spec.allow_multiple_matches,
        "prompt": spec.prompt,
        "score_reasoning_prompt": spec.score_reasoning_prompt,
        "category_selection_prompt": spec.category_selection_prompt,
        "observation_filters": dict(spec.langfuse_observation_filters),
        "legacy_trace_names": list(spec.legacy_trace_names),
        "trace_metadata_filters": dict(spec.trace_metadata_filters),
        "langfuse_filter_group": spec.scope,
        "recommended_adapter_exclusions_if_metadata_negation_supported": list(LLM_JUDGE_ADAPTER_EXCLUSION_HINTS),
        "adapter_exclusion_operator_note": LLM_JUDGE_ADAPTER_EXCLUSION_NOTE,
        "qualitative_only": spec.qualitative_only,
        "runtime_gate": spec.runtime_gate,
        "replaces_deterministic_gates": spec.replaces_deterministic_gates,
        "gate_override_warning": GATE_OVERRIDE_WARNING,
        "langfuse_filter_group_templates": langfuse_evaluator_filter_templates(),
    }
    if spec.scope == "turn_generation":
        out["optional_trace_metadata_hint"] = TURN_JUDGE_OPTIONAL_METADATA_HINT
    return out
