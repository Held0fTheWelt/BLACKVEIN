from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


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
    variant = {
        "variant_id": variant_id,
        "baseline_id": baseline_id,
        "candidate_summary": candidate_summary,
        "metadata": metadata_payload,
        "created_by": actor_id,
        "created_at": _utc_now(),
        "review_status": "pending_review",
        "mutation_plan": mutation_plan,
        "lineage": {
            "baseline_id": baseline_id,
            "derived_from": baseline_id,
            "lineage_depth": 1,
        },
    }
    storage.write_json("variants", variant_id, variant)
    return variant


def _simulate_sandbox_turn(*, variant: dict[str, Any], player_input: str, turn_number: int) -> dict[str, Any]:
    lowered = player_input.lower()
    guard_rejected = any(token in lowered for token in ("kill", "hate", "destroy"))
    repetition = "repeat" in lowered or lowered.count("again") > 1
    return {
        "turn_number": turn_number,
        "player_input": player_input,
        "guard_rejected": guard_rejected,
        "triggered_tags": ["conflict"] if "argue" in lowered or "fight" in lowered else ["dialogue"],
        "repetition_flag": repetition,
        "scene_marker": "scene_1" if turn_number <= 2 else "scene_2",
        "quality_hint": max(0.0, min(1.0, len(player_input) / 80.0)),
        "variant_id": variant["variant_id"],
    }


def _evaluate_transcript(transcript: list[dict[str, Any]]) -> dict[str, float]:
    total = max(1, len(transcript))
    guard_rejects = sum(1 for turn in transcript if turn.get("guard_rejected"))
    repeated = sum(1 for turn in transcript if turn.get("repetition_flag"))
    covered_scene_markers = len({turn.get("scene_marker") for turn in transcript if turn.get("scene_marker")})
    unique_trigger_tags = len({tag for turn in transcript for tag in turn.get("triggered_tags", [])})
    quality_avg = sum(float(turn.get("quality_hint", 0.0)) for turn in transcript) / total
    return {
        "guard_reject_rate": round(guard_rejects / total, 4),
        "trigger_coverage": float(unique_trigger_tags),
        "repetition_signal": round(repeated / total, 4),
        "structure_flow_health": round(max(0.0, 1.0 - (repeated / total)), 4),
        "transcript_quality_heuristic": round(quality_avg, 4),
        "scene_marker_coverage": float(covered_scene_markers),
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
        "evaluation": evaluation,
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
