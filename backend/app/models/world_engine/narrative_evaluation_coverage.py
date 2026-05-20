"""Coverage summaries linked to evaluation runs."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeEvaluationCoverage(db.Model):
    """Normalized coverage metrics per run and coverage kind."""

    __tablename__ = "narrative_evaluation_coverage"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id = db.Column(db.String(64), nullable=False, index=True)
    coverage_kind = db.Column(db.String(64), nullable=False)
    covered_count = db.Column(db.Integer, nullable=False)
    total_count = db.Column(db.Integer, nullable=False)
    coverage_percentage = db.Column(db.Float, nullable=False)
    missing_refs_json = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    __table_args__ = (
        db.Index("ix_narrative_evaluation_coverage_run_kind", "run_id", "coverage_kind"),
    )

    def to_dict(self) -> dict[str, str | int | float | list[str] | None]:
        """Serialize coverage row."""
        return {
            "run_id": self.run_id,
            "coverage_kind": self.coverage_kind,
            "covered_count": self.covered_count,
            "total_count": self.total_count,
            "coverage_percentage": self.coverage_percentage,
            "missing_refs": [str(item) for item in (self.missing_refs_json or [])],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
