from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from sqlalchemy import select

from app.content.builtins import build_god_of_carnage_solo
from app.content.models import ExperienceTemplate
from app.extensions import db
from app.models import GameExperienceTemplate


class GameContentError(RuntimeError):
    pass


class GameContentValidationError(GameContentError):
    pass


class GameContentNotFoundError(GameContentError):
    pass


class GameContentConflictError(GameContentError):
    pass


@dataclass(slots=True)
class ExperienceUpsertPayload:
    template_id: str
    slug: str
    title: str
    kind: str
    summary: str | None
    style_profile: str
    tags: list[str]
    payload: dict


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")



def slugify(value: str) -> str:
    slug = _SLUG_PATTERN.sub("-", value.strip().lower()).strip("-")
    if not slug:
        raise GameContentValidationError("slug cannot be empty")
    return slug[:140]



def _canonicalize_payload(payload: dict) -> ExperienceUpsertPayload:
    if not isinstance(payload, dict):
        raise GameContentValidationError("payload must be an object")
    try:
        template = ExperienceTemplate.model_validate(payload)
    except Exception as exc:  # pragma: no cover - pydantic gives detailed context
        raise GameContentValidationError(f"invalid experience payload: {exc}") from exc

    canonical = template.model_dump(mode="json")
    slug = payload.get("slug") or template.id
    return ExperienceUpsertPayload(
        template_id=template.id,
        slug=slugify(slug),
        title=template.title,
        kind=template.kind.value,
        summary=template.summary,
        style_profile=template.style_profile,
        tags=list(template.tags),
        payload=canonical,
    )



def _now() -> datetime:
    return datetime.now(timezone.utc)



def ensure_default_game_content_seeded() -> None:
    existing = db.session.execute(select(GameExperienceTemplate.id).limit(1)).scalar_one_or_none()
    if existing is not None:
        return
    payload = build_god_of_carnage_solo().model_dump(mode="json")
    normalized = _canonicalize_payload(payload)
    entity = GameExperienceTemplate(
        template_id=normalized.template_id,
        slug=normalized.slug,
        title=normalized.title,
        kind=normalized.kind,
        summary=normalized.summary,
        style_profile=normalized.style_profile,
        tags_json=normalized.tags,
        payload_json=normalized.payload,
        source="authored_seed",
        version=1,
        is_published=True,
        published_at=_now(),
    )
    db.session.add(entity)
    db.session.commit()



def list_experiences(*, include_payload: bool = False) -> list[dict]:
    ensure_default_game_content_seeded()
    rows = db.session.scalars(select(GameExperienceTemplate).order_by(GameExperienceTemplate.created_at.asc())).all()
    return [row.to_dict(include_payload=include_payload) for row in rows]



def get_experience(experience_id: int, *, include_payload: bool = True) -> dict:
    ensure_default_game_content_seeded()
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    return entity.to_dict(include_payload=include_payload)



def _ensure_unique(normalized: ExperienceUpsertPayload, *, ignore_id: int | None = None) -> None:
    rows = db.session.scalars(select(GameExperienceTemplate)).all()
    for row in rows:
        if ignore_id is not None and row.id == ignore_id:
            continue
        if row.template_id == normalized.template_id:
            raise GameContentConflictError("template_id already exists.")
        if row.slug == normalized.slug:
            raise GameContentConflictError("slug already exists.")



def create_experience(*, payload: dict, actor_user_id: int | None = None, source: str = "authored") -> dict:
    normalized = _canonicalize_payload(payload)
    _ensure_unique(normalized)
    entity = GameExperienceTemplate(
        template_id=normalized.template_id,
        slug=normalized.slug,
        title=normalized.title,
        kind=normalized.kind,
        summary=normalized.summary,
        style_profile=normalized.style_profile,
        tags_json=normalized.tags,
        payload_json=normalized.payload,
        source=source,
        version=1,
        is_published=False,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.session.add(entity)
    db.session.commit()
    return entity.to_dict(include_payload=True)



def update_experience(experience_id: int, *, payload: dict, actor_user_id: int | None = None) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    normalized = _canonicalize_payload(payload)
    _ensure_unique(normalized, ignore_id=experience_id)
    entity.template_id = normalized.template_id
    entity.slug = normalized.slug
    entity.title = normalized.title
    entity.kind = normalized.kind
    entity.summary = normalized.summary
    entity.style_profile = normalized.style_profile
    entity.tags_json = normalized.tags
    entity.payload_json = normalized.payload
    entity.updated_by_user_id = actor_user_id
    entity.version = int(entity.version or 0) + 1
    entity.updated_at = _now()
    db.session.commit()
    return entity.to_dict(include_payload=True)



def publish_experience(experience_id: int, *, actor_user_id: int | None = None) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    entity.is_published = True
    entity.published_at = _now()
    entity.updated_by_user_id = actor_user_id
    entity.updated_at = _now()
    db.session.commit()
    return entity.to_dict(include_payload=True)



def list_published_experience_payloads() -> list[dict]:
    ensure_default_game_content_seeded()
    rows = db.session.scalars(
        select(GameExperienceTemplate)
        .where(GameExperienceTemplate.is_published.is_(True))
        .order_by(GameExperienceTemplate.published_at.desc().nullslast(), GameExperienceTemplate.id.asc())
    ).all()
    return [dict(row.payload_json or {}) for row in rows]
