from flask import Blueprint, request, g
from flask_jwt_extended import get_jwt_identity
from importlib import import_module
import time
import sys

from app.services.identity.user_service import update_user_last_seen
from app.observability.trace import (
    LANGFUSE_TRACE_ID,
    TRACE_ID,
    ensure_langfuse_trace_id,
    ensure_trace_id,
    get_langfuse_trace_id,
    get_trace_id,
)
from app.observability.audit_log import log_api_endpoint

api_v1_bp = Blueprint("api_v1", __name__)


def _sync_module_aliases() -> None:
    """Keep ``app.api.v1`` and ``backend.app.api.v1`` import paths unified.

    Some test modules import route helpers via ``backend.app...`` while the app
    runtime imports via ``app...``. Without aliasing, Python can execute route
    modules twice under different module keys, which re-attaches route
    decorators after the blueprint has already been registered.
    """
    canonical = "app.api.v1"
    alternate = "backend.app.api.v1"
    this_module = sys.modules.get(__name__)
    if this_module is None:
        return
    if __name__ == canonical:
        sys.modules.setdefault(alternate, this_module)
        source_prefix = f"{canonical}."
        target_prefix = f"{alternate}."
    elif __name__ == alternate:
        sys.modules.setdefault(canonical, this_module)
        source_prefix = f"{alternate}."
        target_prefix = f"{canonical}."
    else:
        return

    for name, module in list(sys.modules.items()):
        if not name.startswith(source_prefix):
            continue
        suffix = name[len(source_prefix) :]
        sys.modules.setdefault(f"{target_prefix}{suffix}", module)


@api_v1_bp.before_request
def _setup_trace():
    """Set up trace ID from header or generate new one."""
    g.trace_token = TRACE_ID.set(None)
    g.langfuse_trace_token = LANGFUSE_TRACE_ID.set(None)
    incoming_trace = request.headers.get("X-WoS-Trace-Id")
    trace_id = ensure_trace_id(incoming_trace)
    incoming_langfuse_trace = request.headers.get("X-Langfuse-Trace-Id")
    langfuse_trace_id = ensure_langfuse_trace_id(
        incoming_langfuse_trace,
        seed=trace_id,
    )
    g.trace_id = trace_id
    g.langfuse_trace_id = langfuse_trace_id
    g.request_start_time = time.time()


@api_v1_bp.after_request
def _track_api_activity(response):
    """Update last_seen_at for JWT-authenticated users and write audit logs."""
    try:
        uid = get_jwt_identity()
        if uid is not None:
            update_user_last_seen(uid)
    except Exception:
        pass

    # Add trace ID to response header
    trace_id = g.get("trace_id")
    if trace_id:
        response.headers["X-WoS-Trace-Id"] = trace_id
    langfuse_trace_id = g.get("langfuse_trace_id") or get_langfuse_trace_id()
    if langfuse_trace_id:
        response.headers["X-Langfuse-Trace-Id"] = langfuse_trace_id

    # Write audit log for canonical player-session endpoints.
    if "/game/player-sessions" in request.path:
        start_time = g.get("request_start_time", time.time())
        duration_ms = int((time.time() - start_time) * 1000)

        # Extract session_id from path
        session_id = None
        parts = request.path.split("/")
        if len(parts) >= 5 and parts[2] == "game" and parts[3] == "player-sessions":
            session_id = parts[4] if len(parts) > 4 else None

        log_api_endpoint(
            trace_id=trace_id,
            session_id=session_id,
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            outcome="ok" if 200 <= response.status_code < 400 else "error",
        )

    trace_token = g.get("trace_token")
    if trace_token is not None:
        TRACE_ID.reset(trace_token)
    langfuse_trace_token = g.get("langfuse_trace_token")
    if langfuse_trace_token is not None:
        LANGFUSE_TRACE_ID.reset(langfuse_trace_token)

    return response


def _register_api_v1_blueprint_routes() -> None:
    """Import route modules so they attach handlers to ``api_v1_bp`` (import side effects).

    Called once at package load after ``api_v1_bp`` and request hooks exist.
    Submodules import ``api_v1_bp`` from this package; order here should not
    affect URL resolution unless two modules register the same path (avoided).
    """
    for module_name in (
        "admin_routes",
        "area_routes",
        "auth_routes",
        "role_routes",
        "system_routes",
        "news_routes",
        "user_routes",
        "wiki_routes",
        "wiki_admin_routes",
        "slogan_routes",
        "site_routes",
        "data_routes",
        "forum_routes",
        "forum_routes_notifications",
        "forum_routes_tag_discovery",
        "analytics_routes",
        "game_routes",
        "game_admin_routes",
        "writers_room_routes",
        "improvement_routes",
        "ai_stack_governance_routes",
        "narrative_governance_routes",
        "system_diagnosis_routes",
        "play_service_control_routes",
        "world_engine_console_routes",
        "mcp_operations_routes",
        "operational_governance_routes",
        "observability_governance_routes",
        "governance_console_routes",
        "ai_engineer_suite_routes",
        "research_domain_governance_routes",
        "operator_diagnostics_routes",
        "play_qa_diagnostics_routes",
        "admin_settings_routes",
        "security_governance_routes",
        "prompt_store_routes",
    ):
        import_module(f"app.api.v1.{module_name}")


_register_api_v1_blueprint_routes()
_sync_module_aliases()
