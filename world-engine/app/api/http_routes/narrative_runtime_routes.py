from __future__ import annotations

from .common import *
from .models import *

@router.get("/internal/narrative/runtime/state", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_state(module_id: str, request: Request) -> dict[str, Any]:
    loader = _get_narrative_loader(request)
    state = loader.state(module_id)
    return {"ok": True, "data": state}


@router.get("/internal/narrative/runtime/validator-config", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_validator_config(request: Request) -> dict[str, Any]:
    config = _get_validator_config(request)
    return {"ok": True, "data": config.model_dump(mode="json")}


@router.get("/internal/narrative/runtime/health", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_health(request: Request) -> dict[str, Any]:
    counters = _get_runtime_health(request)
    return {"ok": True, "data": counters.summary()}


@router.post("/internal/narrative/runtime/validate-and-recover", dependencies=[Depends(_require_internal_api_key)])
def narrative_runtime_validate_and_recover(payload: NarrativeTurnValidationRequest, request: Request) -> dict[str, Any]:
    """Operator-introspection validator endpoint.

    Exposes the deterministic narrative validator
    (``validate_runtime_output``) and its corrective-retry helper for
    packet / output pairs supplied directly by an operator. This is **not**
    the live player-turn validator lane — live turns validate through
    ``run_validation_seam`` inside ``RuntimeTurnGraphExecutor``, which
    records ``validator_lane="goc_rule_engine_v1"`` on each committed turn's
    ``runtime_governance_surface``. Callers of this endpoint should treat the
    ``validator_lane`` field in the response as evidence that the
    operator-introspection lane ran, distinct from the canonical live lane.
    """
    config = _get_validator_config(request)
    counters = _get_runtime_health(request)
    from app.narrative.package_models import NarrativeDirectorScenePacket, SceneFallbackBundle

    packet = NarrativeDirectorScenePacket.model_validate(payload.packet)
    output = RuntimeTurnStructuredOutputV2.model_validate(payload.output)
    feedback = validate_runtime_output(packet=packet, output=output, config=config)
    validator_lane = "operator_introspection_validate_and_recover"
    if feedback.passed:
        counters.record_first_pass_success(packet.module_id, packet.scene_id)
        return {
            "ok": True,
            "data": {
                "mode": "first_pass",
                "validator_lane": validator_lane,
                "output": output.model_dump(mode="json"),
            },
        }
    if config.enable_corrective_feedback and config.max_retry_attempts > 0:
        retried = apply_corrective_retry(original_output=output, feedback=feedback)
        retry_feedback: ValidationFeedback = validate_runtime_output(packet=packet, output=retried, config=config)
        if retry_feedback.passed:
            counters.record_corrective_retry(packet.module_id, packet.scene_id)
            return {
                "ok": True,
                "data": {
                    "mode": "corrective_retry",
                    "validator_lane": validator_lane,
                    "validation_feedback": feedback.model_dump(mode="json"),
                    "output": retried.model_dump(mode="json"),
                },
            }
    fallback = build_safe_fallback_output(
        fallback_bundle=SceneFallbackBundle(),
        reason="validation_failed_after_retry",
    )
    counters.record_safe_fallback(packet.module_id, packet.scene_id)
    return {
        "ok": True,
        "data": {
            "mode": "safe_fallback",
            "validator_lane": validator_lane,
            "validation_feedback": feedback.model_dump(mode="json"),
            "output": fallback.model_dump(mode="json"),
        },
    }
