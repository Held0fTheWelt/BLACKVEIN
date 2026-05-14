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
CategorySeverity = Literal["positive", "warning", "failure", "neutral", "unknown"]

# Human-maintained canonical rubric + prompts (multi-line). Python catalog mirrors names/categories.
LLM_AS_A_JUDGE_DOC_RELATIVE_PATH: Final[str] = (
    "docs/llm-as-a-judge/LLM-as-a-Judge Definition Table - Judges.csv"
)

# Repo evidence: backend opens root span ``backend.turn.execute``; world-engine participates with
# ``world-engine.turn.execute`` on the same distributed trace (see backend session/game routes).
BACKEND_TURN_ROOT_TRACE_NAME: Final[str] = "backend.turn.execute"
WORLD_ENGINE_TURN_TRACE_NAME: Final[str] = "world-engine.turn.execute"
# Opening trace name (session creation emits this root span — see
# ``OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS`` below).
WORLD_ENGINE_OPENING_TRACE_NAME: Final[str] = "world-engine.session.create"

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
    "Trace Name": [WORLD_ENGINE_TURN_TRACE_NAME],
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
    "trace_name": WORLD_ENGINE_TURN_TRACE_NAME,
    "environment": "live",
    "metadata": {
        "trace_origin": "live_ui",
        "execution_tier": "live",
        "canonical_player_flow": True,
        "opening_turn": False,
    },
    "alternate_backend_root_trace_name": BACKEND_TURN_ROOT_TRACE_NAME,
    "legacy_trace_names": [BACKEND_TURN_ROOT_TRACE_NAME],
}

TURN_JUDGE_OPTIONAL_METADATA_HINT: Final[str] = (
    "If the Langfuse UI supports numeric trace metadata filters, prefer turn_number > 0 "
    f"in addition to Trace Name {WORLD_ENGINE_TURN_TRACE_NAME} and opening_turn=false; "
    f"when scores were recorded on the backend root instead, also try {BACKEND_TURN_ROOT_TRACE_NAME}."
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
    evaluator_group: str = "unknown"
    positive_categories: frozenset[str] = field(default_factory=frozenset)
    warning_categories: frozenset[str] = field(default_factory=frozenset)
    failure_categories: frozenset[str] = field(default_factory=frozenset)
    neutral_categories: frozenset[str] = field(default_factory=frozenset)
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
        f"Canonical rubric wording lives in {LLM_AS_A_JUDGE_DOC_RELATIVE_PATH} "
        "(WoS LLM-as-a-Judge definition table). This catalog mirrors categories, "
        "scopes, and operator semantics for MCP.\n\n"
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
    "runtime_aspect_integrity_judge",
    "narrator_authority_judge",
    "npc_authority_violation_judge",
    "dramatic_capability_realization_judge",
    "beat_realization_judge",
    "recoverable_outcome_quality_judge",
    "visible_origin_consistency_judge",
    "relationship_pressure_judge",
    "player_turn_playability_judge",
)

_SPECS_BY_NAME: dict[str, LangfuseCategoricalEvaluatorSpec] = {
    "opening_experience_judge": LangfuseCategoricalEvaluatorSpec(
        name="opening_experience_judge",
        description=(
            "Bewertet, ob die Eröffnung als spielbarer Einstieg funktioniert. Achtet auf "
            "Narrator-geführte Einführung, klare Rollenverankerung, Ort, Prämisse, sozialen Druck "
            "und fehlende Debug-/Fallback-Artefakte."
        ),
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("excellent", "acceptable", "weak", "invalid"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the player-facing opening. "
            "Mention the main strength or failure: role anchor, premise, staging, theatrical "
            "quality, fallback-like text, diagnostics, or actor dialogue before introduction."
        ),
        category_selection_prompt=(
            "Choose exactly one category: excellent, acceptable, weak, or invalid. "
            "Select invalid if the opening does not function as a player-facing introduction."
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
        evaluator_group="opening_story_quality",
        positive_categories=frozenset({"excellent"}),
        warning_categories=frozenset({"acceptable"}),
        failure_categories=frozenset({"weak", "invalid"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "role_anchor_quality_judge": LangfuseCategoricalEvaluatorSpec(
        name="role_anchor_quality_judge",
        description=(
            "Bewertet, ob der ausgewählte Spielercharakter klar und korrekt im Output "
            "verankert ist. Erkennt fehlende, falsche oder nur schwache Rollenorientierung."
        ),
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("clear", "partial", "missing", "wrong_role"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the role anchoring. Mention whether "
            "the selected player role is clear, partial, missing, or confused with another character."
        ),
        category_selection_prompt=(
            "Choose exactly one category: clear, partial, missing, or wrong_role. "
            "Select wrong_role if the output anchors or controls the wrong character. "
            "Select missing if no usable player-role anchor is present."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "role_anchor", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"partial", "missing", "wrong_role"}),
        repair_card="OPEN-ROLE-01",
        matrix_column_key="role_anchor_category",
        display_short="role anchor",
        evaluator_group="opening_story_quality",
        positive_categories=frozenset({"clear"}),
        warning_categories=frozenset({"partial"}),
        failure_categories=frozenset({"missing", "wrong_role"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "theatrical_style_judge": LangfuseCategoricalEvaluatorSpec(
        name="theatrical_style_judge",
        description=(
            "Bewertet die theatrale Qualität des Outputs. Achtet auf konkrete Inszenierung, "
            "Spannung, Gesten, Subtext und vermeidet flache oder rein funktionale Prosa."
        ),
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("theatrical", "serviceable", "flat", "bad"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the theatrical style. Mention "
            "concrete staging, subtext, rhythm, generic filler, emotional overexplanation, "
            "or lack of dramatic pressure."
        ),
        category_selection_prompt=(
            "Choose exactly one category: theatrical, serviceable, flat, or bad. "
            "Select bad if the prose is generic filler, debug-like, incoherent, or not a "
            "playable dramatic scene."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "theatrical_style", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"flat", "bad"}),
        repair_card="OPEN-STYLE-01",
        matrix_column_key="style_category",
        display_short="theatrical style",
        evaluator_group="opening_story_quality",
        positive_categories=frozenset({"theatrical"}),
        warning_categories=frozenset({"serviceable"}),
        failure_categories=frozenset({"flat", "bad"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "actor_lane_narrative_violation_judge": LangfuseCategoricalEvaluatorSpec(
        name="actor_lane_narrative_violation_judge",
        description=(
            "Bewertet, ob die AI den ausgewählten Human Actor respektiert. Erkennt, wenn die AI "
            "für den Spieler spricht, handelt oder dessen innere Zustände unzulässig festlegt."
        ),
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("no_violation", "possible_violation", "clear_violation"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the actor-lane safety review. "
            "Mention whether the selected human actor is controlled, ambiguously influenced, "
            "or left under player agency."
        ),
        category_selection_prompt=(
            "Choose exactly one category: no_violation, possible_violation, or clear_violation. "
            "Select clear_violation only when the generated output clearly controls the selected "
            "human player character."
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
        evaluator_group="authority_origin",
        positive_categories=frozenset({"no_violation"}),
        warning_categories=frozenset({"possible_violation"}),
        failure_categories=frozenset({"clear_violation"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "rag_context_usefulness_judge": LangfuseCategoricalEvaluatorSpec(
        name="rag_context_usefulness_judge",
        description=(
            "Bewertet, ob bereitgestellter RAG-Kontext sinnvoll genutzt wurde. Erkennt, ob "
            "Kontext hilfreich eingebunden, ignoriert oder falsch/verzerrt verwendet wurde."
        ),
        kind="llm_as_a_judge",
        scope="opening_generation",
        score_type="categorical",
        categories=("strong_use", "some_use", "unused", "misused"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the context use. Mention whether the "
            "output uses, partially uses, ignores, or contradicts the provided context."
        ),
        category_selection_prompt=(
            "Choose exactly one category: strong_use, some_use, unused, or misused. "
            "Select misused if the output contradicts or distorts the provided context. "
            "Select unused if the output is generic or disconnected from the context."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("opening_generation", "rag", "visible_output"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"unused", "misused"}),
        repair_card="OPEN-RAG-01",
        matrix_column_key="rag_use_category",
        display_short="RAG use",
        evaluator_group="opening_story_quality",
        positive_categories=frozenset({"strong_use"}),
        warning_categories=frozenset({"some_use"}),
        failure_categories=frozenset({"unused", "misused"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_opening_trace_meta(),
        legacy_trace_names=("world-engine.session.create",),
    ),
    "player_action_intent_judge": LangfuseCategoricalEvaluatorSpec(
        name="player_action_intent_judge",
        description=(
            "Bewertet, ob die Spielereingabe semantisch richtig verstanden wurde. Unterscheidet "
            "unter anderem Sprache, Frage, Bewegung, Wahrnehmung, soziale Handlung, "
            "Objektinteraktion und Mixed Input."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("correct_intent", "minor_mismatch", "wrong_intent", "invalid_takeover"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches player intent handling. Mention the "
            "apparent player_input_kind and whether the output preserves the player’s intended "
            "action/speech/perception."
        ),
        category_selection_prompt=(
            "Choose exactly one category: correct_intent, minor_mismatch, wrong_intent, or "
            "invalid_takeover. Select invalid_takeover when the player input is assigned to an "
            "NPC or the NPC takes over the player action."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "player_action", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"minor_mismatch", "wrong_intent", "invalid_takeover"}),
        repair_card="TURN-INTENT-01",
        matrix_column_key="player_action_intent_category",
        display_short="player action intent",
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"correct_intent"}),
        warning_categories=frozenset({"minor_mismatch"}),
        failure_categories=frozenset({"wrong_intent", "invalid_takeover"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "narrator_npc_boundary_judge": LangfuseCategoricalEvaluatorSpec(
        name="narrator_npc_boundary_judge",
        description=(
            "Bewertet die Grenze zwischen Narrator- und NPC-Aufgaben. Prüft, ob der Narrator Raum, "
            "Wahrnehmung und Konsequenzen führt und NPCs nicht unzulässig narrativ übernehmen."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("clean_boundary", "minor_blur", "npc_narrates_action", "severe_boundary_violation"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches narrator/NPC boundary quality. "
            "Mention whether spatial/perceptual consequences are handled by the narrator or "
            "incorrectly by NPCs."
        ),
        category_selection_prompt=(
            "Choose exactly one category: clean_boundary, minor_blur, npc_narrates_action, or "
            "severe_boundary_violation. Select severe_boundary_violation when NPCs take over "
            "narrator or player-action responsibilities."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "narrator_npc", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"minor_blur", "npc_narrates_action", "severe_boundary_violation"}),
        repair_card="TURN-NPCBOUNDARY-01",
        matrix_column_key="narrator_npc_boundary_category",
        display_short="narrator/NPC boundary",
        evaluator_group="authority_origin",
        positive_categories=frozenset({"clean_boundary"}),
        warning_categories=frozenset({"minor_blur"}),
        failure_categories=frozenset({"npc_narrates_action", "severe_boundary_violation"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "visible_card_cleanliness_judge": LangfuseCategoricalEvaluatorSpec(
        name="visible_card_cleanliness_judge",
        description=(
            "Bewertet die Sauberkeit der sichtbaren Karten. Achtet auf doppelte Inhalte, "
            "name-only Cards, Label-Stottern, technische Artefakte oder falsch zusammengeführte "
            "Action-/Speech-Texte."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("clean", "minor_artifacts", "messy", "broken_cards"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches visible card cleanliness. Mention "
            "duplicated cards, name stutter, internal labels, or formatting artifacts if present."
        ),
        category_selection_prompt=(
            "Choose exactly one category: clean, minor_artifacts, messy, or broken_cards. "
            "Select broken_cards when visible card formatting seriously harms playability."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"minor_artifacts", "messy", "broken_cards"}),
        repair_card="TURN-CARD-01",
        matrix_column_key="visible_card_cleanliness_category",
        display_short="visible card cleanliness",
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"clean"}),
        warning_categories=frozenset({"minor_artifacts"}),
        failure_categories=frozenset({"messy", "broken_cards"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "turn_relevance_judge": LangfuseCategoricalEvaluatorSpec(
        name="turn_relevance_judge",
        description=(
            "Bewertet, ob der Output auf den aktuellen Spielerinput und die aktuelle Szene "
            "relevant reagiert. Erkennt ausweichende, generische oder thematisch falsche Antworten."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("directly_relevant", "broadly_relevant", "weakly_related", "irrelevant_or_wrong"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches turn relevance. Mention whether the "
            "response answers, reacts to, or misinterprets the player input."
        ),
        category_selection_prompt=(
            "Choose exactly one category: directly_relevant, broadly_relevant, weakly_related, or "
            "irrelevant_or_wrong. Select irrelevant_or_wrong when the output ignores or "
            "misattributes the player input."
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
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"directly_relevant"}),
        warning_categories=frozenset({"broadly_relevant"}),
        failure_categories=frozenset({"weakly_related", "irrelevant_or_wrong"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "language_consistency_judge": LangfuseCategoricalEvaluatorSpec(
        name="language_consistency_judge",
        description=(
            "Bewertet, ob die Sprache des Outputs konsistent zur erwarteten Spielsitzung bleibt. "
            "Erkennt Sprachwechsel, Mischsprache oder falsche Ausgabesprache."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("consistent", "minor_drift", "mixed_language", "wrong_language"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches language consistency. Mention the "
            "expected language and any visible drift or language leakage."
        ),
        category_selection_prompt=(
            "Choose exactly one category: consistent, minor_drift, mixed_language, or wrong_language. "
            "Select wrong_language when the output is mostly not in the expected session language."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"minor_drift", "mixed_language", "wrong_language"}),
        repair_card="TURN-LANG-01",
        matrix_column_key="language_consistency_category",
        display_short="language consistency",
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"consistent"}),
        warning_categories=frozenset({"minor_drift"}),
        failure_categories=frozenset({"mixed_language", "wrong_language"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "dramatic_pacing_judge": LangfuseCategoricalEvaluatorSpec(
        name="dramatic_pacing_judge",
        description=(
            "Bewertet den dramatischen Rhythmus eines Turns. Prüft, ob der Turn Druck, Reaktion "
            "oder Konsequenz erzeugt, ohne zu hetzen, zu stocken oder zu viel zu erklären."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("strong_pacing", "acceptable_pacing", "weak_pacing", "broken_pacing"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches dramatic pacing. Mention whether the "
            "turn is too thin, too verbose, too repetitive, or well paced."
        ),
        category_selection_prompt=(
            "Choose exactly one category: strong_pacing, acceptable_pacing, weak_pacing, or "
            "broken_pacing. Select broken_pacing when the turn is visibly incoherent, stalled, "
            "or repetitive."
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
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"strong_pacing"}),
        warning_categories=frozenset({"acceptable_pacing"}),
        failure_categories=frozenset({"weak_pacing", "broken_pacing"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "goc_tone_fidelity_judge": LangfuseCategoricalEvaluatorSpec(
        name="goc_tone_fidelity_judge",
        description=(
            "Bewertet, ob der Turn den God-of-Carnage-artigen Ton trifft. Achtet auf höfliche "
            "Oberfläche, Subtext, soziale Peinlichkeit, Eskalation und vermeidet generische "
            "Mediation oder Genre-Drift."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("strong_fidelity", "acceptable_fidelity", "generic_tone", "wrong_tone"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches GoC tone fidelity. Mention whether "
            "the output has bourgeois politeness, social pressure, and specific staging or "
            "instead feels generic/wrong-genre."
        ),
        category_selection_prompt=(
            "Choose exactly one category: strong_fidelity, acceptable_fidelity, generic_tone, or "
            "wrong_tone. Select wrong_tone when the output clearly belongs to the wrong genre or style."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "goc", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"generic_tone", "wrong_tone"}),
        repair_card="TURN-GOC-TONE-01",
        matrix_column_key="goc_tone_fidelity_category",
        display_short="GoC tone fidelity",
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"strong_fidelity"}),
        warning_categories=frozenset({"acceptable_fidelity"}),
        failure_categories=frozenset({"generic_tone", "wrong_tone"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
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
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"resolved_well"}),
        warning_categories=frozenset({"partially_resolved"}),
        failure_categories=frozenset({"misresolved", "not_resolved"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "blocked_action_playability_judge": LangfuseCategoricalEvaluatorSpec(
        name="blocked_action_playability_judge",
        description=(
            "Bewertet, ob blockierte, unklare oder nur teilweise mögliche Aktionen spielbar "
            "beantwortet werden. Prüft, ob der Spieler eine verständliche, in-world Erklärung "
            "oder Rückfrage erhält statt eines technischen Fehlers."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("playable_block", "acceptable_clarification", "unclear_block", "technical_failure"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the blocked/clarification handling. "
            "Mention whether the player receives a playable explanation or useful next-step clarification."
        ),
        category_selection_prompt=(
            "Choose exactly one category: playable_block, acceptable_clarification, unclear_block, "
            "or technical_failure. Select technical_failure when the output exposes backend/runtime "
            "failure or gives no playable blocked-action response."
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
        evaluator_group="recovery_playability",
        positive_categories=frozenset({"playable_block"}),
        warning_categories=frozenset({"acceptable_clarification"}),
        failure_categories=frozenset({"unclear_block", "technical_failure"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "affordance_plausibility_judge": LangfuseCategoricalEvaluatorSpec(
        name="affordance_plausibility_judge",
        description=(
            "Bewertet, ob die angenommene Handlungsmöglichkeit zur Szene und zu den etablierten "
            "Objekten/Orten passt. Hilft zu erkennen, ob die Runtime plausible Affordances nutzt "
            "oder unpassende Dinge erfindet."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=("plausible", "acceptable_inference", "questionable", "implausible"),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches affordance plausibility. Mention the "
            "action target, whether it fits the scene, and whether the inference is justified or disruptive."
        ),
        category_selection_prompt=(
            "Choose exactly one category: plausible, acceptable_inference, questionable, or implausible. "
            "Select implausible when the resolved target or affordance clearly contradicts or breaks "
            "the scene context."
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
        evaluator_group="turn_story_quality",
        positive_categories=frozenset({"plausible"}),
        warning_categories=frozenset({"acceptable_inference", "questionable"}),
        failure_categories=frozenset({"implausible"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "npc_reaction_appropriateness_judge": LangfuseCategoricalEvaluatorSpec(
        name="npc_reaction_appropriateness_judge",
        description=(
            "Bewertet, ob NPCs passend auf Spielerhandlung, Sprache oder Situation reagieren. "
            "Achtet darauf, dass NPCs sozial/dramatisch reagieren, aber nicht Narrator-Aufgaben "
            "oder Spielerhandlungen übernehmen."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "appropriate_reaction",
            "minor_overreaction",
            "unnecessary_commentary",
            "npc_takes_over",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches the NPC reaction. Mention whether the "
            "NPC response is socially appropriate, unnecessary commentary, or a takeover of "
            "narrator/player responsibility."
        ),
        category_selection_prompt=(
            "Choose exactly one category: appropriate_reaction, minor_overreaction, "
            "unnecessary_commentary, or npc_takes_over. Select npc_takes_over when the NPC controls, "
            "explains, or overrides the player action in a way that breaks playability."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "npc", "visible_output", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"minor_overreaction", "unnecessary_commentary", "npc_takes_over"}),
        repair_card="TURN-NPC-REACTION-01",
        matrix_column_key="npc_reaction_appropriateness_category",
        display_short="NPC reaction appropriateness",
        evaluator_group="relationship_social",
        positive_categories=frozenset({"appropriate_reaction"}),
        warning_categories=frozenset({"minor_overreaction"}),
        failure_categories=frozenset({"unnecessary_commentary", "npc_takes_over"}),
        neutral_categories=frozenset(),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "runtime_aspect_integrity_judge": LangfuseCategoricalEvaluatorSpec(
        name="runtime_aspect_integrity_judge",
        description=(
            "Bewertet, ob ein Turn genügend Backend-/World-Engine-Evidence enthält, um ihn zu "
            "debuggen. Prüft, ob Ledger- oder Aspect-Daten zu Action, Beat, Authority, Capability, "
            "Validation, Commit und Visible Projection vorhanden sind."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "complete",
            "mostly_complete",
            "incomplete",
            "missing",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches runtime aspect integrity. Mention which "
            "runtime aspect evidence is present, which is missing or weak, and whether the visible "
            "output is consistent with the metadata."
        ),
        category_selection_prompt=(
            "Choose exactly one category: complete, mostly_complete, incomplete, missing, "
            "not_applicable, or insufficient_evidence. Select missing when runtime aspect evidence "
            "is absent or placeholder-like. Select insufficient_evidence only when the provided "
            "input, output, or metadata is too incomplete to judge."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "runtime_aspects", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"incomplete", "missing"}),
        repair_card="RUNTIME-ASPECT-EVIDENCE-01",
        matrix_column_key="runtime_aspect_integrity_category",
        display_short="runtime aspect integrity",
        evaluator_group="runtime_aspect_integrity",
        positive_categories=frozenset({"complete"}),
        warning_categories=frozenset({"mostly_complete"}),
        failure_categories=frozenset({"incomplete", "missing"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "narrator_authority_judge": LangfuseCategoricalEvaluatorSpec(
        name="narrator_authority_judge",
        description=(
            "Bewertet, ob der Narrator seine zuständige Rolle erfüllt. Besonders relevant für "
            "Bewegung, Wahrnehmung, Umgebung, physische Konsequenzen und Szenenrahmung."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "fulfilled",
            "mostly_fulfilled",
            "partial_or_ambiguous",
            "violated",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches narrator authority. Mention what "
            "narrator function was required, whether the narrator fulfilled it, and whether any "
            "NPC, player actor, technical text, or fallback-like output displaced narrator authority."
        ),
        category_selection_prompt=(
            "Choose exactly one category: fulfilled, mostly_fulfilled, partial_or_ambiguous, "
            "violated, not_applicable, or insufficient_evidence. Select violated when narrator "
            "duties are clearly taken over by the wrong origin or when the narrator improperly "
            "overrides actor ownership."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "narrator_authority", "authority_origin", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"partial_or_ambiguous", "violated"}),
        repair_card="AUTH-NARRATOR-01",
        matrix_column_key="narrator_authority_category",
        display_short="narrator authority",
        evaluator_group="authority_origin",
        positive_categories=frozenset({"fulfilled", "mostly_fulfilled"}),
        warning_categories=frozenset({"partial_or_ambiguous"}),
        failure_categories=frozenset({"violated"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "npc_authority_violation_judge": LangfuseCategoricalEvaluatorSpec(
        name="npc_authority_violation_judge",
        description=(
            "Bewertet, ob NPCs ihre Autoritätsgrenzen einhalten. Erkennt semantische Übernahmen "
            "wie NPC führt Spielerhandlung aus, erzählt Spielerwahrnehmung oder ersetzt den Narrator."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "no_violation",
            "minor_blur",
            "ambiguous_violation",
            "clear_violation",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches NPC authority. Mention whether NPCs "
            "stayed within character-level speech/action or whether they took over narrator, "
            "runtime, or selected-player authority."
        ),
        category_selection_prompt=(
            "Choose exactly one category: no_violation, minor_blur, ambiguous_violation, "
            "clear_violation, not_applicable, or insufficient_evidence. Select clear_violation when "
            "an NPC narrates the world, controls the selected player character, resolves runtime "
            "outcome improperly, or exposes technical/system details."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "npc_authority", "authority_origin", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"ambiguous_violation", "clear_violation"}),
        repair_card="AUTH-NPC-01",
        matrix_column_key="npc_authority_violation_category",
        display_short="NPC authority violation",
        evaluator_group="authority_origin",
        positive_categories=frozenset({"no_violation"}),
        warning_categories=frozenset({"minor_blur", "ambiguous_violation"}),
        failure_categories=frozenset({"clear_violation"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "dramatic_capability_realization_judge": LangfuseCategoricalEvaluatorSpec(
        name="dramatic_capability_realization_judge",
        description=(
            "Bewertet, ob ausgewählte dramatische Runtime-Capabilities korrekt realisiert wurden. "
            "Prüft, ob Player-, Narrator- und NPC-Fähigkeiten passend gewählt, umgesetzt oder "
            "blockiert wurden."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "realized_correctly",
            "mostly_realized",
            "partially_realized",
            "violated_or_missing",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches dramatic capability realization. "
            "Mention which capabilities were selected, implied, blocked, missing, contradicted, "
            "or visibly realized."
        ),
        category_selection_prompt=(
            "Choose exactly one category: realized_correctly, mostly_realized, partially_realized, "
            "violated_or_missing, not_applicable, or insufficient_evidence. Select violated_or_missing "
            "when selected capabilities are ignored, contradicted, or replaced by unsupported behavior."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "dramatic_capabilities", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"partially_realized", "violated_or_missing"}),
        repair_card="CAP-REALIZE-01",
        matrix_column_key="dramatic_capability_realization_category",
        display_short="dramatic capability realization",
        evaluator_group="dramatic_runtime_realization",
        positive_categories=frozenset({"realized_correctly"}),
        warning_categories=frozenset({"mostly_realized"}),
        failure_categories=frozenset({"partially_realized", "violated_or_missing"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "beat_realization_judge": LangfuseCategoricalEvaluatorSpec(
        name="beat_realization_judge",
        description=(
            "Bewertet, ob der ausgewählte dramatische Beat im sichtbaren Output tatsächlich "
            "realisiert wurde. Unterscheidet zwischen starker, serviceabler, schwacher oder "
            "fehlender Beat-Realisierung."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "strong_realization",
            "serviceable_realization",
            "weak_realization",
            "not_realized",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches beat realization. Mention the selected "
            "or implied beat, whether it is visible in the output, and whether it advances the scene."
        ),
        category_selection_prompt=(
            "Choose exactly one category: strong_realization, serviceable_realization, "
            "weak_realization, not_realized, not_applicable, or insufficient_evidence. Select "
            "not_realized when the selected beat is absent, contradicted, or replaced by unrelated/generic output."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "beat_algorithm", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak_realization", "not_realized"}),
        repair_card="BEAT-REALIZE-01",
        matrix_column_key="beat_realization_category",
        display_short="beat realization",
        evaluator_group="dramatic_runtime_realization",
        positive_categories=frozenset({"strong_realization"}),
        warning_categories=frozenset({"serviceable_realization"}),
        failure_categories=frozenset({"weak_realization", "not_realized"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "recoverable_outcome_quality_judge": LangfuseCategoricalEvaluatorSpec(
        name="recoverable_outcome_quality_judge",
        description=(
            "Bewertet die Qualität von recoverable, blockierten, unklaren oder teilweise möglichen "
            "Turn-Ergebnissen. Achtet darauf, dass solche Fälle in-world, verständlich, "
            "HTTP-200-spielbar und ohne falschen Commit bleiben."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "playable_recovery",
            "acceptable_recovery",
            "weak_recovery",
            "failed_recovery",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches recoverable outcome quality. Mention the "
            "attempted action, the obstacle or constraint, how the output recovered or failed to "
            "recover it, and whether the player has a playable next step."
        ),
        category_selection_prompt=(
            "Choose exactly one category: playable_recovery, acceptable_recovery, weak_recovery, "
            "failed_recovery, not_applicable, or insufficient_evidence. Select failed_recovery when "
            "the result is a flat denial, technical/fallback text, unrelated output, unsupported "
            "success, or a dead end."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "recovery_playability", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak_recovery", "failed_recovery"}),
        repair_card="RECOVERY-OUTCOME-01",
        matrix_column_key="recoverable_outcome_quality_category",
        display_short="recoverable outcome quality",
        evaluator_group="recovery_playability",
        positive_categories=frozenset({"playable_recovery"}),
        warning_categories=frozenset({"acceptable_recovery", "weak_recovery"}),
        failure_categories=frozenset({"failed_recovery"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "visible_origin_consistency_judge": LangfuseCategoricalEvaluatorSpec(
        name="visible_origin_consistency_judge",
        description=(
            "Bewertet, ob sichtbare Blocks zu ihren Backend-Origin-Metadaten passen. Prüft, ob "
            "origin_aspect, origin_beat_id, origin_capability und authority_owner mit dem "
            "sichtbaren Inhalt übereinstimmen."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "consistent",
            "mostly_consistent",
            "inconsistent_or_incomplete",
            "contradictory",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches visible origin consistency. Mention "
            "whether visible block origins match the actual text, whether any origin is missing or "
            "contradictory, and whether the issue affects narrator/NPC/player authority."
        ),
        category_selection_prompt=(
            "Choose exactly one category: consistent, mostly_consistent, inconsistent_or_incomplete, "
            "contradictory, not_applicable, or insufficient_evidence. Select contradictory when "
            "visible text is clearly assigned to the wrong origin or when technical/fallback content "
            "leaks into player-facing blocks."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "visible_origin", "actor_lane", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"inconsistent_or_incomplete", "contradictory"}),
        repair_card="VISIBLE-ORIGIN-01",
        matrix_column_key="visible_origin_consistency_category",
        display_short="visible origin consistency",
        evaluator_group="authority_origin",
        positive_categories=frozenset({"consistent"}),
        warning_categories=frozenset({"mostly_consistent"}),
        failure_categories=frozenset({"inconsistent_or_incomplete", "contradictory"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "relationship_pressure_judge": LangfuseCategoricalEvaluatorSpec(
        name="relationship_pressure_judge",
        description=(
            "Bewertet, ob Beziehungsspannung sichtbar und kohärent fortgeführt wird. Achtet auf "
            "Paar-Dynamiken, Elternkonflikt, soziale Reibung, Allianzen, Abwehr und "
            "charakterbezogene Reaktionen."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "strong_pressure",
            "serviceable_pressure",
            "weak_pressure",
            "missing_or_wrong",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches relationship pressure. Mention the "
            "relevant relationship or social tension, how it appears or fails to appear in the "
            "visible output, and whether it advances the scene."
        ),
        category_selection_prompt=(
            "Choose exactly one category: strong_pressure, serviceable_pressure, weak_pressure, "
            "missing_or_wrong, not_applicable, or insufficient_evidence. Select missing_or_wrong when "
            "relationship pressure is absent, contradicted, assigned to the wrong actor, or "
            "replaced by generic narration/action."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "relationship_state", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weak_pressure", "missing_or_wrong"}),
        repair_card="RELATION-PRESSURE-01",
        matrix_column_key="relationship_pressure_category",
        display_short="relationship pressure",
        evaluator_group="relationship_social",
        positive_categories=frozenset({"strong_pressure"}),
        warning_categories=frozenset({"serviceable_pressure", "weak_pressure"}),
        failure_categories=frozenset({"missing_or_wrong"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
    ),
    "player_turn_playability_judge": LangfuseCategoricalEvaluatorSpec(
        name="player_turn_playability_judge",
        description=(
            "Holistischer Qualitätssignal-Judge: ob ein Spieleraktions-Turn nach der Eingabe "
            "spielbar bleibt (Erfolg, Teil-Erfolg, Block, Umleitung, Ambiguität)."
        ),
        kind="llm_as_a_judge",
        scope="turn_generation",
        score_type="categorical",
        categories=(
            "playable",
            "mostly_playable",
            "weakly_playable",
            "unplayable",
            "not_applicable",
            "insufficient_evidence",
        ),
        allow_multiple_matches=False,
        prompt=_stub_prompt_preamble(),
        score_reasoning_prompt=(
            "Explain briefly why this category best matches player-turn playability. Mention the "
            "player’s apparent input, how the output handled it, whether the selected actor retained "
            "agency, and whether the player has a concrete situation to continue from."
        ),
        category_selection_prompt=(
            "Choose exactly one category: playable, mostly_playable, weakly_playable, unplayable, "
            "not_applicable, or insufficient_evidence. Select unplayable when the player action is "
            "ignored, replaced by unrelated content, flattened into non-dramatic refusal, or turned "
            "into technical/fallback text."
        ),
        qualitative_only=True,
        runtime_gate=False,
        replaces_deterministic_gates=False,
        applies_to=("interactive_turn", "recovery_playability", "story.model.generation"),
        required_input_fields=("input", "output", "metadata"),
        issue_categories=frozenset({"weakly_playable", "unplayable"}),
        repair_card="TURN-PLAYABILITY-01",
        matrix_column_key="player_turn_playability_category",
        display_short="player turn playability",
        evaluator_group="recovery_playability",
        positive_categories=frozenset({"playable"}),
        warning_categories=frozenset({"mostly_playable", "weakly_playable"}),
        failure_categories=frozenset({"unplayable"}),
        neutral_categories=frozenset({"not_applicable", "insufficient_evidence"}),
        langfuse_observation_filters=TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS,
        trace_metadata_filters=_turn_trace_meta(),
        legacy_trace_names=(BACKEND_TURN_ROOT_TRACE_NAME,),
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
            "alive_style",
            "acceptable",
            "broken_style",
            "strong_anchor",
            "adequate_anchor",
            "weak_anchor",
            "missing_anchor",
            "weak_use",
            "no_or_bad_use",
            "on_tone",
            "effective_pacing",
            "strongly_related",
            "healthy_boundary",
            "appropriate",
            "clear_block",
        }
    ),
)


def doc_table_evaluator_names() -> tuple[str, ...]:
    """Evaluator keys mirrored from the CSV definition table (stable catalog order)."""
    return _ORDER_NAMES


def judge_names_for_scope(scope: EvaluatorScope) -> tuple[str, ...]:
    return tuple(n for n in _ORDER_NAMES if (_SPECS_BY_NAME.get(n)) and _SPECS_BY_NAME[n].scope == scope)


def normalize_judge_category_label(judge_name: str, category: str | None) -> str | None:
    """Map legacy/stale categorical labels to current rubric tokens (lowercase)."""
    if not category:
        return None
    c = str(category).strip().lower()
    if not c:
        return None
    legacy_maps: dict[str, dict[str, str]] = {
        "opening_experience_judge": {"strong": "excellent"},
        "theatrical_style_judge": {
            "alive_style": "theatrical",
            "broken_style": "bad",
            "acceptable": "serviceable",
        },
        "role_anchor_quality_judge": {
            "strong_anchor": "clear",
            "adequate_anchor": "partial",
            "weak_anchor": "partial",
            "missing_anchor": "missing",
        },
        "rag_context_usefulness_judge": {"weak_use": "unused", "no_or_bad_use": "misused"},
        "goc_tone_fidelity_judge": {"on_tone": "strong_fidelity"},
        "dramatic_pacing_judge": {"effective_pacing": "strong_pacing"},
        "turn_relevance_judge": {"strongly_related": "directly_relevant"},
        "narrator_npc_boundary_judge": {"healthy_boundary": "clean_boundary"},
        "npc_reaction_appropriateness_judge": {"appropriate": "appropriate_reaction"},
        "blocked_action_playability_judge": {"clear_block": "playable_block"},
    }
    return legacy_maps.get(judge_name, {}).get(c, c)


def category_severity(judge_name: str, category: str | None) -> CategorySeverity:
    norm = normalize_judge_category_label(judge_name, category)
    if not norm:
        return "unknown"
    spec = get_categorical_evaluator_spec(judge_name)
    if spec is None:
        return "unknown"
    low = norm.strip().lower()
    if low in {x.lower() for x in spec.positive_categories}:
        return "positive"
    if low in {x.lower() for x in spec.warning_categories}:
        return "warning"
    if low in {x.lower() for x in spec.failure_categories}:
        return "failure"
    if low in {x.lower() for x in spec.neutral_categories}:
        return "neutral"
    if low in {x.lower() for x in spec.categories}:
        return "unknown"
    return "unknown"


def build_llm_judge_interpretation(
    judge_scores: dict[str, Any],
    *,
    trace_context: str | None = None,
) -> list[dict[str, Any]]:
    """Category-aware operator interpretation for Langfuse judge score rows."""
    rows: list[dict[str, Any]] = []
    for judge_name, payload in sorted(judge_scores.items()):
        if not str(judge_name).endswith("_judge"):
            continue
        if not isinstance(payload, dict):
            continue
        raw_cat = payload.get("category")
        cat = normalize_judge_category_label(judge_name, str(raw_cat) if raw_cat is not None else None)
        spec = get_categorical_evaluator_spec(judge_name)
        sev = category_severity(judge_name, cat)
        entry: dict[str, Any] = {
            "evaluator": judge_name,
            "category": cat,
            "category_severity": sev,
            "evaluator_group": spec.evaluator_group if spec else "unknown",
            "qualitative_only": True if spec is None else spec.qualitative_only,
            "runtime_gate": False if spec is None else spec.runtime_gate,
            "suggested_repair_area": spec.repair_card if spec else None,
            "what_it_checks": spec.description if spec else None,
            "analysis_focus": list(spec.applies_to) if spec else [],
            "reasoning_excerpt": (payload.get("reasoning") or None),
        }
        if trace_context:
            entry["trace_context"] = trace_context
        if sev == "failure":
            entry["operator_note"] = (
                "Qualitative judge concern (not a deterministic runtime gate). "
                "Inspect suggested_repair_area and Langfuse generation metadata."
            )
        elif sev == "warning":
            entry["operator_note"] = "Qualitative warning — tune prompts/runtime aspects; not a gate failure by itself."
        elif sev == "neutral":
            entry["operator_note"] = (
                "Neutral label (not_applicable / insufficient_evidence): not a runtime failure; "
                "may indicate missing Langfuse evidence for this rubric."
            )
        elif sev == "positive":
            entry["operator_note"] = "Positive qualitative signal."
        rows.append(entry)
    severity_rank = {"failure": 0, "warning": 1, "unknown": 2, "neutral": 3, "positive": 4}
    rows.sort(key=lambda r: (severity_rank.get(str(r.get("category_severity")), 9), r.get("evaluator")))
    return rows


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
        "evaluator_group": spec.evaluator_group,
        "positive_categories": sorted(spec.positive_categories),
        "warning_categories": sorted(spec.warning_categories),
        "failure_categories": sorted(spec.failure_categories),
        "neutral_categories": sorted(spec.neutral_categories),
        "canonical_definition_source": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
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
