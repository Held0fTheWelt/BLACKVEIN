"""Preview package registry rows."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativePreview(db.Model):
    """Isolated preview package lifecycle state."""

    __tablename__ = "narrative_previews"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    preview_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    module_id = db.Column(db.String(128), nullable=False, index=True)
    package_version = db.Column(db.String(64), nullable=False)
    draft_workspace_id = db.Column(db.String(128), nullable=True)
    build_status = db.Column(db.String(32), nullable=False, index=True)
    validation_status = db.Column(db.String(32), nullable=False, default="unknown")
    evaluation_status = db.Column(db.String(32), nullable=False, default="not_run", index=True)
    promotion_readiness_json = db.Column(db.JSON, nullable=False, default=dict)
    artifact_root_path = db.Column(db.String(512), nullable=False)
    created_by = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    def to_dict(self) -> dict[str, str | int | dict[str, object] | None]:
        """Serialize preview row."""
        return {
            "id": self.id,
            "preview_id": self.preview_id,
            "module_id": self.module_id,
            "package_version": self.package_version,
            "draft_workspace_id": self.draft_workspace_id,
            "build_status": self.build_status,
            "validation_status": self.validation_status,
            "evaluation_status": self.evaluation_status,
            "promotion_readiness": self.promotion_readiness_json or {},
            "artifact_root_path": self.artifact_root_path,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
