from flask import Blueprint
from flask_jwt_extended import get_jwt_identity

from app.services.user_service import update_user_last_seen

api_v1_bp = Blueprint("api_v1", __name__)


@api_v1_bp.after_request
def _track_api_activity(response):
    """Update last_seen_at for JWT-authenticated users (throttled in update_user_last_seen)."""
    try:
        uid = get_jwt_identity()
        if uid is not None:
            update_user_last_seen(uid)
    except Exception:
        pass
    return response


# Import after blueprint exists to register routes
from app.api.v1 import admin_routes  # noqa: F401, E402
from app.api.v1 import area_routes  # noqa: F401, E402
from app.api.v1 import auth_routes  # noqa: F401, E402
from app.api.v1 import role_routes  # noqa: F401, E402
from app.api.v1 import system_routes  # noqa: F401, E402
from app.api.v1 import news_routes  # noqa: F401, E402
from app.api.v1 import user_routes  # noqa: F401, E402
from app.api.v1 import wiki_routes  # noqa: F401, E402
from app.api.v1 import wiki_admin_routes  # noqa: F401, E402
from app.api.v1 import slogan_routes  # noqa: F401, E402
from app.api.v1 import site_routes  # noqa: F401, E402
from app.api.v1 import data_routes  # noqa: F401, E402
from app.api.v1 import forum_routes  # noqa: F401, E402
