"""RAG operations status, probes, safe actions, and settings functions."""

from __future__ import annotations

from .common import *
from .repository_paths import *
from .settings_validation import *

def _effective_retrieval_execution_mode(
    *,
    runtime_modes: dict[str, Any] | None = None,
    retrieval_settings: dict[str, Any] | None = None,
) -> str:
    """Canonical retrieval mode: runtime bootstrap first, then retrieval scope setting."""
    modes = runtime_modes if runtime_modes is not None else get_runtime_modes()
    scope = retrieval_settings if retrieval_settings is not None else read_scope_settings("retrieval")
    for candidate in (modes.get("retrieval_execution_mode"), scope.get("retrieval_execution_mode")):
        text = str(candidate or "").strip()
        if text:
            return text
    return "disabled"


def get_rag_operations_status() -> dict[str, Any]:
    retriever, _, corpus = _build_rag_stack()
    probe = embedding_backend_probe()
    runtime_modes = get_runtime_modes()
    retrieval_settings = read_scope_settings("retrieval")
    class_counts = Counter(chunk.content_class.value for chunk in corpus.chunks)
    source_paths = sorted({chunk.source_path for chunk in corpus.chunks})
    root = _repo_root()
    corpus_path = root / _RUNTIME_CORPUS_REL
    npz_path = root / _EMBED_NPZ_REL
    meta_path = root / _EMBED_META_REL
    degraded_reasons: list[str] = []
    if not probe.available:
        degraded_reasons.extend(list(probe.messages))
    degraded_reasons.extend(list(corpus.rag_dense_load_reason_codes or ()))
    if corpus.rag_dense_rebuild_reason:
        degraded_reasons.append(corpus.rag_dense_rebuild_reason)
    mode_effective = _effective_retrieval_execution_mode(
        runtime_modes=runtime_modes,
        retrieval_settings=retrieval_settings,
    )
    scope_mode_setting = str(retrieval_settings.get("retrieval_execution_mode") or "").strip() or None
    operational_state = "healthy"
    if mode_effective == "disabled":
        operational_state = "configured_disabled"
    elif len(corpus.chunks) == 0:
        operational_state = "blocked"
    elif degraded_reasons:
        operational_state = "degraded"
    guidance: list[dict[str, str]] = []
    if operational_state == "blocked":
        guidance.append(
            {
                "severity": "blocked",
                "message": "RAG corpus has no chunks, so retrieval cannot produce useful context.",
                "consequence": "AI responses lose retrieval-backed grounding.",
                "next_step": "Run 'Refresh corpus' and re-run a retrieval probe.",
                "fix_path": "/manage/rag-operations",
            }
        )
    if mode_effective == "disabled":
        guidance.append(
            {
                "severity": "info",
                "message": "Retrieval mode is intentionally disabled by configuration.",
                "consequence": "Runtime relies on non-retrieval behavior.",
                "next_step": "Enable retrieval mode in Runtime Settings or RAG settings when needed.",
                "fix_path": "/manage/runtime-settings",
            }
        )
    if not probe.available and mode_effective != "disabled":
        guidance.append(
            {
                "severity": "degraded",
                "message": "Embedding backend is unavailable while retrieval mode expects dense support.",
                "consequence": "Retrieval can fall back to sparse-only posture with lower recall quality.",
                "next_step": "Inspect embedding diagnostics and rerun probe to validate fallback quality.",
                "fix_path": "/manage/rag-operations",
            }
        )
    from app.services.governance.hf_hub_governance_service import get_hf_hub_status

    hf_hub_status = get_hf_hub_status()
    return {
        "generated_at": corpus.built_at,
        "operational_state": operational_state,
        "status_semantics": STATUS_SEMANTICS,
        "corpus": {
            "chunk_count": len(corpus.chunks),
            "source_count": corpus.source_count,
            "content_class_counts": dict(class_counts),
            "sample_source_paths": source_paths[:10],
            "corpus_fingerprint": corpus.corpus_fingerprint,
            "index_version": corpus.index_version,
            "storage_path": corpus.storage_path or str(corpus_path),
            "built_at": corpus.built_at,
        },
        "retrieval": {
            # retrieval_mode_bootstrap_setting: the value from the governed DB bootstrap record.
            # This IS wired to the live turn path via governed_runtime_config → RuntimeRetrievalConfig.
            "retrieval_mode_bootstrap_setting": runtime_modes.get("retrieval_execution_mode"),
            "mode_effective": mode_effective,
            # mode_runtime kept as alias for backwards-compat with existing admin UI JS.
            "mode_runtime": mode_effective,
            "mode_setting": scope_mode_setting,
            "mode_scope_drift": bool(scope_mode_setting and scope_mode_setting != mode_effective),
            "retrieval_profile": retrieval_settings.get("retrieval_profile") or "runtime_turn_support",
            "retrieval_top_k": retrieval_settings.get("retrieval_top_k") or 4,
            "retrieval_min_score": retrieval_settings.get("retrieval_min_score"),
            "embeddings_enabled_setting": retrieval_settings.get("embeddings_enabled"),
            "governance_wired_to_live_path": True,
            "last_observed_route": getattr(retriever, "last_retrieval_route", "") or "",
            "last_observed_embedding_model_id": getattr(retriever, "last_embedding_model_id", "") or "",
        },
        "embedding_backend": {
            "available": probe.available,
            "disabled_by_env": probe.disabled_by_env,
            "import_ok": probe.import_ok,
            "encode_ok": probe.encode_ok,
            "model_id": probe.model_id,
            "cache_dir": probe.cache_dir,
            "cache_dir_identity": probe.cache_dir_identity,
            "primary_reason_code": probe.primary_reason_code,
            "messages": list(probe.messages),
            # Real env var controls — these are the authoritative gates on embedding availability.
            "env_disable_embeddings_var": "WOS_RAG_DISABLE_EMBEDDINGS",
            "env_disable_embeddings_set": probe.disabled_by_env,
            "env_cache_dir_var": "WOS_RAG_EMBEDDING_CACHE_DIR",
            "env_cache_dir_resolved": probe.cache_dir or "__default__",
        },
        "dense_index": {
            "present_on_retriever": bool(getattr(retriever, "_embedding_index", None) is not None),
            "artifact_validity": corpus.rag_dense_artifact_validity,
            "index_build_action": corpus.rag_dense_index_build_action,
            "rebuild_reason": corpus.rag_dense_rebuild_reason,
            "load_reason_codes": list(corpus.rag_dense_load_reason_codes or ()),
            "embedding_index_version": corpus.rag_embedding_index_version,
            "embedding_cache_dir_identity": corpus.rag_embedding_cache_dir_identity,
            "embedding_backend_primary_code": corpus.rag_embedding_backend_primary_code,
            "npz_path": str(npz_path),
            "npz_exists": npz_path.exists(),
            "meta_path": str(meta_path),
            "meta_exists": meta_path.exists(),
        },
        "degraded_reasons": sorted(set(r for r in degraded_reasons if r)),
        "comparison": {
            "retrieval_mode_runtime": mode_effective,
            "retrieval_mode_effective": mode_effective,
            "retrieval_mode_setting": scope_mode_setting,
            "dense_index_attached": bool(getattr(retriever, "_embedding_index", None) is not None),
            "expected_healthy": {
                "embedding_backend_available": True,
                "dense_index_attached": True,
                "retrieval_mode_not_disabled": True,
            },
        },
        "guidance": guidance,
        "safe_actions": [
            {"action_id": "refresh_corpus", "label": "Refresh corpus from repository sources"},
            {"action_id": "rebuild_dense_index", "label": "Rebuild dense embedding index"},
            {"action_id": "reload_runtime_retriever", "label": "Reload in-process retriever"},
        ],
        "hf_hub": hf_hub_status,
    }


def run_rag_query_probe(payload: dict[str, Any]) -> dict[str, Any]:
    query = str(payload.get("query") or "").strip()
    if not query:
        raise governance_error("setting_value_invalid", "query is required.", 400, {})
    retrieval_settings = read_scope_settings("retrieval")
    requested_max = int(payload.get("max_chunks") or retrieval_settings.get("retrieval_top_k") or 4)
    max_chunks = max(1, min(requested_max, 12))
    mode_effective = _effective_retrieval_execution_mode(retrieval_settings=retrieval_settings)
    use_sparse_only = bool(payload.get("use_sparse_only")) or mode_effective == "sparse_only"
    domain_raw = str(payload.get("domain") or RetrievalDomain.RUNTIME.value).strip().lower()
    try:
        domain = RetrievalDomain(domain_raw)
    except ValueError:
        raise governance_error("setting_value_invalid", "Unsupported probe domain.", 400, {"domain": domain_raw})
    retriever, _, _ = _build_rag_stack()
    request = RetrievalRequest(
        domain=domain,
        profile=str(payload.get("profile") or retrieval_settings.get("retrieval_profile") or "runtime_turn_support"),
        query=query,
        module_id=str(payload.get("module_id") or "").strip() or None,
        scene_id=str(payload.get("scene_id") or "").strip() or None,
        max_chunks=max_chunks,
        use_sparse_only=use_sparse_only,
    )
    result = retriever.retrieve(request)
    hits = []
    for hit in result.hits:
        hits.append(
            {
                "chunk_id": hit.chunk_id,
                "source_path": hit.source_path,
                "source_name": hit.source_name,
                "content_class": hit.content_class,
                "score": hit.score,
                "snippet": hit.snippet,
                "selection_reason": hit.selection_reason,
                "pack_role": hit.pack_role,
                "source_evidence_lane": hit.source_evidence_lane,
                "source_visibility_class": hit.source_visibility_class,
                "policy_note": hit.policy_note,
                "profile_policy_influence": hit.profile_policy_influence,
            }
        )
    return {
        "request": {
            "domain": request.domain.value,
            "profile": request.profile,
            "query": request.query,
            "module_id": request.module_id,
            "scene_id": request.scene_id,
            "max_chunks": request.max_chunks,
            "use_sparse_only": request.use_sparse_only,
        },
        "result": {
            "status": result.status.value,
            "hit_count": len(result.hits),
            "retrieval_route": result.retrieval_route,
            "embedding_model_id": result.embedding_model_id,
            "degradation_mode": result.degradation_mode,
            "dense_index_build_action": result.dense_index_build_action,
            "dense_rebuild_reason": result.dense_rebuild_reason,
            "dense_artifact_validity": result.dense_artifact_validity,
            "ranking_notes": list(result.ranking_notes),
            "embedding_reason_codes": list(result.embedding_reason_codes),
            "index_version": result.index_version,
            "corpus_fingerprint": result.corpus_fingerprint,
            "storage_path": result.storage_path,
            "hits": hits,
        },
    }


def run_rag_safe_action(action_id: str) -> dict[str, Any]:
    normalized = (action_id or "").strip().lower()
    root = _repo_root()
    corpus_path = root / _RUNTIME_CORPUS_REL
    npz_path = root / _EMBED_NPZ_REL
    meta_path = root / _EMBED_META_REL
    if normalized == "refresh_corpus":
        _build_rag_stack(force_corpus_rebuild=True, force_dense_rebuild=True, reset_cache=True)
        return {
            "action_id": normalized,
            "performed": True,
            "operator_message": "Runtime corpus and dense index were rebuilt from repository sources.",
            "paths_touched": [str(corpus_path), str(npz_path), str(meta_path)],
            "status": get_rag_operations_status(),
        }
    if normalized == "rebuild_dense_index":
        _build_rag_stack(force_dense_rebuild=True, reset_cache=True)
        return {
            "action_id": normalized,
            "performed": True,
            "operator_message": "Dense embedding index rebuild was requested and applied.",
            "paths_touched": [str(npz_path), str(meta_path)],
            "status": get_rag_operations_status(),
        }
    if normalized == "reload_runtime_retriever":
        _build_rag_stack(reset_cache=True)
        return {
            "action_id": normalized,
            "performed": True,
            "operator_message": "In-process runtime retriever cache reloaded.",
            "paths_touched": [],
            "status": get_rag_operations_status(),
        }
    raise governance_error("setting_value_invalid", "Unsupported RAG action.", 400, {"action_id": normalized})


def get_rag_settings() -> dict[str, Any]:
    runtime_modes = get_runtime_modes()
    retrieval_settings = read_scope_settings("retrieval")
    return {
        "retrieval_execution_mode": _effective_retrieval_execution_mode(
            runtime_modes=runtime_modes,
            retrieval_settings=retrieval_settings,
        ),
        "embeddings_enabled": retrieval_settings.get("embeddings_enabled"),
        "retrieval_top_k": retrieval_settings.get("retrieval_top_k") or 4,
        "retrieval_min_score": retrieval_settings.get("retrieval_min_score"),
        "retrieval_profile": retrieval_settings.get("retrieval_profile") or "runtime_turn_support",
    }


def update_rag_settings(payload: dict[str, Any], actor: str) -> dict[str, Any]:
    cleaned = _validate_rag_settings_patch(payload)
    if not cleaned:
        return get_rag_settings()
    runtime_patch: dict[str, Any] = {}
    if "retrieval_execution_mode" in cleaned:
        runtime_patch["retrieval_execution_mode"] = cleaned["retrieval_execution_mode"]
    if runtime_patch:
        update_runtime_modes(runtime_patch, actor)
        delete_scope_setting("retrieval", "retrieval_execution_mode", actor)
    persisted = {k: v for k, v in cleaned.items() if k != "retrieval_execution_mode"}
    if persisted:
        update_scope_settings("retrieval", persisted, actor)
    return get_rag_settings()


__all__ = (
    '_effective_retrieval_execution_mode',
    'get_rag_operations_status',
    'run_rag_query_probe',
    'run_rag_safe_action',
    'get_rag_settings',
    'update_rag_settings',
)
