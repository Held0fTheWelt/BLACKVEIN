from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.runtime.input_interpreter import interpret_player_input


# Commands that suggest meta/reset intent rather than story escalation.
_META_COMMAND_NAMES = frozenset(
    {"reset", "restart", "quit", "exit", "help", "pause", "ooc", "meta"}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ImprovementStore:
    root: Path

    @classmethod
    def default(cls) -> "ImprovementStore":
        root = Path(__file__).resolve().parents[2] / "var" / "improvement"
        return cls(root=root)

    def ensure_dirs(self) -> None:
        (self.root / "variants").mkdir(parents=True, exist_ok=True)
        (self.root / "experiments").mkdir(parents=True, exist_ok=True)
        (self.root / "recommendations").mkdir(parents=True, exist_ok=True)

    def write_json(self, category: str, item_id: str, payload: dict[str, Any]) -> Path:
        self.ensure_dirs()
        path = self.root / category / f"{item_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def read_json(self, category: str, item_id: str) -> dict[str, Any]:
        path = self.root / category / f"{item_id}.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def list_json(self, category: str) -> list[dict[str, Any]]:
        folder = self.root / category
        if not folder.exists():
            return []
        items: list[dict[str, Any]] = []
        for file in sorted(folder.glob("*.json")):
            items.append(json.loads(file.read_text(encoding="utf-8")))
        return items


def create_variant(
    *,
    baseline_id: str,
    candidate_summary: str,
    actor_id: str,
    metadata: dict[str, Any] | None = None,
    store: ImprovementStore | None = None,
) -> dict[str, Any]:
    storage = store or ImprovementStore.default()
    variant_id = f"variant_{uuid4().hex}"
    metadata_payload = metadata or {}
    mutation_plan = metadata_payload.get("mutation_plan")
    if not isinstance(mutation_plan, list) or not mutation_plan:
        mutation_plan = [
            {
                "operation": "adjust_conflict_pacing",
                "target": "scene_transition",
                "intent": "reduce repetitive escalation loops",
            },
            {
                "operation": "strengthen_guard_behavior",
                "target": "safety_filter",
                "intent": "lower unsafe response acceptance",
            },
        ]
    parent_variant_id = metadata_payload.get("parent_variant_id")
    parent_variant_id = str(parent_variant_id).strip() if parent_variant_id else ""
    lineage_depth = 1
    if parent_variant_id:
        try:
            lineage_depth = max(2, int(metadata_payload.get("lineage_depth", 2)))
        except (TypeError, ValueError):
            lineage_depth = 2
    lineage: dict[str, Any] = {
        "baseline_id": baseline_id,
        "derived_from": baseline_id,
        "lineage_depth": lineage_depth,
    }
    if parent_variant_id:
        lineage["parent_variant_id"] = parent_variant_id
    mutation_metadata = metadata_payload.get("mutation_metadata")
    if isinstance(mutation_metadata, dict) and mutation_metadata:
        variant_mutation_meta = mutation_metadata
    else:
        variant_mutation_meta = {
            "source": metadata_payload.get("source"),
            "intent_tags": metadata_payload.get("intent_tags") or [],
        }
    variant = {
        "variant_id": variant_id,
        "baseline_id": baseline_id,
        "candidate_summary": candidate_summary,
        "metadata": metadata_payload,
        "created_by": actor_id,
        "created_at": _utc_now(),
        "review_status": "pending_review",
        "mutation_plan": mutation_plan,
        "mutation_metadata": {k: v for k, v in variant_mutation_meta.items() if v is not None},
        "lineage": lineage,
    }
    storage.write_json("variants", variant_id, variant)
    return variant


def _simulate_sandbox_turn(*, variant: dict[str, Any], player_input: str, turn_number: int) -> dict[str, Any]:
    """Simulate a single sandbox turn using semantic input interpretation.

    Guard rejection is now determined by semantic classification rather than
    hardcoded keyword matching.  An ``explicit_command`` whose command_name is
    in the meta/reset set is flagged as a guard-rejection signal; all other
    kinds are treated according to their escalation potential.
    """
    interp = interpret_player_input(player_input)
    kind_value = interp.kind.value  # str, e.g. "speech", "action", ...

    # Determine guard_rejected from semantic signal.
    # explicit_command with a meta/reset command name → guard-relevant signal.
    if interp.kind.value == "explicit_command":
        guard_rejected = interp.command_name in _META_COMMAND_NAMES
    else:
        # For all other kinds, no semantic guard rejection is indicated.
        # (Keyword-based rejection is intentionally removed.)
        guard_rejected = False

    lowered = player_input.lower()
    repetition = "repeat" in lowered or lowered.count("again") > 1

    # Tag based on interpreted kind rather than raw keyword scan.
    if kind_value in ("action", "mixed"):
        triggered_tags = ["conflict"] if any(w in lowered for w in ("argue", "fight", "attack")) else ["action"]
    elif kind_value == "speech":
        triggered_tags = ["dialogue"]
    elif kind_value == "explicit_command":
        triggered_tags = ["command"]
    elif kind_value in ("ambiguous", "intent_only"):
        triggered_tags = ["uncertain"]
    else:
        triggered_tags = ["narrative"]

    return {
        "turn_number": turn_number,
        "player_input": player_input,
        "interpreted_kind": kind_value,
        "interpretation_confidence": interp.confidence,
        "guard_rejected": guard_rejected,
        "triggered_tags": triggered_tags,
        "repetition_flag": repetition,
        "scene_marker": "scene_1" if turn_number <= 2 else "scene_2",
        "quality_hint": max(0.0, min(1.0, len(player_input) / 80.0)),
        "variant_id": variant["variant_id"],
    }


def _evaluate_transcript(transcript: list[dict[str, Any]]) -> dict[str, float]:
    """Evaluate a sandbox transcript and return per-metric scores.

    ``guard_reject_rate`` is now based on the semantic ``guard_rejected`` flag
    produced by ``_simulate_sandbox_turn`` (which uses ``interpret_player_input``
    rather than hardcoded keyword matching).  The metric value is therefore a
    genuine semantic signal, not a vocabulary accident.
    """
    total = max(1, len(transcript))
    guard_rejects = sum(1 for turn in transcript if turn.get("guard_rejected"))
    repeated = sum(1 for turn in transcript if turn.get("repetition_flag"))
    covered_scene_markers = len({turn.get("scene_marker") for turn in transcript if turn.get("scene_marker")})
    unique_trigger_tags = len({tag for turn in transcript for tag in turn.get("triggered_tags", [])})
    quality_avg = sum(float(turn.get("quality_hint", 0.0)) for turn in transcript) / total

    # Collect semantic kind distribution for informational purposes.
    kind_counts: dict[str, int] = {}
    for turn in transcript:
        k = turn.get("interpreted_kind")
        if k:
            kind_counts[k] = kind_counts.get(k, 0) + 1

    return {
        "guard_reject_rate": round(guard_rejects / total, 4),
        "trigger_coverage": float(unique_trigger_tags),
        "repetition_signal": round(repeated / total, 4),
        "structure_flow_health": round(max(0.0, 1.0 - (repeated / total)), 4),
        "transcript_quality_heuristic": round(quality_avg, 4),
        "scene_marker_coverage": float(covered_scene_markers),
        # Semantic breakdown: proportion of turns classified as each kind.
        "semantic_action_rate": round(kind_counts.get("action", 0) / total, 4),
        "semantic_speech_rate": round(kind_counts.get("speech", 0) / total, 4),
        "semantic_command_rate": round(kind_counts.get("explicit_command", 0) / total, 4),
    }


def run_sandbox_experiment(
    *,
    variant_id: str,
    actor_id: str,
    test_inputs: list[str] | None = None,
    store: ImprovementStore | None = None,
) -> dict[str, Any]:
    storage = store or ImprovementStore.default()
    variant = storage.read_json("variants", variant_id)
    inputs = test_inputs or [
        "I try to calm the argument and ask for clarity.",
        "I repeat the same accusation again and again.",
        "I argue and escalate the conflict.",
    ]
    transcript = [
        _simulate_sandbox_turn(variant=variant, player_input=player_input, turn_number=index)
        for index, player_input in enumerate(inputs, start=1)
    ]
    baseline_variant = {
        "variant_id": f"baseline::{variant['baseline_id']}",
        "mutation_plan": [],
    }
    baseline_transcript = [
        _simulate_sandbox_turn(variant=baseline_variant, player_input=player_input, turn_number=index)
        for index, player_input in enumerate(inputs, start=1)
    ]
    experiment_id = f"experiment_{uuid4().hex}"
    experiment = {
        "experiment_id": experiment_id,
        "variant_id": variant_id,
        "baseline_id": variant["baseline_id"],
        "created_by": actor_id,
        "created_at": _utc_now(),
        "sandbox": True,
        "transcript": transcript,
        "baseline_transcript": baseline_transcript,
        "lineage": variant.get("lineage", {}),
        "metadata": {
            "execution_mode": "sandbox",
            "publish_state": "isolated_non_authoritative",
            "mutation_plan": variant.get("mutation_plan", []),
        },
    }
    storage.write_json("experiments", experiment_id, experiment)
    return experiment


def evaluate_experiment(
    *,
    experiment_id: str,
    store: ImprovementStore | None = None,
) -> dict[str, Any]:
    storage = store or ImprovementStore.default()
    experiment = storage.read_json("experiments", experiment_id)
    transcript = experiment.get("transcript", [])
    baseline_transcript = experiment.get("baseline_transcript", [])
    metrics = _evaluate_transcript(transcript if isinstance(transcript, list) else [])
    baseline_metrics = _evaluate_transcript(baseline_transcript if isinstance(baseline_transcript, list) else [])
    comparison = {
        "guard_reject_rate_delta": round(
            metrics["guard_reject_rate"] - baseline_metrics["guard_reject_rate"],
            4,
        ),
        "repetition_signal_delta": round(
            metrics["repetition_signal"] - baseline_metrics["repetition_signal"],
            4,
        ),
        "structure_flow_health_delta": round(
            metrics["structure_flow_health"] - baseline_metrics["structure_flow_health"],
            4,
        ),
        "quality_heuristic_delta": round(
            metrics["transcript_quality_heuristic"] - baseline_metrics["transcript_quality_heuristic"],
            4,
        ),
    }
    evaluation = {
        "experiment_id": experiment_id,
        "variant_id": experiment["variant_id"],
        "baseline_id": experiment["baseline_id"],
        "generated_at": _utc_now(),
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "comparison": comparison,
        "notable_failures": [
            "guard_rejections_detected" if metrics["guard_reject_rate"] > 0 else "none",
            "repetition_detected" if metrics["repetition_signal"] > 0 else "none",
        ],
    }
    return evaluation


def build_comparison_package(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Structured baseline vs candidate comparison for governance review."""
    metrics = evaluation.get("metrics") or {}
    baseline_metrics = evaluation.get("baseline_metrics") or {}
    comparison = evaluation.get("comparison") or {}
    dimensions: list[dict[str, Any]] = [
        {
            "metric": "guard_reject_rate",
            "candidate_value": metrics.get("guard_reject_rate"),
            "baseline_value": baseline_metrics.get("guard_reject_rate"),
            "delta": comparison.get("guard_reject_rate_delta"),
        },
        {
            "metric": "repetition_signal",
            "candidate_value": metrics.get("repetition_signal"),
            "baseline_value": baseline_metrics.get("repetition_signal"),
            "delta": comparison.get("repetition_signal_delta"),
        },
        {
            "metric": "structure_flow_health",
            "candidate_value": metrics.get("structure_flow_health"),
            "baseline_value": baseline_metrics.get("structure_flow_health"),
            "delta": comparison.get("structure_flow_health_delta"),
        },
        {
            "metric": "transcript_quality_heuristic",
            "candidate_value": metrics.get("transcript_quality_heuristic"),
            "baseline_value": baseline_metrics.get("transcript_quality_heuristic"),
            "delta": comparison.get("quality_heuristic_delta"),
        },
    ]
    semantic_speech_c = float(metrics.get("semantic_speech_rate") or 0.0)
    semantic_speech_b = float(baseline_metrics.get("semantic_speech_rate") or 0.0)
    semantic_action_c = float(metrics.get("semantic_action_rate") or 0.0)
    semantic_action_b = float(baseline_metrics.get("semantic_action_rate") or 0.0)
    return {
        "experiment_id": evaluation.get("experiment_id"),
        "variant_id": evaluation.get("variant_id"),
        "baseline_id": evaluation.get("baseline_id"),
        "generated_at": evaluation.get("generated_at"),
        "dimensions": dimensions,
        "semantic_delta": {
            "semantic_speech_rate_delta": round(semantic_speech_c - semantic_speech_b, 4),
            "semantic_action_rate_delta": round(semantic_action_c - semantic_action_b, 4),
        },
        "notable_failures": evaluation.get("notable_failures", []),
    }


def build_evidence_strength_map(
    *,
    evaluation: dict[str, Any],
    retrieval_hit_count: int = 0,
    transcript_tool_ok: bool = False,
    governance_bundle_attached: bool = False,
) -> dict[str, Any]:
    """Declarative map: which evidence classes back the recommendation (not numeric confidence)."""
    _ = evaluation  # reserved for future per-metric weighting
    return {
        "sandbox_candidate_metrics": "primary",
        "baseline_control_transcript": "primary",
        "comparison_deltas": "primary",
        "retrieval_context": "moderate" if retrieval_hit_count > 0 else "none",
        "transcript_tool_readback": "moderate" if transcript_tool_ok else "low",
        "governance_review_bundle": "moderate" if governance_bundle_attached else "pending_until_route",
    }


def build_recommendation_rationale(
    *,
    evaluation: dict[str, Any],
    recommendation_summary: str,
    retrieval_hit_count: int = 0,
    retrieval_source_paths: list[str] | None = None,
    transcript_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Explicit drivers tying the summary to metrics, deltas, and optional runtime evidence."""
    metrics = evaluation["metrics"]
    comp = evaluation["comparison"]
    drivers: list[dict[str, Any]] = []

    if metrics["guard_reject_rate"] > 0.4:
        drivers.append(
            {
                "category": "sandbox_metrics",
                "metric": "guard_reject_rate",
                "observed": metrics["guard_reject_rate"],
                "threshold": 0.4,
                "relation": "greater_than",
                "recommendation_effect": "favors_revise_before_review",
            }
        )
    if metrics["repetition_signal"] > 0.5:
        drivers.append(
            {
                "category": "sandbox_metrics",
                "metric": "repetition_signal",
                "observed": metrics["repetition_signal"],
                "threshold": 0.5,
                "relation": "greater_than",
                "recommendation_effect": "favors_revise_before_review",
            }
        )
    if comp["structure_flow_health_delta"] < 0:
        drivers.append(
            {
                "category": "comparison_delta",
                "metric": "structure_flow_health_delta",
                "observed": comp["structure_flow_health_delta"],
                "threshold": 0.0,
                "relation": "less_than",
                "recommendation_effect": "favors_revise_before_review",
            }
        )
    if comp["quality_heuristic_delta"] < 0:
        drivers.append(
            {
                "category": "comparison_delta",
                "metric": "quality_heuristic_delta",
                "observed": comp["quality_heuristic_delta"],
                "threshold": 0.0,
                "relation": "less_than",
                "recommendation_effect": "favors_revise_before_review",
            }
        )

    tm = transcript_meta if isinstance(transcript_meta, dict) else {}
    rep_ct = tm.get("repetition_turn_count")
    if isinstance(rep_ct, int) and rep_ct >= 2:
        drivers.append(
            {
                "category": "transcript_tool_evidence",
                "metric": "repetition_turn_count",
                "observed": rep_ct,
                "threshold": 2,
                "relation": "greater_equal",
                "recommendation_effect": "aligns_with_revise_suffix_from_transcript_tool",
            }
        )

    paths = [p for p in (retrieval_source_paths or []) if p]
    if retrieval_hit_count > 0 and paths:
        drivers.append(
            {
                "category": "retrieval_context",
                "hit_count": retrieval_hit_count,
                "top_paths": paths[:5],
                "recommendation_effect": "grounds_human_review_in_retrieved_sources",
            }
        )

    if not drivers:
        drivers.append(
            {
                "category": "baseline_pass",
                "detail": "No threshold violations on core sandbox metrics or negative comparison deltas.",
                "recommendation_effect": "allows_promote_for_human_review",
            }
        )

    return {
        "recommendation_summary": recommendation_summary,
        "drivers": drivers,
        "confidence_notes": (
            "Rationale is assembled from explicit metrics, comparison deltas, transcript tool signals, "
            "and retrieval paths. It does not auto-promote to production."
        ),
    }


def finalize_recommendation_rationale_with_retrieval_digest(
    rationale: dict[str, Any],
    *,
    context_text: str,
    retrieval_source_paths: list[str],
    hit_count: int,
) -> dict[str, Any]:
    """Copy rationale and append a digest driver so retrieval shape is fingerprint-bound (testable)."""
    out = copy.deepcopy(rationale)
    paths_sorted = sorted(p for p in retrieval_source_paths if p)
    raw = "\n".join(paths_sorted) + "||" + (context_text or "")[:4096]
    fp = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
    drivers = list(out.get("drivers") or [])
    drivers.append(
        {
            "category": "retrieval_context_digest",
            "hit_count": hit_count,
            "context_fingerprint_sha256_16": fp,
            "path_signature": paths_sorted[:8],
            "recommendation_effect": "binds_review_package_to_retrieval_shape",
        }
    )
    out["drivers"] = drivers
    out["retrieval_context_fingerprint_sha256_16"] = fp
    return out


def build_recommendation_package(
    *,
    experiment_id: str,
    actor_id: str,
    store: ImprovementStore | None = None,
) -> dict[str, Any]:
    storage = store or ImprovementStore.default()
    experiment = storage.read_json("experiments", experiment_id)
    variant = storage.read_json("variants", experiment["variant_id"])
    evaluation = evaluate_experiment(experiment_id=experiment_id, store=storage)
    metrics = evaluation["metrics"]
    comparison = evaluation["comparison"]
    recommendation = "promote_for_human_review"
    if metrics["guard_reject_rate"] > 0.4 or metrics["repetition_signal"] > 0.5:
        recommendation = "revise_before_review"
    if comparison["structure_flow_health_delta"] < 0 or comparison["quality_heuristic_delta"] < 0:
        recommendation = "revise_before_review"
    comparison_package = build_comparison_package(evaluation)
    recommendation_rationale = build_recommendation_rationale(
        evaluation=evaluation,
        recommendation_summary=recommendation,
        retrieval_hit_count=0,
        retrieval_source_paths=[],
        transcript_meta=None,
    )
    evidence_strength_map = build_evidence_strength_map(
        evaluation=evaluation,
        retrieval_hit_count=0,
        transcript_tool_ok=False,
        governance_bundle_attached=False,
    )
    package_id = f"recommendation_{uuid4().hex}"
    package = {
        "package_id": package_id,
        "generated_at": _utc_now(),
        "generated_by": actor_id,
        "baseline": {"baseline_id": variant["baseline_id"]},
        "candidate": {"variant_id": variant["variant_id"], "candidate_summary": variant["candidate_summary"]},
        "experiment": {"experiment_id": experiment_id, "sandbox": True},
        "lineage": variant.get("lineage", {}),
        "mutation_plan": variant.get("mutation_plan", []),
        "mutation_metadata": variant.get("mutation_metadata") or {},
        "evaluation": evaluation,
        "comparison_package": comparison_package,
        "recommendation_rationale": recommendation_rationale,
        "evidence_strength_map": evidence_strength_map,
        "evidence_bundle": {
            "experiment_id": experiment_id,
            "variant_id": variant["variant_id"],
            "baseline_id": variant["baseline_id"],
            "comparison": comparison,
            "artifact_refs": [
                f"experiments/{experiment_id}.json",
                f"variants/{variant['variant_id']}.json",
            ],
        },
        "recommendation_summary": recommendation,
        "review_status": "pending_governance_review",
        "next_action": "admin_review_required",
    }
    storage.write_json("recommendations", package_id, package)
    return package


def list_recommendation_packages(*, store: ImprovementStore | None = None) -> list[dict[str, Any]]:
    storage = store or ImprovementStore.default()
    return storage.list_json("recommendations")
