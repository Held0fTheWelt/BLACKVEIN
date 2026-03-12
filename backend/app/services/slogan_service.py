"""
Slogan CRUD and runtime placement resolution.
Selection: active only; valid_from/valid_until window; pinned overrides; then highest priority.
Language fallback: try requested lang, then DEFAULT_LANGUAGE.
"""
from datetime import datetime, timezone

from sqlalchemy import or_

from app.extensions import db
from app.models import Slogan
from flask import current_app


def _utc_now():
    return datetime.now(timezone.utc)


def _parse_dt(value):
    """Parse ISO datetime string to timezone-aware datetime or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc) if value.tzinfo is None else value
    if isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    return None


def _validate_category(category: str) -> bool:
    return category in Slogan.CATEGORIES


def _validate_placement(placement_key: str) -> bool:
    return placement_key in Slogan.PLACEMENTS


def list_slogans(category=None, placement_key=None, language_code=None, active_only=False):
    """Return list of slogans, optionally filtered."""
    q = Slogan.query
    if category:
        q = q.filter(Slogan.category == category)
    if placement_key:
        q = q.filter(Slogan.placement_key == placement_key)
    if language_code:
        q = q.filter(Slogan.language_code == language_code)
    if active_only:
        q = q.filter(Slogan.is_active.is_(True))
    q = q.order_by(Slogan.priority.desc(), Slogan.id.asc())
    return q.all()


def get_slogan_by_id(slogan_id):
    """Return Slogan by id or None."""
    if slogan_id is None:
        return None
    try:
        sid = int(slogan_id)
    except (TypeError, ValueError):
        return None
    return db.session.get(Slogan, sid)


def create_slogan(
    text,
    category,
    placement_key,
    language_code,
    is_active=True,
    is_pinned=False,
    priority=0,
    valid_from=None,
    valid_until=None,
    created_by=None,
):
    """Create a slogan. Returns (slogan, None) or (None, error_message)."""
    text = (text or "").strip()
    if not text:
        return None, "Text is required"
    if not _validate_category(category):
        return None, f"Invalid category. Allowed: {', '.join(Slogan.CATEGORIES)}"
    if not _validate_placement(placement_key):
        return None, f"Invalid placement_key. Allowed: {', '.join(Slogan.PLACEMENTS)}"
    lang_ok = current_app.config.get("SUPPORTED_LANGUAGES", ["de", "en"])
    if language_code not in lang_ok:
        return None, f"Unsupported language. Allowed: {', '.join(lang_ok)}"
    slogan = Slogan(
        text=text,
        category=category,
        placement_key=placement_key,
        language_code=language_code,
        is_active=bool(is_active),
        is_pinned=bool(is_pinned),
        priority=int(priority) if priority is not None else 0,
        valid_from=_parse_dt(valid_from),
        valid_until=_parse_dt(valid_until),
        created_by=created_by,
        updated_by=created_by,
    )
    db.session.add(slogan)
    db.session.commit()
    return slogan, None


def update_slogan(
    slogan_id,
    text=None,
    category=None,
    placement_key=None,
    language_code=None,
    is_active=None,
    is_pinned=None,
    priority=None,
    valid_from=None,
    valid_until=None,
    updated_by=None,
):
    """Update slogan. Returns (slogan, None) or (None, error_message)."""
    slogan = get_slogan_by_id(slogan_id)
    if not slogan:
        return None, "Slogan not found"
    if text is not None:
        t = (text or "").strip()
        if not t:
            return None, "Text cannot be empty"
        slogan.text = t
    if category is not None:
        if not _validate_category(category):
            return None, f"Invalid category. Allowed: {', '.join(Slogan.CATEGORIES)}"
        slogan.category = category
    if placement_key is not None:
        if not _validate_placement(placement_key):
            return None, f"Invalid placement_key. Allowed: {', '.join(Slogan.PLACEMENTS)}"
        slogan.placement_key = placement_key
    if language_code is not None:
        lang_ok = current_app.config.get("SUPPORTED_LANGUAGES", ["de", "en"])
        if language_code not in lang_ok:
            return None, f"Unsupported language. Allowed: {', '.join(lang_ok)}"
        slogan.language_code = language_code
    if is_active is not None:
        slogan.is_active = bool(is_active)
    if is_pinned is not None:
        slogan.is_pinned = bool(is_pinned)
    if priority is not None:
        slogan.priority = int(priority)
    if valid_from is not None:
        slogan.valid_from = _parse_dt(valid_from)
    if valid_until is not None:
        slogan.valid_until = _parse_dt(valid_until)
    slogan.updated_by = updated_by
    slogan.updated_at = _utc_now()
    db.session.commit()
    return slogan, None


def delete_slogan(slogan_id):
    """Delete slogan. Returns (True, None) or (False, error_message)."""
    slogan = get_slogan_by_id(slogan_id)
    if not slogan:
        return False, "Slogan not found"
    db.session.delete(slogan)
    db.session.commit()
    return True, None


def activate_slogan(slogan_id):
    """Set is_active=True. Returns (slogan, None) or (None, error_message)."""
    return update_slogan(slogan_id, is_active=True)


def deactivate_slogan(slogan_id):
    """Set is_active=False. Returns (slogan, None) or (None, error_message)."""
    return update_slogan(slogan_id, is_active=False)


def _slogans_query_for_placement(placement_key: str, lang: str):
    """Base query for placement+lang: active, valid window, ordered by priority desc, id asc."""
    now = _utc_now()
    return (
        Slogan.query.filter(
            Slogan.placement_key == placement_key,
            Slogan.language_code == lang,
            Slogan.is_active.is_(True),
        )
        .filter(or_(Slogan.valid_from.is_(None), Slogan.valid_from <= now))
        .filter(or_(Slogan.valid_until.is_(None), Slogan.valid_until > now))
        .order_by(Slogan.priority.desc(), Slogan.id.asc())
    )


def list_slogans_for_placement(placement_key: str, lang: str):
    """
    Return all slogans for the placement and language (for rotation).
    Same filters as resolve_slogan_for_placement; tries lang then DEFAULT_LANGUAGE.
    Returns list of Slogan (may be empty).
    """
    default_lang = current_app.config.get("DEFAULT_LANGUAGE", "de")
    for try_lang in (lang, default_lang):
        if not try_lang:
            continue
        items = _slogans_query_for_placement(placement_key, try_lang).all()
        if items:
            return items
    return []


def resolve_slogan_for_placement(placement_key: str, lang: str):
    """
    Return one slogan for the placement and language. Selection: active only;
    valid_from <= now <= valid_until (null = no bound); pinned first; else highest priority.
    Language fallback: try lang, then DEFAULT_LANGUAGE.
    Returns Slogan or None.
    """
    default_lang = current_app.config.get("DEFAULT_LANGUAGE", "de")
    for try_lang in (lang, default_lang):
        if not try_lang:
            continue
        q = _slogans_query_for_placement(placement_key, try_lang)
        pinned = q.filter(Slogan.is_pinned.is_(True)).first()
        if pinned:
            return pinned
        first = q.first()
        if first:
            return first
    return None
