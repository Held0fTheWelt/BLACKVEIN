"""Flask extensions; init_app(app) called from create_app."""
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_migrate import Migrate
from flask_mail import Mail

db = SQLAlchemy()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address, default_limits=[])
migrate = Migrate()
mail = Mail()


def init_app(app):
    """Bind extensions to app. CORS uses configurable origins from config."""
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    mail.init_app(app)
    if not app.config.get("TESTING"):
        migrate.init_app(app, db)
    origins = app.config.get("CORS_ORIGINS")
    if origins:
        CORS(
            app,
            origins=origins,
            allow_headers=["Content-Type", "Authorization"],
            expose_headers=["Content-Type"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            supports_credentials=False,
        )
