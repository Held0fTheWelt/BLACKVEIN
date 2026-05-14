"""Deterministic context synthesis for live runtime prompt support."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ai_stack.context_synthesis_contracts import (
    CONTEXT_SYNTHESIS_AUTHORITY,
    CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS,
    CONTEXT_SYNTHESIS_SCHEMA_VERSION,
    ContextEvidenceItem,
    ContextSynthesisBundle,
    SynthesisConflict,
    SynthesisGap,
    SynthesisObligation,
)


_SCENE_KEYS = (
    "scene_core",
    "pressure_state",
    "guidance_phase_key",
    "guidance_phase_title",
    "canonical_setting",
    "narrative_scope",
    "continuity_carry_forward_note",
    "thread_pressure_state",
)
_SEMANTIC_KEYS = (
    "move_type",
    "social_move_family",
    "target_actor_hint",
    "directness",
    "pressure_tactic",
    "scene_risk_band",
)
_SOCIAL_KEYS = (
    "scene_pressure_state",
    "guidance_phase_key",
    "responder_asymmetry_code",
    "social_risk_band",
    "social_continuity_status",
    "active_thread_count",
)


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _short(value: Any, *, max_chars: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _token(value: Any, *, default: str = "unknown") -> str:
    text = "_".join(str(value or "").strip().lower().split())
    return text or default


def _source_ref(source: Mapping[str, Any]) -> str:
    path = str(source.get("source_path") or source.get("source_name") or "").strip()
    chunk = str(source.get("chunk_id") or "").strip()
    if path and chunk:
        return f"{path}#{chunk}"
    return path or chunk or "retrieval_source"


def _score_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_for_source(source: Mapping[str, Any]) -> str:
    lane = _token(source.get("source_evidence_lane"))
    if lane in {"canonical", "compiled_canonical", "committed_memory", "runtime_state"}:
        return "high"
    score = _score_float(source.get("score"))
    if score is None:
        return "medium"
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def _lane_mix(evidence_items: list[ContextEvidenceItem]) -> dict[str, int]:
    mix: dict[str, int] = {}
    for item in evidence_items:
        lane = _token(item.source_evidence_lane)
        mix[lane] = mix.get(lane, 0) + 1
    return dict(sorted(mix.items()))


def _source_refs_for(items: list[ContextEvidenceItem]) -> tuple[str, ...]:
    refs: list[str] = []
    for item in items:
        refs.extend(item.source_refs)
    return tuple(refs)


def _runtime_item(
    *,
    item_id: str,
    summary: str,
    derived_from: str,
    source_ref: str,
    lane: str = "runtime_state",
    confidence: str = "high",
) -> ContextEvidenceItem:
    return ContextEvidenceItem(
        item_id=item_id,
        summary=summary,
        kind="runtime_state",
        source_refs=(source_ref,),
        source_evidence_lane=lane,
        source_visibility_class="internal_runtime",
        confidence=confidence,
        derived_from=(derived_from,),
        canonical_priority=10,
    )


def _append_runtime_record(
    evidence_items: list[ContextEvidenceItem],
    *,
    prefix: str,
    record: dict[str, Any],
    keys: tuple[str, ...],
    item_id: str,
) -> None:
    parts: list[str] = []
    for key in keys:
        value = record.get(key)
        if value is not None and str(value).strip():
            parts.append(f"{key}={_short(value, max_chars=90)}")
    if not parts:
        return
    evidence_items.append(
        _runtime_item(
            item_id=item_id,
            summary=f"{prefix}: " + "; ".join(parts),
            derived_from=prefix,
            source_ref=f"runtime.{prefix}",
        )
    )


def _retrieval_evidence(retrieval: dict[str, Any]) -> list[ContextEvidenceItem]:
    evidence_items: list[ContextEvidenceItem] = []
    for index, raw_source in enumerate(_list(retrieval.get("sources")), start=1):
        source = _mapping(raw_source)
        if not source:
            continue
        snippet = _short(source.get("snippet"), max_chars=240)
        if not snippet:
            snippet = _short(source.get("selection_reason") or source.get("why_selected"), max_chars=160)
        evidence_items.append(
            ContextEvidenceItem(
                item_id=f"retrieval:{index:03d}",
                summary=snippet or "retrieved evidence source without snippet",
                source_refs=(_source_ref(source),),
                source_evidence_lane=_token(source.get("source_evidence_lane")),
                source_visibility_class=_token(source.get("source_visibility_class")),
                confidence=_confidence_for_source(source),
                derived_from=("retrieval",),
                canonical_priority=5 if _token(source.get("source_evidence_lane")) == "canonical" else 1,
                pack_role=str(source.get("pack_role") or ""),
                score=str(source.get("score") or ""),
                why_selected=_short(source.get("why_selected") or source.get("selection_reason"), max_chars=160),
                policy_note=_short(source.get("policy_note"), max_chars=160),
            )
        )
    return evidence_items


def _memory_evidence(memory_context: dict[str, Any]) -> list[ContextEvidenceItem]:
    evidence_items: list[ContextEvidenceItem] = []
    for index, raw_line in enumerate(_list(memory_context.get("context_lines"))[:4], start=1):
        text = _short(raw_line, max_chars=220)
        if not text:
            continue
        evidence_items.append(
            ContextEvidenceItem(
                item_id=f"memory:{index:03d}",
                summary=text,
                kind="committed_memory",
                source_refs=("runtime.hierarchical_memory_context",),
                source_evidence_lane="committed_memory",
                source_visibility_class="internal_runtime",
                confidence="high",
                derived_from=("hierarchical_memory_context",),
                canonical_priority=8,
            )
        )
    return evidence_items


def _aspect_evidence(aspect_ledger: dict[str, Any]) -> ContextEvidenceItem | None:
    if not aspect_ledger:
        return None
    applicable = 0
    partial = 0
    for value in aspect_ledger.values():
        if not isinstance(value, Mapping):
            continue
        if value.get("applicable") is True:
            applicable += 1
        if str(value.get("status") or "").strip().lower() == "partial":
            partial += 1
    return _runtime_item(
        item_id="runtime_aspects:001",
        summary=f"turn_aspect_ledger: applicable={applicable}; partial={partial}; total={len(aspect_ledger)}",
        derived_from="turn_aspect_ledger",
        source_ref="runtime.turn_aspect_ledger",
    )


def _validation_feedback_evidence(validation_feedback: dict[str, Any]) -> ContextEvidenceItem | None:
    if not validation_feedback:
        return None
    codes = validation_feedback.get("codes")
    if not isinstance(codes, list):
        codes = validation_feedback.get("feedback_codes")
    code_text = ", ".join(str(code) for code in _list(codes)[:8]) or "validation feedback present"
    return _runtime_item(
        item_id="validation_feedback:001",
        summary=f"validation_feedback: {code_text}",
        derived_from="validation_feedback",
        source_ref="runtime.validation_feedback",
        confidence="high",
    )


def _input_sources(
    *,
    retrieval: dict[str, Any],
    context_text: str,
    scene_assessment: dict[str, Any],
    semantic_move_record: dict[str, Any],
    social_state_record: dict[str, Any],
    turn_aspect_ledger: dict[str, Any],
    hierarchical_memory_context: dict[str, Any],
    validation_feedback: dict[str, Any],
) -> tuple[str, ...]:
    sources: list[str] = []
    if retrieval:
        sources.append("retrieval")
    if context_text.strip():
        sources.append("context_text")
    if scene_assessment:
        sources.append("scene_assessment")
    if semantic_move_record:
        sources.append("semantic_move_record")
    if social_state_record:
        sources.append("social_state_record")
    if turn_aspect_ledger:
        sources.append("turn_aspect_ledger")
    if hierarchical_memory_context:
        sources.append("hierarchical_memory_context")
    if validation_feedback:
        sources.append("validation_feedback")
    return tuple(sources)


def _gaps(
    *,
    retrieval: dict[str, Any],
    scene_assessment: dict[str, Any],
    semantic_move_record: dict[str, Any],
    social_state_record: dict[str, Any],
    turn_aspect_ledger: dict[str, Any],
) -> list[SynthesisGap]:
    gaps: list[SynthesisGap] = []
    try:
        hit_count = int(retrieval.get("hit_count") or 0)
    except (TypeError, ValueError):
        hit_count = 0
    retrieval_status = str(retrieval.get("status") or "").strip().lower()
    if not retrieval or retrieval_status in {"skipped", "disabled"} or hit_count <= 0:
        gaps.append(
            SynthesisGap(
                code="retrieval_context_missing",
                description="No retrieved evidence items are available for synthesis.",
                required_for="grounding",
                severity="warning",
            )
        )
    if not scene_assessment:
        gaps.append(
            SynthesisGap(
                code="scene_assessment_missing",
                description="Director scene assessment was absent when synthesis ran.",
                required_for="scene_guidance",
                severity="warning",
            )
        )
    if not semantic_move_record:
        gaps.append(
            SynthesisGap(
                code="semantic_move_missing",
                description="Semantic move record was absent when synthesis ran.",
                required_for="move_guidance",
                severity="info",
            )
        )
    if not social_state_record:
        gaps.append(
            SynthesisGap(
                code="social_state_missing",
                description="Social state record was absent when synthesis ran.",
                required_for="response_scope",
                severity="info",
            )
        )
    if not turn_aspect_ledger:
        gaps.append(
            SynthesisGap(
                code="runtime_aspect_ledger_missing",
                description="Runtime aspect ledger was absent from synthesis inputs.",
                required_for="auditability",
                severity="info",
            )
        )
    return gaps


def _conflicts(evidence_items: list[ContextEvidenceItem]) -> list[SynthesisConflict]:
    lanes = {item.source_evidence_lane for item in evidence_items}
    retrieval_items = [item for item in evidence_items if "retrieval" in item.derived_from]
    conflicts: list[SynthesisConflict] = []
    has_canonical = bool(lanes & {"canonical", "compiled_canonical", "committed_memory"})
    has_draft = bool(lanes & {"draft", "generated", "unknown"})
    if has_canonical and has_draft and retrieval_items:
        conflicts.append(
            SynthesisConflict(
                code="mixed_authority_context",
                description=(
                    "Retrieved context includes mixed authority lanes; canonical and validator state "
                    "must outrank lower-confidence support."
                ),
                evidence_item_ids=tuple(item.item_id for item in retrieval_items),
                source_refs=_source_refs_for(retrieval_items),
            )
        )
    return conflicts


def _obligations(
    *,
    evidence_items: list[ContextEvidenceItem],
    retrieval_items: list[ContextEvidenceItem],
    scene_assessment: dict[str, Any],
    semantic_move_record: dict[str, Any],
    social_state_record: dict[str, Any],
    validation_feedback: dict[str, Any],
) -> list[SynthesisObligation]:
    obligations = [
        SynthesisObligation(
            code="preserve_runtime_authority_boundary",
            instruction=(
                "Use synthesis only as model-prompt support; validator approval and runtime commit remain authoritative."
            ),
            evidence_item_ids=tuple(item.item_id for item in evidence_items[:8]),
            source_refs=_source_refs_for(evidence_items[:8]),
        )
    ]
    if retrieval_items:
        obligations.append(
            SynthesisObligation(
                code="ground_generation_in_retrieved_evidence",
                instruction=(
                    "Treat retrieved snippets as supporting context and prefer canonical or validator state on conflict."
                ),
                evidence_item_ids=tuple(item.item_id for item in retrieval_items),
                source_refs=_source_refs_for(retrieval_items),
            )
        )
    if scene_assessment or semantic_move_record or social_state_record:
        runtime_items = [
            item for item in evidence_items if item.source_evidence_lane in {"runtime_state", "committed_memory"}
        ]
        obligations.append(
            SynthesisObligation(
                code="reflect_runtime_scene_state",
                instruction=(
                    "Align response planning with director scene state, semantic move, social state, and responder scope."
                ),
                evidence_item_ids=tuple(item.item_id for item in runtime_items[:8]),
                source_refs=_source_refs_for(runtime_items[:8]),
            )
        )
    if validation_feedback:
        feedback_items = [item for item in evidence_items if "validation_feedback" in item.derived_from]
        obligations.append(
            SynthesisObligation(
                code="address_validation_feedback",
                instruction="Use validation feedback as corrective guidance for the next proposal attempt.",
                evidence_item_ids=tuple(item.item_id for item in feedback_items),
                source_refs=_source_refs_for(feedback_items),
            )
        )
    obligations.append(
        SynthesisObligation(
            code="respect_actor_lanes_and_validation",
            instruction=(
                "Do not assign output to forbidden actor lanes; generated effects remain proposals until validation."
            ),
            evidence_item_ids=tuple(item.item_id for item in evidence_items if item.source_evidence_lane == "runtime_state")[:8],
            source_refs=_source_refs_for(
                [item for item in evidence_items if item.source_evidence_lane == "runtime_state"][:8]
            ),
        )
    )
    return obligations


def _status(evidence_items: list[ContextEvidenceItem], gaps: list[SynthesisGap], conflicts: list[SynthesisConflict]) -> str:
    if not evidence_items:
        return "degraded_empty"
    if conflicts:
        return "ok_with_conflicts"
    if gaps:
        return "partial"
    return "ok"


def build_context_synthesis_bundle(
    *,
    retrieval: dict[str, Any] | None,
    context_text: str | None,
    scene_assessment: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    turn_aspect_ledger: dict[str, Any] | None,
    hierarchical_memory_context: dict[str, Any] | None,
    validation_feedback: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build deterministic synthesis evidence, obligations, gaps, and conflicts."""

    retrieval_map = _mapping(retrieval)
    scene_map = _mapping(scene_assessment)
    semantic_map = _mapping(semantic_move_record)
    social_map = _mapping(social_state_record)
    aspect_map = _mapping(turn_aspect_ledger)
    memory_map = _mapping(hierarchical_memory_context)
    feedback_map = _mapping(validation_feedback)

    evidence_items = _retrieval_evidence(retrieval_map)
    _append_runtime_record(
        evidence_items,
        prefix="scene_assessment",
        record=scene_map,
        keys=_SCENE_KEYS,
        item_id="scene_assessment:001",
    )
    _append_runtime_record(
        evidence_items,
        prefix="semantic_move_record",
        record=semantic_map,
        keys=_SEMANTIC_KEYS,
        item_id="semantic_move:001",
    )
    _append_runtime_record(
        evidence_items,
        prefix="social_state_record",
        record=social_map,
        keys=_SOCIAL_KEYS,
        item_id="social_state:001",
    )
    evidence_items.extend(_memory_evidence(memory_map))
    aspect_item = _aspect_evidence(aspect_map)
    if aspect_item is not None:
        evidence_items.append(aspect_item)
    feedback_item = _validation_feedback_evidence(feedback_map)
    if feedback_item is not None:
        evidence_items.append(feedback_item)

    retrieval_items = [item for item in evidence_items if "retrieval" in item.derived_from]
    gaps = _gaps(
        retrieval=retrieval_map,
        scene_assessment=scene_map,
        semantic_move_record=semantic_map,
        social_state_record=social_map,
        turn_aspect_ledger=aspect_map,
    )
    conflicts = _conflicts(evidence_items)
    obligations = _obligations(
        evidence_items=evidence_items,
        retrieval_items=retrieval_items,
        scene_assessment=scene_map,
        semantic_move_record=semantic_map,
        social_state_record=social_map,
        validation_feedback=feedback_map,
    )
    bundle = ContextSynthesisBundle(
        status=_status(evidence_items, gaps, conflicts),
        evidence_items=tuple(evidence_items),
        obligations=tuple(obligations),
        conflicts=tuple(conflicts),
        gaps=tuple(gaps),
        input_sources=_input_sources(
            retrieval=retrieval_map,
            context_text=str(context_text or ""),
            scene_assessment=scene_map,
            semantic_move_record=semantic_map,
            social_state_record=social_map,
            turn_aspect_ledger=aspect_map,
            hierarchical_memory_context=memory_map,
            validation_feedback=feedback_map,
        ),
        source_lane_mix=_lane_mix(evidence_items),
    )
    return bundle.to_dict()


def build_context_synthesis_error_bundle(error: Exception) -> dict[str, Any]:
    """Return a degraded bundle when synthesis itself fails."""

    bundle = ContextSynthesisBundle(
        status="degraded_error",
        gaps=(
            SynthesisGap(
                code="context_synthesis_error",
                description=f"Synthesis engine failed with {type(error).__name__}.",
                required_for="prompt_support",
                severity="warning",
            ),
        ),
        input_sources=(),
        source_lane_mix={},
    )
    return bundle.to_dict()


def summarize_context_synthesis_for_diagnostics(
    bundle: dict[str, Any] | None,
    *,
    used_in_model_prompt: bool = False,
) -> dict[str, Any]:
    """Project a bounded diagnostics summary from a synthesis bundle."""

    bundle_map = _mapping(bundle)
    evidence = _list(bundle_map.get("evidence_items"))
    obligations = _list(bundle_map.get("obligations"))
    conflicts = _list(bundle_map.get("conflicts"))
    gaps = _list(bundle_map.get("gaps"))
    gap_codes = [
        str(item.get("code"))
        for item in gaps
        if isinstance(item, Mapping) and str(item.get("code") or "").strip()
    ]
    obligation_codes = [
        str(item.get("code"))
        for item in obligations
        if isinstance(item, Mapping) and str(item.get("code") or "").strip()
    ]
    conflict_codes = [
        str(item.get("code"))
        for item in conflicts
        if isinstance(item, Mapping) and str(item.get("code") or "").strip()
    ]
    input_sources = [
        str(item) for item in _list(bundle_map.get("input_sources")) if str(item).strip()
    ]
    return {
        "schema_version": str(bundle_map.get("schema_version") or CONTEXT_SYNTHESIS_SCHEMA_VERSION),
        "status": str(bundle_map.get("status") or "missing"),
        "authority": str(bundle_map.get("authority") or CONTEXT_SYNTHESIS_AUTHORITY),
        "forbidden_as_truth": bool(bundle_map.get("forbidden_as_truth", True)),
        "forbidden_truth_fields_absent": all(field not in bundle_map for field in CONTEXT_SYNTHESIS_FORBIDDEN_TRUTH_FIELDS),
        "evidence_item_count": len(evidence),
        "obligation_count": len(obligations),
        "conflict_count": len(conflicts),
        "obligation_codes": obligation_codes,
        "gap_codes": gap_codes,
        "conflict_codes": conflict_codes,
        "source_lane_mix": _mapping(bundle_map.get("source_lane_mix")),
        "input_sources": input_sources,
        "used_in_model_prompt": bool(used_in_model_prompt),
        "validation_feedback_included": "validation_feedback" in input_sources,
        "resynthesis_count": 0,
        "used_for_self_correction": False,
    }


def context_synthesis_prompt_lines(bundle: dict[str, Any] | None) -> list[str]:
    """Render a bounded model-visible synthesis section."""

    bundle_map = _mapping(bundle)
    if not bundle_map:
        return []
    evidence = [item for item in _list(bundle_map.get("evidence_items")) if isinstance(item, Mapping)]
    obligations = [item for item in _list(bundle_map.get("obligations")) if isinstance(item, Mapping)]
    conflicts = [item for item in _list(bundle_map.get("conflicts")) if isinstance(item, Mapping)]
    gaps = [item for item in _list(bundle_map.get("gaps")) if isinstance(item, Mapping)]
    lines = [
        "Context Synthesis (proposal support, non-authoritative):",
        (
            f"- status: {str(bundle_map.get('status') or 'missing')}; "
            f"authority: {str(bundle_map.get('authority') or CONTEXT_SYNTHESIS_AUTHORITY)}; "
            f"evidence_items: {len(evidence)}; obligations: {len(obligations)}; "
            f"gaps: {len(gaps)}; conflicts: {len(conflicts)}"
        ),
    ]
    if evidence:
        lines.append("Synthesis Evidence Summary:")
        for item in evidence[:5]:
            item_id = _short(item.get("item_id"), max_chars=48)
            lane = _short(item.get("source_evidence_lane"), max_chars=48)
            summary = _short(item.get("summary"), max_chars=180)
            lines.append(f"- {item_id} lane={lane}: {summary}")
    if obligations:
        lines.append("Synthesis Obligations:")
        for obligation in obligations[:6]:
            code = _short(obligation.get("code"), max_chars=80)
            instruction = _short(obligation.get("instruction"), max_chars=180)
            lines.append(f"- {code}: {instruction}")
    if conflicts:
        lines.append("Synthesis Conflicts:")
        for conflict in conflicts[:4]:
            code = _short(conflict.get("code"), max_chars=80)
            description = _short(conflict.get("description"), max_chars=180)
            lines.append(f"- {code}: {description}")
    if gaps:
        lines.append("Synthesis Gaps:")
        for gap in gaps[:6]:
            code = _short(gap.get("code"), max_chars=80)
            description = _short(gap.get("description"), max_chars=180)
            lines.append(f"- {code}: {description}")
    return lines
