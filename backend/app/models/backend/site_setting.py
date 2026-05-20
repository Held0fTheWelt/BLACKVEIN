"""Key-value site settings (admin-editable)."""
from app.extensions import db


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.Text(), nullable=True)
