"""Feature-to-area mapping: which areas can access which admin/dashboard/view feature."""
from app.extensions import db


class FeatureArea(db.Model):
    """
    Assigns an area to a feature (view/action). A feature can have multiple areas.
    If a feature has no rows, it is treated as global (all areas). User can access
    if they have role/level and (user has area 'all' or user has one of these areas).
    """
    __tablename__ = "feature_areas"

    feature_id = db.Column(db.String(128), primary_key=True, nullable=False)
    area_id = db.Column(db.Integer, db.ForeignKey("areas.id", ondelete="CASCADE"), primary_key=True, nullable=False)

    area_rel = db.relationship("Area", backref=db.backref("feature_areas", lazy="dynamic", cascade="all, delete-orphan"))
