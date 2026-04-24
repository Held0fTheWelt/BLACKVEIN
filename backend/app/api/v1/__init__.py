from flask import Blueprint, request, g
from flask_jwt_extended import get_jwt_identity
import time
import sys

from app.services.user_service import update_user_last_seen
from app.observability.trace import ensure_trace_id, get_trace_id, reset_trace_id
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
    incoming_trace = request.headers.get("X-WoS-Trace-Id")
    trace_id = ensure_trace_id(incoming_trace)
    g.trace_id = trace_id
    g.trace_token = None  # Will store token for reset in after_request
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

    # Write audit log for session endpoints
    if "/sessions" in request.path:
        start_time = g.get("request_start_time", time.time())
        duration_ms = int((time.time() - start_time) * 1000)

        # Extract session_id from path
        session_id = None
        parts = request.path.split("/")
        if len(parts) >= 4 and parts[2] == "sessions":
            session_id = parts[3] if len(parts) > 3 and parts[3] not in ("export",) else None

        log_api_endpoint(
            trace_id=trace_id,
            session_id=session_id,
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            outcome="ok" if 200 <= response.status_code < 400 else "error",
        )

    return response


def _register_api_v1_blueprint_routes() -> None:
    """Import route modules so they attach handlers to ``api_v1_bp`` (import side effects).

    Called once at package load after ``api_v1_bp`` and request hooks exist.
    Submodules import ``api_v1_bp`` from this package; order here should not
    affect URL resolution unless two modules register the same path (avoided).
    """
    from app.api.v1 import admin_routes  # noqa: F401
    from app.api.v1 import area_routes  # noqa: F401
    from app.api.v1 import auth_routes  # noqa: F401
    from app.api.v1 import role_routes  # noqa: F401
    from app.api.v1 import system_routes  # noqa: F401
    from app.api.v1 import news_routes  # noqa: F401
    from app.api.v1 import user_routes  # noqa: F401
    from app.api.v1 import wiki_routes  # noqa: F401
    from app.api.v1 import wiki_admin_routes  # noqa: F401
    from app.api.v1 import slogan_routes  # noqa: F401
    from app.api.v1 import site_routes  # noqa: F401
    from app.api.v1 import data_routes  # noqa: F401
    from app.api.v1 import forum_routes  # noqa: F401
    from app.api.v1 import forum_routes_notifications  # noqa: F401
    from app.api.v1 import forum_routes_tag_discovery  # noqa: F401
    from app.api.v1 import analytics_routes  # noqa: F401
    from app.api.v1 import game_routes  # noqa: F401
    from app.api.v1 import game_admin_routes  # noqa: F401
    from app.api.v1 import session_routes  # noqa: F401
    from app.api.v1 import writers_room_routes  # noqa: F401
    from app.api.v1 import improvement_routes  # noqa: F401
    from app.api.v1 import ai_stack_governance_routes  # noqa: F401
    from app.api.v1 import narrative_governance_routes  # noqa: F401
    from app.api.v1 import system_diagnosis_routes  # noqa: F401
    from app.api.v1 import play_service_control_routes  # noqa: F401
    from app.api.v1 import world_engine_console_routes  # noqa: F401
    from app.api.v1 import mcp_operations_routes  # noqa: F401
    from app.api.v1 import operational_governance_routes  # noqa: F401
    from app.api.v1 import observability_governance_routes  # noqa: F401
    from app.api.v1 import ai_engineer_suite_routes  # noqa: F401
    from app.api.v1 import research_domain_governance_routes  # noqa: F401
    from app.api.v1 import player_routes  # noqa: F401
    from app.api.v1 import operator_diagnostics_routes  # noqa: F401
    from app.api.v1 import play_qa_diagnostics_routes  # noqa: F401


_register_api_v1_blueprint_routes()
_sync_module_aliases()
