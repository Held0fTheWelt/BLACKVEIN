from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from sqlalchemy import or_, select

from app.content.builtins import build_god_of_carnage_solo
from app.content.compiler import compile_module
from app.content.module_exceptions import ModuleLoadError
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


class GameContentLifecycleError(GameContentError):
    """Raised when a lifecycle transition or publish gate is violated."""

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        content_lifecycle: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.content_lifecycle = content_lifecycle


CONTENT_LIFECYCLE_DRAFT = "draft"
CONTENT_LIFECYCLE_REVIEW_PENDING = "review_pending"
CONTENT_LIFECYCLE_REVISION_REQUESTED = "revision_requested"
CONTENT_LIFECYCLE_APPROVED = "approved"
CONTENT_LIFECYCLE_REJECTED = "rejected"
CONTENT_LIFECYCLE_PUBLISHABLE = "publishable"
CONTENT_LIFECYCLE_PUBLISHED = "published"
CONTENT_LIFECYCLE_UNPUBLISHED = "unpublished"
CONTENT_LIFECYCLE_ARCHIVED = "archived"

CONTENT_LIFECYCLES = frozenset(
    {
        CONTENT_LIFECYCLE_DRAFT,
        CONTENT_LIFECYCLE_REVIEW_PENDING,
        CONTENT_LIFECYCLE_REVISION_REQUESTED,
        CONTENT_LIFECYCLE_APPROVED,
        CONTENT_LIFECYCLE_REJECTED,
        CONTENT_LIFECYCLE_PUBLISHABLE,
        CONTENT_LIFECYCLE_PUBLISHED,
        CONTENT_LIFECYCLE_UNPUBLISHED,
        CONTENT_LIFECYCLE_ARCHIVED,
    }
)

ORIGIN_CANONICAL_AUTHORED = "canonical_authored"
ORIGIN_WRITERS_ROOM_WORKFLOW = "writers_room_workflow"
ORIGIN_IMPROVEMENT_WORKFLOW = "improvement_workflow"
ORIGIN_DERIVED_CANDIDATE = "derived_candidate"
ORIGIN_PUBLISHED_BUNDLE_REIMPORT = "published_bundle_reimport"

ORIGIN_KINDS = frozenset(
    {
        ORIGIN_CANONICAL_AUTHORED,
        ORIGIN_WRITERS_ROOM_WORKFLOW,
        ORIGIN_IMPROVEMENT_WORKFLOW,
        ORIGIN_DERIVED_CANDIDATE,
        ORIGIN_PUBLISHED_BUNDLE_REIMPORT,
    }
)


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
    if isinstance(payload.get("canonical_compilation"), dict):
        canonical["canonical_compilation"] = payload["canonical_compilation"]
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


def _iso_now() -> str:
    return _now().isoformat()


def _governance_provenance_dict(entity: GameExperienceTemplate) -> dict[str, Any]:
    raw = entity.governance_provenance_json
    if not isinstance(raw, dict):
        return {"origin_kind": ORIGIN_CANONICAL_AUTHORED, "lifecycle_history": []}
    base = deepcopy(raw)
    if "lifecycle_history" not in base or not isinstance(base["lifecycle_history"], list):
        base["lifecycle_history"] = []
    if "origin_kind" not in base:
        base["origin_kind"] = ORIGIN_CANONICAL_AUTHORED
    return base


def _set_governance_provenance(entity: GameExperienceTemplate, prov: dict[str, Any]) -> None:
    entity.governance_provenance_json = prov


def _append_lifecycle_event(
    entity: GameExperienceTemplate,
    *,
    action: str,
    from_lifecycle: str,
    to_lifecycle: str,
    actor_user_id: int | None,
    note: str | None = None,
) -> None:
    prov = _governance_provenance_dict(entity)
    history = prov["lifecycle_history"]
    history.append(
        {
            "at": _iso_now(),
            "action": action,
            "from": from_lifecycle,
            "to": to_lifecycle,
            "by_user_id": actor_user_id,
            "note": (note or "")[:2000],
        }
    )
    prov["lifecycle_history"] = history
    _set_governance_provenance(entity, prov)


def validate_and_merge_governance_provenance(
    base: dict[str, Any] | None,
    *,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return merged provenance for persistence (origin_kind + optional refs + lifecycle_history)."""
    merged: dict[str, Any] = deepcopy(base) if isinstance(base, dict) else {}
    if "lifecycle_history" not in merged or not isinstance(merged["lifecycle_history"], list):
        merged["lifecycle_history"] = []
    if override:
        if not isinstance(override, dict):
            raise GameContentValidationError("governance_provenance must be an object")
        ok = str(override.get("origin_kind") or "").strip()
        if ok and ok not in ORIGIN_KINDS:
            raise GameContentValidationError(f"invalid governance_provenance.origin_kind: {ok!r}")
        if ok:
            merged["origin_kind"] = ok
        for key in ("writers_room_review_id", "improvement_package_id", "variant_id", "notes"):
            if key in override and override[key] is not None:
                val = override[key]
                if key == "notes":
                    merged[key] = str(val)[:5000]
                else:
                    merged[key] = str(val).strip()[:500]
    if "origin_kind" not in merged:
        merged["origin_kind"] = ORIGIN_CANONICAL_AUTHORED
    return merged


def _is_seed_publish_bypass(entity: GameExperienceTemplate) -> bool:
    return entity.template_id == "god_of_carnage_solo" and entity.source == "authored_seed"


def _resolve_canonical_module_id(template_id: str) -> str | None:
    if not template_id:
        return None
    if template_id == "god_of_carnage_solo":
        return "god_of_carnage"
    return template_id


def _attach_canonical_compilation(payload: dict) -> dict:
    template_id = str(payload.get("id") or "").strip()
    module_id = _resolve_canonical_module_id(template_id)
    if not module_id:
        return payload

    try:
        compiled = compile_module(module_id)
    except ModuleLoadError:
        return payload
    except Exception as exc:  # pragma: no cover - fail loudly for unknown compiler errors
        raise GameContentValidationError(f"failed to compile canonical module '{module_id}': {exc}") from exc

    result = dict(payload)
    result["canonical_compilation"] = {
        "canonical_model": compiled.canonical_model,
        "module_id": module_id,
        "runtime_projection": compiled.runtime_projection.model_dump(mode="json"),
        "retrieval_corpus_seed": compiled.retrieval_corpus_seed.model_dump(mode="json"),
        "review_export_seed": compiled.review_export_seed.model_dump(mode="json"),
        # VERTICAL_SLICE_CONTRACT_GOC.md §6.1 — YAML module tree is sole canonical dramatic source.
        "canonical_content_authority": f"content/modules/{module_id}/",
    }
    return result


def ensure_default_game_content_seeded() -> None:
    existing = db.session.execute(select(GameExperienceTemplate.id).limit(1)).scalar_one_or_none()
    if existing is not None:
        return
    payload = _attach_canonical_compilation(build_god_of_carnage_solo().model_dump(mode="json"))
    normalized = _canonicalize_payload(payload)
    seed_prov = validate_and_merge_governance_provenance(
        {"origin_kind": ORIGIN_CANONICAL_AUTHORED, "lifecycle_history": []},
        override=None,
    )
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
        content_lifecycle=CONTENT_LIFECYCLE_PUBLISHED,
        governance_provenance_json=seed_prov,
    )
    db.session.add(entity)
    db.session.commit()


def list_experiences(
    *,
    include_payload: bool = False,
    q: str | None = None,
    status: str | None = None,
    lifecycle: str | None = None,
) -> list[dict]:
    ensure_default_game_content_seeded()
    stmt = select(GameExperienceTemplate).order_by(GameExperienceTemplate.created_at.asc())
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                GameExperienceTemplate.title.ilike(needle),
                GameExperienceTemplate.template_id.ilike(needle),
                GameExperienceTemplate.slug.ilike(needle),
            )
        )
    if status:
        s = status.strip().lower()
        if s == "published":
            stmt = stmt.where(GameExperienceTemplate.is_published.is_(True))
        elif s == "draft":
            stmt = stmt.where(GameExperienceTemplate.is_published.is_(False))
    if lifecycle:
        lc = lifecycle.strip().lower()
        if lc in CONTENT_LIFECYCLES:
            stmt = stmt.where(GameExperienceTemplate.content_lifecycle == lc)
    rows = db.session.scalars(stmt).all()
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


def create_experience(
    *,
    payload: dict,
    actor_user_id: int | None = None,
    source: str = "authored",
    governance_provenance: dict[str, Any] | None = None,
) -> dict:
    normalized = _canonicalize_payload(_attach_canonical_compilation(payload))
    _ensure_unique(normalized)
    prov = validate_and_merge_governance_provenance(
        {"origin_kind": ORIGIN_CANONICAL_AUTHORED, "lifecycle_history": []},
        override=governance_provenance,
    )
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
        content_lifecycle=CONTENT_LIFECYCLE_DRAFT,
        governance_provenance_json=prov,
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
    was_published = bool(entity.is_published) or entity.content_lifecycle == CONTENT_LIFECYCLE_PUBLISHED
    normalized = _canonicalize_payload(_attach_canonical_compilation(payload))
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
    # Editing live content invalidates publication; draft must be re-governed before publish.
    if was_published:
        prev = entity.content_lifecycle or CONTENT_LIFECYCLE_DRAFT
        entity.is_published = False
        entity.published_at = None
        entity.content_lifecycle = CONTENT_LIFECYCLE_DRAFT
        _append_lifecycle_event(
            entity,
            action="content_edit_invalidates_publication",
            from_lifecycle=prev,
            to_lifecycle=CONTENT_LIFECYCLE_DRAFT,
            actor_user_id=actor_user_id,
            note="Payload updated while published; experience returned to draft and taken offline.",
        )
    db.session.commit()
    return entity.to_dict(include_payload=True)


def submit_experience_for_review(experience_id: int, *, actor_user_id: int | None = None, note: str | None = None) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    cur = entity.content_lifecycle or CONTENT_LIFECYCLE_DRAFT
    if cur not in (
        CONTENT_LIFECYCLE_DRAFT,
        CONTENT_LIFECYCLE_REVISION_REQUESTED,
        CONTENT_LIFECYCLE_UNPUBLISHED,
    ):
        raise GameContentLifecycleError(
            f"Cannot submit for review from lifecycle {cur!r}.",
            code="invalid_lifecycle_transition",
            content_lifecycle=cur,
        )
    entity.content_lifecycle = CONTENT_LIFECYCLE_REVIEW_PENDING
    _append_lifecycle_event(
        entity,
        action="submit_for_review",
        from_lifecycle=cur,
        to_lifecycle=CONTENT_LIFECYCLE_REVIEW_PENDING,
        actor_user_id=actor_user_id,
        note=note,
    )
    entity.updated_by_user_id = actor_user_id
    entity.updated_at = _now()
    db.session.commit()
    return entity.to_dict(include_payload=True)


def apply_editorial_decision(
    experience_id: int,
    *,
    decision: str,
    actor_user_id: int | None = None,
    note: str | None = None,
) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    cur = entity.content_lifecycle or CONTENT_LIFECYCLE_DRAFT
    if cur != CONTENT_LIFECYCLE_REVIEW_PENDING:
        raise GameContentLifecycleError(
            f"Editorial decision allowed only in review_pending; current={cur!r}.",
            code="invalid_lifecycle_transition",
            content_lifecycle=cur,
        )
    norm = decision.strip().lower()
    if norm == "approve":
        nxt = CONTENT_LIFECYCLE_APPROVED
        action = "editorial_approve"
    elif norm == "reject":
        nxt = CONTENT_LIFECYCLE_REJECTED
        action = "editorial_reject"
    elif norm in ("request_revision", "revise"):
        nxt = CONTENT_LIFECYCLE_REVISION_REQUESTED
        action = "editorial_request_revision"
    else:
        raise GameContentValidationError("decision must be approve, reject, or request_revision")
    entity.content_lifecycle = nxt
    _append_lifecycle_event(
        entity,
        action=action,
        from_lifecycle=cur,
        to_lifecycle=nxt,
        actor_user_id=actor_user_id,
        note=note,
    )
    entity.updated_by_user_id = actor_user_id
    entity.updated_at = _now()
    db.session.commit()
    return entity.to_dict(include_payload=True)


def mark_experience_publishable(experience_id: int, *, actor_user_id: int | None = None, note: str | None = None) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    cur = entity.content_lifecycle or CONTENT_LIFECYCLE_DRAFT
    if cur != CONTENT_LIFECYCLE_APPROVED:
        raise GameContentLifecycleError(
            f"mark_publishable requires approved; current={cur!r}.",
            code="invalid_lifecycle_transition",
            content_lifecycle=cur,
        )
    entity.content_lifecycle = CONTENT_LIFECYCLE_PUBLISHABLE
    _append_lifecycle_event(
        entity,
        action="mark_publishable",
        from_lifecycle=cur,
        to_lifecycle=CONTENT_LIFECYCLE_PUBLISHABLE,
        actor_user_id=actor_user_id,
        note=note,
    )
    entity.updated_by_user_id = actor_user_id
    entity.updated_at = _now()
    db.session.commit()
    return entity.to_dict(include_payload=True)


def publish_experience(experience_id: int, *, actor_user_id: int | None = None) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    cur = entity.content_lifecycle or CONTENT_LIFECYCLE_DRAFT
    if not _is_seed_publish_bypass(entity):
        if cur not in (CONTENT_LIFECYCLE_APPROVED, CONTENT_LIFECYCLE_PUBLISHABLE):
            raise GameContentLifecycleError(
                "Publish blocked until editorial approval (approved or publishable lifecycle).",
                code="lifecycle_blocks_publish",
                content_lifecycle=cur,
            )
    entity.payload_json = _attach_canonical_compilation(dict(entity.payload_json or {}))
    prev = cur
    entity.content_lifecycle = CONTENT_LIFECYCLE_PUBLISHED
    entity.is_published = True
    entity.published_at = _now()
    entity.updated_by_user_id = actor_user_id
    entity.updated_at = _now()
    _append_lifecycle_event(
        entity,
        action="publish",
        from_lifecycle=prev,
        to_lifecycle=CONTENT_LIFECYCLE_PUBLISHED,
        actor_user_id=actor_user_id,
        note=None,
    )
    db.session.commit()
    return entity.to_dict(include_payload=True)


def unpublish_experience(experience_id: int, *, actor_user_id: int | None = None, note: str | None = None) -> dict:
    entity = db.session.get(GameExperienceTemplate, experience_id)
    if entity is None:
        raise GameContentNotFoundError("Experience not found.")
    cur = entity.content_lifecycle or CONTENT_LIFECYCLE_DRAFT
    if cur != CONTENT_LIFECYCLE_PUBLISHED and not entity.is_published:
        raise GameContentLifecycleError(
            "Unpublish only applies to published experiences.",
            code="invalid_lifecycle_transition",
            content_lifecycle=cur,
        )
    prev = CONTENT_LIFECYCLE_PUBLISHED if cur == CONTENT_LIFECYCLE_PUBLISHED or entity.is_published else cur
    entity.is_published = False
    entity.published_at = None
    entity.content_lifecycle = CONTENT_LIFECYCLE_UNPUBLISHED
    _append_lifecycle_event(
        entity,
        action="unpublish",
        from_lifecycle=prev,
        to_lifecycle=CONTENT_LIFECYCLE_UNPUBLISHED,
        actor_user_id=actor_user_id,
        note=note,
    )
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
