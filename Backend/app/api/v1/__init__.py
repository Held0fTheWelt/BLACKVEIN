from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

# Import after blueprint exists to register routes
from app.api.v1 import auth_routes  # noqa: F401, E402
from app.api.v1 import system_routes  # noqa: F401, E402
