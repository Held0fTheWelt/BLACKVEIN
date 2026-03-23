from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class GameSaveSlot(db.Model):
    __tablename__ = "game_save_slots"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    character_id = db.Column(db.Integer, db.ForeignKey("game_characters.id", ondelete="SET NULL"), nullable=True, index=True)
    slot_key = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(140), nullable=False)
    template_id = db.Column(db.String(120), nullable=False, index=True)
    template_title = db.Column(db.String(160), nullable=True)
    run_id = db.Column(db.String(120), nullable=True, index=True)
    kind = db.Column(db.String(40), nullable=True)
    status = db.Column(db.String(40), nullable=False, default="active")
    metadata_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)
    last_played_at = db.Column(db.DateTime(timezone=True), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("user_id", "slot_key", name="uq_game_save_slots_user_slot_key"),
    )

    user = db.relationship("User", backref=db.backref("game_save_slots", lazy="dynamic", cascade="all, delete-orphan"))
    character = db.relationship("GameCharacter", backref=db.backref("save_slots", lazy="dynamic"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "slot_key": self.slot_key,
            "title": self.title,
            "template_id": self.template_id,
            "template_title": self.template_title,
            "run_id": self.run_id,
            "kind": self.kind,
            "status": self.status,
            "metadata": self.metadata_json or {},
            "last_played_at": self.last_played_at.isoformat() if self.last_played_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<GameSaveSlot id={self.id} user_id={self.user_id} slot_key={self.slot_key!r}>"
