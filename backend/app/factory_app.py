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

    # Import all models to register them with SQLAlchemy metadata
    from app.models import (
        ObservabilityConfig, ObservabilityCredential
    )

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
            app.langfuse_adapter = LangfuseAdapter.get_instance()

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
    """Initialize Langfuse observability adapter from database configuration, with env var fallback."""
    try:
        import os
        from sqlalchemy import inspect as _sa_inspect
        from app.observability.langfuse_adapter import LangfuseAdapter
        from app.extensions import db

        _inspector = _sa_inspect(db.engine)
        if not _inspector.has_table("observability_configs"):
            # Table not yet created (e.g., test environment before db.create_all())
            app.langfuse_adapter = LangfuseAdapter.get_instance()
            return

        from app.observability.langfuse_adapter import LangfuseConfig
        from app.services.observability_governance_service import (
            get_observability_config,
            get_observability_credential_for_runtime,
        )

        db_config = get_observability_config()

        # Check environment variables as fallback for local development/testing
        env_enabled = os.getenv("LANGFUSE_ENABLED", "").lower() in ("true", "1", "yes")
        env_secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
        env_public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
        env_base_url = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com").strip()

        # Use env vars if database config is disabled but env vars are provided
        if not db_config.get("is_enabled") and (env_enabled or env_secret_key):
            config = LangfuseConfig()
            config.enabled = env_enabled or bool(env_secret_key)
            config.public_key = env_public_key
            config.secret_key = env_secret_key
            config.base_url = env_base_url
            config.environment = os.getenv("LANGFUSE_ENVIRONMENT", "development")
            config.release = os.getenv("LANGFUSE_RELEASE", "unknown")
            config.sample_rate = float(os.getenv("LANGFUSE_SAMPLE_RATE", "1.0"))
            config.capture_prompts = os.getenv("LANGFUSE_CAPTURE_PROMPTS", "true").lower() in ("true", "1")
            config.capture_outputs = os.getenv("LANGFUSE_CAPTURE_OUTPUTS", "true").lower() in ("true", "1")
            config.capture_retrieval = os.getenv("LANGFUSE_CAPTURE_RETRIEVAL", "false").lower() in ("true", "1")
            config.redaction_mode = os.getenv("LANGFUSE_REDACTION_MODE", "strict")

            app.langfuse_adapter = LangfuseAdapter.get_instance(config)
            print("[INFO] Langfuse observability initialized from environment variables")
            return

        if not db_config.get("is_enabled"):
            app.langfuse_adapter = LangfuseAdapter.get_instance()
            print("[INFO] Langfuse observability is disabled (no-op mode)")
            return

        secret_key = get_observability_credential_for_runtime("secret_key")
        if not secret_key:
            print("[WARN] Langfuse enabled but secret_key not configured; using no-op adapter")
            app.langfuse_adapter = LangfuseAdapter.get_instance()
            return

        public_key = get_observability_credential_for_runtime("public_key")

        config = LangfuseConfig()
        config.enabled = True
        config.public_key = public_key or ""
        config.secret_key = secret_key
        config.base_url = db_config.get("base_url", "https://cloud.langfuse.com")
        config.environment = db_config.get("environment", "development")
        config.release = db_config.get("release", "unknown")
        config.sample_rate = float(db_config.get("sample_rate", 1.0))
        config.capture_prompts = db_config.get("capture_prompts", True)
        config.capture_outputs = db_config.get("capture_outputs", True)
        config.capture_retrieval = db_config.get("capture_retrieval", False)
        config.redaction_mode = db_config.get("redaction_mode", "strict")

        app.langfuse_adapter = LangfuseAdapter.get_instance(config)
        print("[INFO] Langfuse observability initialized and ready")

    except Exception as e:
        print(f"[WARN] Failed to initialize Langfuse: {e}; using no-op adapter")
        from app.observability.langfuse_adapter import LangfuseAdapter

        app.langfuse_adapter = LangfuseAdapter.get_instance()
