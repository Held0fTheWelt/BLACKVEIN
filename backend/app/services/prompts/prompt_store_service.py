"""Prompt Store service: seed files, editable rows, and runtime bundles."""

from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path
from typing import Any

from flask import current_app

from ai_stack.prompt_store import PromptDefinition, load_prompt_files
from app.extensions import db
from app.governance.errors import governance_error
from app.models import PromptStorePrompt
from app.utils.time_utils import utc_now


PROMPT_STORE_BUNDLE_VERSION = "prompt_store_bundle.v1"


def _content_hash(template: str) -> str:
    return sha256(str(template or "").encode("utf-8")).hexdigest()


def _repo_root() -> Path:
    configured = (current_app.config.get("WOS_REPO_ROOT") or os.getenv("WOS_REPO_ROOT") or "").strip()
    if configured:
        return Path(configured)
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "backend" / "app").is_dir() and (parent / "prompts").is_dir():
            return parent
    return current.parents[4]


def default_prompt_seed_root() -> Path:
    configured = (
        current_app.config.get("WOS_PROMPT_STORE_DIR")
        or os.getenv("WOS_PROMPT_STORE_DIR")
        or ""
    ).strip()
    if configured:
        return Path(configured)
    return _repo_root() / "prompts"


def _row_from_definition(definition: PromptDefinition, *, actor: str) -> PromptStorePrompt:
    now = utc_now()
    content_hash = definition.content_hash
    return PromptStorePrompt(
        prompt_key=definition.prompt_key,
        name=definition.name,
        description=definition.description,
        category=definition.category,
        prompt_type=definition.prompt_type,
        domain=definition.domain,
        template=definition.template,
        variables_json=list(definition.variables),
        tags_json=list(definition.tags),
        metadata_json=dict(definition.metadata or {}),
        source_path=definition.source_path,
        source_symbol=definition.source_symbol,
        seed_version=definition.seed_version,
        seed_content_hash=content_hash,
        current_content_hash=content_hash,
        is_active=True,
        is_editable=True,
        is_seeded=True,
        last_seeded_at=now,
        created_at=now,
        updated_at=now,
        updated_by=actor,
    )


def seed_prompt_store_from_files(
    *,
    root: Path | str | None = None,
    overwrite: bool = False,
    actor: str = "system",
) -> dict[str, Any]:
    """Seed prompts from JSON files.

    Existing DB rows are preserved by default so live edits survive container
    rebuilds. Set overwrite=True for deterministic test/refresh environments.
    """
    seed_root = Path(root) if root is not None else default_prompt_seed_root()
    definitions = load_prompt_files(seed_root)
    inserted = 0
    updated = 0
    skipped = 0
    for definition in definitions:
        row = db.session.get(PromptStorePrompt, definition.prompt_key)
        now = utc_now()
        if row is None:
            db.session.add(_row_from_definition(definition, actor=actor))
            inserted += 1
            continue
        if not overwrite:
            skipped += 1
            continue
        row.name = definition.name
        row.description = definition.description
        row.category = definition.category
        row.prompt_type = definition.prompt_type
        row.domain = definition.domain
        row.template = definition.template
        row.variables_json = list(definition.variables)
        row.tags_json = list(definition.tags)
        row.metadata_json = dict(definition.metadata or {})
        row.source_path = definition.source_path
        row.source_symbol = definition.source_symbol
        row.seed_version = definition.seed_version
        row.seed_content_hash = definition.content_hash
        row.current_content_hash = definition.content_hash
        row.is_seeded = True
        row.last_seeded_at = now
        row.updated_at = now
        row.updated_by = actor
        updated += 1
    db.session.commit()
    return {
        "seed_root": str(seed_root),
        "overwrite": bool(overwrite),
        "loaded": len(definitions),
        "inserted": inserted,
        "updated": updated,
        "skipped_existing": skipped,
    }


def _prompt_query():
    return PromptStorePrompt.query.order_by(
        PromptStorePrompt.category.asc(),
        PromptStorePrompt.name.asc(),
        PromptStorePrompt.prompt_key.asc(),
    )


def _row_matches_tag(row: PromptStorePrompt, tag: str | None) -> bool:
    if not tag:
        return True
    needle = tag.strip().lower()
    return any(str(item).strip().lower() == needle for item in (row.tags_json or []))


def _row_matches_search(row: PromptStorePrompt, search: str | None) -> bool:
    needle = (search or "").strip().lower()
    if not needle:
        return True
    haystack = [
        row.prompt_key,
        row.name,
        row.description,
        row.category,
        row.prompt_type,
        row.domain,
        " ".join(str(item) for item in (row.tags_json or [])),
    ]
    return any(needle in str(value or "").lower() for value in haystack)


def list_prompt_records(
    *,
    category: str | None = None,
    prompt_type: str | None = None,
    domain: str | None = None,
    tag: str | None = None,
    drift: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    query = _prompt_query()
    if category:
        query = query.filter(PromptStorePrompt.category == category)
    if prompt_type:
        query = query.filter(PromptStorePrompt.prompt_type == prompt_type)
    if domain:
        query = query.filter(PromptStorePrompt.domain == domain)
    rows = query.all()
    rows = [row for row in rows if _row_matches_tag(row, tag) and _row_matches_search(row, search)]
    if drift == "edited":
        rows = [
            row
            for row in rows
            if row.seed_content_hash and row.current_content_hash and row.seed_content_hash != row.current_content_hash
        ]
    elif drift == "seed":
        rows = [
            row
            for row in rows
            if not row.seed_content_hash or row.seed_content_hash == row.current_content_hash
        ]
    categories = sorted({row.category for row in PromptStorePrompt.query.all()})
    prompt_types = sorted({row.prompt_type for row in PromptStorePrompt.query.all()})
    domains = sorted({row.domain for row in PromptStorePrompt.query.all()})
    tags = sorted(
        {
            str(tag).strip()
            for row in PromptStorePrompt.query.all()
            for tag in (row.tags_json or [])
            if str(tag).strip()
        }
    )
    return {
        "prompts": [row.to_dict(include_template=False) for row in rows],
        "categories": categories,
        "prompt_types": prompt_types,
        "domains": domains,
        "tags": tags,
        "count": len(rows),
    }


def get_prompt_record(prompt_key: str) -> dict[str, Any]:
    row = db.session.get(PromptStorePrompt, prompt_key)
    if row is None:
        raise governance_error("prompt_not_found", "Prompt not found.", 404, {"prompt_key": prompt_key})
    return row.to_dict(include_template=True)


def update_prompt_record(prompt_key: str, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    row = db.session.get(PromptStorePrompt, prompt_key)
    if row is None:
        raise governance_error("prompt_not_found", "Prompt not found.", 404, {"prompt_key": prompt_key})
    if not row.is_editable:
        raise governance_error("prompt_not_editable", "Prompt is not editable.", 409, {"prompt_key": prompt_key})

    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise governance_error("prompt_value_invalid", "Prompt name is required.", 400, {})
        row.name = name[:180]
    if "description" in payload:
        row.description = str(payload.get("description") or "").strip()
    if "category" in payload:
        category = str(payload.get("category") or "").strip()
        if not category:
            raise governance_error("prompt_value_invalid", "Prompt category is required.", 400, {})
        row.category = category[:96]
    if "prompt_type" in payload:
        prompt_type = str(payload.get("prompt_type") or "").strip()
        if not prompt_type:
            raise governance_error("prompt_value_invalid", "Prompt type is required.", 400, {})
        row.prompt_type = prompt_type[:64]
    if "domain" in payload:
        domain = str(payload.get("domain") or "").strip()
        if not domain:
            raise governance_error("prompt_value_invalid", "Prompt domain is required.", 400, {})
        row.domain = domain[:96]
    if "template" in payload:
        template = str(payload.get("template") or "")
        if not template.strip():
            raise governance_error("prompt_value_invalid", "Prompt template is required.", 400, {})
        row.template = template
        row.current_content_hash = _content_hash(template)
    if "variables" in payload:
        raw_variables = payload.get("variables")
        if not isinstance(raw_variables, list):
            raise governance_error("prompt_value_invalid", "variables must be a list.", 400, {})
        row.variables_json = [str(item).strip() for item in raw_variables if str(item).strip()]
    if "tags" in payload:
        raw_tags = payload.get("tags")
        if not isinstance(raw_tags, list):
            raise governance_error("prompt_value_invalid", "tags must be a list.", 400, {})
        row.tags_json = [str(item).strip() for item in raw_tags if str(item).strip()]
    if "metadata" in payload:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            raise governance_error("prompt_value_invalid", "metadata must be an object.", 400, {})
        row.metadata_json = metadata
    if "is_active" in payload:
        row.is_active = bool(payload.get("is_active"))

    row.updated_by = actor
    row.updated_at = utc_now()
    db.session.commit()
    return row.to_dict(include_template=True)


def get_active_prompt_bundle() -> dict[str, Any]:
    rows = PromptStorePrompt.query.filter_by(is_active=True).order_by(PromptStorePrompt.prompt_key.asc()).all()
    return {
        "schema_version": PROMPT_STORE_BUNDLE_VERSION,
        "generated_at": utc_now().isoformat(),
        "count": len(rows),
        "prompts": [row.to_dict(include_template=True) for row in rows],
    }


def get_prompt_store_status() -> dict[str, Any]:
    total = PromptStorePrompt.query.count()
    active = PromptStorePrompt.query.filter_by(is_active=True).count()
    seeded = PromptStorePrompt.query.filter_by(is_seeded=True).count()
    categories = sorted({row.category for row in PromptStorePrompt.query.all()})
    prompt_types = sorted({row.prompt_type for row in PromptStorePrompt.query.all()})
    domains = sorted({row.domain for row in PromptStorePrompt.query.all()})
    tags = sorted(
        {
            str(tag).strip()
            for row in PromptStorePrompt.query.all()
            for tag in (row.tags_json or [])
            if str(tag).strip()
        }
    )
    return {
        "total_prompts": total,
        "active_prompts": active,
        "seeded_prompts": seeded,
        "categories": categories,
        "prompt_types": prompt_types,
        "domains": domains,
        "tags": tags,
        "seed_root": str(default_prompt_seed_root()),
        "seed_overwrite_default": bool(current_app.config.get("WOS_PROMPT_STORE_SEED_OVERWRITE", False)),
    }
