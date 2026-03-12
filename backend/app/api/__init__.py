"""Register API v1 blueprint with the app."""
from app.api.v1 import api_v1_bp


def register_api(app):
    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")
