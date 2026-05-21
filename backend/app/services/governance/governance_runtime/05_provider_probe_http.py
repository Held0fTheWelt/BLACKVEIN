"""Governance runtime source segment: provider_probe_http.

Loaded by governance_runtime_service.py to keep service files small.
"""

SOURCE = r'''
        dek_nonce=row.dek_nonce,
    )


def _normalize_provider_url(base_url: str | None, contract: dict) -> str:
    base = (base_url or "").strip() or str(contract.get("default_base_url") or "").strip()
    if not base:
        return ""
    return base.rstrip("/")


_GENERATION_MODEL_ROLES = frozenset({"llm", "slm"})
_EMBEDDING_MODEL_ROLE = "embedding_role"
_EMBEDDING_ROUTE_TASK_KINDS = frozenset({"retrieval_embedding_generation"})
_MODEL_ROLE_ALIASES = {
    "embedding": _EMBEDDING_MODEL_ROLE,
    "embeddings": _EMBEDDING_MODEL_ROLE,
    "embedding_model": _EMBEDDING_MODEL_ROLE,
    "embedding_role": _EMBEDDING_MODEL_ROLE,
    "text_embedding": _EMBEDDING_MODEL_ROLE,
    "text_embeddings": _EMBEDDING_MODEL_ROLE,
}


def _looks_like_embedding_model_name(model_name: str | None) -> bool:
    normalized = (model_name or "").strip().lower()
    return normalized.startswith("text-embedding-")


def _normalize_model_role(raw_role: str | None, *, model_name: str | None = None) -> str:
    role = (raw_role or "llm").strip().lower()
    role = _MODEL_ROLE_ALIASES.get(role, role)
    if _looks_like_embedding_model_name(model_name) and role in {*_GENERATION_MODEL_ROLES, _EMBEDDING_MODEL_ROLE}:
        role = _EMBEDDING_MODEL_ROLE
    if role not in {*_GENERATION_MODEL_ROLES, "mock", _EMBEDDING_MODEL_ROLE}:
        raise governance_error(
            "model_role_invalid",
            "model_role must be one of llm, slm, mock, embedding_role, or text_embedding.",
            400,
            {"model_role": raw_role},
        )
    return role


def _is_generation_model(model: AIModelConfig) -> bool:
    if _looks_like_embedding_model_name(model.model_name):
        return False
    return (model.model_role or "").strip().lower() in _GENERATION_MODEL_ROLES


def _is_embedding_model(model: AIModelConfig) -> bool:
    role = _normalize_model_role(model.model_role, model_name=model.model_name)
    return role == _EMBEDDING_MODEL_ROLE or _looks_like_embedding_model_name(model.model_name)


def _route_expects_embedding_model(*, task_kind: str | None, route_id: str | None = None) -> bool:
    task = (task_kind or "").strip().lower()
    rid = (route_id or "").strip().lower()
    return task in _EMBEDDING_ROUTE_TASK_KINDS or rid == "retrieval_embedding_generation_global"


def _route_model_role_kind(*, task_kind: str | None, route_id: str | None = None) -> str:
    return _EMBEDDING_MODEL_ROLE if _route_expects_embedding_model(task_kind=task_kind, route_id=route_id) else "generation"


def _derive_model_id(provider_id: str, model_name: str) -> str:
    return _slug(f"{provider_id}_{model_name}")


def _probe_target(base_url: str, contract: dict) -> str:
    path = str(contract.get("health_check_path") or "").strip()
    if not path:
'''
