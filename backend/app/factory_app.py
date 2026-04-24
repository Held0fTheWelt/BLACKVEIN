"""Flask application factory (DS-042); wiring in dedicated factory_* modules."""

from __future__ import annotations

from flask import Flask
from flask_wtf.csrf import CSRFProtect

from app.api import register_api
from app.config import Config, TestingConfig
from app.extensions import init_app as init_extensions, limiter
from app.factory_background import schedule_token_blacklist_cleanup
from app.factory_http_shell import register_http_shell
from app.factory_secrets_and_logging import configure_app_secrets_jwt_and_logging
from app.info import info_bp
from app.web import web_bp


def create_app(config_object=None, *, testing: bool | None = None):
    app = Flask(__name__)
    resolved_config = config_object
    if resolved_config is None and testing is True:
        resolved_config = TestingConfig
    app.config.from_object(resolved_config or Config)
    configure_app_secrets_jwt_and_logging(app)

    init_extensions(app)
    limiter.default_limits = [app.config.get("RATELIMIT_DEFAULT", "100 per minute")]

    from app.services.play_service_control_service import (
        bootstrap_play_service_control,
        validate_play_service_env_pairing,
    )

    bootstrap_play_service_control(app)
    validate_play_service_env_pairing(app)

    schedule_token_blacklist_cleanup(app)

    register_http_shell(app)

    app.register_blueprint(info_bp, url_prefix="/backend")
    app.register_blueprint(web_bp)
    register_api(app)

    from app.runtime.routing_registry_bootstrap import init_routing_registry_bootstrap

    init_routing_registry_bootstrap(app)

    from app.services.governance_runtime_service import ensure_governance_baseline

    with app.app_context():
        ensure_governance_baseline()

    csrf = CSRFProtect(app)
    from app.api.v1 import api_v1_bp

    csrf.exempt(api_v1_bp)

    return app
