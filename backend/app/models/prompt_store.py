"""Database-backed prompt store for live AI/runtime prompt editing."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now


class PromptStorePrompt(db.Model):
    """Editable prompt template plus seed/source metadata."""

    __tablename__ = "prompt_store_prompts"

    prompt_key = db.Column(db.String(160), primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text(), nullable=False, default="")
    category = db.Column(db.String(96), nullable=False, index=True)
    prompt_type = db.Column(db.String(64), nullable=False, default="runtime_prompt", index=True)
    domain = db.Column(db.String(96), nullable=False, default="ai_stack", index=True)
    template = db.Column(db.Text(), nullable=False)
    variables_json = db.Column(db.JSON, nullable=False, default=list)
    tags_json = db.Column(db.JSON, nullable=False, default=list)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    source_path = db.Column(db.String(512), nullable=False, default="")
    source_symbol = db.Column(db.String(256), nullable=False, default="")
    seed_version = db.Column(db.String(128), nullable=False, default="")
    seed_content_hash = db.Column(db.String(64), nullable=False, default="")
    current_content_hash = db.Column(db.String(64), nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_editable = db.Column(db.Boolean, nullable=False, default=True)
    is_seeded = db.Column(db.Boolean, nullable=False, default=True, index=True)
    last_seeded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
    updated_by = db.Column(db.String(128), nullable=True)

    def to_dict(self, *, include_template: bool = True) -> dict:
        payload = {
            "prompt_key": self.prompt_key,
            "id": self.prompt_key,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "prompt_type": self.prompt_type,
            "domain": self.domain,
            "variables": list(self.variables_json or []),
            "tags": list(self.tags_json or []),
            "metadata": dict(self.metadata_json or {}),
            "source_path": self.source_path,
            "source_symbol": self.source_symbol,
            "seed_version": self.seed_version,
            "seed_content_hash": self.seed_content_hash,
            "current_content_hash": self.current_content_hash,
            "is_active": bool(self.is_active),
            "is_editable": bool(self.is_editable),
            "is_seeded": bool(self.is_seeded),
            "last_seeded_at": self.last_seeded_at.isoformat() if self.last_seeded_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
            "template_length": len(self.template or ""),
        }
        if include_template:
            payload["template"] = self.template
        return payload
