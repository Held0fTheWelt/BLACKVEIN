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
FEATURE_MANAGE_SYSTEM_DIAGNOSIS = "manage.system_diagnosis"
FEATURE_MANAGE_PLAY_SERVICE_CONTROL = "manage.play_service_control"
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
    FEATURE_MANAGE_SYSTEM_DIAGNOSIS,
    FEATURE_MANAGE_PLAY_SERVICE_CONTROL,
    FEATURE_DASHBOARD_METRICS,
    FEATURE_DASHBOARD_LOGS,
    FEATURE_DASHBOARD_SETTINGS,
    FEATURE_DASHBOARD_USER_SETTINGS,
]

# Required role names for each feature (user must have one of these). Admin-only by default.
FEATURE_REQUIRED_ROLES = {
    FEATURE_MANAGE_NEWS: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_USERS: (User.ROLE_ADMIN,),
    FEATURE_MANAGE_ROLES: (User.ROLE_ADMIN,),
    FEATURE_MANAGE_WIKI: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_SLOGANS: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_AREAS: (User.ROLE_ADMIN,),
    FEATURE_MANAGE_FEATURE_AREAS: (User.ROLE_ADMIN,),
    FEATURE_MANAGE_DATA_EXPORT: (User.ROLE_ADMIN,),
    FEATURE_MANAGE_DATA_IMPORT: (User.ROLE_ADMIN,),
    FEATURE_MANAGE_FORUM: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_GAME_CONTENT: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_GAME_OPERATIONS: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_SYSTEM_DIAGNOSIS: (User.ROLE_MODERATOR, User.ROLE_ADMIN),
    FEATURE_MANAGE_PLAY_SERVICE_CONTROL: (User.ROLE_ADMIN,),
    FEATURE_DASHBOARD_METRICS: (User.ROLE_ADMIN,),
    FEATURE_DASHBOARD_LOGS: (User.ROLE_ADMIN,),
    FEATURE_DASHBOARD_SETTINGS: (User.ROLE_ADMIN,),
    FEATURE_DASHBOARD_USER_SETTINGS: (),  # any logged-in user
}


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


def user_can_access_feature(user: User, feature_id: str) -> bool:
    """
    True if user may access the feature: role, not banned, and area check.
    - Role: user must have one of FEATURE_REQUIRED_ROLES[feature_id] (empty = any).
    - Area: if feature has no area assignments, allow.
      If the feature is area-scoped: users with **no** area assignments are not restricted
      (see AREA_ACCESS_CONTROL.md). Otherwise user must have 'all' or overlap with the feature's areas.
    """
    if not user:
        return False
    if getattr(user, "is_banned", False):
        return False
    if not is_valid_feature_id(feature_id):
        return False
    required = FEATURE_REQUIRED_ROLES.get(feature_id, (User.ROLE_ADMIN,))
    if required and not user.has_any_role(required):
        return False
    feature_areas = get_feature_area_ids(feature_id)
    if not feature_areas:
        return True  # no area restriction = global
    # No rows in user_areas → do not apply feature_areas filter (legacy / full access until areas are assigned).
    if not list(user.areas or []):
        return True
    if _user_has_area_all(user):
        return True
    user_aids = _user_area_ids(user)
    return bool(user_aids & set(feature_areas))
