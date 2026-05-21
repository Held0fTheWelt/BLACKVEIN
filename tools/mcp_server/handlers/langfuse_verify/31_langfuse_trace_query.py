"""Langfuse verify source segment: langfuse_trace_query.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
                    timeout=12.0,
                )
            except Exception as exc:
                return {"error": f"langfuse_http_request_failed:{exc}"}
    if resp.status_code != 200:
        return {"error": f"langfuse_http_{resp.status_code}", "body": resp.text[:400]}
    try:
        return resp.json()
    except Exception as exc:
        return {"error": f"langfuse_json_decode_failed:{exc}"}


def _langfuse_get_trace(trace_id: str) -> dict[str, Any]:
    tracer = McpLangfuseTracer.get_instance()
    client = tracer._get_client()
    if client is not None and hasattr(client, "get_trace"):
        try:
            raw = _to_plain(client.get_trace(trace_id))
            if isinstance(raw, dict):
                return raw
        except Exception:
            pass
    payload = _langfuse_public_get_json(endpoint=f"/api/public/traces/{trace_id}")
    if payload.get("error"):
        return payload
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    if isinstance(payload, dict):
        return payload
    return {"error": "langfuse_trace_unreadable"}


def _langfuse_query_traces(
    *,
    limit: int,
    trace_origin: str | None,
    canonical_player_flow: bool | None,
    execution_tier: str | None = None,
    trace_name: str | None = None,
    trace_names: tuple[str, ...] | None = None,
    environment: str | None = None,
) -> list[dict[str, Any]]:
    payload = _langfuse_public_get_json(
        endpoint="/api/public/traces",
        params={"limit": max(1, min(int(limit), 100))},
    )
    if payload.get("error"):
        return [{"error": payload["error"], "body": payload.get("body")}]
    rows = payload.get("data")
    if not isinstance(rows, list):
        return []
    filtered: list[dict[str, Any]] = []
    env_target = str(environment or "").strip().lower() or None
    for row in rows:
        if not isinstance(row, dict):
            continue
        meta = _extract_metadata(row)
        origin_ok = True
        canonical_ok = True
        if trace_origin is not None:
            origin_ok = str(meta.get("trace_origin") or "").strip().lower() == trace_origin.lower()
        if canonical_player_flow is not None:
            canonical_ok = bool(meta.get("canonical_player_flow")) is canonical_player_flow
        tier_ok = True
        if execution_tier is not None:
            tier_ok = (
                str(meta.get("execution_tier") or "").strip().lower()
                == str(execution_tier).strip().lower()
            )
        name_ok = True
        if trace_name is not None:
            name_ok = str(row.get("name") or "").strip() == str(trace_name).strip()
'''
