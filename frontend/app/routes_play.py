"""Play / session shell routes (registered on ``frontend_bp``)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from flask import flash, g, jsonify, make_response, redirect, render_template, request, session, url_for

from . import player_backend
from .player_backend import BackendApiError
from .auth import require_login
from .frontend_blueprint import frontend_bp

PLAY_SHELL_RUNTIME_VIEWS_KEY = "play_shell_runtime_views"
PLAY_SHELL_TURN_LOG_KEY = "play_shell_turn_logs"
PLAY_SHELL_OPERATOR_KEY = "play_shell_operator_payloads"

TURN_LOG_MAX = 50
DIAGNOSTICS_MAX_ROWS = 40
OPERATOR_SESSION_JSON_MAX = 120_000

_QUALITY_CLASS_VALUES = {"healthy", "weak_but_legal", "degraded", "failed"}
_DEGRADED_QUALITY_CLASSES = {"degraded", "failed"}

# Flask session key: deep diagnostics strip for play shell (Phase B).
PLAY_SHELL_DIAGNOSTICS_SESSION_KEY = "play_shell_diagnostics_deep"

# Whitelist: only these logical dramatic-context keys may surface in the player shell.
# Values are taken from ``dramatic_context_summary`` (story-window shape) plus a few
# safe fallbacks from ``authority_summary`` — never raw nested blobs or tool payloads.
_DRAMATIC_CONTEXT_DISPLAY_SPECS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("scene_function", "Scene", ("scene_function", "selected_scene_function")),
    ("pacing_mode", "Pacing", ("pacing_mode",)),
    ("silence_mode", "Silence", ("silence_mode",)),
    ("retrieval_route", "Retrieval route", ("retrieval_route",)),
    ("retrieval_status", "Retrieval status", ("retrieval_status",)),
    ("thread_pressure_level", "Thread pressure", ("thread_pressure_level",)),
    ("social_continuity_status", "Social continuity", ("social_continuity_status",)),
    ("continuity_classes", "Continuity", ("continuity_classes",)),
    ("beat_id", "Beat", ("beat_id",)),
)


def _play_shell_diagnostics_deep_from_session() -> bool:
    return bool(session.get(PLAY_SHELL_DIAGNOSTICS_SESSION_KEY))


def _sync_play_shell_diagnostics_from_request() -> None:
    raw = (request.args.get("diagnostics") or "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        session[PLAY_SHELL_DIAGNOSTICS_SESSION_KEY] = True
    elif raw in {"0", "false", "no", "off"}:
        session[PLAY_SHELL_DIAGNOSTICS_SESSION_KEY] = False


def _textish(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (list, tuple)):
        parts = [_textish(v).strip() for v in value if _textish(v).strip()]
        return ", ".join(parts[:12])
    return str(value).strip()


def _dramatic_context_whitelist_value(
    logical_key: str,
    dramatic_context: dict[str, Any],
    authority_summary: dict[str, Any] | None,
) -> str:
    dc = dramatic_context
    auth = authority_summary if isinstance(authority_summary, dict) else {}
    if logical_key == "scene_function":
        return _textish(dc.get("scene_function") or dc.get("selected_scene_function"))
    if logical_key == "social_continuity_status":
        return _textish(dc.get("social_continuity_status") or auth.get("social_continuity_status"))
    if logical_key == "continuity_classes":
        return _textish(dc.get("continuity_classes"))
    if logical_key not in dc:
        return ""
    raw = dc.get(logical_key)
    if raw is None or raw == "" or raw == [] or raw == {}:
        return ""
    return _textish(raw)


def _build_display_dramatic_context_items(
    dramatic_context: dict[str, Any],
    authority_summary: dict[str, Any] | None,
) -> list[dict[str, str]]:
    """Bounded whitelist items for diagnostics (no recursive walk, no raw JSON dumps)."""
    dc = dramatic_context if isinstance(dramatic_context, dict) else {}
    items: list[dict[str, str]] = []
    for logical_key, label, _aliases in _DRAMATIC_CONTEXT_DISPLAY_SPECS:
        value = _dramatic_context_whitelist_value(logical_key, dc, authority_summary)
        if value:
            items.append({"key": logical_key, "label": label, "value": value})
    return items


def _build_display_dramatic_context_compact(items: list[dict[str, str]], *, max_len: int = 200) -> str:
    if not items:
        return ""
    parts = [f"{row['label']}: {row['value']}" for row in items]
    text = " · ".join(parts)
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _build_display_passivity_line(factors: list[str]) -> str:
    clean = [str(f).strip() for f in factors if str(f).strip()]
    if not clean:
        return ""
    return "Passivity: " + ", ".join(clean[:5])


def _build_display_vitality_line(vitality_summary: dict[str, Any]) -> str:
    if not vitality_summary:
        return ""
    bits: list[str] = []
    if vitality_summary.get("response_present"):
        bits.append("response")
    if vitality_summary.get("initiative_present"):
        bits.append("initiative")
    if vitality_summary.get("multi_actor_realized"):
        bits.append("multi-actor")
    if vitality_summary.get("sparse_input_recovery_applied"):
        bits.append("sparse-recovery")
    g = int(vitality_summary.get("rendered_spoken_line_count") or 0)
    a = int(vitality_summary.get("rendered_action_line_count") or 0)
    if g or a:
        bits.append(f"lines {g}s/{a}a")
    if not bits:
        return ""
    return "Vitality: " + ", ".join(bits)


def _build_display_actor_turn_line(entry: dict[str, Any]) -> str:
    ats = entry.get("actor_turn_summary")
    if not isinstance(ats, dict):
        return ""
    parts: list[str] = []
    lo = ats.get("last_actor_outcome_summary")
    if lo:
        parts.append(str(lo).strip())
    init = ats.get("initiative_summary") if isinstance(ats.get("initiative_summary"), dict) else {}
    ec = int(init.get("event_count") or 0) if init else 0
    if ec:
        parts.append(f"initiative_events={ec}")
    text = " · ".join(parts) if parts else ""
    return ("Turn outcome: " + text) if text else ""


def _format_reaction_order_divergence(div: Any) -> str:
    """Format reaction_order_divergence dict as bounded, readable message (never raw dict)."""
    if not isinstance(div, dict):
        return str(div).strip() if div else ""

    justification = div.get("justification")
    if justification and isinstance(justification, str) and justification.strip():
        return f"Divergence: {justification}"

    reason = div.get("reason", "")
    if reason:
        reason_display = reason.replace("_", " ").capitalize()
        return f"Order divergence: {reason_display}"

    return "Order divergence detected"


def _build_display_render_support_warning(entry: dict[str, Any], vitality: dict[str, Any]) -> str:
    """Player shell: only explicit warn strings (no generic render_support dump)."""
    messages: list[str] = []
    rs = entry.get("render_support")
    if isinstance(rs, dict):
        floor = rs.get("vitality_floor_warning")
        if floor:
            messages.append(str(floor).strip())
        div = rs.get("reaction_order_divergence")
        if div:
            messages.append(_format_reaction_order_divergence(div))
    div_v = vitality.get("reaction_order_divergence") if isinstance(vitality, dict) else None
    if div_v:
        formatted = _format_reaction_order_divergence(div_v)
        if formatted and formatted not in messages:
            messages.append(formatted)
    return " · ".join(messages) if messages else ""


def _runtime_entry_presentation_fields(
    entry: dict[str, Any],
    *,
    dramatic_context: dict[str, Any],
    vitality_summary: dict[str, Any],
    passivity_factors: list[str],
    role: str,
    diagnostics_deep: bool,
) -> dict[str, Any]:
    if role != "runtime":
        return {
            "display_passivity_line": "",
            "display_vitality_line": "",
            "display_actor_turn_line": "",
            "display_render_support_warning": "",
            "display_dramatic_context_compact": "",
            "display_dramatic_context_items": [],
        }
    auth = entry.get("authority_summary") if isinstance(entry.get("authority_summary"), dict) else {}
    vitality = _extract_entry_vitality(entry)
    items = _build_display_dramatic_context_items(dramatic_context, auth)
    compact = _build_display_dramatic_context_compact(items)
    return {
        "display_passivity_line": _build_display_passivity_line(passivity_factors),
        "display_vitality_line": _build_display_vitality_line(vitality_summary),
        "display_actor_turn_line": _build_display_actor_turn_line(entry),
        "display_render_support_warning": _build_display_render_support_warning(entry, vitality),
        "display_dramatic_context_compact": compact,
        "display_dramatic_context_items": list(items) if diagnostics_deep else [],
    }


def _coerce_shell_lines(value: Any) -> list[str]:
    if isinstance(value, str):
        line = value.strip()
        return [line] if line else []
    if not isinstance(value, list):
        return []
    lines: list[str] = []
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            speaker = str(item.get("speaker_id") or item.get("actor_id") or "").strip()
            tone = str(item.get("tone") or "").strip()
            prefix = f"{speaker}: " if speaker else ""
            suffix = f" ({tone})" if tone else ""
            lines.append(f"{prefix}{text}{suffix}".strip())
            continue
        line = str(item).strip()
        if line:
            lines.append(line)
    return lines


def _is_runtime_entry_degraded(entry: dict[str, Any]) -> tuple[bool, list[str], str]:
    authority = entry.get("authority_summary") if isinstance(entry.get("authority_summary"), dict) else {}
    governance = (
        entry.get("runtime_governance_surface")
        if isinstance(entry.get("runtime_governance_surface"), dict)
        else {}
    )
    quality = str(
        entry.get("quality_class")
        or governance.get("quality_class")
        or authority.get("quality_class")
        or ""
    ).strip().lower()
    if quality in _QUALITY_CLASS_VALUES:
        signals = entry.get("degradation_signals")
        if not isinstance(signals, list):
            signals = governance.get("degradation_signals")
        if not isinstance(signals, list):
            signals = authority.get("degradation_signals")
        reasons = [str(s).strip() for s in signals if str(s).strip()]
        return quality in _DEGRADED_QUALITY_CLASSES, reasons, quality

    reasons: list[str] = []
    validation_status = str(authority.get("validation_status") or "").strip().lower()
    if validation_status and validation_status != "approved":
        quality = "failed"

    fallback_stage = str(governance.get("fallback_stage_reached") or "").strip().lower()
    if fallback_stage and fallback_stage != "primary_only":
        reasons.append("fallback_used")

    if bool(governance.get("mock_output_flag")):
        reasons.append("fallback_used")

    failure_markers = entry.get("failure_markers")
    if isinstance(failure_markers, list) and failure_markers:
        reasons.append("non_factual_staging")

    if not quality:
        quality = "degraded" if reasons else "healthy"
    deduped_reasons: list[str] = []
    for reason in reasons:
        if reason not in deduped_reasons:
            deduped_reasons.append(reason)
    return quality in _DEGRADED_QUALITY_CLASSES, deduped_reasons, quality


def _extract_entry_vitality(entry: dict[str, Any]) -> dict[str, Any]:
    telemetry = entry.get("actor_survival_telemetry") if isinstance(entry.get("actor_survival_telemetry"), dict) else {}
    vitality = telemetry.get("vitality_telemetry_v1") if isinstance(telemetry.get("vitality_telemetry_v1"), dict) else {}
    if vitality:
        return vitality
    governance = entry.get("runtime_governance_surface") if isinstance(entry.get("runtime_governance_surface"), dict) else {}
    fallback = governance.get("vitality_telemetry_v1") if isinstance(governance.get("vitality_telemetry_v1"), dict) else {}
    return fallback


def _derive_row_passivity_factors(entry: dict[str, Any], vitality: dict[str, Any]) -> list[str]:
    factors = entry.get("why_turn_felt_passive") if isinstance(entry.get("why_turn_felt_passive"), list) else []
    if factors:
        return [str(f).strip() for f in factors if str(f).strip()]

    derived: list[str] = []
    if vitality.get("fallback_used"):
        derived.append("fallback_used")
    if vitality.get("thin_edge_applied") and vitality.get("withheld_applied"):
        derived.append("thin_edge_withheld")
    if not vitality.get("response_present"):
        derived.append("no_visible_actor_response")
    if (vitality.get("selected_secondary_responder_ids") or []) and not vitality.get("multi_actor_realized"):
        derived.append("single_actor_only")
    if vitality.get("quality_class") == "weak_but_legal":
        derived.append("weak_signal_accepted")
    if vitality.get("sparse_input_detected") and not vitality.get("sparse_input_recovery_applied"):
        derived.append("sparse_input_not_recovered")

    deduped: list[str] = []
    for factor in derived:
        if factor not in deduped:
            deduped.append(factor)
    return deduped


def _extract_passivity_diagnosis(entry: dict[str, Any]) -> dict[str, Any]:
    telemetry = entry.get("actor_survival_telemetry") if isinstance(entry.get("actor_survival_telemetry"), dict) else {}
    diagnosis = telemetry.get("passivity_diagnosis_v1")
    if isinstance(diagnosis, dict):
        return diagnosis
    fallback = telemetry.get("operator_diagnostic_hints")
    return fallback if isinstance(fallback, dict) else {}


def _compute_rising_degraded_posture(story_entries: list[dict[str, Any]]) -> bool:
    runtime_entries = [
        row
        for row in story_entries
        if isinstance(row, dict) and str(row.get("role") or "").strip() == "runtime"
    ]
    flags = [
        1 if str(row.get("quality_class") or "").strip().lower() in _DEGRADED_QUALITY_CLASSES else 0
        for row in runtime_entries
    ]
    if len(flags) < 6:
        return False
    tail = flags[-5:]
    prior = flags[:-5]
    if not prior:
        return False
    return (sum(tail) / len(tail)) > (sum(prior) / len(prior))


def _normalize_story_entries_for_shell(
    story_entries: list[dict[str, Any]],
    *,
    shell_state_view: dict[str, Any] | None = None,
    diagnostics_deep: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(story_entries, list):
        return []
    shell = shell_state_view if isinstance(shell_state_view, dict) else {}
    player_shell_context = (
        shell.get("player_shell_context")
        if isinstance(shell.get("player_shell_context"), dict)
        else {}
    )
    default_responder_id = str(player_shell_context.get("responder_id") or "").strip() or None
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(story_entries):
        if not isinstance(item, dict):
            continue
        entry = dict(item)
        role = str(entry.get("role") or "runtime").strip() or "runtime"
        spoken_lines = _coerce_shell_lines(entry.get("spoken_lines"))
        action_lines = _coerce_shell_lines(entry.get("action_lines"))
        committed_consequences = _coerce_shell_lines(entry.get("committed_consequences"))
        dramatic_context = (
            entry.get("dramatic_context_summary")
            if isinstance(entry.get("dramatic_context_summary"), dict)
            else {}
        )
        responder_id = str(
            entry.get("responder_id")
            or dramatic_context.get("responder_id")
            or default_responder_id
            or ""
        ).strip() or None
        validation_status = str(
            entry.get("validation_status")
            or (
                entry.get("authority_summary", {}).get("validation_status")
                if isinstance(entry.get("authority_summary"), dict)
                else ""
            )
            or ""
        ).strip() or None
        degraded, degraded_reasons, quality_class = _is_runtime_entry_degraded(entry) if role == "runtime" else (False, [], "healthy")
        vitality = _extract_entry_vitality(entry) if role == "runtime" else {}
        diagnosis = _extract_passivity_diagnosis(entry) if role == "runtime" else {}
        passivity_factors = (
            [str(f).strip() for f in (diagnosis.get("why_turn_felt_passive") or []) if str(f).strip()]
            if role == "runtime"
            else []
        )
        if role == "runtime" and not passivity_factors:
            passivity_factors = _derive_row_passivity_factors(entry, vitality)
        vitality_summary = {
            "response_present": bool(vitality.get("response_present")),
            "initiative_present": bool(vitality.get("initiative_present")),
            "multi_actor_realized": bool(vitality.get("multi_actor_realized")),
            "sparse_input_recovery_applied": bool(vitality.get("sparse_input_recovery_applied")),
            "selected_primary_responder_id": vitality.get("selected_primary_responder_id"),
            "realized_actor_ids": list(vitality.get("realized_actor_ids") or []),
            "realized_secondary_responder_ids": list(vitality.get("realized_secondary_responder_ids") or []),
            "rendered_actor_ids": list(vitality.get("rendered_actor_ids") or []),
            "preferred_reaction_order_ids": list(vitality.get("preferred_reaction_order_ids") or []),
            "reaction_order_divergence": vitality.get("reaction_order_divergence"),
            "generated_spoken_line_count": int(vitality.get("generated_spoken_line_count") or 0),
            "validated_spoken_line_count": int(vitality.get("validated_spoken_line_count") or 0),
            "rendered_spoken_line_count": int(vitality.get("rendered_spoken_line_count") or 0),
            "generated_action_line_count": int(vitality.get("generated_action_line_count") or 0),
            "validated_action_line_count": int(vitality.get("validated_action_line_count") or 0),
            "rendered_action_line_count": int(vitality.get("rendered_action_line_count") or 0),
        }
        presentation = _runtime_entry_presentation_fields(
            entry,
            dramatic_context=dramatic_context,
            vitality_summary=vitality_summary,
            passivity_factors=passivity_factors,
            role=role,
            diagnostics_deep=diagnostics_deep,
        )
        normalized.append(
            {
                **entry,
                "entry_id": entry.get("entry_id") or f"entry-{idx}",
                "role": role,
                "speaker": entry.get("speaker") or ("You" if role == "player" else "World of Shadows"),
                "text": str(entry.get("text") or "").strip(),
                "spoken_lines": spoken_lines,
                "action_lines": action_lines,
                "committed_consequences": committed_consequences,
                "responder_id": responder_id,
                "validation_status": validation_status,
                "quality_class": quality_class,
                "degradation_signals": degraded_reasons,
                "degradation_summary": str(entry.get("degradation_summary") or "").strip() or (", ".join(degraded_reasons) if degraded_reasons else "none"),
                "degraded": degraded,
                "degraded_reasons": degraded_reasons,
                "vitality_schema_version": vitality.get("schema_version"),
                "passivity_schema_version": diagnosis.get("schema_version"),
                "vitality_summary": vitality_summary,
                "why_turn_felt_passive": passivity_factors,
                "primary_passivity_factors": passivity_factors[:3],
                **presentation,
            }
        )
    return normalized


def _runtime_status_view_from_story_entries(
    story_entries: list[dict[str, Any]],
    *,
    shell_state_view: dict[str, Any] | None = None,
) -> dict[str, Any]:
    shell = shell_state_view if isinstance(shell_state_view, dict) else {}
    player_shell_context = (
        shell.get("player_shell_context")
        if isinstance(shell.get("player_shell_context"), dict)
        else {}
    )
    runtime_entries = [
        entry
        for entry in story_entries
        if isinstance(entry, dict) and str(entry.get("role") or "").strip() == "runtime"
    ]
    latest_runtime = runtime_entries[-1] if runtime_entries else None

    if not isinstance(latest_runtime, dict):
        return {
            "contract": "play_shell_runtime_status.v1",
            "selected_responder_id": player_shell_context.get("responder_id"),
            "validation_status": None,
            "quality_class": "healthy",
            "degradation_signals": [],
            "aggregated_degradation_signals": [],
            "rising_degraded_posture": False,
            "degraded": False,
            "degraded_reasons": [],
            "degradation_summary": "none",
            "latest_turn_number": None,
            "latest_vitality_summary": {},
            "latest_why_turn_felt_passive": [],
            "latest_display_passivity_line": "",
            "latest_display_vitality_line": "",
        }

    aggregated_signals: list[str] = []
    for entry in runtime_entries:
        for signal in (entry.get("degradation_signals") or []):
            cleaned = str(signal).strip()
            if cleaned and cleaned not in aggregated_signals:
                aggregated_signals.append(cleaned)

    return {
        "contract": "play_shell_runtime_status.v1",
        "selected_responder_id": latest_runtime.get("responder_id") or player_shell_context.get("responder_id"),
        "validation_status": latest_runtime.get("validation_status"),
        "quality_class": latest_runtime.get("quality_class") or "healthy",
        "degradation_signals": list(latest_runtime.get("degradation_signals") or []),
        "aggregated_degradation_signals": aggregated_signals,
        "rising_degraded_posture": _compute_rising_degraded_posture(runtime_entries),
        "degraded": bool(latest_runtime.get("degraded")),
        "degraded_reasons": list(latest_runtime.get("degraded_reasons") or []),
        "degradation_summary": str(latest_runtime.get("degradation_summary") or "").strip() or "none",
        "latest_turn_number": latest_runtime.get("turn_number"),
        "latest_vitality_summary": latest_runtime.get("vitality_summary") if isinstance(latest_runtime.get("vitality_summary"), dict) else {},
        "latest_why_turn_felt_passive": list(latest_runtime.get("why_turn_felt_passive") or []),
        "latest_display_passivity_line": str(latest_runtime.get("display_passivity_line") or "").strip(),
        "latest_display_vitality_line": str(latest_runtime.get("display_vitality_line") or "").strip(),
    }


def _load_template_mapping() -> dict[str, str]:
    """Load template ID to content module ID mapping from config file.

    Falls back to default mapping if config file is not found or yaml unavailable.
    """
    if HAS_YAML:
        config_path = Path(__file__).resolve().parent.parent / "config" / "template_module_mapping.yaml"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                    return data.get("templates", {})
            except Exception:
                pass
    # Fallback to inline mapping if config not found or yaml not available
    return {
        "god_of_carnage_solo": "god_of_carnage",
    }


_PLAY_TEMPLATE_TO_CONTENT_MODULE_ID = _load_template_mapping()


def play_template_to_content_module_id(template_id: str) -> str:
    """Map play launcher template id to backend content module directory id.

    Uses mapping from frontend/config/template_module_mapping.yaml.
    Falls back to using template_id as module_id if no mapping found.
    """
    tid = (template_id or "").strip()
    return _PLAY_TEMPLATE_TO_CONTENT_MODULE_ID.get(tid, tid)


def _build_play_shell_opening_view(
    opening_turn: dict[str, Any],
    *,
    opening_meta: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Project Turn 0 opening envelope (world-engine session create) into play-shell rows."""
    meta = opening_meta if isinstance(opening_meta, dict) else {}
    nc = opening_turn.get("narrative_commit") if isinstance(opening_turn.get("narrative_commit"), dict) else {}
    consequences = nc.get("committed_consequences")
    cons_list: list[str] = []
    if isinstance(consequences, list):
        cons_list = [str(x) for x in consequences[:12]]
    synthetic: dict[str, Any] = {
        "current_scene_id": meta.get("current_scene_id"),
        "turn_counter": meta.get("turn_counter"),
        "committed_state": {
            "last_narrative_commit": nc,
            "last_narrative_commit_summary": nc,
            "last_committed_consequences": cons_list,
        },
    }
    return _build_play_shell_runtime_view(
        {
            "trace_id": trace_id or opening_turn.get("trace_id"),
            "turn": opening_turn,
            "state": synthetic,
        }
    )


def _build_play_shell_runtime_view(api_payload: dict[str, Any]) -> dict[str, Any]:
    """Project world-engine bridge JSON into a compact, player-facing last-turn view.

    WARNING: Session audit log function only. Not the canonical player render path.
    Called only by _build_play_shell_opening_view (opening turn) and _persist_turn_success
    (orphaned audit logger). Do not use for live route responses.

    PHASE 2: Validates that world-engine turn response contains canonical contract fields
    before projecting to player view.
    """
    turn = api_payload.get("turn") if isinstance(api_payload.get("turn"), dict) else {}
    st = api_payload.get("state") if isinstance(api_payload.get("state"), dict) else {}

    # PHASE 2 VALIDATION: Check for critical fields from canonical contract
    critical_fields = ["visible_output_bundle", "validation_outcome", "narrative_commit"]
    missing = [f for f in critical_fields if f not in turn]
    if missing:
        import sys
        print(
            f"[WARN] World-engine turn missing critical fields for player view: {', '.join(missing)}",
            file=sys.stderr,
        )

    bundle = turn.get("visible_output_bundle") if isinstance(turn.get("visible_output_bundle"), dict) else {}
    gm = bundle.get("gm_narration")
    lines: list[str] = []
    if isinstance(gm, list):
        lines = [str(x).strip() for x in gm if str(x).strip()]
    narration_text = "\n\n".join(lines)
    spoken = bundle.get("spoken_lines")
    spoken_lines: list[str] = []
    if isinstance(spoken, list):
        spoken_lines = [str(x).strip() for x in spoken if str(x).strip()]

    committed = st.get("committed_state") if isinstance(st.get("committed_state"), dict) else {}
    summary = (
        committed.get("last_narrative_commit_summary")
        if isinstance(committed.get("last_narrative_commit_summary"), dict)
        else {}
    )
    consequences = committed.get("last_committed_consequences")
    cons_list: list[str] = []
    if isinstance(consequences, list):
        cons_list = [str(x) for x in consequences[:12]]

    val = turn.get("validation_outcome") if isinstance(turn.get("validation_outcome"), dict) else {}
    val_status = str(val.get("status") or "").strip() or None

    graph = turn.get("graph") if isinstance(turn.get("graph"), dict) else {}
    errs = graph.get("errors")
    err_count = len(errs) if isinstance(errs, list) else 0

    interp = turn.get("interpreted_input") if isinstance(turn.get("interpreted_input"), dict) else {}
    input_kind = str(interp.get("kind") or "").strip() or "unknown"
    if str(turn.get("turn_kind") or "").strip() == "opening":
        input_kind = "opening"

    nc = committed.get("last_narrative_commit") if isinstance(committed.get("last_narrative_commit"), dict) else {}
    if not nc:
        nc = turn.get("narrative_commit") if isinstance(turn.get("narrative_commit"), dict) else {}

    player_line = str(turn.get("raw_input") or "").strip()
    if str(turn.get("turn_kind") or "").strip() == "opening":
        player_line = ""

    include_runtime_audit_fields = "turn_counter" in st

    view = {
        "turn_number": turn.get("turn_number"),
        "player_line": player_line,
        "interpreted_input_kind": input_kind,
        "narration_text": narration_text,
        "spoken_lines": spoken_lines,
        "committed_consequences": cons_list,
    }
    if include_runtime_audit_fields:
        view.update(
            {
                "validation_status": val_status,
                "graph_error_count": err_count,
                "committed_scene_id": nc.get("committed_scene_id"),
                "current_scene_id": st.get("current_scene_id"),
                "turn_counter": st.get("turn_counter"),
            }
        )
    return view


def _truncate_operator_payload(payload: dict[str, Any]) -> dict[str, Any]:
    turn = payload.get("turn") if isinstance(payload.get("turn"), dict) else {}
    st = payload.get("state") if isinstance(payload.get("state"), dict) else {}
    diag = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    out: dict[str, Any] = {
        "session_id": payload.get("session_id"),
        "trace_id": payload.get("trace_id"),
        "world_engine_story_session_id": payload.get("world_engine_story_session_id"),
        "turn": turn,
        "state": st,
        "diagnostics": dict(diag),
        "backend_interpretation_preview": payload.get("backend_interpretation_preview"),
        "warnings": payload.get("warnings"),
    }
    d_inner = out["diagnostics"]
    rows = d_inner.get("diagnostics")
    if isinstance(rows, list) and len(rows) > DIAGNOSTICS_MAX_ROWS:
        d_inner = {
            **d_inner,
            "diagnostics": rows[-DIAGNOSTICS_MAX_ROWS:],
            "_truncated_row_count": len(rows),
        }
        out["diagnostics"] = d_inner
    raw = json.dumps(out, default=str)
    if len(raw) > OPERATOR_SESSION_JSON_MAX:
        out["diagnostics"] = {"_truncated": True, "note": "Full payload too large for play session storage"}
        out["state"] = {"_truncated": True}
    return out


def _append_turn_log(run_id: str, view: dict[str, Any]) -> None:
    logs = session.get(PLAY_SHELL_TURN_LOG_KEY)
    if not isinstance(logs, dict):
        logs = {}
    lst = list(logs.get(run_id) or [])
    lst.append(view)
    if len(lst) > TURN_LOG_MAX:
        lst = lst[-TURN_LOG_MAX:]
    logs[run_id] = lst
    session[PLAY_SHELL_TURN_LOG_KEY] = logs


def _persist_turn_success(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    opening_turn = payload.get("opening_turn")
    opening_meta = payload.get("world_engine_opening_meta")
    trace_id = str(payload.get("trace_id") or "").strip() or None
    if isinstance(opening_turn, dict):
        opening_view = _build_play_shell_opening_view(
            opening_turn,
            opening_meta=opening_meta if isinstance(opening_meta, dict) else None,
            trace_id=trace_id,
        )
        _append_turn_log(run_id, opening_view)
    view = _build_play_shell_runtime_view(payload)
    views = session.get(PLAY_SHELL_RUNTIME_VIEWS_KEY)
    if not isinstance(views, dict):
        views = {}
    views[run_id] = view
    session[PLAY_SHELL_RUNTIME_VIEWS_KEY] = views
    _append_turn_log(run_id, view)
    op = session.get(PLAY_SHELL_OPERATOR_KEY)
    if not isinstance(op, dict):
        op = {}
    truncated = _truncate_operator_payload(payload)
    op[run_id] = truncated
    session[PLAY_SHELL_OPERATOR_KEY] = op
    session.modified = True
    return {"runtime_view": view, "operator_bundle": truncated}


def _ensure_turn_log_from_legacy(run_id: str, runtime_view: dict[str, Any] | None) -> list[dict[str, Any]]:
    logs = session.get(PLAY_SHELL_TURN_LOG_KEY)
    if not isinstance(logs, dict):
        logs = {}
    lst = logs.get(run_id)
    if isinstance(lst, list) and lst:
        return lst
    if runtime_view:
        logs[run_id] = [runtime_view]
        session[PLAY_SHELL_TURN_LOG_KEY] = logs
        session.modified = True
        return [runtime_view]
    return []


def _wants_json_response() -> bool:
    if request.is_json:
        return True
    return request.accept_mimetypes.best_match(["application/json", "text/html"]) == "application/json"


def _player_input_from_request() -> str:
    if request.is_json:
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return (data.get("player_input") or "").strip()
        return ""
    return (request.form.get("player_input") or "").strip()


def _run_backend_turn(run_id: str, player_input: str) -> tuple[dict[str, Any] | None, str | None]:
    text = player_input.strip()
    if not text:
        return None, "Please describe your turn in natural language (or use an explicit command)."
    response = player_backend.request_backend(
        "POST",
        f"/api/v1/game/player-sessions/{run_id}/turns",
        json_data={"player_input": text},
    )
    try:
        pl = player_backend.require_success(response, "Runtime turn execution failed.")
    except BackendApiError as exc:
        return None, str(exc)
    if isinstance(pl, dict):
        return pl, None
    return None, "Runtime turn execution returned an invalid response."


@frontend_bp.route("/play")
@require_login
def play_start():
    response = player_backend.request_backend("GET", "/api/v1/game/bootstrap")
    bootstrap = response.json() if response.ok else {}
    return render_template("session_start.html", bootstrap=bootstrap)


_PROFILE_ONLY_TEMPLATES = {"god_of_carnage_solo"}
_GOC_VALID_ROLES = {"annette", "alain"}


@frontend_bp.route("/play/start", methods=["POST"])
@require_login
def play_create():
    from uuid import uuid4

    template_id = (request.form.get("template_id") or "").strip()
    if not template_id:
        flash("Please select a template.", "error")
        return redirect(url_for("frontend.play_start"))

    trace_id = g.get("trace_id") or uuid4().hex

    # FIX-005: god_of_carnage_solo requires runtime_profile_id + selected_player_role.
    if template_id in _PROFILE_ONLY_TEMPLATES:
        selected_player_role = (request.form.get("selected_player_role") or "").strip()
        if not selected_player_role:
            flash("Please choose a character (Annette or Alain) to start God of Carnage.", "error")
            return redirect(url_for("frontend.play_start"))
        if selected_player_role not in _GOC_VALID_ROLES:
            flash(f"Invalid character selection: {selected_player_role!r}. Choose Annette or Alain.", "error")
            return redirect(url_for("frontend.play_start"))
        json_data = {
            "runtime_profile_id": template_id,
            "selected_player_role": selected_player_role,
            "trace_id": trace_id,
        }
    else:
        json_data = {"template_id": template_id, "trace_id": trace_id}

    session_output_language = (request.form.get("session_output_language") or "de").strip()
    json_data["session_output_language"] = session_output_language

    response = player_backend.request_backend(
        "POST",
        "/api/v1/game/player-sessions",
        json_data=json_data,
    )
    try:
        payload = player_backend.require_success(response, "Could not create play run.")
    except BackendApiError as exc:
        # Extract error details from exception
        error_code = exc.payload.get("error_code") if isinstance(exc.payload, dict) else None
        backend_url = exc.payload.get("backend_url") if isinstance(exc.payload, dict) else None
        error_code = error_code or str(exc).split(":")[0][:50] if str(exc) else "UNKNOWN"
        error_detail = str(exc)[:200] if str(exc) else "Unknown error"

        # Check if this is a JSON request
        if _wants_json_response():
            response_data = {
                "error": "Could not start game session",
                "error_code": error_code,
                "error_detail": error_detail,
                "debug_id": trace_id,
            }
            if backend_url:
                response_data["backend_url"] = backend_url
            return jsonify(response_data), 400

        # For HTML requests, show error code and debug ID in flash message
        error_msg = f"Could not start game session.\nError code: {error_code}\nDebug ID: {trace_id}"
        if backend_url:
            error_msg += f"\nBackend URL: {backend_url}"
        flash(error_msg, "error")
        return redirect(url_for("frontend.play_start"))
    run_id = payload.get("run_id") or payload.get("run", {}).get("id")
    if not run_id:
        flash("Player session creation returned no run id.", "error")
        return redirect(url_for("frontend.play_start"))
    return redirect(url_for("frontend.play_shell", session_id=run_id))


@frontend_bp.route("/play/<session_id>")
@require_login
def play_shell(session_id: str):
    cookie_key = f"wos_backend_session_{session_id}"
    backend_sessions = session.get("play_shell_backend_sessions")
    if not isinstance(backend_sessions, dict):
        backend_sessions = {}

    response = player_backend.request_backend("GET", f"/api/v1/game/player-sessions/{session_id}")
    payload: dict[str, Any] = {}
    if response.ok:
        raw = response.json()
        payload = raw if isinstance(raw, dict) else {}
    else:
        error_payload = response.json() if response.content else {}
        flash(error_payload.get("error", "Could not resume player session."), "error")

    _sync_play_shell_diagnostics_from_request()
    diagnostics_deep = _play_shell_diagnostics_deep_from_session()
    payload_backend_session_id = str(
        payload.get("runtime_session_id") or payload.get("session_id") or ""
    ).strip()
    backend_session_id = (
        (request.cookies.get(cookie_key) or "").strip()
        or str(backend_sessions.get(session_id) or "").strip()
        or payload_backend_session_id
    )
    if backend_session_id:
        backend_sessions[session_id] = backend_session_id
        session["play_shell_backend_sessions"] = backend_sessions
        session.modified = True

    raw_story_entries = payload.get("story_entries") if isinstance(payload.get("story_entries"), list) else []
    shell_state_view = payload.get("shell_state_view") if isinstance(payload.get("shell_state_view"), dict) else {}
    story_entries = _normalize_story_entries_for_shell(
        raw_story_entries,
        shell_state_view=shell_state_view,
        diagnostics_deep=diagnostics_deep,
    )
    runtime_status_view = _runtime_status_view_from_story_entries(
        story_entries,
        shell_state_view=shell_state_view,
    )
    play_bootstrap_json = json.dumps(
        {
            "contract": payload.get("contract"),
            "run_id": session_id,
            "runtime_session_id": payload.get("runtime_session_id") or backend_session_id,
            "backend_session_id": backend_session_id or None,
            "narrator_streaming": payload.get("narrator_streaming") if isinstance(payload.get("narrator_streaming"), dict) else None,
            "visible_scene_output": payload.get("visible_scene_output") if isinstance(payload.get("visible_scene_output"), dict) else None,
            "story_entries": story_entries,
            "shell_state_view": shell_state_view,
            "runtime_status_view": runtime_status_view,
            "show_play_diagnostics": diagnostics_deep,
        }
    )
    response_obj = make_response(
        render_template(
            "session_shell.html",
            session_id=session_id,
            runtime_session_id=payload.get("runtime_session_id") or backend_session_id,
            runtime_session_ready=bool(payload.get("runtime_session_ready")),
            can_execute=bool(payload.get("can_execute")),
            story_entries=story_entries,
            shell_state_view=shell_state_view,
            runtime_status_view=runtime_status_view,
            governance=payload.get("governance") if isinstance(payload.get("governance"), dict) else {},
            play_bootstrap_json=play_bootstrap_json,
            show_play_diagnostics=diagnostics_deep,
        )
    )
    if backend_session_id:
        response_obj.set_cookie(
            cookie_key,
            backend_session_id,
            max_age=7 * 24 * 60 * 60,
            secure=True,
            httponly=True,
            samesite="Strict",
        )
    response_obj.template = "session_shell.html"
    return response_obj


@frontend_bp.route("/play/<session_id>/execute", methods=["POST"])
@require_login
def play_execute(session_id: str):
    wants_json = _wants_json_response()
    player_input = _player_input_from_request()
    payload, err = _run_backend_turn(session_id, player_input)
    if err:
        if wants_json:
            return jsonify({"ok": False, "error": err}), 400
        flash(err, "error")
        return redirect(url_for("frontend.play_shell", session_id=session_id))
    assert payload is not None
    _sync_play_shell_diagnostics_from_request()
    diagnostics_deep = _play_shell_diagnostics_deep_from_session()

    interpreted = (((payload.get("turn") or {}).get("interpreted_input") or {}).get("kind") or "unknown").strip()
    shell_state_view = payload.get("shell_state_view") if isinstance(payload.get("shell_state_view"), dict) else {}
    raw_story_entries = payload.get("story_entries") if isinstance(payload.get("story_entries"), list) else []
    story_entries = _normalize_story_entries_for_shell(
        raw_story_entries,
        shell_state_view=shell_state_view,
        diagnostics_deep=diagnostics_deep,
    )
    runtime_status_view = _runtime_status_view_from_story_entries(
        story_entries,
        shell_state_view=shell_state_view,
    )
    if wants_json:
        return jsonify(
            {
                "ok": True,
                "interpreted_input_kind": interpreted,
                "narrator_streaming": payload.get("narrator_streaming") if isinstance(payload.get("narrator_streaming"), dict) else None,
                "visible_scene_output": payload.get("visible_scene_output") if isinstance(payload.get("visible_scene_output"), dict) else None,
                "story_entries": story_entries,
                "story_window": payload.get("story_window") if isinstance(payload.get("story_window"), dict) else {},
                "shell_state_view": shell_state_view,
                "runtime_status_view": runtime_status_view,
                "show_play_diagnostics": diagnostics_deep,
            }
        ), 200
    play_bootstrap_json = json.dumps(
        {
            "contract": payload.get("contract"),
            "run_id": session_id,
            "runtime_session_id": payload.get("runtime_session_id"),
            "narrator_streaming": payload.get("narrator_streaming") if isinstance(payload.get("narrator_streaming"), dict) else None,
            "visible_scene_output": payload.get("visible_scene_output") if isinstance(payload.get("visible_scene_output"), dict) else None,
            "story_entries": story_entries,
            "shell_state_view": shell_state_view,
            "runtime_status_view": runtime_status_view,
            "show_play_diagnostics": diagnostics_deep,
        }
    )
    return render_template(
        "session_shell.html",
        session_id=session_id,
        runtime_session_id=payload.get("runtime_session_id"),
        runtime_session_ready=bool(payload.get("runtime_session_ready")),
        can_execute=bool(payload.get("can_execute")),
        story_entries=story_entries,
        shell_state_view=shell_state_view,
        runtime_status_view=runtime_status_view,
        governance=payload.get("governance") if isinstance(payload.get("governance"), dict) else {},
        play_bootstrap_json=play_bootstrap_json,
        show_play_diagnostics=diagnostics_deep,
    )
