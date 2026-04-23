"""
Central registry of feature/view identifiers and area-based access evaluation.
Use these identifiers for feature_areas mapping and permission checks.
"""
from app.extensions import db
from app.models import Area, FeatureArea, User

# Stable identifiers for admin/dashboard/frontend features. Use these in feature_areas and API.
FEATURE_MANAGE_NEWS = "manage.news"
FEATURE_MANAGE_USERS = "manage.users"
FEATURE_MANAGE_ROLES = "manage.roles"
FEATURE_MANAGE_WIKI = "manage.wiki"
FEATURE_MANAGE_SLOGANS = "manage.slogans"
FEATURE_MANAGE_AREAS = "manage.areas"
FEATURE_MANAGE_FEATURE_AREAS = "manage.feature_areas"
FEATURE_MANAGE_DATA_EXPORT = "manage.data_export"
FEATURE_MANAGE_DATA_IMPORT = "manage.data_import"
FEATURE_MANAGE_FORUM = "manage.forum"
FEATURE_MANAGE_GAME_CONTENT = "manage.game_content"
FEATURE_MANAGE_GAME_OPERATIONS = "manage.game_operations"
FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE = "manage.ai_runtime_governance"
FEATURE_MANAGE_SYSTEM_DIAGNOSIS = "manage.system_diagnosis"
FEATURE_MANAGE_PLAY_SERVICE_CONTROL = "manage.play_service_control"
FEATURE_MANAGE_WORLD_ENGINE_OBSERVE = "manage.world_engine_observe"
FEATURE_MANAGE_WORLD_ENGINE_OPERATE = "manage.world_engine_operate"
FEATURE_MANAGE_WORLD_ENGINE_AUTHOR = "manage.world_engine_author"
FEATURE_MANAGE_MCP_OPERATIONS = "manage.mcp_operations"
FEATURE_MANAGE_RESEARCH_GOVERNANCE = "manage.research_governance"
FEATURE_VIEW_QA_CANONICAL_TURN = "view.qa.canonical_turn"
FEATURE_DASHBOARD_METRICS = "dashboard.metrics"
FEATURE_DASHBOARD_LOGS = "dashboard.logs"
FEATURE_DASHBOARD_SETTINGS = "dashboard.settings"
FEATURE_DASHBOARD_USER_SETTINGS = "dashboard.user_settings"

FEATURE_IDS = [
    FEATURE_MANAGE_NEWS,
    FEATURE_MANAGE_USERS,
    FEATURE_MANAGE_ROLES,
    FEATURE_MANAGE_WIKI,
    FEATURE_MANAGE_SLOGANS,
    FEATURE_MANAGE_AREAS,
    FEATURE_MANAGE_FEATURE_AREAS,
    FEATURE_MANAGE_DATA_EXPORT,
    FEATURE_MANAGE_DATA_IMPORT,
    FEATURE_MANAGE_FORUM,
    FEATURE_MANAGE_GAME_CONTENT,
    FEATURE_MANAGE_GAME_OPERATIONS,
    FEATURE_MANAGE_AI_RUNTIME_GOVERNANCE,
    FEATURE_MANAGE_SYSTEM_DIAGNOSIS,
    FEATURE_MANAGE_PLAY_SERVICE_CONTROL,
    FEATURE_MANAGE_WORLD_ENGINE_OBSERVE,
    FEATURE_MANAGE_WORLD_ENGINE_OPERATE,
    FEATURE_MANAGE_WORLD_ENGINE_AUTHOR,
    FEATURE_MANAGE_MCP_OPERATIONS,
    FEATURE_MANAGE_RESEARCH_GOVERNANCE,
    FEATURE_VIEW_QA_CANONICAL_TURN,
    FEATURE_DASHBOARD_METRICS,
    FEATURE_DASHBOARD_LOGS,
    FEATURE_DASHBOARD_SETTINGS,
    FEATURE_DASHBOARD_USER_SETTINGS,
]

# Legacy tuple view derived from ``app.auth.feature_access_resolver.FEATURE_ACCESS_RULES`` (import lazily).
def feature_required_roles_legacy(feature_id: str) -> tuple[str, ...]:
    """Approximate previous FEATURE_REQUIRED_ROLES tuples for migration notes and tooling."""
    from app.auth.feature_access_resolver import (
        ACCESS_TIER_ADMIN,
        ACCESS_TIER_MODERATOR,
        ACCESS_TIER_AUTHENTICATED,
        FEATURE_ACCESS_RULES,
    )

    meta = FEATURE_ACCESS_RULES.get(feature_id) or {}
    tier = int(meta.get("min_tier", ACCESS_TIER_ADMIN))
    if tier >= ACCESS_TIER_ADMIN:
        return (User.ROLE_ADMIN,)
    if tier >= ACCESS_TIER_MODERATOR:
        return (User.ROLE_MODERATOR, User.ROLE_ADMIN)
    return ()  # authenticated-only (e.g. dashboard user settings)


def is_valid_feature_id(feature_id: str) -> bool:
    """Return True if feature_id is a known feature."""
    return feature_id in FEATURE_IDS


def get_feature_area_ids(feature_id: str):
    """Return list of area IDs assigned to this feature. Empty means global (all areas)."""
    if not feature_id:
        return []
    rows = FeatureArea.query.filter_by(feature_id=feature_id).all()
    return [r.area_id for r in rows]


def set_feature_areas(feature_id: str, area_ids: list[int]) -> None:
    """Set area assignments for a feature. Replaces existing. area_ids empty = global."""
    if not is_valid_feature_id(feature_id):
        raise ValueError(f"Unknown feature_id: {feature_id!r}")
    FeatureArea.query.filter_by(feature_id=feature_id).delete()
    for aid in area_ids or []:
        db.session.add(FeatureArea(feature_id=feature_id, area_id=aid))
    db.session.commit()


def _user_has_area_all(user: User) -> bool:
    """True if user is assigned the 'all' (wildcard) area."""
    if not user or not user.areas:
        return False
    for a in user.areas:
        if a.slug == Area.SLUG_ALL:
            return True
    return False


def _user_area_ids(user: User) -> set:
    """Set of area IDs the user is assigned to."""
    if not user or not user.areas:
        return set()
    return {a.id for a in user.areas}


def user_can_access_world_engine_capability(user: User | None, min_capability: str) -> bool:
    """
    Hierarchical World-Engine console rights: author ⊃ operate ⊃ observe.
    min_capability: "observe" | "operate" | "author"
    """
    if not user:
        return False
    has_author = user_can_access_feature(user, FEATURE_MANAGE_WORLD_ENGINE_AUTHOR)
    has_operate = user_can_access_feature(user, FEATURE_MANAGE_WORLD_ENGINE_OPERATE)
    has_observe = user_can_access_feature(user, FEATURE_MANAGE_WORLD_ENGINE_OBSERVE)
    if min_capability == "author":
        return has_author
    if min_capability == "operate":
        return has_author or has_operate
    if min_capability == "observe":
        return has_author or has_operate or has_observe
    return False


def user_can_access_feature(user: User | None, feature_id: str) -> bool:
    """
    True if the user may access the feature (JWT-backed admin/manage surfaces).

    Delegates to ``app.auth.feature_access_resolver`` so backend routes, ``/auth/me``,
    and the same tier + area rules stay aligned. See ``resolve_feature_access`` for diagnostics.
    """
    from app.auth.feature_access_resolver import user_can_access_feature_resolved

    return user_can_access_feature_resolved(user, feature_id)
