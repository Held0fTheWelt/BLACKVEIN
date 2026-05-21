from __future__ import annotations

from .common import *
from .models import *

@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def ready(request: Request, manager: RuntimeManager = Depends(get_manager)) -> dict[str, Any]:
    # Operator readiness diagnostic: provider secrets are governed by backend
    # AI Runtime Governance, not direct Compose env slots.
    import os as _os
    runtime_config = getattr(request.app.state, "resolved_runtime_config", None)
    providers = runtime_config.get("providers", []) if isinstance(runtime_config, dict) else []
    governed_provider_credentials_present = any(
        isinstance(provider, dict)
        and str(provider.get("provider_type") or "").strip().lower() not in {"mock", "ollama"}
        and bool(provider.get("credential_configured"))
        for provider in providers
    )
    lf_env_raw = (_os.environ.get("LANGFUSE_TRACING_ENVIRONMENT") or "").strip()
    lf_env_explicit = bool(lf_env_raw)
    resolved_env = lf_env_raw or "staging"  # matches resolve_langfuse_environment default fallback
    return {
        "status": "ready",
        "app": request.app.title,
        "store": manager.store.describe(),
        "template_count": len(manager.list_templates()),
        "run_count": len(manager.list_runs()),
        "operator_readiness": {
            "provider_credential_source": "backend_governance_or_secret_manager",
            "governed_provider_credentials_present": governed_provider_credentials_present,
            "openai_api_key_present": False,
            "langfuse_tracing_environment_explicit": lf_env_explicit,
            "resolved_langfuse_environment": resolved_env,
            "model_path_can_run_live": governed_provider_credentials_present,
        },
    }
