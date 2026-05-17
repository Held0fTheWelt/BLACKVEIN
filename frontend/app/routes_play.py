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

import requests as _requests

from flask import Response, current_app, flash, g, jsonify, make_response, redirect, render_template, request, session, stream_with_context, url_for

from . import player_backend
from .player_backend import BackendApiError
from .auth import require_login
from .frontend_blueprint import frontend_bp

# Session keys that must be removed from the Flask session cookie.
# Includes the three orphaned audit-logger keys (removed) and play_shell_backend_sessions,
# which accumulated one unbounded entry per play session created and blows the 4KB limit.
# The per-run response cookie (wos_backend_session_{run_id}) is the canonical store instead.
_LEGACY_LARGE_SESSION_KEYS = (
    "play_shell_runtime_views",
    "play_shell_turn_logs",
    "play_shell_operator_payloads",
    "play_shell_backend_sessions",
)

_QUALITY_CLASS_VALUES = {"healthy", "weak_but_legal", "degraded", "failed"}
_DEGRADED_QUALITY_CLASSES = {"degraded", "failed"}


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
    vitality_summary: dict[str, Any],
    passivity_factors: list[str],
    role: str,
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
    vitality = _extract_entry_vitality(entry)
    return {
        "display_passivity_line": _build_display_passivity_line(passivity_factors),
        "display_vitality_line": _build_display_vitality_line(vitality_summary),
        "display_actor_turn_line": _build_display_actor_turn_line(entry),
        "display_render_support_warning": _build_display_render_support_warning(entry, vitality),
        "display_dramatic_context_compact": "",
        "display_dramatic_context_items": [],
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


def _normalize_story_entries_for_shell(
    story_entries: list[dict[str, Any]],
    *,
    shell_state_view: dict[str, Any] | None = None,
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
            vitality_summary=vitality_summary,
            passivity_factors=passivity_factors,
            role=role,
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


def _visible_scene_output_for_typewriter(
    payload: dict[str, Any],
    *,
    story_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_vso = payload.get("visible_scene_output") if isinstance(payload.get("visible_scene_output"), dict) else None
    if isinstance(raw_vso, dict) and isinstance(raw_vso.get("blocks"), list) and raw_vso.get("blocks"):
        return raw_vso

    blocks: list[dict[str, Any]] = []
    for idx, entry in enumerate(story_entries):
        if not isinstance(entry, dict):
            continue
        lines = [str(entry.get("text") or "").strip()]
        lines.extend(str(x).strip() for x in (entry.get("spoken_lines") or []) if str(x).strip())
        lines.extend(str(x).strip() for x in (entry.get("action_lines") or []) if str(x).strip())
        lines.extend(str(x).strip() for x in (entry.get("committed_consequences") or []) if str(x).strip())
        text = "\n".join(line for line in lines if line).strip()
        if not text:
            continue
        role = str(entry.get("role") or "").strip()
        block_type = "player_input" if role == "player" else "narrator"
        blocks.append(
            {
                "id": str(entry.get("entry_id") or f"story-entry-{idx}"),
                "block_type": block_type,
                "text": text,
                "player_display_text": text,
                "speaker_label": entry.get("speaker") or ("You" if role == "player" else "World of Shadows"),
                "card_style": "player_lane" if role == "player" else "narrative_story",
            }
        )
    if blocks:
        return {
            "blocks": blocks,
            "typewriter_slice_start_index": max(0, len(blocks) - 1),
            "source": "frontend_story_entries_typewriter_projection",
        }

    liveness_text = "\n".join(
        [
            "Typewriter-Test: Die Session-Shell lebt.",
            "Der neue Runtime-Pfad ist verbunden.",
            "Noch keine Erzaehlung generiert; dies ist nur ein UI-Lebenszeichen.",
        ]
    )
    return {
        "blocks": [
            {
                "id": "typewriter-ui-liveness-probe",
                "block_type": "narrator",
                "text": liveness_text,
                "player_display_text": liveness_text,
                "speaker_label": "World of Shadows",
                "card_style": "narrative_story",
                "narration_beat": "role_anchor",
            }
        ],
        "typewriter_slice_start_index": 0,
        "source": "typewriter_ui_liveness_probe",
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


def _evict_legacy_large_session_keys() -> None:
    """Pop oversized audit keys left by the old session-storage layer from existing cookies."""
    changed = False
    for k in _LEGACY_LARGE_SESSION_KEYS:
        if k in session:
            session.pop(k)
            changed = True
    if changed:
        session.modified = True


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
            status_code = exc.status_code if 400 <= int(exc.status_code or 0) <= 599 else 502
            response_data = {
                "error": "Could not start game session",
                "error_code": error_code,
                "error_detail": error_detail,
                "debug_id": trace_id,
                "backend_status_code": exc.status_code,
            }
            if backend_url:
                response_data["backend_url"] = backend_url
            return jsonify(response_data), status_code

        # For HTML requests, show error code and debug ID in flash message
        error_msg = (
            f"Could not start game session.\n"
            f"Status: {exc.status_code}\n"
            f"Error code: {error_code}\n"
            f"Detail: {error_detail}\n"
            f"Debug ID: {trace_id}"
        )
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
    _evict_legacy_large_session_keys()
    cookie_key = f"wos_backend_session_{session_id}"

    response = player_backend.request_backend("GET", f"/api/v1/game/player-sessions/{session_id}")
    payload: dict[str, Any] = {}
    if response.ok:
        raw = response.json()
        payload = raw if isinstance(raw, dict) else {}
    else:
        error_payload = response.json() if response.content else {}
        flash(error_payload.get("error", "Could not resume player session."), "error")

    payload_backend_session_id = str(
        payload.get("runtime_session_id") or payload.get("session_id") or ""
    ).strip()
    # Resolve backend_session_id from per-run response cookie (primary) or backend payload.
    # play_shell_backend_sessions is evicted above; the per-run cookie is the canonical store.
    backend_session_id = (
        (request.cookies.get(cookie_key) or "").strip()
        or payload_backend_session_id
    )

    raw_story_entries = payload.get("story_entries") if isinstance(payload.get("story_entries"), list) else []
    shell_state_view = payload.get("shell_state_view") if isinstance(payload.get("shell_state_view"), dict) else {}
    story_entries = _normalize_story_entries_for_shell(
        raw_story_entries,
        shell_state_view=shell_state_view,
    )
    visible_scene_output = _visible_scene_output_for_typewriter(
        payload,
        story_entries=story_entries,
    )
    play_bootstrap_json = json.dumps(
        {
            "contract": payload.get("contract"),
            "run_id": session_id,
            "template_id": payload.get("template_id"),
            "module_id": payload.get("module_id"),
            "runtime_session_id": payload.get("runtime_session_id") or backend_session_id,
            "backend_session_id": backend_session_id or None,
            "runtime_session_ready": bool(payload.get("runtime_session_ready")),
            "can_execute": bool(payload.get("can_execute")),
            "opening_generation_status": payload.get("opening_generation_status"),
            "session_loop": payload.get("session_loop") if isinstance(payload.get("session_loop"), dict) else None,
            "shell_state_view": shell_state_view,
            "narrator_streaming": payload.get("narrator_streaming") if isinstance(payload.get("narrator_streaming"), dict) else None,
            "visible_scene_output": visible_scene_output,
            "story_entries": story_entries,
        }
    )
    response_obj = make_response(
        render_template(
            "session_shell.html",
            session_id=session_id,
            runtime_session_id=payload.get("runtime_session_id") or backend_session_id,
            runtime_session_ready=bool(payload.get("runtime_session_ready")),
            can_execute=bool(payload.get("can_execute")),
            governance=payload.get("governance") if isinstance(payload.get("governance"), dict) else {},
            play_bootstrap_json=play_bootstrap_json,
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
    _evict_legacy_large_session_keys()

    interpreted = (((payload.get("turn") or {}).get("interpreted_input") or {}).get("kind") or "unknown").strip()
    shell_state_view = payload.get("shell_state_view") if isinstance(payload.get("shell_state_view"), dict) else {}
    raw_story_entries = payload.get("story_entries") if isinstance(payload.get("story_entries"), list) else []
    story_entries = _normalize_story_entries_for_shell(
        raw_story_entries,
        shell_state_view=shell_state_view,
    )
    visible_scene_output = _visible_scene_output_for_typewriter(
        payload,
        story_entries=story_entries,
    )
    if wants_json:
        return jsonify(
            {
                "ok": True,
                "interpreted_input_kind": interpreted,
                "template_id": payload.get("template_id"),
                "module_id": payload.get("module_id"),
                "runtime_session_ready": bool(payload.get("runtime_session_ready")),
                "can_execute": bool(payload.get("can_execute")),
                "opening_generation_status": payload.get("opening_generation_status"),
                "session_loop": payload.get("session_loop") if isinstance(payload.get("session_loop"), dict) else None,
                "shell_state_view": shell_state_view,
                "narrator_streaming": payload.get("narrator_streaming") if isinstance(payload.get("narrator_streaming"), dict) else None,
                "visible_scene_output": visible_scene_output,
                "story_entries": story_entries,
                "story_window": payload.get("story_window") if isinstance(payload.get("story_window"), dict) else {},
            }
        ), 200
    play_bootstrap_json = json.dumps(
        {
            "contract": payload.get("contract"),
            "run_id": session_id,
            "template_id": payload.get("template_id"),
            "module_id": payload.get("module_id"),
            "runtime_session_id": payload.get("runtime_session_id"),
            "runtime_session_ready": bool(payload.get("runtime_session_ready")),
            "can_execute": bool(payload.get("can_execute")),
            "opening_generation_status": payload.get("opening_generation_status"),
            "session_loop": payload.get("session_loop") if isinstance(payload.get("session_loop"), dict) else None,
            "shell_state_view": shell_state_view,
            "narrator_streaming": payload.get("narrator_streaming") if isinstance(payload.get("narrator_streaming"), dict) else None,
            "visible_scene_output": visible_scene_output,
            "story_entries": story_entries,
        }
    )
    return render_template(
        "session_shell.html",
        session_id=session_id,
        runtime_session_id=payload.get("runtime_session_id"),
        runtime_session_ready=bool(payload.get("runtime_session_ready")),
        can_execute=bool(payload.get("can_execute")),
        governance=payload.get("governance") if isinstance(payload.get("governance"), dict) else {},
        play_bootstrap_json=play_bootstrap_json,
    )


@frontend_bp.route("/api/story/sessions/<session_id>/stream-narrator", methods=["GET"])
@require_login
def stream_narrator_proxy(session_id: str):
    """Same-origin SSE proxy: forwards narrator event-stream from play service to browser.

    Keeps the browser EventSource on the frontend origin — avoids CORS, CSP, and
    firewall issues that arise when the browser connects directly to the play service port.
    """
    play_url = (current_app.config.get("PLAY_SERVICE_INTERNAL_URL") or "").rstrip("/")
    if not play_url:
        return Response("Play service not configured", status=503, mimetype="text/plain")
    target = f"{play_url}/api/story/sessions/{session_id}/stream-narrator"
    try:
        upstream = _requests.get(target, stream=True, timeout=120)
    except _requests.RequestException as exc:
        return Response(f"Play service unavailable: {exc!s:.80}", status=502, mimetype="text/plain")

    def _generate():
        try:
            for chunk in upstream.iter_content(chunk_size=None):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(
        stream_with_context(_generate()),
        content_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
