"""Backend runtime session persistence model.

Stores session metadata for cross-worker access in multi-process deployments.
Complements the volatile in-memory RuntimeSession wrapper with durable storage.
"""

from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSON
import json
from app.extensions import db


class RuntimeSessionRecord(db.Model):
    """Durable record of a backend runtime session.

    Allows sessions created in one worker process to be retrieved by another.
    Stores the minimal metadata needed for turn execution routing to World-Engine.
    """

    __tablename__ = "runtime_sessions"

    session_id = db.Column(db.String(64), primary_key=True)
    module_id = db.Column(db.String(120), nullable=False)
    module_version = db.Column(db.String(32), nullable=False, default="1.0.0")

    # Metadata about the session (stored as JSON)
    session_metadata = db.Column(JSON, nullable=False, default={})

    # Canonical state snapshot (stored as JSON)
    canonical_state = db.Column(JSON, nullable=False, default={})

    # Current scene in the module
    current_scene_id = db.Column(db.String(120), nullable=False)

    # Session status
    status = db.Column(db.String(32), nullable=False, default="active")

    # Turn counter
    turn_counter = db.Column(db.Integer, nullable=False, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "module_id": self.module_id,
            "module_version": self.module_version,
            "metadata": self.session_metadata or {},
            "canonical_state": self.canonical_state or {},
            "current_scene_id": self.current_scene_id,
            "status": self.status,
            "turn_counter": self.turn_counter,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
