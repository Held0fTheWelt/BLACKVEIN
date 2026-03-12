"""CRUD and helpers for Area and user-area assignments. Used by API."""
import re

from sqlalchemy import func

from app.extensions import db
from app.models import Area, User, user_areas
from app.auth.feature_registry import (
    FEATURE_IDS,
    get_feature_area_ids,
    is_valid_feature_id,
    set_feature_areas as set_feature_areas_impl,
)

AREA_SLUG_PATTERN = re.compile(r"^[a-z0-9_]+$")
AREA_NAME_MAX = 128
AREA_SLUG_MAX = 64


def list_areas(page: int = 1, per_page: int = 50, q: str | None = None):
    """Return (list of Area, total count). Optional search by name/slug (case-insensitive contains)."""
    query = Area.query
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        query = query.filter(
            db.or_(func.lower(Area.name).like(term), func.lower(Area.slug).like(term))
        )
    total = query.count()
    query = query.order_by(Area.slug.asc()).offset((page - 1) * per_page).limit(per_page)
    return query.all(), total


def get_area_by_id(area_id) -> Area | None:
    """Return Area by id or None."""
    if area_id is None:
        return None
    try:
        aid = int(area_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Area, aid)


def get_area_by_slug(slug: str) -> Area | None:
    """Return Area by slug or None."""
    if not slug or not isinstance(slug, str):
        return None
    return Area.query.filter_by(slug=slug.strip().lower()).first()


def validate_area_name(name: str) -> str | None:
    if not name or not isinstance(name, str):
        return "Area name is required"
    name = name.strip()
    if len(name) < 1:
        return "Area name cannot be empty"
    if len(name) > AREA_NAME_MAX:
        return f"Area name must be at most {AREA_NAME_MAX} characters"
    return None


def validate_area_slug(slug: str) -> str | None:
    if not slug or not isinstance(slug, str):
        return "Area slug is required"
    slug = slug.strip().lower()
    if len(slug) < 1:
        return "Area slug cannot be empty"
    if len(slug) > AREA_SLUG_MAX:
        return f"Area slug must be at most {AREA_SLUG_MAX} characters"
    if not AREA_SLUG_PATTERN.match(slug):
        return "Area slug may only contain lowercase letters, digits, and underscore"
    return None


def create_area(
    name: str,
    slug: str | None = None,
    description: str | None = None,
    is_system: bool = False,
) -> tuple[Area | None, str | None]:
    """Create an area. slug defaults to name lowercased with spaces to underscores. Returns (area, None) or (None, error)."""
    err = validate_area_name(name)
    if err:
        return None, err
    name = name.strip()
    slug = (slug or name).strip().lower().replace(" ", "_")
    err = validate_area_slug(slug)
    if err:
        return None, err
    if Area.query.filter_by(slug=slug).first():
        return None, "Area slug already exists"
    if Area.query.filter_by(name=name).first():
        return None, "Area name already exists"
    area = Area(
        name=name,
        slug=slug,
        description=(description or "").strip() or None,
        is_system=bool(is_system),
    )
    db.session.add(area)
    db.session.commit()
    db.session.refresh(area)
    return area, None


def update_area(
    area_id: int,
    name: str | None = None,
    slug: str | None = None,
    description: str | None = None,
) -> tuple[Area | None, str | None]:
    """Update an area. System areas may have name/description updated but slug protection is design-dependent. Returns (area, None) or (None, error)."""
    area = get_area_by_id(area_id)
    if not area:
        return None, "Area not found"
    if area.is_system and area.slug == Area.SLUG_ALL:
        return None, "Cannot modify the system 'all' area"
    if name is not None:
        err = validate_area_name(name)
        if err:
            return None, err
        name = name.strip()
        if name != area.name and Area.query.filter_by(name=name).first():
            return None, "Area name already exists"
        area.name = name
    if slug is not None:
        slug = slug.strip().lower()
        if area.is_system:
            return None, "Cannot change slug of system area"
        err = validate_area_slug(slug)
        if err:
            return None, err
        if slug != area.slug and Area.query.filter_by(slug=slug).first():
            return None, "Area slug already exists"
        area.slug = slug
    if description is not None:
        area.description = (description or "").strip() or None
    db.session.commit()
    db.session.refresh(area)
    return area, None


def delete_area(area_id: int) -> tuple[bool, str | None]:
    """Delete an area. Fails if system area or if any user/feature is assigned. Returns (True, None) or (False, error)."""
    area = get_area_by_id(area_id)
    if not area:
        return False, "Area not found"
    if area.is_system:
        return False, "Cannot delete system area"
    from app.models import FeatureArea
    if db.session.query(user_areas).filter_by(area_id=area_id).first():
        return False, "Area is assigned to users; remove assignments first"
    if FeatureArea.query.filter_by(area_id=area_id).first():
        return False, "Area is assigned to features; remove assignments first"
    db.session.delete(area)
    db.session.commit()
    return True, None


def get_user_area_ids(user_id: int) -> list[int]:
    """Return list of area IDs assigned to the user."""
    user = db.session.get(User, user_id)
    if not user:
        return []
    return [a.id for a in user.areas]


def set_user_areas(user_id: int, area_ids: list[int]) -> tuple[User | None, str | None]:
    """Set area assignments for a user. Replaces existing. Returns (user, None) or (None, error)."""
    user = db.session.get(User, user_id)
    if not user:
        return None, "User not found"
    valid_ids = {a.id for a in Area.query.filter(Area.id.in_(area_ids or [])).all()}
    if area_ids is not None and len(area_ids) != len(valid_ids):
        invalid = set(area_ids or []) - valid_ids
        if invalid:
            return None, f"Unknown area id(s): {invalid}"
    user.areas = Area.query.filter(Area.id.in_(valid_ids)).all() if valid_ids else []
    db.session.commit()
    db.session.refresh(user)
    return user, None


def list_feature_areas_mapping():
    """Return list of { feature_id, area_ids, area_slugs } for all FEATURE_IDS."""
    from app.models import FeatureArea
    out = []
    for fid in FEATURE_IDS:
        area_ids = get_feature_area_ids(fid)
        areas = Area.query.filter(Area.id.in_(area_ids)).all() if area_ids else []
        out.append({
            "feature_id": fid,
            "area_ids": area_ids,
            "area_slugs": [a.slug for a in areas],
        })
    return out


def set_feature_areas(feature_id: str, area_ids: list[int]) -> tuple[bool, str | None]:
    """Set area assignments for a feature. Returns (True, None) or (False, error)."""
    if not is_valid_feature_id(feature_id):
        return False, f"Unknown feature_id: {feature_id!r}"
    valid_ids = list(Area.query.filter(Area.id.in_(area_ids or [])).all())
    if area_ids is not None and len(area_ids) != len(valid_ids):
        valid_set = {a.id for a in valid_ids}
        invalid = set(area_ids or []) - valid_set
        if invalid:
            return False, f"Unknown area id(s): {invalid}"
    try:
        set_feature_areas_impl(feature_id, [a.id for a in valid_ids])
        return True, None
    except ValueError as e:
        return False, str(e)
