"""Langfuse verify source segment: runtime_matrix_public_client.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
                if isinstance(row, dict) and not row.get("observations")
                else row
                for row in broad_rows
                if isinstance(row, dict)
            ]
        raw_rows = [
            row
            for row in raw_rows
            if isinstance(row, dict)
            and (row.get("error") or _runtime_aspect_trace_matches_filters(row, arguments))
        ]
    rows = [_runtime_aspect_matrix_row(row) for row in raw_rows if isinstance(row, dict) and not row.get("error")]
    errors = [row for row in raw_rows if isinstance(row, dict) and row.get("error")]
    return {
        "ok": not errors,
        "columns": list(_RUNTIME_ASPECT_MATRIX_COLUMNS),
        "count": len(rows),
        "rows": rows,
        "errors": errors,
    }


def _langfuse_public_get_json(
    *,
    endpoint: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tracer = McpLangfuseTracer.get_instance()
    tracer._get_client()  # best effort: ensures backend/env credential fetch happened
    public_key = str(getattr(tracer, "_public_key", "") or "").strip()
    secret_key = str(getattr(tracer, "_secret_key", "") or "").strip()
    # Verify tools are read-only; bypass LANGFUSE_MCP_ENABLED gate if keys still missing.
    # _get_client() returns early when LANGFUSE_MCP_ENABLED≠1, leaving keys empty even
    # when INTERNAL_RUNTIME_CONFIG_TOKEN is present and the backend has credentials.
    if not (public_key and secret_key) and not getattr(tracer, "_credentials_fetched", False):
        tracer._fetch_credentials_from_backend()
        public_key = str(getattr(tracer, "_public_key", "") or "").strip()
        secret_key = str(getattr(tracer, "_secret_key", "") or "").strip()
    base_url = str(getattr(tracer, "_base_url", "") or "").strip()
    if not (public_key and secret_key and base_url):
        return {"error": "langfuse_credentials_unavailable"}
    url = f"{base_url.rstrip('/')}{endpoint}"
    try:
        resp = requests.get(
            url,
            params=params or {},
            auth=(public_key, secret_key),
            timeout=12.0,
        )
    except Exception as exc:
        return {"error": f"langfuse_http_request_failed:{exc}"}
    if resp.status_code == 401:
        # Repo-root .env may still contain stale/cloud Langfuse keys while the
        # local Docker stack publishes its active local credentials through the
        # backend internal endpoint. Verification tools are read-only, so retry
        # once with backend-fetched credentials before reporting auth failure.
        before = (public_key, secret_key, base_url)
        try:
            tracer._fetch_credentials_from_backend()
        except Exception:
            pass
        public_key = str(getattr(tracer, "_public_key", "") or "").strip()
        secret_key = str(getattr(tracer, "_secret_key", "") or "").strip()
        base_url = str(getattr(tracer, "_base_url", "") or "").strip()
        after = (public_key, secret_key, base_url)
        if public_key and secret_key and base_url and after != before:
            url = f"{base_url.rstrip('/')}{endpoint}"
            try:
                resp = requests.get(
                    url,
                    params=params or {},
                    auth=(public_key, secret_key),
'''
