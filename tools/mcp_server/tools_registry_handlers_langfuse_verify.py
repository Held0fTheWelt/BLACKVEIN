"""MCP handlers for projection-test orchestration and Langfuse trace verification."""

from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

from tools.mcp_server.config import Config
from tools.mcp_server.langfuse_tracing import McpLangfuseTracer


def _to_plain(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_plain(v) for v in value]
    if hasattr(value, "model_dump"):
        try:
            return _to_plain(value.model_dump())
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return _to_plain(value.to_dict())
        except Exception:
            pass
    if hasattr(value, "__dict__"):
        try:
            return _to_plain(vars(value))
        except Exception:
            pass
    return str(value)


def _extract_scores(raw_trace: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    score_rows = raw_trace.get("scores")
    if isinstance(score_rows, list):
        for row in score_rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            out[name] = row.get("value")
    return out


def _is_judge_score(name: str) -> bool:
    return name.endswith("_judge")


def _extract_scores_split(
    raw_trace: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Split trace scores into (deterministic_gates, judge_scores).

    Deduplicates by name (first occurrence wins). Judge scores carry
    category and reasoning extracted from score row metadata/comment.
    """
    det: dict[str, Any] = {}
    judge: dict[str, Any] = {}
    score_rows = raw_trace.get("scores")
    if not isinstance(score_rows, list):
        return det, judge
    for row in score_rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        value = row.get("value")
        if _is_judge_score(name):
            if name in judge:
                continue
            comment = str(row.get("comment") or "").strip()
            row_meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            category = str(row_meta.get("category") or "").strip() or None
            judge[name] = {"value": value, "category": category, "reasoning": comment or None}
        else:
            if name in det:
                continue
            det[name] = value
    return det, judge


def _extract_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = raw_trace.get("metadata")
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


# ---------------------------------------------------------------------------
# WoS evidence extraction helpers
# ---------------------------------------------------------------------------

def _coerce_dict_or_json(value: Any) -> dict[str, Any]:
    """Return dict from value; parse JSON if it's a string."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
    return {}


def _get_observations(raw_trace: dict[str, Any]) -> list[dict[str, Any]]:
    """Return observations list, normalising each entry to a plain dict."""
    raw_obs = raw_trace.get("observations") or []
    result: list[dict[str, Any]] = []
    for o in raw_obs:
        if isinstance(o, dict):
            result.append(o)
        elif hasattr(o, "model_dump"):
            try:
                d = o.model_dump()
                if isinstance(d, dict):
                    result.append(d)
            except Exception:
                pass
    return result


def _find_observation_by_name(
    observations: list[dict[str, Any]], name: str
) -> dict[str, Any] | None:
    for obs in observations:
        if obs.get("name") == name:
            return obs
    return None


def _parse_status_tokens(status_message: str) -> dict[str, str]:
    """Parse 'key=value ...' tokens from a Langfuse statusMessage string."""
    result: dict[str, str] = {}
    for m in re.finditer(r"(\w+)=([^\s]+)", str(status_message or "")):
        result[m.group(1).lower()] = m.group(2).strip()
    return result


def _first_score_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    """Return metadata from the first score row that has a non-empty metadata dict.

    All scores in a trace share the same ``score_metadata_base`` (session_id,
    selected_player_role, human_actor_id, final_adapter, quality_class, etc.)
    so any score entry is an equally valid source.
    """
    for row in (raw_trace.get("scores") or []):
        if not isinstance(row, dict):
            continue
        meta = _coerce_dict_or_json(row.get("metadata"))
        if meta:
            return meta
    return {}


def _sif(ev: dict[str, Any], field: str, value: Any) -> None:
    """Set ev[field] = value only if the field is currently None."""
    if value is not None and ev.get(field) is None:
        ev[field] = value


def _extract_normalized_wos_evidence(
    raw_trace: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract WoS evidence from a Langfuse trace using a four-source priority chain.

    Priority (first non-None wins per field):
      1. trace.output.path_summary (or trace.output if it IS the path_summary)
      2. story.graph.path_summary observation (output → input → metadata)
      3. Score metadata (score_metadata_base carries player-role, adapter, quality)
      4. Turn span metadata (backend.turn.execute / world-engine.turn.execute)
      5. trace.metadata (top-level, usually only trace_origin/execution_tier)
      6. world-engine.session.create statusMessage (key=value fallback)

    Returns (evidence_dict, evidence_sources_dict).
    """
    obs_list = _get_observations(raw_trace)

    ev: dict[str, Any] = {
        "trace_id": str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip(),
        "session_id": None,
        "selected_player_role": None,
        "human_actor_id": None,
        "npc_actor_ids": [],
        "trace_origin": None,
        "execution_tier": None,
        "canonical_player_flow": None,
        "final_adapter": None,
        "quality_class": None,
        "fallback_reason": None,
    }

    path_summary_source = "missing"
    score_source = "missing"
    status_message_fallback_used = False

    _PS_FIELDS = {
        "session_id", "selected_player_role", "human_actor_id", "npc_actor_ids",
        "trace_origin", "execution_tier", "canonical_player_flow",
        "final_adapter", "quality_class", "fallback_reason",
    }
    _CLASSIFICATION_FIELDS = {"trace_origin", "execution_tier", "canonical_player_flow"}

    def _apply(src: dict[str, Any], fields: set[str]) -> None:
        for f in fields:
            _sif(ev, f, src.get(f))

    # --- Source 1: trace.output ---
    trace_output = _coerce_dict_or_json(raw_trace.get("output"))
    if trace_output:
        nested_ps = _coerce_dict_or_json(trace_output.get("path_summary"))
        direct_ps = (
            trace_output
            if trace_output.get("contract") == "story_runtime_path_observability.v1"
            else {}
        )
        ps = nested_ps or direct_ps
        if ps:
            path_summary_source = "trace.output"
            _apply(ps, _PS_FIELDS)
        # Classification fields may be present even without a full path_summary
        _apply(trace_output, _CLASSIFICATION_FIELDS)

    # --- Source 2: story.graph.path_summary observation ---
    ps_obs = _find_observation_by_name(obs_list, "story.graph.path_summary")
    if ps_obs:
        for block_key in ("output", "input", "metadata"):
            block = _coerce_dict_or_json(ps_obs.get(block_key))
            if block:
                if path_summary_source == "missing":
                    path_summary_source = f"observation.{block_key}"
                _apply(block, _PS_FIELDS)

    # --- Source 3: score metadata (score_metadata_base carries WoS-specific fields) ---
    score_meta = _first_score_metadata(raw_trace)
    if score_meta:
        score_source = "trace.scores"
        _apply(score_meta, {
            "session_id", "selected_player_role", "human_actor_id",
            "final_adapter", "quality_class", "fallback_reason",
        })

    # --- Source 4: turn span metadata ---
    for span_name in ("backend.turn.execute", "world-engine.turn.execute"):
        span_obs = _find_observation_by_name(obs_list, span_name)
        if span_obs:
            for block_key in ("metadata", "output", "input"):
                block = _coerce_dict_or_json(span_obs.get(block_key))
                _apply(block, _CLASSIFICATION_FIELDS | {"session_id"})

    # --- Source 5: trace.metadata (top-level) ---
    trace_meta = _extract_metadata(raw_trace)
    _apply(trace_meta, _PS_FIELDS)

    # --- Source 6: world-engine.session.create statusMessage (key=value fallback) ---
    we_create = _find_observation_by_name(obs_list, "world-engine.session.create")
    if we_create:
        sm = str(
            we_create.get("statusMessage")
            or we_create.get("status_message")
            or ""
        )
        if sm:
            tokens = _parse_status_tokens(sm)
            if tokens:
                status_message_fallback_used = True
                if not ev.get("final_adapter") and tokens.get("adapter"):
                    ev["final_adapter"] = tokens["adapter"]
                if not ev.get("quality_class") and tokens.get("quality"):
                    ev["quality_class"] = tokens["quality"]

    # --- Gate scores ---
    det_scores, _ = _extract_scores_split(raw_trace)
    if det_scores:
        score_source = "trace.scores"
    for gate in (
        "opening_shape_contract_pass",
        "opening_contract_pass",
        "live_runtime_contract_pass",
        "live_runtime_visible_surface_pass",
        "live_opening_contract_pass",
        "fallback_absent",
        "non_mock_generation_pass",
        "visible_output_present",
        "usage_present",
        "rag_context_attached",
        "actor_lane_safety_pass",
    ):
        ev[gate] = det_scores.get(gate)

    if not isinstance(ev.get("npc_actor_ids"), list):
        ev["npc_actor_ids"] = []

    sources = {
        "path_summary_source": path_summary_source,
        "score_source": score_source,
        "status_message_fallback_used": status_message_fallback_used,
    }
    return ev, sources


def _trace_summary(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = _extract_metadata(raw_trace)
    scores = _extract_scores(raw_trace)
    trace_id = str(raw_trace.get("id") or raw_trace.get("trace_id") or "").strip()
    return {
        "trace_id": trace_id,
        "name": raw_trace.get("name"),
        "timestamp": raw_trace.get("timestamp"),
        "metadata": metadata,
        "scores": scores,
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
        if origin_ok and canonical_ok:
            filtered.append(row)
    return filtered


def _assertions_for_mode(mode: str) -> list[tuple[str, bool, str]]:
    if mode == "test":
        return [
            ("trace_origin == pytest", True, "metadata.trace_origin must be pytest"),
            (
                "canonical_player_flow == false",
                True,
                "metadata.canonical_player_flow must be false",
            ),
            (
                "live_opening_contract_pass == 0",
                True,
                "score live_opening_contract_pass must be 0",
            ),
        ]
    return [
        ("trace_origin == live_ui", True, "metadata.trace_origin must be live_ui"),
        ("execution_tier == live", True, "metadata.execution_tier must be live"),
        (
            "canonical_player_flow == true",
            True,
            "metadata.canonical_player_flow must be true",
        ),
        (
            "selected_player_role in [annette, alain]",
            True,
            "metadata.selected_player_role must be annette or alain",
        ),
        (
            "human_actor_id == selected_player_role",
            True,
            "metadata.human_actor_id must equal selected_player_role",
        ),
        (
            "opening_shape_contract_pass == 1",
            True,
            "score opening_shape_contract_pass must be 1",
        ),
        (
            "live_runtime_contract_pass == 1",
            True,
            "score live_runtime_contract_pass must be 1",
        ),
        (
            "live_opening_contract_pass == 1",
            True,
            "score live_opening_contract_pass must be 1",
        ),
        (
            "final_adapter != ldss_fallback",
            True,
            "metadata.final_adapter must not be ldss_fallback",
        ),
        (
            "quality_class not in [degraded, failed]",
            True,
            "metadata.quality_class must not be degraded/failed",
        ),
    ]


def build_langfuse_verify_mcp_handlers() -> dict[str, Callable[..., dict[str, Any]]]:
    config = Config()
    repo_root = Path(config.repo_root)

    def run_projection_tests(arguments: dict[str, Any]) -> dict[str, Any]:
        python_executable = sys.executable
        extra_pytest_args: list[str] = []
        if arguments.get("extra_pytest_args") and isinstance(arguments["extra_pytest_args"], list):
            extra_pytest_args = [str(x) for x in arguments["extra_pytest_args"] if str(x).strip()]

        def _tail(raw: str) -> str:
            return "\n".join((raw or "").splitlines()[-40:])

        def _run_pytest_subprocess(
            *,
            cmd: list[str],
            cwd: Path,
            pythonpath_parts: list[str],
        ) -> dict[str, Any]:
            env = dict(os.environ)
            existing_py_path = str(env.get("PYTHONPATH") or "").strip()
            py_path_parts = [x for x in pythonpath_parts if str(x).strip()]
            if existing_py_path:
                py_path_parts.append(existing_py_path)
            env["PYTHONPATH"] = os.pathsep.join(py_path_parts)
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "command": cmd,
                "cwd": str(cwd),
                "pythonpath": env.get("PYTHONPATH", ""),
                "stdout_tail": _tail(proc.stdout),
                "stderr_tail": _tail(proc.stderr),
            }

        world_engine_path = repo_root / "world-engine"
        world_engine_cwd = world_engine_path
        world_engine_py_path = [str(world_engine_path), str(repo_root)]
        world_engine_preflight_env = dict(os.environ)
        existing_preflight_path = str(world_engine_preflight_env.get("PYTHONPATH") or "").strip()
        if existing_preflight_path:
            world_engine_preflight_env["PYTHONPATH"] = os.pathsep.join(
                [*world_engine_py_path, existing_preflight_path]
            )
        else:
            world_engine_preflight_env["PYTHONPATH"] = os.pathsep.join(world_engine_py_path)
        preflight_cmd = [
            python_executable,
            "-c",
            "import app.story_runtime; print('import_ok=app.story_runtime')",
        ]
        preflight = subprocess.run(
            preflight_cmd,
            cwd=str(world_engine_cwd),
            env=world_engine_preflight_env,
            text=True,
            capture_output=True,
            check=False,
        )
        if preflight.returncode != 0:
            world_engine_result = {
                "ok": False,
                "returncode": preflight.returncode,
                "command": preflight_cmd,
                "cwd": str(world_engine_cwd),
                "pythonpath": world_engine_preflight_env.get("PYTHONPATH", ""),
                "stdout_tail": _tail(preflight.stdout),
                "stderr_tail": _tail(preflight.stderr),
            }
            ai_stack_result = {
                "ok": False,
                "returncode": None,
                "command": [
                    python_executable,
                    "-m",
                    "pytest",
                    "ai_stack/tests/test_actor_lane_absence_governance.py",
                    "-q",
                    *extra_pytest_args,
                ],
                "cwd": str(repo_root),
                "pythonpath": "",
                "stdout_tail": "",
                "stderr_tail": "skipped_due_to_world_engine_preflight_failure",
            }
            return {
                "ok": False,
                "world_engine": world_engine_result,
                "ai_stack": ai_stack_result,
            }

        world_engine_result = _run_pytest_subprocess(
            cmd=[
                python_executable,
                "-m",
                "pytest",
                "tests/test_trace_middleware.py",
                "-q",
                *extra_pytest_args,
            ],
            cwd=world_engine_cwd,
            pythonpath_parts=world_engine_py_path,
        )
        ai_stack_result = _run_pytest_subprocess(
            cmd=[
                python_executable,
                "-m",
                "pytest",
                "ai_stack/tests/test_actor_lane_absence_governance.py",
                "-q",
                *extra_pytest_args,
            ],
            cwd=repo_root,
            pythonpath_parts=[str(repo_root)],
        )
        return {
            "ok": bool(world_engine_result["ok"] and ai_stack_result["ok"]),
            "world_engine": world_engine_result,
            "ai_stack": ai_stack_result,
        }

    def fetch_langfuse_trace(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("langfuse_trace_id") or "").strip()
        if not trace_id:
            return {"error": "langfuse_trace_id required"}
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"], "details": raw}
        evidence, sources = _extract_normalized_wos_evidence(raw)
        return {
            "ok": True,
            "trace": _trace_summary(raw),
            "raw_trace": raw,
            "normalized_wos_evidence": evidence,
            "evidence_sources": sources,
        }

    def query_langfuse_traces(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 10)
        trace_origin = arguments.get("trace_origin")
        cpf_raw = arguments.get("canonical_player_flow")
        canonical_player_flow = (
            bool(cpf_raw)
            if isinstance(cpf_raw, bool)
            else None
        )
        rows = _langfuse_query_traces(
            limit=limit,
            trace_origin=str(trace_origin) if isinstance(trace_origin, str) else None,
            canonical_player_flow=canonical_player_flow,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"], "details": rows[0].get("body")}
        return {"ok": True, "count": len(rows), "traces": [_trace_summary(x) for x in rows]}

    def assert_langfuse_opening_contract(arguments: dict[str, Any]) -> dict[str, Any]:
        mode = str(arguments.get("mode") or "live").strip().lower()
        if mode not in {"live", "test"}:
            return {"ok": False, "error": "mode must be live or test"}
        trace_id = str(arguments.get("langfuse_trace_id") or "").strip()
        if trace_id:
            raw = _langfuse_get_trace(trace_id)
            if raw.get("error"):
                return {"ok": False, "error": raw["error"], "missing_field": "trace"}
        else:
            origin = "live_ui" if mode == "live" else "pytest"
            rows = _langfuse_query_traces(
                limit=int(arguments.get("limit") or 10),
                trace_origin=origin,
                canonical_player_flow=True if mode == "live" else False,
            )
            if not rows or (isinstance(rows[0], dict) and rows[0].get("error")):
                return {"ok": False, "error": "no_matching_trace_found", "missing_field": "trace"}
            raw = rows[0]
            trace_id = str(raw.get("id") or "")

        ev, _src = _extract_normalized_wos_evidence(raw)
        failures: list[dict[str, Any]] = []

        def fail(rule: str, message: str, field: str, actual: Any) -> None:
            failures.append(
                {"rule": rule, "message": message, "missing_field": field, "actual": actual}
            )

        if mode == "live":
            if str(ev.get("trace_origin") or "").lower() != "live_ui":
                fail("trace_origin == live_ui", "live trace origin mismatch", "normalized.trace_origin", ev.get("trace_origin"))
            if str(ev.get("execution_tier") or "").lower() != "live":
                fail("execution_tier == live", "execution tier mismatch", "normalized.execution_tier", ev.get("execution_tier"))
            if bool(ev.get("canonical_player_flow")) is not True:
                fail("canonical_player_flow == true", "canonical flow mismatch", "normalized.canonical_player_flow", ev.get("canonical_player_flow"))
            role = str(ev.get("selected_player_role") or "").lower()
            if role not in {"annette", "alain"}:
                fail("selected_player_role in [annette, alain]", "role mismatch", "normalized.selected_player_role", ev.get("selected_player_role"))
            if str(ev.get("human_actor_id") or "").lower() != role:
                fail("human_actor_id == selected_player_role", "human actor mismatch", "normalized.human_actor_id", ev.get("human_actor_id"))
            for score_name in (
                "opening_shape_contract_pass",
                "live_runtime_contract_pass",
                "live_opening_contract_pass",
            ):
                if float(ev.get(score_name) or 0.0) != 1.0:
                    fail(f"{score_name} == 1", "score mismatch", f"scores.{score_name}", ev.get(score_name))
            if str(ev.get("final_adapter") or "").lower() == "ldss_fallback":
                fail("final_adapter != ldss_fallback", "fallback adapter used", "normalized.final_adapter", ev.get("final_adapter"))
            if str(ev.get("quality_class") or "").lower() in {"degraded", "failed"}:
                fail("quality_class not degraded/failed", "quality class degraded", "normalized.quality_class", ev.get("quality_class"))
        else:
            if str(ev.get("trace_origin") or "").lower() != "pytest":
                fail("trace_origin == pytest", "test trace origin mismatch", "normalized.trace_origin", ev.get("trace_origin"))
            if bool(ev.get("canonical_player_flow")) is not False:
                fail("canonical_player_flow == false", "test flow mismatch", "normalized.canonical_player_flow", ev.get("canonical_player_flow"))
            if float(ev.get("live_opening_contract_pass") or 0.0) != 0.0:
                fail(
                    "live_opening_contract_pass == 0",
                    "test trace has live opening pass",
                    "scores.live_opening_contract_pass",
                    ev.get("live_opening_contract_pass"),
                )

        return {
            "ok": len(failures) == 0,
            "trace_id": trace_id,
            "mode": mode,
            "failures": failures,
            "trace": _trace_summary(raw),
            "assertion_count": len(_assertions_for_mode(mode)),
        }

    def summarize_live_opening_matrix(arguments: dict[str, Any]) -> dict[str, Any]:
        limit = int(arguments.get("limit") or 20)
        rows = _langfuse_query_traces(
            limit=limit,
            trace_origin="live_ui",
            canonical_player_flow=True,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"]}
        matrix: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ev, _src = _extract_normalized_wos_evidence(row)
            matrix.append(
                {
                    "trace_id": row.get("id"),
                    "selected_player_role": ev.get("selected_player_role"),
                    "trace_origin": ev.get("trace_origin"),
                    "execution_tier": ev.get("execution_tier"),
                    "canonical_player_flow": ev.get("canonical_player_flow"),
                    "opening_shape_contract_pass": ev.get("opening_shape_contract_pass"),
                    "live_runtime_contract_pass": ev.get("live_runtime_contract_pass"),
                    "live_opening_contract_pass": ev.get("live_opening_contract_pass"),
                    "final_adapter": ev.get("final_adapter"),
                    "quality_class": ev.get("quality_class"),
                    "narration_summary_synthesized": _extract_metadata(row).get("narration_summary_synthesized"),
                }
            )
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(matrix),
            "rows": matrix,
        }

    _BAD_JUDGE_CATS = frozenset({
        "invalid", "weak", "flat", "bad", "missing", "wrong_role",
        "possible_violation", "clear_violation", "unused", "misused", "partial",
    })

    def fetch_langfuse_trace_scores(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("trace_id") or "").strip()
        if not trace_id:
            return {"ok": False, "error": "trace_id required"}
        allow_non_live = bool(arguments.get("allow_non_live", False))
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"], "details": raw}
        meta = _extract_metadata(raw)
        if not allow_non_live:
            origin = str(meta.get("trace_origin") or "").lower()
            tier = str(meta.get("execution_tier") or "").lower()
            cpf = bool(meta.get("canonical_player_flow"))
            if origin != "live_ui" or tier != "live" or not cpf:
                return {
                    "ok": False,
                    "error": "trace_filtered_as_non_live",
                    "reason": (
                        "trace_origin, execution_tier, or canonical_player_flow does not match "
                        "live evidence criteria (live_ui / live / true)"
                    ),
                    "actual": {
                        "trace_origin": meta.get("trace_origin"),
                        "execution_tier": meta.get("execution_tier"),
                        "canonical_player_flow": meta.get("canonical_player_flow"),
                    },
                    "hint": "Pass allow_non_live: true to inspect non-live traces",
                }
        det_scores, judge_scores = _extract_scores_split(raw)
        return {
            "ok": True,
            "trace_id": trace_id,
            "trace_origin": meta.get("trace_origin"),
            "execution_tier": meta.get("execution_tier"),
            "canonical_player_flow": meta.get("canonical_player_flow"),
            "selected_player_role": meta.get("selected_player_role"),
            "human_actor_id": meta.get("human_actor_id"),
            "deterministic_scores": det_scores,
            "judge_scores": judge_scores,
        }

    def summarize_opening_judge_scores(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_origin = str(arguments.get("trace_origin") or "live_ui").strip()
        execution_tier = str(arguments.get("execution_tier") or "live").strip()
        cpf_arg = arguments.get("canonical_player_flow")
        canonical_player_flow = bool(cpf_arg) if isinstance(cpf_arg, bool) else True
        roles_raw = arguments.get("roles")
        roles = (
            [str(r).strip().lower() for r in roles_raw if str(r).strip()]
            if isinstance(roles_raw, list)
            else None
        )
        limit_per_role = int(arguments.get("limit_per_role") or 5)
        fetch_limit = min(max(limit_per_role * (len(roles) if roles else 2) * 4, 20), 100)
        rows = _langfuse_query_traces(
            limit=fetch_limit,
            trace_origin=trace_origin,
            canonical_player_flow=canonical_player_flow,
        )
        if rows and isinstance(rows[0], dict) and rows[0].get("error"):
            return {"ok": False, "error": rows[0]["error"]}
        matrix: list[dict[str, Any]] = []
        role_counts: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            meta = _extract_metadata(row)
            if execution_tier and str(meta.get("execution_tier") or "").lower() != execution_tier.lower():
                continue
            role = str(meta.get("selected_player_role") or "").strip().lower() or None
            if roles is not None and role not in roles:
                continue
            r_key = role or "unknown"
            if role_counts.get(r_key, 0) >= limit_per_role:
                continue
            role_counts[r_key] = role_counts.get(r_key, 0) + 1
            det_scores, judge_scores = _extract_scores_split(row)

            def _jcat(jname: str, _j: dict = judge_scores) -> str | None:
                j = _j.get(jname)
                if not j:
                    return None
                return j.get("category") or (str(j.get("value") or "") or None)

            live_opening_val = det_scores.get("live_opening_contract_pass")
            live_opening_str = (
                "pass" if live_opening_val == 1.0
                else "fail" if live_opening_val == 0.0
                else str(live_opening_val or "—")
            )
            main_issue: str | None = None
            if live_opening_val == 0.0:
                main_issue = "live_opening_fail"
            elif det_scores.get("live_runtime_contract_pass") == 0.0:
                main_issue = "runtime_contract_fail"
            else:
                for jname in (
                    "opening_experience_judge",
                    "role_anchor_quality_judge",
                    "theatrical_style_judge",
                    "actor_lane_narrative_violation_judge",
                    "rag_context_usefulness_judge",
                ):
                    cat = _jcat(jname)
                    if cat and cat.lower() in _BAD_JUDGE_CATS:
                        main_issue = jname
                        break
            matrix.append({
                "role": role,
                "trace_id": row.get("id"),
                "live_opening": live_opening_str,
                "opening_judge_category": _jcat("opening_experience_judge"),
                "role_anchor_category": _jcat("role_anchor_quality_judge"),
                "style_category": _jcat("theatrical_style_judge"),
                "actor_lane_judge_category": _jcat("actor_lane_narrative_violation_judge"),
                "rag_use_category": _jcat("rag_context_usefulness_judge"),
                "main_issue": main_issue,
            })
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "filter": {
                "trace_origin": trace_origin,
                "execution_tier": execution_tier,
                "canonical_player_flow": canonical_player_flow,
                "roles": roles,
                "limit_per_role": limit_per_role,
            },
            "count": len(matrix),
            "matrix": matrix,
        }

    def build_opening_quality_context(arguments: dict[str, Any]) -> dict[str, Any]:
        trace_id = str(arguments.get("trace_id") or "").strip()
        if not trace_id:
            return {"ok": False, "error": "trace_id required"}
        include_raw_reasoning = bool(arguments.get("include_raw_reasoning", False))
        raw = _langfuse_get_trace(trace_id)
        if raw.get("error"):
            return {"ok": False, "error": raw["error"]}
        meta = _extract_metadata(raw)
        origin = str(meta.get("trace_origin") or "").lower()
        cpf = bool(meta.get("canonical_player_flow"))
        if origin != "live_ui" or not cpf:
            return {
                "ok": False,
                "error": "trace_not_live_evidence",
                "reason": (
                    "build_opening_quality_context only interprets live_ui traces "
                    "with canonical_player_flow=true"
                ),
                "actual": {
                    "trace_origin": meta.get("trace_origin"),
                    "canonical_player_flow": meta.get("canonical_player_flow"),
                },
            }
        det_scores, judge_scores = _extract_scores_split(raw)
        role = str(meta.get("selected_player_role") or "").strip().title() or "Unknown"
        live_opening = float(det_scores.get("live_opening_contract_pass") or 0.0)
        live_runtime = float(det_scores.get("live_runtime_contract_pass") or 0.0)

        def _jcat(name: str) -> str | None:
            j = judge_scores.get(name)
            return (j or {}).get("category") if j else None

        recommended_next_card: str | None = None
        must_not_change = [
            "Do not weaken live_opening_contract_pass",
            "Do not let LLM judge override deterministic actor-lane gates",
        ]
        summary_parts: list[str] = [f"This {role} live opening"]
        if live_opening < 1.0:
            recommended_next_card = "RUNTIME-CONTRACT-01"
            summary_parts.append(
                "failed deterministic runtime gates — contract repair required before quality work."
            )
            must_not_change.append("Do not attempt style/content repairs until runtime gates pass")
        elif live_runtime < 1.0:
            recommended_next_card = "RUNTIME-CONTRACT-01"
            summary_parts.append("failed live_runtime_contract_pass — runtime repair required.")
        else:
            summary_parts.append("passed deterministic runtime gates")
            judge_issue_labels: list[str] = []
            judge_cats = {
                "opening_experience_judge": _jcat("opening_experience_judge"),
                "role_anchor_quality_judge": _jcat("role_anchor_quality_judge"),
                "theatrical_style_judge": _jcat("theatrical_style_judge"),
                "actor_lane_narrative_violation_judge": _jcat("actor_lane_narrative_violation_judge"),
                "rag_context_usefulness_judge": _jcat("rag_context_usefulness_judge"),
            }
            detail_parts = []
            for short, full in (
                ("opening experience", "opening_experience_judge"),
                ("role anchor", "role_anchor_quality_judge"),
                ("theatrical style", "theatrical_style_judge"),
                ("actor-lane judge", "actor_lane_narrative_violation_judge"),
                ("RAG use", "rag_context_usefulness_judge"),
            ):
                cat = judge_cats[full]
                if cat:
                    detail_parts.append(f"{short}: {cat}")
                if cat and cat.lower() in _BAD_JUDGE_CATS:
                    judge_issue_labels.append(short.replace("-", "_").replace(" ", "_"))
                    if not recommended_next_card:
                        recommended_next_card = {
                            "opening_experience_judge": "OPEN-EXP-01",
                            "role_anchor_quality_judge": "OPEN-ROLE-01",
                            "theatrical_style_judge": "OPEN-STYLE-01",
                            "actor_lane_narrative_violation_judge": "OPEN-ACTORLANE-01",
                            "rag_context_usefulness_judge": "OPEN-RAG-01",
                        }[full]
                    if full == "actor_lane_narrative_violation_judge":
                        must_not_change.append(
                            "Deterministic actor-lane gate is authoritative — judge is advisory only"
                        )
            if detail_parts:
                summary_parts.append(f"({', '.join(detail_parts)})")
            if judge_issue_labels:
                summary_parts.append(
                    f". Main improvement targets: {', '.join(judge_issue_labels)}."
                )
            else:
                summary_parts.append(". No judge issues detected.")
        evidence_judges: dict[str, Any] = {}
        for jname, detail in judge_scores.items():
            entry: dict[str, Any] = {"category": detail.get("category"), "value": detail.get("value")}
            if include_raw_reasoning and detail.get("reasoning"):
                entry["reasoning"] = detail["reasoning"]
            evidence_judges[jname] = entry
        return {
            "ok": True,
            "trace_id": trace_id,
            "ai_context_summary": " ".join(summary_parts),
            "recommended_next_card": recommended_next_card,
            "must_not_change": must_not_change,
            "evidence": {"deterministic": det_scores, "judges": evidence_judges},
        }

    return {
        "run_projection_tests": run_projection_tests,
        "fetch_langfuse_trace": fetch_langfuse_trace,
        "query_langfuse_traces": query_langfuse_traces,
        "assert_langfuse_opening_contract": assert_langfuse_opening_contract,
        "summarize_live_opening_matrix": summarize_live_opening_matrix,
        "fetch_langfuse_trace_scores": fetch_langfuse_trace_scores,
        "summarize_opening_judge_scores": summarize_opening_judge_scores,
        "build_opening_quality_context": build_opening_quality_context,
    }

