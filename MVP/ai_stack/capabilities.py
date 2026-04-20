from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback
    from enum import Enum
    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

if TYPE_CHECKING:
    from ai_stack.rag import ContextPackAssembler, ContextRetriever


def _summarize_invocation_result(capability_name: str, result: dict[str, Any]) -> dict[str, Any] | None:
    """Small, workflow-safe audit hints (no full payloads)."""
    if capability_name == "wos.context_pack.build":
        retrieval = result.get("retrieval")
        if not isinstance(retrieval, dict):
            return {"kind": "context_pack", "hit_count": 0, "note": "missing_retrieval_dict"}
        hit_count = int(retrieval.get("hit_count") or 0)
        summary: dict[str, Any] = {
            "kind": "context_pack",
            "hit_count": hit_count,
            "status": retrieval.get("status"),
            "domain": retrieval.get("domain"),
            "profile": retrieval.get("profile"),
        }
        fp = retrieval.get("corpus_fingerprint")
        if isinstance(fp, str) and fp:
            summary["corpus_fingerprint_prefix"] = fp[:24]
        iv = retrieval.get("index_version")
        if isinstance(iv, str) and iv:
            summary["index_version"] = iv
        route = retrieval.get("retrieval_route")
        if isinstance(route, str) and route:
            summary["retrieval_route"] = route
        top_hit = retrieval.get("top_hit_score")
        if isinstance(top_hit, str) and top_hit:
            summary["top_hit_score"] = top_hit
        trace_hint = build_retrieval_trace(retrieval)
        summary["evidence_tier"] = trace_hint.get("evidence_tier")
        summary["evidence_rationale"] = trace_hint.get("evidence_rationale")
        summary["evidence_lane_mix"] = trace_hint.get("evidence_lane_mix")
        summary["readiness_label"] = trace_hint.get("readiness_label")
        summary["retrieval_quality_hint"] = trace_hint.get("retrieval_quality_hint")
        summary["policy_outcome_hint"] = trace_hint.get("policy_outcome_hint")
        summary["dedup_shaped_selection"] = trace_hint.get("dedup_shaped_selection")
        summary["retrieval_trace_schema_version"] = trace_hint.get("retrieval_trace_schema_version")
        from ai_stack.rag import RETRIEVAL_POLICY_VERSION
        summary["retrieval_policy_version"] = retrieval.get("retrieval_policy_version") or RETRIEVAL_POLICY_VERSION
        if hit_count > 0:
            sources = retrieval.get("sources")
            if isinstance(sources, list) and sources:
                first = sources[0]
                if isinstance(first, dict):
                    lane = first.get("source_evidence_lane")
                    if isinstance(lane, str) and lane:
                        summary["primary_source_evidence_lane"] = lane
                    inf = first.get("profile_policy_influence")
                    if isinstance(inf, str) and inf:
                        summary["primary_profile_policy_influence"] = inf
        return summary
    if capability_name == "wos.review_bundle.build":
        evidence = result.get("evidence_sources", [])
        n_evidence = len(evidence) if isinstance(evidence, list) else 0
        return {
            "kind": "review_bundle",
            "bundle_id": result.get("bundle_id"),
            "status": result.get("status"),
            "evidence_source_count": n_evidence,
            "workflow_impact": "feeds_governance_review_package" if n_evidence else "metadata_only_bundle",
        }
    if capability_name == "wos.transcript.read":
        content = result.get("content", "")
        turn_count = 0
        repetition_turns = 0
        try:
            parsed = json.loads(str(content))
            if isinstance(parsed, dict):
                turns = parsed.get("transcript")
                if isinstance(turns, list):
                    turn_count = len(turns)
                    repetition_turns = sum(1 for row in turns if isinstance(row, dict) and row.get("repetition_flag"))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        return {
            "kind": "transcript_read",
            "run_id": result.get("run_id"),
            "content_length": len(str(content)),
            "transcript_turn_count": turn_count,
            "repetition_turn_count": repetition_turns,
            "workflow_impact": (
                "drives_improvement_recommendation_suffix"
                if turn_count
                else "no_parsed_transcript_rows"
            ),
        }
    if capability_name == "wos.research.explore":
        summary = result.get("exploration_summary", {})
        if not isinstance(summary, dict):
            summary = {}
        consumed = summary.get("consumed_budget")
        effective = summary.get("effective_budget")
        return {
            "kind": "research_explore",
            "run_id": result.get("run_id"),
            "node_count": summary.get("node_count", 0),
            "edge_count": summary.get("edge_count", 0),
            "abort_reason": summary.get("abort_reason"),
            "promoted_candidate_count": summary.get("promoted_candidate_count", 0),
            "consumed_budget": consumed if isinstance(consumed, dict) else {},
            "effective_budget": effective if isinstance(effective, dict) else {},
        }
    if capability_name == "wos.research.bundle.build":
        bundle = result.get("bundle", {})
        if not isinstance(bundle, dict):
            bundle = {}
        return {
            "kind": "research_bundle",
            "run_id": bundle.get("run_id"),
            "section_count": len(bundle.get("sections", [])) if isinstance(bundle.get("sections"), list) else 0,
            "review_safe": (bundle.get("governance") or {}).get("review_safe"),
        }
    if capability_name == "wos.canon.improvement.propose":
        issues = result.get("issues", [])
        proposals = result.get("proposals", [])
        return {
            "kind": "canon_improvement_propose",
            "issue_count": len(issues) if isinstance(issues, list) else 0,
            "proposal_count": len(proposals) if isinstance(proposals, list) else 0,
        }
    return None


def _parse_top_hit_score(retrieval: dict[str, Any]) -> float | None:
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
    notes = retrieval.get("ranking_notes")
    if not isinstance(notes, list):
        return ""
    return " ".join(str(n) for n in notes)


def _sources_list(retrieval: dict[str, Any]) -> list[dict[str, Any]]:
    s = retrieval.get("sources")
    if not isinstance(s, list):
        return []
    return [x for x in s if isinstance(x, dict)]


def _lanes_from_sources(sources: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for row in sources:
        lane = row.get("source_evidence_lane")
        if isinstance(lane, str) and lane:
            out.append(lane)
    return out


def evidence_lane_mix_from_sources(sources: list[dict[str, Any]] | None) -> str:
    """Compact governance mix over packed sources (lanes only; not a score)."""
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
    m = re.search(r"policy_hard_excluded_pool_count=(\d+)", notes_joined)
    if not m:
        return 0
    try:
        return int(m.group(1))
    except ValueError:
        return 0


def _dedup_shaped(notes_joined: str) -> bool:
    return "dup_suppressed" in notes_joined


def _policy_outcome_hint(notes_joined: str) -> str:
    if _hard_exclusion_count(notes_joined) > 0:
        return "hard_pool_exclusions_applied"
    return "no_hard_pool_exclusions_in_notes"


def _sources_have_lane(sources: list[dict[str, Any]], lane: str) -> bool:
    return any(row.get("source_evidence_lane") == lane for row in sources)


def _canonical_lane_hits(sources: list[dict[str, Any]]) -> int:
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

    Raw hit count never implies ``strong`` for multi-hit packs without hybrid-backed
    lane anchors. Policy-hard pool reshapes and thin canonical anchors further cap
    ``strong`` so operators are not misled by volume alone.
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
    """Dense operator token: lane hit counts in stable key order (not a score)."""
    keys = ("canonical", "supporting", "draft_working", "internal_review", "evaluative", "unknown")
    counts: dict[str, int] = {k: 0 for k in keys}
    for row in sources:
        lane = row.get("source_evidence_lane")
        lk = lane if isinstance(lane, str) and lane in counts else "unknown"
        counts[lk] = counts.get(lk, 0) + 1
    parts = [f"{k[:1]}={counts[k]}" for k in keys if counts[k]]
    return "|".join(parts) if parts else "none"


def _governance_influence_compact(*, hard_excl: int, dedup: bool, policy_hint: str) -> str:
    return f"hard_excl={hard_excl};dedup={'yes' if dedup else 'no'};policy={policy_hint}"


def _confidence_posture(
    *,
    tier: str,
    route_s: str,
    degradation_mode: Any,
    rationale: str,
) -> str:
    """Honest coarse confidence (implementation-grounded; not a calibrated probability)."""
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
    """Normalize capability ``retrieval`` dict into workflow-facing trace fields.

    ``evidence_tier`` (and ``evidence_strength``, same value) use a four-level scale:
    ``none`` / ``weak`` / ``moderate`` / ``strong``. Task 4 adds explicit caps so raw
    hit count alone cannot label a pack ``strong`` when the signal path is sparse-only,
    degraded, or the packed lanes are supporting-heavy without canonical or evaluative
    anchors. This is a small, documented heuristic layer—not a second ranker.

    Additional compact fields (operator-facing, English):
    ``evidence_lane_mix``, ``lane_anchor_counts``, ``retrieval_quality_hint``,
    ``policy_outcome_hint``, ``dedup_shaped_selection``, ``readiness_label``,
    ``confidence_posture``, ``governance_influence_compact``,
    ``retrieval_posture_summary``, ``retrieval_trace_schema_version``.
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
    RETRIEVAL = "retrieval"
    ACTION = "action"


class CapabilityAccessDeniedError(PermissionError):
    def __init__(self, capability_name: str, mode: str) -> None:
        super().__init__(f"Capability '{capability_name}' denied for mode '{mode}'")
        self.capability_name = capability_name
        self.mode = mode


class CapabilityValidationError(ValueError):
    def __init__(self, capability_name: str, field_name: str) -> None:
        super().__init__(f"Capability '{capability_name}' missing required field '{field_name}'")
        self.capability_name = capability_name
        self.field_name = field_name


class CapabilityInvocationError(RuntimeError):
    def __init__(self, capability_name: str, detail: str) -> None:
        super().__init__(f"Capability '{capability_name}' failed: {detail}")
        self.capability_name = capability_name
        self.detail = detail


@dataclass(slots=True)
class CapabilityDefinition:
    name: str
    kind: CapabilityKind
    input_schema: dict[str, Any]
    result_schema: dict[str, Any]
    allowed_modes: set[str]
    audit_required: bool
    failure_semantics: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


class CapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[str, CapabilityDefinition] = {}
        self._audit_log: list[dict[str, Any]] = []

    def register(self, definition: CapabilityDefinition) -> None:
        self._capabilities[definition.name] = definition

    def list_capabilities(self) -> list[dict[str, Any]]:
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


def create_default_capability_registry(
    *,
    retriever: "ContextRetriever",
    assembler: "ContextPackAssembler",
    repo_root: Path,
) -> CapabilityRegistry:
    # Keep lightweight capability metadata imports free from heavy retrieval dependencies.
    from ai_stack.rag import RetrievalDomain, RetrievalRequest
    from ai_stack.research_contract import ExplorationBudget
    from ai_stack.research_langgraph import (
        build_research_bundle,
        exploration_graph,
        get_run,
        inspect_canon_issue,
        inspect_source,
        list_claims,
        preview_canon_improvement,
        propose_canon_improvement,
        research_store_from_repo_root,
        run_research_pipeline,
    )

    registry = CapabilityRegistry()
    research_store = research_store_from_repo_root(repo_root)

    def context_pack_handler(payload: dict[str, Any]) -> dict[str, Any]:
        domain = RetrievalDomain(payload.get("domain", RetrievalDomain.RUNTIME.value))
        request = RetrievalRequest(
            domain=domain,
            profile=payload["profile"],
            query=payload["query"],
            module_id=payload.get("module_id"),
            scene_id=payload.get("scene_id"),
            max_chunks=int(payload.get("max_chunks", 4)),
        )
        retrieval_result = retriever.retrieve(request)
        context_pack = assembler.assemble(retrieval_result)
        top_score = ""
        if context_pack.sources:
            top_score = str(context_pack.sources[0].get("score", ""))
        from ai_stack.rag import RETRIEVAL_POLICY_VERSION
        return {
            "retrieval": {
                "domain": context_pack.domain,
                "profile": context_pack.profile,
                "status": context_pack.status,
                "hit_count": context_pack.hit_count,
                "sources": context_pack.sources,
                "ranking_notes": context_pack.ranking_notes,
                "index_version": context_pack.index_version,
                "corpus_fingerprint": context_pack.corpus_fingerprint,
                "storage_path": context_pack.storage_path,
                "retrieval_route": context_pack.retrieval_route,
                "embedding_model_id": context_pack.embedding_model_id,
                "top_hit_score": top_score,
                "degradation_mode": context_pack.degradation_mode,
                "dense_index_build_action": context_pack.dense_index_build_action,
                "dense_rebuild_reason": context_pack.dense_rebuild_reason,
                "dense_artifact_validity": context_pack.dense_artifact_validity,
                "embedding_reason_codes": list(context_pack.embedding_reason_codes),
                "embedding_index_version": context_pack.embedding_index_version,
                "embedding_cache_dir_identity": context_pack.embedding_cache_dir_identity,
                "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
            },
            "context_text": context_pack.compact_context,
        }

    def transcript_read_handler(payload: dict[str, Any]) -> dict[str, Any]:
        run_id = payload["run_id"]
        run_file = repo_root / "world-engine" / "app" / "var" / "runs" / f"{run_id}.json"
        if not run_file.exists():
            raise CapabilityInvocationError("wos.transcript.read", "run_not_found")
        return {"run_id": run_id, "content": run_file.read_text(encoding="utf-8", errors="ignore")[:10000]}

    def review_bundle_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "bundle_id": uuid4().hex,
            "module_id": payload["module_id"],
            "summary": payload.get("summary", ""),
            "recommendations": payload.get("recommendations", []),
            "evidence_sources": payload.get("evidence_sources", []),
            "status": "recommendation_only",
        }

    def research_source_inspect_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return inspect_source(store=research_store, source_id=str(payload["source_id"]))

    def research_aspect_extract_handler(payload: dict[str, Any]) -> dict[str, Any]:
        source_id = str(payload["source_id"])
        inspected = inspect_source(store=research_store, source_id=source_id)
        if inspected.get("error"):
            return inspected
        return {
            "source_id": source_id,
            "aspects": inspected.get("aspects", []),
        }

    def research_claim_list_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return list_claims(store=research_store, work_id=payload.get("work_id"))

    def research_run_get_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return get_run(store=research_store, run_id=str(payload["run_id"]))

    def research_exploration_graph_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return exploration_graph(store=research_store, run_id=str(payload["run_id"]))

    def canon_issue_inspect_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return inspect_canon_issue(store=research_store, module_id=payload.get("module_id"))

    def research_explore_handler(payload: dict[str, Any]) -> dict[str, Any]:
        # Hard budget validation at capability level.
        budget = ExplorationBudget.from_payload(payload.get("budget", {}))
        run = run_research_pipeline(
            store=research_store,
            work_id=str(payload["work_id"]),
            module_id=str(payload["module_id"]),
            source_inputs=list(payload["source_inputs"]),
            seed_question=str(payload.get("seed_question", "")),
            budget_payload=budget.to_dict(),
            mode="capability_explore",
        )
        return {
            "run_id": run["run_id"],
            "exploration_summary": (run.get("outputs", {}) or {}).get("exploration_summary", {}),
            "effective_budget": budget.to_dict(),
        }

    def research_validate_handler(payload: dict[str, Any]) -> dict[str, Any]:
        run_id = str(payload["run_id"])
        run = get_run(store=research_store, run_id=run_id)
        if run.get("error"):
            return run
        return {
            "run_id": run_id,
            "claims": ((run.get("run", {}) or {}).get("outputs", {}) or {}).get("claim_ids", []),
            "status": "validated_from_run_outputs",
        }

    def research_bundle_build_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return build_research_bundle(store=research_store, run_id=str(payload["run_id"]))

    def canon_improvement_propose_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return propose_canon_improvement(store=research_store, module_id=str(payload["module_id"]))

    def canon_improvement_preview_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return preview_canon_improvement(store=research_store, module_id=str(payload["module_id"]))

    registry.register(
        CapabilityDefinition(
            name="wos.context_pack.build",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string"},
                    "profile": {"type": "string"},
                    "query": {"type": "string"},
                    "module_id": {"type": "string"},
                    "scene_id": {"type": "string"},
                    "max_chunks": {"type": "integer"},
                },
                "required": ["profile", "query"],
            },
            result_schema={
                "type": "object",
                "properties": {"retrieval": {"type": "object"}, "context_text": {"type": "string"}},
                "required": ["retrieval", "context_text"],
            },
            allowed_modes={"runtime", "writers_room", "improvement"},
            audit_required=True,
            failure_semantics="returns capability error and emits audit event",
            handler=context_pack_handler,
        )
    )
    # wos.transcript.read: used by the improvement sandbox experiment route (persisted run JSON
    # under world-engine var/runs). Runtime and admin remain secondary / optional call sites.
    registry.register(
        CapabilityDefinition(
            name="wos.transcript.read",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}, "content": {"type": "string"}},
                "required": ["run_id", "content"],
            },
            allowed_modes={"runtime", "improvement", "admin"},
            audit_required=True,
            failure_semantics="raises run_not_found error with audited trace",
            handler=transcript_read_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.review_bundle.build",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "module_id": {"type": "string"},
                    "summary": {"type": "string"},
                    "recommendations": {"type": "array"},
                    "evidence_sources": {"type": "array"},
                },
                "required": ["module_id"],
            },
            result_schema={
                "type": "object",
                "properties": {
                    "bundle_id": {"type": "string"},
                    "module_id": {"type": "string"},
                    "status": {"type": "string"},
                },
                "required": ["bundle_id", "module_id", "status"],
            },
            allowed_modes={"writers_room", "improvement", "admin"},
            audit_required=True,
            failure_semantics="returns recommendation-only bundle metadata",
            handler=review_bundle_handler,
        )
    )

    registry.register(
        CapabilityDefinition(
            name="wos.research.source.inspect",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns source_not_found when unknown",
            handler=research_source_inspect_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.aspect.extract",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"source_id": {"type": "string"}},
                "required": ["source_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns stored deterministic aspect rows",
            handler=research_aspect_extract_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.claim.list",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"work_id": {"type": "string"}},
                "required": [],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns deterministic claim listing",
            handler=research_claim_list_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.run.get",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns run_not_found when unknown",
            handler=research_run_get_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.exploration.graph",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns bounded run graph",
            handler=research_exploration_graph_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.canon.issue.inspect",
            kind=CapabilityKind.RETRIEVAL,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": [],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns deterministic issue listing",
            handler=canon_issue_inspect_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.explore",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {
                    "work_id": {"type": "string"},
                    "module_id": {"type": "string"},
                    "seed_question": {"type": "string"},
                    "source_inputs": {"type": "array"},
                    "budget": {"type": "object"},
                },
                "required": ["work_id", "module_id", "source_inputs", "budget"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="fails if budget object is missing or invalid",
            handler=research_explore_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.validate",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="validates run outputs in deterministic flow",
            handler=research_validate_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.research.bundle.build",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"run_id": {"type": "string"}},
                "required": ["run_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns review-safe bundle only",
            handler=research_bundle_build_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.canon.improvement.propose",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": ["module_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns taxonomy-constrained issues and proposals",
            handler=canon_improvement_propose_handler,
        )
    )
    registry.register(
        CapabilityDefinition(
            name="wos.canon.improvement.preview",
            kind=CapabilityKind.ACTION,
            input_schema={
                "type": "object",
                "properties": {"module_id": {"type": "string"}},
                "required": ["module_id"],
            },
            result_schema={"type": "object"},
            allowed_modes={"research", "admin", "improvement"},
            audit_required=True,
            failure_semantics="returns preview payloads, no mutation",
            handler=canon_improvement_preview_handler,
        )
    )
    return registry


def capability_catalog() -> list[dict[str, Any]]:
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
