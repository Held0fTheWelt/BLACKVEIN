"""
``ai_stack/langchain_integration/bridges.py`` — expand purpose, primary
entrypoints, and invariants for maintainers.
"""
from __future__ import annotations

import inspect
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.documents import Document
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from ai_stack.rag_retrieval_dtos import RetrievalRequest
from ai_stack.rag_types import RetrievalDomain


def _adapter_generate_kwargs(adapter: BaseModelAdapter, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return ``kwargs`` restricted to names accepted by ``adapter.generate``.

    Production adapters accept ``model_name``; lightweight test doubles often omit it.
    Filtering avoids ``TypeError`` while still forwarding new optional parameters when implemented.
    """
    try:
        sig = inspect.signature(adapter.generate)
    except (TypeError, ValueError):
        return dict(kwargs)
    params = list(sig.parameters.values())
    if not params:
        return {}
    rest = params[1:] if params[0].name == "self" else params
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in rest):
        return dict(kwargs)
    allowed = {
        p.name
        for p in rest
        if p.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return {k: v for k, v in kwargs.items() if k in allowed}


# ---------------------------------------------------------------------------
# Tolerant JSON extraction and normalization (PARSER-ROBUSTNESS-01)
# ---------------------------------------------------------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")
_JSON_OBJECT_RE = re.compile(r"\{[\s\S]*\}")

# Lane list fields that GPT-4.x sometimes returns as JSON strings instead of lists.
_LANE_LIST_FIELDS: tuple[str, ...] = (
    "spoken_lines",
    "action_lines",
    "initiative_events",
    "state_effects",
    "secondary_responder_ids",
    "responder_actor_ids",
)

# Fields whose presence signals the output is runtime_actor_turn_v1 schema.
_SCHEMA_SIGNAL_FIELDS: frozenset[str] = frozenset({
    "spoken_lines",
    "action_lines",
    "primary_responder_id",
    "narration_summary",
    "narrative_response",
})


def _extract_json_object(raw: str) -> tuple[dict | None, list[str]]:
    """Extract a JSON dict from raw model output using progressively tolerant strategies.

    Returns (extracted_dict | None, repair_log).
    repair_log is empty when no extraction repair was needed.
    """
    repairs: list[str] = []
    text = raw.strip()

    # Strategy 0: direct JSON parse — clean output, no repair needed.
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, repairs
    except (json.JSONDecodeError, ValueError):
        pass

    # Strategy 1: content inside a markdown code fence (GPT-4.x common deviation).
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        try:
            obj = json.loads(fence_match.group(1).strip())
            if isinstance(obj, dict):
                repairs.append("extracted_from_markdown_fence")
                return obj, repairs
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 2: first JSON object anywhere in the text (handles prose prefix/suffix).
    obj_match = _JSON_OBJECT_RE.search(text)
    if obj_match:
        try:
            obj = json.loads(obj_match.group(0))
            if isinstance(obj, dict):
                repairs.append("extracted_from_prose_context")
                return obj, repairs
        except (json.JSONDecodeError, ValueError):
            pass

    return None, repairs


def _normalize_raw_dict(data: dict) -> tuple[dict, list[str]]:
    """Apply safe normalization to a raw extracted dict before Pydantic validation.

    Handles known GPT-4.x output deviations that are unambiguously safe to repair:
    - Lane list fields returned as a JSON string → parse to list.
    - Missing schema_version when structure clearly matches runtime_actor_turn_v1 → default it.

    Does NOT invent actors, synthesize content, or weaken actor-lane constraints.
    """
    repairs: list[str] = []
    data = dict(data)

    for fname in _LANE_LIST_FIELDS:
        val = data.get(fname)
        if isinstance(val, str):
            stripped = val.strip()
            if stripped.startswith("["):
                try:
                    parsed_val = json.loads(stripped)
                    if isinstance(parsed_val, list):
                        data[fname] = parsed_val
                        repairs.append(f"coerced_str_to_list:{fname}")
                except (json.JSONDecodeError, ValueError):
                    pass

    if not data.get("schema_version") and bool(_SCHEMA_SIGNAL_FIELDS & data.keys()):
        data["schema_version"] = "runtime_actor_turn_v1"
        repairs.append("defaulted_schema_version")

    ns = data.get("narration_summary")
    if isinstance(ns, str):
        stripped = ns.strip()
        if stripped.startswith("["):
            try:
                parsed_ns = json.loads(stripped)
            except (json.JSONDecodeError, ValueError, TypeError):
                parsed_ns = None
            if isinstance(parsed_ns, list) and all(isinstance(x, str) for x in parsed_ns):
                data["narration_summary"] = [str(x).strip() for x in parsed_ns if str(x).strip()]
                repairs.append("coerced_str_to_list:narration_summary")
    elif isinstance(ns, list):
        data["narration_summary"] = [str(x).strip() for x in ns if isinstance(x, str) and str(x).strip()]

    return data, repairs


def _apply_narration_summary_post_repairs(
    parsed: "RuntimeTurnStructuredOutput",
) -> tuple["RuntimeTurnStructuredOutput", list[str]]:
    """When the fast Pydantic path accepts a JSON array literal as ``str``, coerce to ``list[str]``.

    ``_normalize_raw_dict`` already handles this on the tolerant path; this closes the gap for
    ``parser.parse`` successes (models sometimes emit ``narration_summary`` as a quoted JSON array).
    """
    repairs: list[str] = []
    ns = parsed.narration_summary
    if not isinstance(ns, str):
        return parsed, repairs
    stripped = ns.strip()
    if not stripped.startswith("["):
        return parsed, repairs
    try:
        parsed_ns = json.loads(stripped)
    except (json.JSONDecodeError, ValueError, TypeError):
        return parsed, repairs
    if not isinstance(parsed_ns, list) or not parsed_ns or not all(isinstance(x, str) for x in parsed_ns):
        return parsed, repairs
    coerced = [str(x).strip() for x in parsed_ns if str(x).strip()]
    if not coerced:
        return parsed, repairs
    joined = "\n\n".join(coerced)
    nr = (parsed.narrative_response or "").strip()
    updates: dict[str, Any] = {"narration_summary": coerced}
    if not nr or nr == stripped:
        updates["narrative_response"] = joined
    repairs.append("coerced_str_to_list:narration_summary")
    return parsed.model_copy(update=updates), repairs


def _tolerant_parse(
    raw: str,
    parser: "PydanticOutputParser",
) -> "tuple[RuntimeTurnStructuredOutput | None, str | None, list[str]]":
    """Parse raw model output into RuntimeTurnStructuredOutput with progressive fallback.

    Strategy 1 (fast path): standard PydanticOutputParser — handles GPT-5.x clean output.
    Strategy 2 (tolerant path): JSON extraction + normalization + Pydantic model_validate.

    Returns:
        (parsed_output, parser_error, repair_log)
        repair_log is empty on clean parse; populated when repairs were applied.
        parser_error is set only when ALL strategies fail.
    """
    # Fast path: standard parser (LangChain handles fence extraction + Pydantic validation).
    try:
        parsed = parser.parse(raw)
        parsed, post_repairs = _apply_narration_summary_post_repairs(parsed)
        return parsed, None, post_repairs
    except Exception as first_exc:
        first_error = str(first_exc)

    # Tolerant path: explicit extraction + normalization + direct Pydantic validation.
    extracted, extract_repairs = _extract_json_object(raw)
    if extracted is not None:
        normalized, norm_repairs = _normalize_raw_dict(extracted)
        all_repairs = extract_repairs + norm_repairs
        try:
            parsed = RuntimeTurnStructuredOutput.model_validate(normalized)
            parsed, post_repairs = _apply_narration_summary_post_repairs(parsed)
            return parsed, None, all_repairs + post_repairs
        except Exception:
            pass
        # Last resort: filter to known fields (defensive against strict-mode extras).
        known = set(RuntimeTurnStructuredOutput.model_fields)
        filtered = {k: v for k, v in normalized.items() if k in known}
        if filtered != normalized:
            try:
                parsed = RuntimeTurnStructuredOutput.model_validate(filtered)
                all_repairs.append("filtered_unknown_fields")
                parsed, post_repairs = _apply_narration_summary_post_repairs(parsed)
                return parsed, None, all_repairs + post_repairs
            except Exception:
                pass

    return None, first_error, []


class RuntimeTurnStructuredOutput(BaseModel):
    """Normalized runtime output parsed through LangChain parser primitives.

    The model is intentionally backward-compatible:
    - Legacy callers can keep using ``narrative_response``.
    - Actor-level callers can use ``narration_summary`` plus structured lanes.
    """

    class RuntimeSpokenLine(BaseModel):
        speaker_id: str | None = Field(
            default=None,
            description="Canonical runtime actor id for the speaker (required when this row carries speech).",
        )
        text: str = Field(
            default="",
            description=(
                "Player-visible speech: wrap the spoken words in ASCII double quotes, e.g. "
                '"Natürlich." or "Yes." '
                "Optional German attributive lead-ins before the opening quote are allowed "
                '(e.g. "meint: ", "führt aus: ", "stimmt zu: ") and may include the figure name '
                '(e.g. "Alain stimmt zu: "). Avoid redundant SpeakerName: immediately before quoted speech '
                "when the same name was already used in a clumsy duplicate. "
                'English sessions: same quoting; optional lead-ins like "Name says: " are allowed.'
            ),
        )
        tone: str | None = None

    class RuntimeActionLine(BaseModel):
        actor_id: str | None = Field(
            default=None,
            description="Canonical runtime actor id performing the physical beat (required for this row).",
        )
        text: str = Field(
            default="",
            description=(
                "Pure stage action / blocking in third-person prose. The figure name should appear naturally "
                "inside the sentence (e.g. \"Veronique steht auf und zeigt auf die Tür.\"). "
                "Do NOT start this field with \"Name:\" — that colon-attribution form is reserved for spoken_lines."
            ),
        )

    class RuntimeInitiativeEvent(BaseModel):
        actor_id: str | None = None
        type: Literal["interrupt", "escalate", "withdraw", "deflect", "counter"] | str | None = None
        reason: str | None = None

    class RuntimeStateEffect(BaseModel):
        effect_type: Literal["pressure_shift", "relationship_shift", "scene_shift"] | str | None = None
        target: str | None = None
        value: str | None = None

    schema_version: str = Field(default="runtime_actor_turn_v1")
    narration_summary: str | list[str] = Field(
        default="",
        description=(
            "Brief scene-level summary derived from actor lanes (spoken_lines, action_lines, "
            "initiative_events). Narration is a prose projection of actor realization, not the source of truth—"
            "actor lanes hold primary authority. On opening turn (turn 0) for God of Carnage, prefer exactly "
            "three strings: narrator_intro, role_anchor, scene_setup (see session opening prompt). "
            "On later turns a single string remains normal."
        ),
    )
    proposed_scene_id: str | None = None
    intent_summary: str | None = None

    primary_responder_id: str | None = Field(default=None, description="Required for actor-bearing turns. The actor who responds in this turn. Falls back to director scope if absent.")
    secondary_responder_ids: list[str] = Field(default_factory=list, description="Actors who react or interrupt, if any.")
    spoken_lines: list[RuntimeSpokenLine | str] = Field(
        default_factory=list,
        description=(
            "Required when actors speak. Each entry must have speaker_id. "
            "Each text must follow the player-visible speech quoting rules described on RuntimeSpokenLine.text. "
            "Prefer one row per speaking beat and per speaker so the transcript can render as person-scoped shell "
            "blocks—not one internal novel paragraph for everyone."
        ),
    )
    action_lines: list[RuntimeActionLine | str] = Field(
        default_factory=list,
        description=(
            "Physical actions by actors. Each entry must have actor_id. "
            "Each text must follow RuntimeActionLine.text: no leading Name: attribution; weave the name in prose. "
            "Prefer one row per actor beat when multiple people move on stage so blocks stay person-scoped."
        ),
    )
    initiative_events: list[RuntimeInitiativeEvent] = Field(default_factory=list, description="Semantics of who seized or lost the turn.")
    state_effects: list[RuntimeStateEffect] = Field(default_factory=list, description="World-state changes this turn produces.")
    sensory_context_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Structured evidence for selected sensory_context layers. Each row should carry layer_id and "
            "source_ref from the dramatic generation packet; prose wording is not the contract."
        ),
    )
    responder_actor_ids: list[str] = Field(default_factory=list)
    opening_event_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Opening turn only: ordered ids from the opening_scene_sequence contract that this output realizes. "
            "Validation reads this field as deterministic coverage evidence."
        ),
    )
    opening_events_covered: list[str] = Field(
        default_factory=list,
        description="Opening turn compatibility alias for opening_event_ids.",
    )
    covered_event_ids: list[str] = Field(
        default_factory=list,
        description="Generic compatibility alias for opening/opening_event_coverage covered event ids.",
    )
    opening_event_coverage: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Opening turn only: optional nested coverage evidence, including covered_event_ids and "
            "must_establish_coverage."
        ),
    )
    opening_must_establish_coverage: list[str] | dict[str, bool] = Field(
        default_factory=list,
        description="Opening turn only: must_establish ids covered by the generated scenic opening.",
    )
    must_establish_coverage: list[str] | dict[str, bool] = Field(
        default_factory=list,
        description="Compatibility alias for opening_must_establish_coverage.",
    )
    opening_render_policy_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Opening turn only: local evidence for scenic dramatization vs summary-only rendering."
        ),
    )
    runtime_gate_detections: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Structured ids for hard-forbidden runtime gate detections, when any are present.",
    )

    responder_id: str | None = None
    narrative_response: str = Field(default="", description="Deprecated. Copy of narration_summary for legacy callers only.")
    function_type: str | None = None
    emotional_shift: dict | None = None
    social_outcome: str | None = None
    dramatic_direction: str | None = None

    def effective_narration_summary(self) -> str:
        raw = self.narration_summary
        if isinstance(raw, list):
            joined = "\n\n".join(str(x).strip() for x in raw if str(x).strip())
            if joined:
                return joined
        else:
            summary = str(raw or "").strip()
            if summary:
                return summary
        return (self.narrative_response or "").strip()


def _narration_summary_joined_plain(parsed: RuntimeTurnStructuredOutput) -> str:
    return parsed.effective_narration_summary()


def _normalize_runtime_structured_output(parsed: RuntimeTurnStructuredOutput) -> RuntimeTurnStructuredOutput:
    """Normalize new and legacy fields into one compatible runtime shape."""
    updates: dict[str, Any] = {}
    narration_plain = _narration_summary_joined_plain(parsed)
    narrative_response = (parsed.narrative_response or "").strip()
    if not narration_plain and narrative_response:
        updates["narration_summary"] = narrative_response
    if not narrative_response and narration_plain:
        updates["narrative_response"] = narration_plain

    primary_responder = (parsed.primary_responder_id or "").strip()
    legacy_responder = (parsed.responder_id or "").strip()
    if not primary_responder and legacy_responder:
        updates["primary_responder_id"] = legacy_responder
        primary_responder = legacy_responder
    if not legacy_responder and primary_responder:
        updates["responder_id"] = primary_responder

    secondary_ids = [str(x).strip() for x in parsed.secondary_responder_ids if str(x).strip()]
    legacy_scope = [str(x).strip() for x in parsed.responder_actor_ids if str(x).strip()]
    if not secondary_ids and legacy_scope:
        secondary_ids = [x for x in legacy_scope if x != primary_responder]
        updates["secondary_responder_ids"] = secondary_ids

    if updates:
        return parsed.model_copy(update=updates)
    return parsed


class WritersRoomStructuredOutput(BaseModel):
    """Writers-room review generation output parsed through LangChain parser
    primitives.
    """

    review_notes: str = Field(default="")
    recommendations: list[str] = Field(default_factory=list)


def _build_runtime_prompt_template() -> ChatPromptTemplate:
    """Build runtime prompt template from catalog with hardcoded fallback.

    Attempts to load from CanonicalPromptCatalog for governance integration.
    Falls back to hardcoded template if catalog unavailable.

    Returns:
        ChatPromptTemplate for runtime turn model invocation
    """
    try:
        from ai_stack.canonical_prompt_catalog import CanonicalPromptCatalog
        catalog = CanonicalPromptCatalog()
        return catalog.get_runtime_turn_template()
    except (ImportError, KeyError, Exception):
        # Fallback to hardcoded template if catalog fails
        return ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are the World of Shadows runtime turn model. Generate actor behavior first, prose projection second.\n\n"
                    "PRIMARY TASK — Actor Realization:\n"
                    "Your job is to determine and output:\n"
                    "1. **Who responds in this turn** (primary_responder_id)\n"
                    "2. **What they say** (spoken_lines with speaker_id and text)\n"
                    "3. **What they do** (action_lines with actor_id and physical action)\n"
                    "4. **Who else reacts** (secondary_responder_ids, initiative_events)\n"
                    "5. **What pressure/state changes** (state_effects)\n\n"
                    "SECONDARY OUTPUT — Prose Narration:\n"
                    "After actor lanes are complete, synthesize narration_summary: a prose narrative projecting the actor choices above. "
                    "Narration is a view of actor realization, not the source of truth.\n\n"
                    "MECHANICS:\n"
                    "- spoken_lines entries MUST have speaker_id (the actor speaking)\n"
                    "- action_lines entries MUST have actor_id (the actor acting)\n"
                    "- initiative_events capture turn seizure/escalation/deflection\n"
                    "- state_effects document world-state changes from actor choices\n"
                    "- narration_summary describes what happened (derived from actor output)\n"
                    "- narrative_response MUST be a copy of narration_summary only\n"
                    "- PLAYER-VISIBLE TYPOGRAPHY: spoken_lines[].text wraps spoken words in ASCII double quotes; optional "
                    "attributive lead-ins (e.g. German \"meint:\", \"führt aus:\", \"Name stimmt zu:\") allowed before the quote; "
                    "no name-only colon lines. action_lines[].text is third-person blocking with the name inside the sentence; "
                    "never start with \"Name:\".\n\n"
                    "Return valid JSON. Prioritize actor lanes over prose beauty.\n"
                    "PLAYER INPUT OWNERSHIP: primary_responder_id selects the NPC who reacts; it must never mean the "
                    "player's raw words belong to that NPC. The human lane already consumed verbatim player speech; "
                    "generate only NPC/narrator reaction.",
                ),
                (
                    "human",
                    "{full_context}"
                    "{correction_block}"
                    "ACTOR REALIZATION TASK:\n"
                    "0. If the packet states the human actor already spoke verbatim_player_input, do not rewrite that "
                    "line as NPC dialogue under primary_responder_id.\n"
                    "1. Identify the primary responder (actor responding to this move).\n"
                    "2. Determine what they say (if speech: populate spoken_lines with speaker_id; use quoted speech per typography rules).\n"
                    "3. Determine what they do (if action: populate action_lines with actor_id; prose action without a leading Name: prefix).\n"
                    "4. Capture secondary reactions (secondary_responder_ids and initiative_events if others respond/interrupt/escalate).\n"
                    "5. Identify state changes (state_effects for pressure/relationship/scene shifts).\n\n"
                    "PROSE PROJECTION:\n"
                    "After completing actor realization above, write narration_summary that expresses the scene from the actor choices you determined. "
                    "Think of this as a narrative view of the actor output, not a separate prose invention. Narration should be grounded in actor behavior.\n\n"
                    "COHERENCE CHECK:\n"
                    "- Does narration_summary reflect the actor choices (responder, spoken/action lines, initiative)?\n"
                    "- Does it avoid inventing actors or dialogue not in the actor lanes?\n"
                    "- Does it ground state_effects in visible narrative consequence?\n\n"
                    "COPY INSTRUCTION:\n"
                    "Copy narration_summary content exactly to narrative_response (no separate prose).\n\n"
                    "Format instructions:\n{format_instructions}",
                ),
            ]
        )


_RUNTIME_PROMPT_TEMPLATE = _build_runtime_prompt_template()
_WRITERS_ROOM_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are the World of Shadows writers-room review assistant. "
            "Return strictly valid JSON matching the requested schema.",
        ),
        (
            "human",
            "Module: {module_id}\n"
            "Review focus: {focus}\n\n"
            "Retrieved context for evidence:\n{retrieval_context}\n\n"
            "Format instructions:\n{format_instructions}",
        ),
    ]
)
_RUNTIME_OUTPUT_PARSER = PydanticOutputParser(pydantic_object=RuntimeTurnStructuredOutput)
_WRITERS_ROOM_OUTPUT_PARSER = PydanticOutputParser(pydantic_object=WritersRoomStructuredOutput)


@dataclass
class RuntimeInvocationResult:
    """``RuntimeInvocationResult`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    call: ModelCallResult
    prompt_text: str
    parsed_output: RuntimeTurnStructuredOutput | None
    parser_error: str | None
    repair_log: list[str] = field(default_factory=list)


def invoke_runtime_adapter_with_langchain(
    *,
    adapter: BaseModelAdapter,
    player_input: str,
    interpreted_input: dict[str, Any],
    retrieval_context: str | None,
    timeout_seconds: float,
    model_prompt: str | None = None,
    prior_output: str | None = None,
    feedback_codes: list[str] | None = None,
    rewrite_instruction: str | None = None,
    model_name: str | None = None,
    dramatic_generation_packet: dict[str, Any] | None = None,
) -> RuntimeInvocationResult:
    """Describe what ``invoke_runtime_adapter_with_langchain`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        adapter: ``adapter`` (BaseModelAdapter); meaning follows the type and call sites.
        player_input: ``player_input`` (str); meaning follows the type and call sites.
        interpreted_input: ``interpreted_input`` (dict[str, Any]); meaning follows the type and call sites.
        retrieval_context: ``retrieval_context`` (str |
            None); meaning follows the type and call sites.
        timeout_seconds: ``timeout_seconds`` (float); meaning follows the type and call sites.
    
    Returns:
        RuntimeInvocationResult:
            Returns a value of type ``RuntimeInvocationResult``; see the function body for structure, error paths, and sentinels.
    """
    parser = _RUNTIME_OUTPUT_PARSER
    correction_block = ""
    if rewrite_instruction:
        fb = ", ".join(str(x) for x in (feedback_codes or []) if str(x).strip()) or "(none)"
        correction_block = (
            "Self-correction pass:\n"
            f"Prior draft (reference only):\n{(prior_output or '').strip() or '(none)'}\n\n"
            f"Instruction:\n{rewrite_instruction}\n\n"
            f"Feedback codes: {fb}\n\n"
        )
    if model_prompt:
        full_context = model_prompt
        if isinstance(dramatic_generation_packet, dict) and dramatic_generation_packet:
            full_context = (
                f"{full_context}\n\n"
                "Dramatic generation packet (authoritative JSON):\n"
                f"{json.dumps(dramatic_generation_packet, sort_keys=True)}"
            )
    else:
        interp_str = "\n".join(f"- {k}: {v}" for k, v in interpreted_input.items()) if interpreted_input else "(none)"
        full_context = (
            f"Player input:\n{player_input}\n\n"
            f"Interpreted input:\n{interp_str}\n\n"
            f"Runtime retrieval context:\n{retrieval_context or '(none)'}"
        )
        if isinstance(dramatic_generation_packet, dict) and dramatic_generation_packet:
            full_context = (
                f"{full_context}\n\n"
                "Dramatic generation packet (authoritative JSON):\n"
                f"{json.dumps(dramatic_generation_packet, sort_keys=True)}"
            )
    rendered_messages = _RUNTIME_PROMPT_TEMPLATE.format_messages(
        full_context=full_context,
        correction_block=correction_block,
        format_instructions=parser.get_format_instructions(),
    )
    prompt_text = "\n\n".join(f"{message.type.upper()}: {message.content}" for message in rendered_messages)
    gen_kw: dict[str, Any] = {
        "timeout_seconds": timeout_seconds,
        "retrieval_context": retrieval_context,
    }
    if model_name:
        gen_kw["model_name"] = model_name
    _t0 = time.monotonic()
    call = adapter.generate(prompt_text, **_adapter_generate_kwargs(adapter, gen_kw))
    _latency_ms = (time.monotonic() - _t0) * 1000.0
    _md = dict(call.metadata)
    _md["generation_latency_ms"] = round(_latency_ms, 3)
    _md["llm_invocation_streaming"] = False
    call = ModelCallResult(content=call.content, success=call.success, metadata=_md)
    if not call.success:
        return RuntimeInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=None)
    parsed, parser_error, repair_log = _tolerant_parse(call.content, parser)
    if parsed is not None:
        parsed = _normalize_runtime_structured_output(parsed)
    return RuntimeInvocationResult(
        call=call,
        prompt_text=prompt_text,
        parsed_output=parsed,
        parser_error=parser_error,
        repair_log=repair_log,
    )


@dataclass
class WritersRoomInvocationResult:
    """``WritersRoomInvocationResult`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    call: ModelCallResult
    prompt_text: str
    parsed_output: WritersRoomStructuredOutput | None
    parser_error: str | None


def invoke_writers_room_adapter_with_langchain(
    *,
    adapter: BaseModelAdapter,
    module_id: str,
    focus: str,
    retrieval_context: str | None,
    timeout_seconds: float,
) -> WritersRoomInvocationResult:
    """Describe what ``invoke_writers_room_adapter_with_langchain`` does in
    one line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        adapter: ``adapter`` (BaseModelAdapter); meaning follows the type and call sites.
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        focus: ``focus`` (str); meaning follows the type and call sites.
        retrieval_context: ``retrieval_context`` (str |
            None); meaning follows the type and call sites.
        timeout_seconds: ``timeout_seconds`` (float); meaning follows the type and call sites.
    
    Returns:
        WritersRoomInvocationResult:
            Returns a value of type ``WritersRoomInvocationResult``; see the function body for structure, error paths, and sentinels.
    """
    parser = _WRITERS_ROOM_OUTPUT_PARSER
    rendered_messages = _WRITERS_ROOM_PROMPT_TEMPLATE.format_messages(
        module_id=module_id,
        focus=focus,
        retrieval_context=retrieval_context or "(none)",
        format_instructions=parser.get_format_instructions(),
    )
    prompt_text = "\n\n".join(f"{message.type.upper()}: {message.content}" for message in rendered_messages)
    call = adapter.generate(
        prompt_text,
        timeout_seconds=timeout_seconds,
        retrieval_context=retrieval_context,
    )
    if not call.success:
        return WritersRoomInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=None)
    try:
        parsed = parser.parse(call.content)
        return WritersRoomInvocationResult(call=call, prompt_text=prompt_text, parsed_output=parsed, parser_error=None)
    except Exception as exc:  # pragma: no cover - parser error path exercised in tests
        return WritersRoomInvocationResult(call=call, prompt_text=prompt_text, parsed_output=None, parser_error=str(exc))


@dataclass
class LangChainRetrieverBridge:
    """``LangChainRetrieverBridge`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    retriever: Any

    def get_runtime_documents(
        self,
        *,
        query: str,
        module_id: str,
        scene_id: str | None = None,
        max_chunks: int = 4,
    ) -> list[Document]:
        """Describe what ``get_runtime_documents`` does in one line
        (verb-led summary for this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            query: ``query`` (str); meaning follows the type and call sites.
            module_id: ``module_id`` (str); meaning follows the type and call sites.
            scene_id: ``scene_id`` (str | None); meaning follows the type and call sites.
            max_chunks: ``max_chunks`` (int); meaning follows the type and call sites.
        
        Returns:
            list[Document]:
                Returns a value of type ``list[Document]``; see the function body for structure, error paths, and sentinels.
        """
        request = RetrievalRequest(
            domain=RetrievalDomain.RUNTIME,
            profile="runtime_turn_support",
            query=query,
            module_id=module_id,
            scene_id=scene_id,
            max_chunks=max_chunks,
        )
        result = self.retriever.retrieve(request)
        return [
            Document(
                page_content=hit.snippet,
                metadata={
                    "chunk_id": hit.chunk_id,
                    "source_path": hit.source_path,
                    "source_version": hit.source_version,
                    "domain": request.domain.value,
                    "content_class": hit.content_class,
                    "score": hit.score,
                    "index_version": result.index_version,
                    "corpus_fingerprint": result.corpus_fingerprint,
                },
            )
            for hit in result.hits
        ]

    def get_writers_room_documents(
        self,
        *,
        query: str,
        module_id: str,
        max_chunks: int = 6,
    ) -> list[Document]:
        """LangChain Document preview for writers-room domain (aligns with
        wos.context_pack.build writers_review).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            query: ``query`` (str); meaning follows the type and call sites.
            module_id: ``module_id`` (str); meaning follows the type and call sites.
            max_chunks: ``max_chunks`` (int); meaning follows the type and call sites.
        
        Returns:
            list[Document]:
                Returns a value of type ``list[Document]``; see the function body for structure, error paths, and sentinels.
        """
        request = RetrievalRequest(
            domain=RetrievalDomain.WRITERS_ROOM,
            profile="writers_review",
            query=query,
            module_id=module_id,
            scene_id=None,
            max_chunks=max_chunks,
        )
        result = self.retriever.retrieve(request)
        return [
            Document(
                page_content=hit.snippet,
                metadata={
                    "chunk_id": hit.chunk_id,
                    "source_path": hit.source_path,
                    "source_version": hit.source_version,
                    "domain": request.domain.value,
                    "content_class": hit.content_class,
                    "score": hit.score,
                    "index_version": result.index_version,
                    "corpus_fingerprint": result.corpus_fingerprint,
                },
            )
            for hit in result.hits
        ]


def build_langchain_retriever_bridge(retriever: Any) -> LangChainRetrieverBridge:
    """Describe what ``build_langchain_retriever_bridge`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retriever: ``retriever`` (Any); meaning follows the type and call sites.
    
    Returns:
        LangChainRetrieverBridge:
            Returns a value of type ``LangChainRetrieverBridge``; see the function body for structure, error paths, and sentinels.
    """
    return LangChainRetrieverBridge(retriever=retriever)


def build_capability_tool_bridge(
    *,
    capability_registry: Any,
    capability_name: str,
    mode: str,
    actor: str,
) -> StructuredTool:
    """Describe what ``build_capability_tool_bridge`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        capability_registry: ``capability_registry`` (Any); meaning follows the type and call sites.
        capability_name: ``capability_name`` (str); meaning follows the type and call sites.
        mode: ``mode`` (str); meaning follows the type and call sites.
        actor: ``actor`` (str); meaning follows the type and call sites.
    
    Returns:
        StructuredTool:
            Returns a value of type ``StructuredTool``; see the function body for structure, error paths, and sentinels.
    """
    def _invoke_capability(
        module_id: str,
        summary: str,
        recommendations: list[str],
        evidence_sources: list[str],
    ) -> dict[str, Any]:
        payload = {
            "module_id": module_id,
            "summary": summary,
            "recommendations": recommendations,
            "evidence_sources": evidence_sources,
        }
        return capability_registry.invoke(
            name=capability_name,
            mode=mode,
            actor=actor,
            payload=payload,
        )

    return StructuredTool.from_function(
        func=_invoke_capability,
        name=f"{capability_name}.tool_bridge",
        description=f"LangChain tool bridge for capability {capability_name}.",
    )
