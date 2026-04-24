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
        # Ensure all database tables exist before initializing observability
        ensure_governance_baseline()

        # Only initialize observability if tables are ready
        try:
            _initialize_observability(app)
        except Exception as e:
            print(f"[WARN] Could not initialize observability: {e}; using no-op adapter")
            from app.observability.langfuse_adapter import LangfuseAdapter
            app.langfuse_adapter = LangfuseAdapter()

    csrf = CSRFProtect(app)
    from app.api.v1 import api_v1_bp

    csrf.exempt(api_v1_bp)

    # Register teardown handler for Langfuse shutdown
    @app.teardown_appcontext
    def _shutdown_observability(exc=None):
        if hasattr(app, 'langfuse_adapter'):
            try:
                app.langfuse_adapter.shutdown()
            except Exception:
                pass

    return app


def _initialize_observability(app: Flask) -> None:
    """Initialize Langfuse observability adapter from database configuration."""
    try:
        from app.observability.langfuse_adapter import LangfuseAdapter, LangfuseConfig
        from app.services.observability_governance_service import (
            get_observability_config,
            get_observability_credential_for_runtime,
        )

        db_config = get_observability_config()

        if not db_config.get("is_enabled"):
            # Disabled: use no-op adapter (defaults from env)
            app.langfuse_adapter = LangfuseAdapter()
            print("[INFO] Langfuse observability is disabled (no-op mode)")
            return

        # Enabled: fetch credentials and initialize with custom config
        secret_key = get_observability_credential_for_runtime("secret_key")
        if not secret_key:
            print("[WARN] Langfuse enabled but secret_key not configured; using no-op adapter")
            app.langfuse_adapter = LangfuseAdapter()
            return

        public_key = get_observability_credential_for_runtime("public_key")

        # Create config object from database settings
        config = LangfuseConfig()
        config.enabled = True
        config.public_key = public_key or ""
        config.secret_key = secret_key
        config.host = db_config.get("base_url", "https://cloud.langfuse.com")
        config.environment = db_config.get("environment", "development")
        config.release = db_config.get("release", "unknown")
        config.sample_rate = float(db_config.get("sample_rate", 1.0))
        config.capture_prompts = db_config.get("capture_prompts", True)
        config.capture_outputs = db_config.get("capture_outputs", True)
        config.capture_retrieval = db_config.get("capture_retrieval", False)
        config.redaction_mode = db_config.get("redaction_mode", "strict")

        app.langfuse_adapter = LangfuseAdapter(config)
        print("[INFO] Langfuse observability initialized and ready")

    except Exception as e:
        print(f"[WARN] Failed to initialize Langfuse: {e}; using no-op adapter")
        from app.observability.langfuse_adapter import LangfuseAdapter

        app.langfuse_adapter = LangfuseAdapter()
