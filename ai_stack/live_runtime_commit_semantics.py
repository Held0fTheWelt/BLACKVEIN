"""ADR-0033 live runtime success and opening-readiness semantics."""

from __future__ import annotations

from typing import Any


_REAL_ADAPTER_KINDS = {"real", "provider", "live"}
_MOCK_MARKERS = ("mock", "stub", "fake", "placeholder", "deterministic")


def _text_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_text_present(item) for item in value.values())
    if isinstance(value, list):
        return any(_text_present(item) for item in value)
    return value is not None and value is not False


def _renderable_output_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_renderable_output_present(item) for item in value)
    if not isinstance(value, dict):
        return False

    for key in ("text", "content", "markdown", "html"):
        if _renderable_output_present(value.get(key)):
            return True
    for key in ("spoken_lines", "action_lines", "committed_consequences", "scene_blocks", "blocks"):
        if _renderable_output_present(value.get(key)):
            return True
    return False


def _visible_blocks(payload: dict[str, Any]) -> list[Any]:
    visible_scene_output = (
        payload.get("visible_scene_output")
        if isinstance(payload.get("visible_scene_output"), dict)
        else {}
    )
    blocks = visible_scene_output.get("blocks")
    return blocks if isinstance(blocks, list) else []


def _story_entries(payload: dict[str, Any]) -> list[Any]:
    entries = payload.get("story_entries")
    return entries if isinstance(entries, list) else []


def visible_output_present(payload: dict[str, Any]) -> bool:
    """True when canonical player-visible story output contains renderable text/data."""
    for block in _visible_blocks(payload):
        if _renderable_output_present(block):
            return True
    for entry in _story_entries(payload):
        if _renderable_output_present(entry):
            return True
    stream = payload.get("narrator_stream")
    if isinstance(stream, dict):
        events = stream.get("events")
        if isinstance(events, list) and any(_renderable_output_present(event) for event in events):
            return True
    return False


def _adapter_kind(payload: dict[str, Any]) -> str:
    raw_kind = str(payload.get("adapter_kind") or "").strip().lower()
    raw_adapter = str(payload.get("adapter_id") or payload.get("adapter") or "").strip().lower()
    raw_provider = str(payload.get("provider_id") or payload.get("provider") or "").strip().lower()
    joined = " ".join(part for part in (raw_kind, raw_adapter, raw_provider) if part)
    if any(marker in joined for marker in _MOCK_MARKERS):
        return "mock"
    if bool(payload.get("fallback_used")) or raw_kind == "fallback":
        return "fallback"
    if raw_kind in _REAL_ADAPTER_KINDS:
        return "real"
    return raw_kind or "unknown"


def _trace_observations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    trace = payload.get("trace") if isinstance(payload.get("trace"), dict) else {}
    observations = trace.get("observations")
    if isinstance(observations, list):
        return [item for item in observations if isinstance(item, dict)]
    observations = payload.get("observations")
    if isinstance(observations, list):
        return [item for item in observations if isinstance(item, dict)]
    return []


def real_generation_observation_present(payload: dict[str, Any]) -> bool:
    """True when diagnostics prove a real non-mock generation produced output."""
    for observation in _trace_observations(payload):
        obs_type = str(observation.get("type") or observation.get("as_type") or "").strip().lower()
        obs_name = str(observation.get("name") or "").strip().lower()
        if obs_type != "generation" and "generation" not in obs_name:
            continue

        adapter_kind = _adapter_kind(observation)
        provider_id = str(observation.get("provider_id") or observation.get("provider") or "").strip()
        model_id = str(observation.get("model_id") or observation.get("model") or "").strip()
        generated = bool(observation.get("generated_output_present")) or _text_present(observation.get("output"))
        if adapter_kind == "real" and provider_id and model_id and generated:
            return True
    return False


def _append_signal(signals: list[str], signal: str) -> None:
    if signal not in signals:
        signals.append(signal)


def evaluate_live_turn_success_gate(payload: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether a turn satisfies ADR-0033 live-success proof."""
    adapter_kind = _adapter_kind(payload)
    visible_present = visible_output_present(payload)
    real_generation_present = real_generation_observation_present(payload)
    generated_output_present = bool(payload.get("generated_output_present"))
    validation_approved = str(payload.get("validation_status") or "").strip().lower() == "approved"
    commit_applied = bool(payload.get("commit_applied"))
    invocation_ok = bool(payload.get("model_invocation_attempted")) and bool(payload.get("model_invocation_success"))
    runtime_profile_present = bool(str(payload.get("runtime_profile_id") or "").strip())
    signals: list[str] = []

    if not runtime_profile_present:
        _append_signal(signals, "missing_runtime_profile")
    if adapter_kind == "mock":
        _append_signal(signals, "mock_adapter")
    elif adapter_kind != "real":
        _append_signal(signals, "non_live_adapter")
    if bool(payload.get("fallback_used")) or adapter_kind == "fallback":
        _append_signal(signals, "fallback_used")
    if not invocation_ok:
        _append_signal(signals, "model_invocation_failed")
    if not generated_output_present:
        _append_signal(signals, "missing_generated_output")
    if not real_generation_present:
        _append_signal(signals, "missing_real_generation_observation")
    if not validation_approved:
        _append_signal(signals, "validation_not_approved")
    if not commit_applied:
        _append_signal(signals, "commit_not_applied")
    if not visible_present:
        _append_signal(signals, "empty_visible_output")

    live_success = not signals
    quality_class = "healthy" if live_success else "degraded"
    if not validation_approved or not commit_applied:
        quality_class = "failed"

    return {
        "live_success": live_success,
        "adapter_kind": adapter_kind,
        "fallback_used": bool(payload.get("fallback_used")),
        "model_invocation_attempted": bool(payload.get("model_invocation_attempted")),
        "model_invocation_success": bool(payload.get("model_invocation_success")),
        "generated_output_present": generated_output_present,
        "real_generation_observation_present": real_generation_present,
        "validation_status": str(payload.get("validation_status") or "").strip().lower() or None,
        "commit_applied": commit_applied,
        "visible_output_present": visible_present,
        "visible_output_count": len(_visible_blocks(payload)) + len(_story_entries(payload)),
        "quality_class": quality_class,
        "degradation_signals": signals,
    }


def evaluate_session_opening_readiness(
    *,
    story_entries: list[Any],
    visible_scene_output: dict[str, Any] | None,
    created: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return explicit player-readiness state for a session opening."""
    payload = {
        "story_entries": story_entries,
        "visible_scene_output": visible_scene_output or {},
    }
    if visible_output_present(payload):
        return {
            "runtime_session_ready": True,
            "can_execute": True,
            "opening_generation_status": "ready_with_opening",
            "opening_present": True,
        }

    created_payload = created if isinstance(created, dict) else {}
    opening_turn = (
        created_payload.get("opening_turn")
        if isinstance(created_payload.get("opening_turn"), dict)
        else {}
    )
    opening_status = str(
        opening_turn.get("opening_generation_status")
        or created_payload.get("opening_generation_status")
        or ""
    ).strip()
    if opening_status == "pending":
        status = "creating_opening"
    elif opening_status in {"failed", "failed_opening_generation"}:
        status = "failed_opening_generation"
    else:
        status = "blocked_missing_opening"

    return {
        "runtime_session_ready": False,
        "can_execute": False,
        "opening_generation_status": status,
        "opening_present": False,
    }
