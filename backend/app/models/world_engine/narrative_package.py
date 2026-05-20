"""Persistent package pointer rows for narrative governance."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativePackage(db.Model):
    """Active package metadata by module."""

    __tablename__ = "narrative_packages"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_id = db.Column(db.String(128), nullable=False, unique=True, index=True)
    active_package_version = db.Column(db.String(64), nullable=False, index=True)
    active_manifest_path = db.Column(db.String(512), nullable=False)
    active_package_path = db.Column(db.String(512), nullable=False)
    active_source_revision = db.Column(db.String(256), nullable=False)
    validation_status = db.Column(db.String(32), nullable=False, default="unknown")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    def to_dict(self) -> dict[str, str | int | None]:
        """Serialize row for API envelopes."""
        return {
            "id": self.id,
            "module_id": self.module_id,
            "active_package_version": self.active_package_version,
            "active_manifest_path": self.active_manifest_path,
            "active_package_path": self.active_package_path,
            "active_source_revision": self.active_source_revision,
            "validation_status": self.validation_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
