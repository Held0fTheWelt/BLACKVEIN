"""Conflict records for competing revision candidates."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeRevisionConflict(db.Model):
    """First-class conflict object for review governance."""

    __tablename__ = "narrative_revision_conflicts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    conflict_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    module_id = db.Column(db.String(128), nullable=False, index=True)
    candidate_ids_json = db.Column(db.JSON, nullable=False, default=list)
    conflict_type = db.Column(db.String(64), nullable=False)
    target_kind = db.Column(db.String(64), nullable=False)
    target_ref = db.Column(db.String(255), nullable=False)
    resolution_status = db.Column(db.String(32), nullable=False, default="pending", index=True)
    resolution_strategy = db.Column(db.String(64), nullable=True)
    winner_revision_id = db.Column(db.String(64), nullable=True)
    resolved_by = db.Column(db.String(128), nullable=True)
    resolved_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    __table_args__ = (
        db.Index(
            "ix_narrative_revision_conflicts_module_target",
            "module_id",
            "target_kind",
            "target_ref",
        ),
    )

    def to_dict(self) -> dict[str, str | list[str] | None]:
        """Serialize conflict row."""
        return {
            "conflict_id": self.conflict_id,
            "module_id": self.module_id,
            "candidate_ids": [str(item) for item in (self.candidate_ids_json or [])],
            "conflict_type": self.conflict_type,
            "target_kind": self.target_kind,
            "target_ref": self.target_ref,
            "resolution_status": self.resolution_status,
            "resolution_strategy": self.resolution_strategy,
            "winner_revision_id": self.winner_revision_id,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
