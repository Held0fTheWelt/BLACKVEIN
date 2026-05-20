from __future__ import annotations

from ._deps import *

def _recoverable_runtime_aspect_ledger(
    *,
    session_id: str,
    module_id: str,
    turn_number: int,
    turn_kind: str,
    player_input: str,
    trace_id: str | None,
    reason: str,
    validation_status: str = "rejected",
    existing_ledger: dict[str, Any] | None = None,
    visible_output_present: bool = True,
) -> dict[str, Any]:
    """Return a ledger for a playable rejected turn path."""
    ledger = ensure_runtime_aspect_ledger(
        existing_ledger,
        session_id=session_id,
        module_id=module_id,
        turn_number=turn_number,
        turn_kind=turn_kind,
        raw_player_input=player_input,
        trace_id=trace_id,
    )
    aspects = ledger.get("turn_aspect_ledger") if isinstance(ledger.get("turn_aspect_ledger"), dict) else {}
    existing_validation = aspects.get(ASPECT_VALIDATION) if isinstance(aspects.get(ASPECT_VALIDATION), dict) else {}
    existing_commit = aspects.get(ASPECT_COMMIT) if isinstance(aspects.get(ASPECT_COMMIT), dict) else {}
    existing_visible = (
        aspects.get(ASPECT_VISIBLE_PROJECTION)
        if isinstance(aspects.get(ASPECT_VISIBLE_PROJECTION), dict)
        else {}
    )
    existing_validation_expected = (
        existing_validation.get("expected")
        if isinstance(existing_validation.get("expected"), dict)
        else {}
    )
    existing_validation_actual = (
        existing_validation.get("actual")
        if isinstance(existing_validation.get("actual"), dict)
        else {}
    )
    existing_commit_expected = (
        existing_commit.get("expected")
        if isinstance(existing_commit.get("expected"), dict)
        else {}
    )
    existing_commit_actual = (
        existing_commit.get("actual")
        if isinstance(existing_commit.get("actual"), dict)
        else {}
    )
    existing_failure_class = (
        str(existing_commit.get("failure_class") or existing_validation.get("failure_class") or "").strip()
        or None
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_VALIDATION,
        make_aspect_record(
            applicable=True,
            status="failed",
            expected=existing_validation_expected,
            actual={
                **existing_validation_actual,
                "validation_status": validation_status,
                "recoverable_rejection": True,
                "hard_boundary_failure": False,
            },
            reasons=[reason],
            source="validator",
            failure_class=existing_failure_class or "recoverable_dramatic_failure",
            failure_reason=reason,
        ),
    )
    ledger = set_aspect_record(
        ledger,
        ASPECT_COMMIT,
        make_aspect_record(
            applicable=True,
            status="partial",
            expected={
                **existing_commit_expected,
                "player_action_commit_allowed": False,
            },
            actual={
                **existing_commit_actual,
                "commit_applied": False,
                "recoverable_rejection": True,
                "failure_committed_to_player_surface": visible_output_present,
            },
            reasons=[reason],
            source="runtime",
            failure_class=existing_failure_class or "recoverable_dramatic_failure",
            failure_reason=reason,
        ),
    )
    if existing_visible.get("status") != "failed":
        ledger = set_aspect_record(
            ledger,
            ASPECT_VISIBLE_PROJECTION,
            make_aspect_record(
                applicable=True,
                status="passed" if visible_output_present else "failed",
                expected={"visible_output_present": True},
                actual={"visible_output_present": bool(visible_output_present)},
                reasons=[] if visible_output_present else [reason],
                source="projection",
                failure_class=None if visible_output_present else "projection_failure",
                failure_reason=None if visible_output_present else reason,
            ),
        )
    return normalize_runtime_aspect_ledger(ledger)

def _canonical_turn_id(session_id: str, turn_number: int) -> str:
    sid = str(session_id or "").strip() or "session"
    return f"{sid}:turn:{int(turn_number or 0)}"

def _runtime_profile_id_from_projection(projection: dict[str, Any] | None) -> str | None:
    if not isinstance(projection, dict):
        return None
    for key in ("runtime_profile_id", "experience_template_id", "seed_template_id", "template_id"):
        value = str(projection.get(key) or "").strip()
        if value:
            return value
    return None

def _observability_environment_for_session(session: "StorySession") -> str | None:
    projection = session.runtime_projection if isinstance(session.runtime_projection, dict) else {}
    provenance = session.content_provenance if isinstance(session.content_provenance, dict) else {}
    trace_classification = (
        provenance.get("trace_classification")
        if isinstance(provenance.get("trace_classification"), dict)
        else {}
    )
    for value in (
        trace_classification.get("environment"),
        projection.get("environment"),
        os.environ.get("LANGFUSE_ENVIRONMENT"),
        os.environ.get("WOS_LANGFUSE_ENVIRONMENT"),
        os.environ.get("ENVIRONMENT"),
    ):
        text = str(value or "").strip()
        if text:
            return text
    return None

def _stamp_turn_aspect_ledger_identity(
    ledger: dict[str, Any] | None,
    *,
    session: "StorySession",
    commit_turn_number: int,
    turn_kind: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(ledger, dict):
        return None
    stamped = normalize_runtime_aspect_ledger(ledger)
    stamped["session_id"] = session.session_id
    stamped["story_session_id"] = session.session_id
    stamped["canonical_turn_id"] = _canonical_turn_id(session.session_id, commit_turn_number)
    stamped["turn_number"] = int(commit_turn_number or 0)
    if turn_kind:
        stamped["turn_kind"] = str(turn_kind)
    stamped.setdefault("module_id", session.module_id)
    runtime_profile_id = _runtime_profile_id_from_projection(
        session.runtime_projection if isinstance(session.runtime_projection, dict) else None
    )
    if runtime_profile_id and not stamped.get("runtime_profile_id"):
        stamped["runtime_profile_id"] = runtime_profile_id
    return normalize_runtime_aspect_ledger(stamped)

def _runtime_aspect_commit_blocking_failure(ledger: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(ledger, dict):
        return None
    normalized = normalize_runtime_aspect_ledger(ledger)
    aspects = (
        normalized.get("turn_aspect_ledger")
        if isinstance(normalized.get("turn_aspect_ledger"), dict)
        else {}
    )
    blocking_failure_classes = {
        "hard_contract_failure",
        "projection_failure",
        "recoverable_dramatic_failure",
    }
    for aspect in (
        ASPECT_VISIBLE_PROJECTION,
        ASPECT_BEAT,
        ASPECT_CAPABILITY_SELECTION,
        ASPECT_NARRATIVE_ASPECT,
        ASPECT_VALIDATION,
    ):
        record = aspects.get(aspect)
        if not isinstance(record, dict):
            continue
        status = str(record.get("status") or "").strip().lower()
        failure_class = str(record.get("failure_class") or "").strip()
        failure_reason = str(record.get("failure_reason") or "").strip()
        actual = record.get("actual") if isinstance(record.get("actual"), dict) else {}
        reasons = record.get("reasons") if isinstance(record.get("reasons"), list) else []
        reason = failure_reason or next((str(item).strip() for item in reasons if str(item).strip()), "")
        if status == "failed" and (
            failure_class in blocking_failure_classes
            or aspect in {ASPECT_VISIBLE_PROJECTION, ASPECT_CAPABILITY_SELECTION}
            or bool(actual.get("projection_failure_detected"))
            or bool(actual.get("required_beat_lost"))
            or bool(actual.get("narrative_aspect_failure"))
        ):
            return {
                "aspect": aspect,
                "status": status,
                "failure_class": failure_class or "hard_contract_failure",
                "failure_reason": reason or f"{aspect}_failed",
            }
    return None

def _scene_blocks_from_visible_bundle(bundle: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(bundle, dict):
        return []
    blocks = bundle.get("scene_blocks")
    if not isinstance(blocks, list):
        return []
    return [dict(block) for block in blocks if isinstance(block, dict)]

def _recoverable_turn_message(*, session: "StorySession", reason: str) -> str:
    lang = str(getattr(session, "session_output_language", DEFAULT_SESSION_LANGUAGE) or DEFAULT_SESSION_LANGUAGE).strip().lower()[:2] or DEFAULT_SESSION_LANGUAGE
    if lang == "en":
        if reason == "graph_execution_exception":
            return "Fallback: the moment catches and stays playable. Try a simpler move from here."
        return "Fallback: the turn could not be accepted by the runtime. Try a clearer move from this same state."
    if reason == "graph_execution_exception":
        return "Fallback: Der Moment hakt, bleibt aber spielbar. Versuche von hier aus einen einfacheren Zug."
    return "Fallback: Der Zug wurde von der Runtime nicht akzeptiert. Versuche aus demselben Zustand heraus einen klareren Zug."

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
