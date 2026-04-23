"""
``ai_stack/capabilities.py`` — expand purpose, primary entrypoints, and
invariants for maintainers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback
    from enum import Enum
    class StrEnum(str, Enum):
        """``StrEnum`` groups related behaviour; callers should read members for contracts and threading assumptions.
        """
        def __str__(self) -> str:
            """``__str__`` — see implementation for behaviour and contracts.
            
            Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
            
            Returns:
                str:
                    Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
            """
            return self.value
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

if TYPE_CHECKING:
    from ai_stack.rag import ContextPackAssembler, ContextRetriever

from ai_stack.capabilities_invocation_summaries import summarize_invocation_result as _summarize_invocation_result


def _parse_top_hit_score(retrieval: dict[str, Any]) -> float | None:
    """``_parse_top_hit_score`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retrieval: ``retrieval`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        float | None:
            Returns a value of type ``float | None``; see the function body for structure, error paths, and sentinels.
    """
    raw = retrieval.get("top_hit_score")
    if raw is None or raw == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


# Explicit trace schema tag for downstream consumers (additive, not a ranking score).
RETRIEVAL_TRACE_SCHEMA_VERSION = "retrieval_closure_v1"

# Degradation labels that justify capping ``strong`` to ``moderate`` for multi-hit packs.
_DEGRADATION_CAP_STRONG_TO_MODERATE: frozenset[str] = frozenset(
    {
        "sparse_fallback_due_to_no_backend",
        "sparse_fallback_due_to_encode_failure",
        "sparse_fallback_due_to_invalid_or_missing_dense_index",
        "degraded_due_to_partial_persistence_problem",
    }
)


def _join_ranking_notes(retrieval: dict[str, Any]) -> str:
    """``_join_ranking_notes`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retrieval: ``retrieval`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    notes = retrieval.get("ranking_notes")
    if not isinstance(notes, list):
        return ""
    return " ".join(str(n) for n in notes)


def _sources_list(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    """``_sources_list`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retrieval: ``retrieval`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    s = retrieval.get("sources")
    if not isinstance(s, list):
        return []
    return [x for x in s if isinstance(x, dict)]


def _lanes_from_sources(sources: list[dict[str, Any]]) -> list[str]:
    """``_lanes_from_sources`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sources: ``sources`` (list[dict[str, Any]]); meaning follows the type and call sites.
    
    Returns:
        list[str]:
            Returns a value of type ``list[str]``; see the function body for structure, error paths, and sentinels.
    """
    out: list[str] = []
    for row in sources:
        lane = row.get("source_evidence_lane")
        if isinstance(lane, str) and lane:
            out.append(lane)
    return out


def evidence_lane_mix_from_sources(sources: list[dict[str, Any]] | None) -> str:
    """Compact governance mix over packed sources (lanes only; not a
    score).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sources: ``sources`` (list[dict[str, Any]] |
            None); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if not sources:
        return "unknown"
    lanes = _lanes_from_sources(sources)
    if not lanes:
        return "unknown"
    if any(l == "evaluative" for l in lanes):
        if any(l != "evaluative" for l in lanes):
            return "evaluative_mixed"
        return "evaluative_present"
    has_canon = any(l == "canonical" for l in lanes)
    non_canon = [l for l in lanes if l != "canonical"]
    if has_canon and non_canon:
        return "mixed"
    if has_canon and all(l == "canonical" for l in lanes):
        return "canonical_heavy"
    # supporting, draft_working, internal_review only
    if all(l in ("supporting", "draft_working", "internal_review") for l in lanes):
        return "supporting_heavy"
    return "mixed"


def _hard_exclusion_count(notes_joined: str) -> int:
    """``_hard_exclusion_count`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        notes_joined: ``notes_joined`` (str); meaning follows the type and call sites.
    
    Returns:
        int:
            Returns a value of type ``int``; see the function body for structure, error paths, and sentinels.
    """
    m = re.search(r"policy_hard_excluded_pool_count=(\d+)", notes_joined)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except ValueError:
        return 0


def _dedup_shaped(notes_joined: str) -> bool:
    """``_dedup_shaped`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        notes_joined: ``notes_joined`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return "dup_suppressed" in notes_joined


def _policy_outcome_hint(notes_joined: str) -> str:
    """``_policy_outcome_hint`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        notes_joined: ``notes_joined`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    if _hard_exclusion_count(notes_joined) > 0:
        return "hard_pool_exclusions_applied"
    return "no_hard_pool_exclusions_in_notes"


def _sources_have_lane(sources: list[dict[str, Any]], lane: str) -> bool:
    """``_sources_have_lane`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sources: ``sources`` (list[dict[str, Any]]); meaning follows the type and call sites.
        lane: ``lane`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return any(row.get("source_evidence_lane") == lane for row in sources)


def _canonical_lane_hits(sources: list[dict[str, Any]]) -> int:
    """``_canonical_lane_hits`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sources: ``sources`` (list[dict[str, Any]]); meaning follows the type and call sites.
    
    Returns:
        int:
            Returns a value of type ``int``; see the function body for structure, error paths, and sentinels.
    """
    return sum(1 for row in sources if row.get("source_evidence_lane") == "canonical")


def _compute_evidence_tier_task4(
    *,
    hit_count: int,
    status: Any,
    top: float | None,
    route_s: str,
    degradation_mode: Any,
    sources: list[dict[str, Any]],
    lane_mix: str,
    hard_excl: int,
) -> tuple[str, str]:
    """Four-level tier with explicit caps (no hidden second ranker).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        hit_count: ``hit_count`` (int); meaning follows the type and call sites.
        status: ``status`` (Any); meaning follows the type and call sites.
        top: ``top`` (float | None); meaning follows the type and call sites.
        route_s: ``route_s`` (str); meaning follows the type and call sites.
        degradation_mode: ``degradation_mode`` (Any); meaning follows the type and call sites.
        sources: ``sources`` (list[dict[str, Any]]); meaning follows the type and call sites.
        lane_mix: ``lane_mix`` (str); meaning follows the type and call sites.
        hard_excl: ``hard_excl`` (int); meaning follows the type and call sites.
    
    Returns:
        tuple[str, str]:
            Returns a value of type ``tuple[str, str]``; see the function body for structure, error paths, and sentinels.
    """
    if hit_count <= 0 or status == "fallback":
        if hit_count <= 0:
            return "none", "no_usable_hits"
        return "none", "fallback_status_without_hits"

    if hit_count == 1:
        if top is not None and top >= 8.0:
            tier1 = "strong"
            rationale1 = "single_hit_high_score"
        elif top is not None and top >= 4.0:
            tier1 = "moderate"
            rationale1 = "single_hit_mid_score"
        else:
            tier1 = "weak"
            rationale1 = "single_hit_low_or_unknown_score"
        if tier1 == "strong" and hard_excl > 0:
            tier1 = "moderate"
            rationale1 = f"{rationale1};capped_policy_hard_pool_reshape"
        return tier1, rationale1

    if hit_count == 2:
        if top is not None and top >= 7.0:
            tier2 = "strong"
            rationale2 = "two_hits_with_strong_top_score"
        else:
            tier2 = "moderate"
            rationale2 = "two_hits_typical_scores"
        if tier2 == "strong" and hard_excl > 0:
            tier2 = "moderate"
            rationale2 = f"{rationale2};capped_policy_hard_pool_reshape"
        return tier2, rationale2

    # Multi-hit (>=3): do not default to strong purely from count.
    tier = "moderate"
    rationale = "multi_hit_baseline"
    if route_s == "hybrid" and top is not None and top >= 7.0 and _sources_have_lane(sources, "canonical"):
        tier = "strong"
        rationale = "multi_hit_hybrid_canonical_backed"
    elif route_s == "hybrid" and top is not None and top >= 8.5:
        tier = "strong"
        rationale = "multi_hit_hybrid_very_high_top_score"
    elif route_s == "hybrid" and top is not None and top >= 7.0 and lane_mix in (
        "evaluative_present",
        "evaluative_mixed",
    ):
        tier = "strong"
        rationale = "multi_hit_hybrid_evaluative_backed"

    if tier == "strong" and route_s == "sparse_fallback":
        tier = "moderate"
        rationale = f"{rationale};capped_sparse_route"

    deg_s = degradation_mode if isinstance(degradation_mode, str) else ""
    if tier == "strong" and deg_s in _DEGRADATION_CAP_STRONG_TO_MODERATE:
        tier = "moderate"
        rationale = f"{rationale};capped_degraded_path"

    if tier == "strong" and hit_count >= 3 and lane_mix == "supporting_heavy":
        tier = "moderate"
        rationale = f"{rationale};capped_supporting_heavy_no_canonical_or_evaluative"

    if tier == "strong" and hard_excl > 0:
        tier = "moderate"
        rationale = f"{rationale};capped_policy_hard_pool_reshape"

    if tier == "strong" and hit_count >= 4 and _canonical_lane_hits(sources) == 1:
        tier = "moderate"
        rationale = f"{rationale};capped_thin_canonical_anchor_density"

    if hit_count >= 3 and route_s == "sparse_fallback" and "capped_sparse_route" not in rationale:
        rationale = f"{rationale};sparse_route_multi_hit_context"

    return tier, rationale


def _lane_anchor_counts_compact(sources: list[dict[str, Any]]) -> str:
    """Dense operator token: lane hit counts in stable key order (not a
    score).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sources: ``sources`` (list[dict[str, Any]]); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    keys = ("canonical", "supporting", "draft_working", "internal_review", "evaluative", "unknown")
    counts: dict[str, int] = {k: 0 for k in keys}
    for row in sources:
        lane = row.get("source_evidence_lane")
        lk = lane if isinstance(lane, str) and lane in counts else "unknown"
        counts[lk] = counts.get(lk, 0) + 1
    parts = [f"{k[:1]}={counts[k]}" for k in keys if counts[k]]
    return "|".join(parts) if parts else "none"


def _governance_influence_compact(*, hard_excl: int, dedup: bool, policy_hint: str) -> str:
    """Describe what ``_governance_influence_compact`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        hard_excl: ``hard_excl`` (int); meaning follows the type and call sites.
        dedup: ``dedup`` (bool); meaning follows the type and call sites.
        policy_hint: ``policy_hint`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    return f"hard_excl={hard_excl};dedup={'yes' if dedup else 'no'};policy={policy_hint}"


def _confidence_posture(
    *,
    tier: str,
    route_s: str,
    degradation_mode: Any,
    rationale: str,
) -> str:
    """Honest coarse confidence (implementation-grounded; not a calibrated
    probability).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        tier: ``tier`` (str); meaning follows the type and call sites.
        route_s: ``route_s`` (str); meaning follows the type and call sites.
        degradation_mode: ``degradation_mode`` (Any); meaning follows the type and call sites.
        rationale: ``rationale`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    deg_s = degradation_mode if isinstance(degradation_mode, str) else ""
    degraded_signal = bool(deg_s and deg_s not in ("hybrid_ok", "rebuilt_dense_index", ""))
    capped = "capped_" in rationale
    if tier == "none":
        return "low"
    if tier == "weak":
        return "low"
    if tier == "moderate":
        if route_s == "sparse_fallback" or degraded_signal:
            return "low"
        return "medium"
    if route_s == "sparse_fallback" or degraded_signal or capped:
        return "medium"
    return "high"


def _retrieval_posture_summary(
    *,
    tier: str,
    lane_mix: str,
    route_s: str,
    confidence_posture: str,
    quality_hint: str,
    gov_compact: str,
) -> str:
    """Describe what ``_retrieval_posture_summary`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        tier: ``tier`` (str); meaning follows the type and call sites.
        lane_mix: ``lane_mix`` (str); meaning follows the type and call sites.
        route_s: ``route_s`` (str); meaning follows the type and call sites.
        confidence_posture: ``confidence_posture`` (str); meaning follows the type and call sites.
        quality_hint: ``quality_hint`` (str); meaning follows the type and call sites.
        gov_compact: ``gov_compact`` (str); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    r = route_s or "n/a"
    return (
        f"tier={tier};confidence={confidence_posture};lanes={lane_mix};route={r};"
        f"quality={quality_hint};gov={gov_compact}"
    )


def _retrieval_quality_hint(
    *,
    route_s: str,
    degradation_mode: Any,
    dedup: bool,
    hard_excl: int,
) -> str:
    """``_retrieval_quality_hint`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        route_s: ``route_s`` (str); meaning follows the type and call sites.
        degradation_mode: ``degradation_mode`` (Any); meaning follows the type and call sites.
        dedup: ``dedup`` (bool); meaning follows the type and call sites.
        hard_excl: ``hard_excl`` (int); meaning follows the type and call sites.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    parts: list[str] = []
    if route_s == "sparse_fallback":
        parts.append("sparse_signal_path")
    if dedup:
        parts.append("dedup_shaped_selection")
    if hard_excl > 0:
        parts.append("hard_policy_pool_shaped")
    deg_s = degradation_mode if isinstance(degradation_mode, str) else ""
    if deg_s and deg_s not in ("hybrid_ok", "rebuilt_dense_index"):
        parts.append("degradation_marker_present")
    if not parts:
        parts.append("standard_hybrid_or_clean_sparse_context")
    return ";".join(parts)


def build_retrieval_trace(retrieval: Any) -> dict[str, Any]:
    """Normalize capability ``retrieval`` dict into workflow-facing trace
    fields.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retrieval: ``retrieval`` (Any); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    if not isinstance(retrieval, dict):
        retrieval = {}
    hit_count = int(retrieval.get("hit_count") or 0)
    status = retrieval.get("status")
    top = _parse_top_hit_score(retrieval)
    route = retrieval.get("retrieval_route")
    route_s = route if isinstance(route, str) else ""
    notes_joined = _join_ranking_notes(retrieval)
    sources = _sources_list(retrieval)
    lane_mix = evidence_lane_mix_from_sources(sources)
    hard_excl = _hard_exclusion_count(notes_joined)
    dedup = _dedup_shaped(notes_joined)
    policy_hint = _policy_outcome_hint(notes_joined)
    degradation_mode = retrieval.get("degradation_mode")

    tier, rationale = _compute_evidence_tier_task4(
        hit_count=hit_count,
        status=status,
        top=top,
        route_s=route_s,
        degradation_mode=degradation_mode,
        sources=sources,
        lane_mix=lane_mix,
        hard_excl=hard_excl,
    )

    quality_hint = _retrieval_quality_hint(
        route_s=route_s,
        degradation_mode=degradation_mode,
        dedup=dedup,
        hard_excl=hard_excl,
    )

    gov_compact = _governance_influence_compact(
        hard_excl=hard_excl, dedup=dedup, policy_hint=policy_hint
    )
    conf = _confidence_posture(
        tier=tier,
        route_s=route_s,
        degradation_mode=degradation_mode,
        rationale=rationale,
    )
    lane_counts = _lane_anchor_counts_compact(sources)
    posture_summary = _retrieval_posture_summary(
        tier=tier,
        lane_mix=lane_mix,
        route_s=route_s,
        confidence_posture=conf,
        quality_hint=quality_hint,
        gov_compact=gov_compact,
    )

    readiness_label = (
        f"confidence={conf}; tier={tier}; lanes={lane_mix}; route={route_s or 'n/a'}; "
        f"policy={policy_hint}; quality={quality_hint}; anchors={lane_counts}"
    )
    if len(readiness_label) > 280:
        readiness_label = readiness_label[:277] + "..."

    out: dict[str, Any] = {
        "evidence_strength": tier,
        "evidence_tier": tier,
        "hit_count": hit_count,
        "status": status,
        "domain": retrieval.get("domain"),
        "profile": retrieval.get("profile"),
        "index_version": retrieval.get("index_version"),
        "corpus_fingerprint": retrieval.get("corpus_fingerprint"),
        "retrieval_route": route_s or None,
        "top_hit_score": retrieval.get("top_hit_score"),
        "evidence_rationale": rationale,
        "evidence_lane_mix": lane_mix,
        "retrieval_quality_hint": quality_hint,
        "policy_outcome_hint": policy_hint,
        "dedup_shaped_selection": dedup,
        "hard_policy_exclusion_count": hard_excl,
        "readiness_label": readiness_label,
        "lane_anchor_counts": lane_counts,
        "confidence_posture": conf,
        "governance_influence_compact": gov_compact,
        "retrieval_posture_summary": posture_summary,
        "retrieval_trace_schema_version": RETRIEVAL_TRACE_SCHEMA_VERSION,
    }
    rgs = retrieval.get("retrieval_governance_summary")
    if isinstance(rgs, dict):
        # Passthrough canonical summary only — do not rebuild provenance from sources here.
        out["retrieval_governance_summary"] = rgs
    return out


class CapabilityKind(StrEnum):
    """``CapabilityKind`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    RETRIEVAL = "retrieval"
    ACTION = "action"


class CapabilityAccessDeniedError(PermissionError):
    """``CapabilityAccessDeniedError`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def __init__(self, capability_name: str, mode: str) -> None:
        """``__init__`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            capability_name: ``capability_name`` (str); meaning follows the type and call sites.
            mode: ``mode`` (str); meaning follows the type and call sites.
        """
        super().__init__(f"Capability '{capability_name}' denied for mode '{mode}'")
        self.capability_name = capability_name
        self.mode = mode


class CapabilityValidationError(ValueError):
    """``CapabilityValidationError`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def __init__(self, capability_name: str, field_name: str) -> None:
        """``__init__`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            capability_name: ``capability_name`` (str); meaning follows the type and call sites.
            field_name: ``field_name`` (str); meaning follows the type and call sites.
        """
        super().__init__(f"Capability '{capability_name}' missing required field '{field_name}'")
        self.capability_name = capability_name
        self.field_name = field_name


class CapabilityInvocationError(RuntimeError):
    """``CapabilityInvocationError`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def __init__(self, capability_name: str, detail: str) -> None:
        """``__init__`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            capability_name: ``capability_name`` (str); meaning follows the type and call sites.
            detail: ``detail`` (str); meaning follows the type and call sites.
        """
        super().__init__(f"Capability '{capability_name}' failed: {detail}")
        self.capability_name = capability_name
        self.detail = detail


@dataclass(slots=True)
class CapabilityDefinition:
    """``CapabilityDefinition`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    name: str
    kind: CapabilityKind
    input_schema: dict[str, Any]
    result_schema: dict[str, Any]
    allowed_modes: set[str]
    audit_required: bool
    failure_semantics: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class CapabilityRegistry:
    """``CapabilityRegistry`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def __init__(self) -> None:
        """``__init__`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        """
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._audit_log: list[dict[str, Any]] = []
        # AUDIT_LOG_SCOPE: Records capability invocation outcomes (allowed/denied) and result summaries.
        # Does NOT capture full action explainability (e.g., why an actor passed, why a responder was passive).
        # Full passivity explanations and detailed decision reasoning belong on operator surfaces (director dashboards,
        # debug traces), not in the audit log. Audit log is accountability-focused (who invoked what, outcome);
        # operator surfaces are explainability-focused (why the system chose A over B).

    def register(self, definition: CapabilityDefinition) -> None:
        """``register`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            definition: ``definition`` (CapabilityDefinition); meaning follows the type and call sites.
        """
        self._capabilities[definition.name] = definition

    def list_capabilities(self) -> list[dict[str, Any]]:
        """``list_capabilities`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            list[dict[str, Any]]:
                Returns a value of type ``list[dict[str,
                Any]]``; see the function body for structure, error paths, and sentinels.
        """
        return [
            {
                "name": definition.name,
                "kind": definition.kind.value,
                "input_schema": definition.input_schema,
                "result_schema": definition.result_schema,
                "allowed_modes": sorted(definition.allowed_modes),
                "audit_required": definition.audit_required,
                "failure_semantics": definition.failure_semantics,
            }
            for definition in self._capabilities.values()
        ]

    def recent_audit(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """``recent_audit`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            limit: ``limit`` (int); meaning follows the type and call sites.
        
        Returns:
            list[dict[str, Any]]:
                Returns a value of type ``list[dict[str,
                Any]]``; see the function body for structure, error paths, and sentinels.
        """
        return self._audit_log[-limit:]

    def invoke(
        self,
        *,
        name: str,
        mode: str,
        actor: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Describe what ``invoke`` does in one line (verb-led summary for
        this method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            name: ``name`` (str); meaning follows the type and call sites.
            mode: ``mode`` (str); meaning follows the type and call sites.
            actor: ``actor`` (str); meaning follows the type and call sites.
            payload: ``payload`` (dict[str, Any]); meaning follows the type and call sites.
            trace_id: ``trace_id`` (str | None); meaning follows the type and call sites.
        
        Returns:
            dict[str, Any]:
                Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
        """
        definition = self._capabilities.get(name)
        if not definition:
            raise CapabilityInvocationError(name, "unknown_capability")
        audit_id = trace_id or uuid4().hex
        try:
            if mode not in definition.allowed_modes:
                raise CapabilityAccessDeniedError(name, mode)
            self._validate_payload(definition, payload)
            result = definition.handler(payload)
            self._append_audit(
                capability_name=name,
                mode=mode,
                actor=actor,
                outcome="allowed",
                trace_id=audit_id,
                error=None,
                result_summary=_summarize_invocation_result(name, result),
            )
            return result
        except CapabilityAccessDeniedError as exc:
            self._append_audit(
                capability_name=name,
                mode=mode,
                actor=actor,
                outcome="denied",
                trace_id=audit_id,
                error=str(exc),
                result_summary=None,
            )
            raise
        except Exception as exc:
            self._append_audit(
                capability_name=name,
                mode=mode,
                actor=actor,
                outcome="error",
                trace_id=audit_id,
                error=str(exc),
                result_summary=None,
            )
            if isinstance(exc, (CapabilityValidationError, CapabilityInvocationError)):
                raise
            raise CapabilityInvocationError(name, str(exc)) from exc

    def _validate_payload(self, definition: CapabilityDefinition, payload: dict[str, Any]) -> None:
        """``_validate_payload`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            definition: ``definition`` (CapabilityDefinition); meaning follows the type and call sites.
            payload: ``payload`` (dict[str, Any]); meaning follows the type and call sites.
        """
        required = definition.input_schema.get("required", [])
        for field_name in required:
            if field_name not in payload:
                raise CapabilityValidationError(definition.name, field_name)

    def _append_audit(
        self,
        *,
        capability_name: str,
        mode: str,
        actor: str,
        outcome: str,
        trace_id: str,
        error: str | None,
        result_summary: dict[str, Any] | None = None,
    ) -> None:
        """``_append_audit`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            capability_name: ``capability_name`` (str); meaning follows the type and call sites.
            mode: ``mode`` (str); meaning follows the type and call sites.
            actor: ``actor`` (str); meaning follows the type and call sites.
            outcome: ``outcome`` (str); meaning follows the type and call sites.
            trace_id: ``trace_id`` (str); meaning follows the type and call sites.
            error: ``error`` (str | None); meaning follows the type and call sites.
            result_summary: ``result_summary`` (dict[str,
                Any] | None); meaning follows the type and call sites.
        """
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "capability_name": capability_name,
            "mode": mode,
            "actor": actor,
            "outcome": outcome,
            "trace_id": trace_id,
            "error": error,
            "result_summary": result_summary,
        }
        self._audit_log.append(entry)
        if len(self._audit_log) > 2000:
            self._audit_log[:] = self._audit_log[-2000:]


def __getattr__(name: str) -> Any:
    """Describe what ``__getattr__`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        name: ``name`` (str); meaning follows the type and call sites.
    
    Returns:
        Any:
            Returns a value of type ``Any``; see the function body for structure, error paths, and sentinels.
    """
    if name == "create_default_capability_registry":
        from ai_stack.capabilities_default_registry import create_default_capability_registry as _factory

        return _factory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def capability_catalog() -> list[dict[str, Any]]:
    """``capability_catalog`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    return [
        {
            "name": "wos.context_pack.build",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["runtime", "writers_room", "improvement"],
        },
        {
            "name": "wos.transcript.read",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["runtime", "improvement", "admin"],
        },
        {
            "name": "wos.review_bundle.build",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["writers_room", "improvement", "admin"],
        },
        {
            "name": "wos.research.source.inspect",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.aspect.extract",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.claim.list",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.run.get",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.exploration.graph",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.canon.issue.inspect",
            "kind": CapabilityKind.RETRIEVAL.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.explore",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.validate",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.research.bundle.build",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.canon.improvement.propose",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
        {
            "name": "wos.canon.improvement.preview",
            "kind": CapabilityKind.ACTION.value,
            "allowed_modes": ["research", "admin", "improvement"],
        },
    ]
