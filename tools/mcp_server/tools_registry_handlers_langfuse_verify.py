"""MCP handlers for projection-test orchestration and Langfuse trace verification."""

from __future__ import annotations

import os
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


def _extract_metadata(raw_trace: dict[str, Any]) -> dict[str, Any]:
    metadata = raw_trace.get("metadata")
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


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
        return {"ok": True, "trace": _trace_summary(raw), "raw_trace": raw}

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

        meta = _extract_metadata(raw)
        scores = _extract_scores(raw)
        failures: list[dict[str, Any]] = []

        def fail(rule: str, message: str, field: str, actual: Any) -> None:
            failures.append(
                {"rule": rule, "message": message, "missing_field": field, "actual": actual}
            )

        if mode == "live":
            if str(meta.get("trace_origin") or "").lower() != "live_ui":
                fail("trace_origin == live_ui", "live trace origin mismatch", "metadata.trace_origin", meta.get("trace_origin"))
            if str(meta.get("execution_tier") or "").lower() != "live":
                fail("execution_tier == live", "execution tier mismatch", "metadata.execution_tier", meta.get("execution_tier"))
            if bool(meta.get("canonical_player_flow")) is not True:
                fail("canonical_player_flow == true", "canonical flow mismatch", "metadata.canonical_player_flow", meta.get("canonical_player_flow"))
            role = str(meta.get("selected_player_role") or "").lower()
            if role not in {"annette", "alain"}:
                fail("selected_player_role in [annette, alain]", "role mismatch", "metadata.selected_player_role", meta.get("selected_player_role"))
            if str(meta.get("human_actor_id") or "").lower() != role:
                fail("human_actor_id == selected_player_role", "human actor mismatch", "metadata.human_actor_id", meta.get("human_actor_id"))
            for score_name in (
                "opening_shape_contract_pass",
                "live_runtime_contract_pass",
                "live_opening_contract_pass",
            ):
                if float(scores.get(score_name) or 0.0) != 1.0:
                    fail(f"{score_name} == 1", "score mismatch", f"scores.{score_name}", scores.get(score_name))
            if str(meta.get("final_adapter") or "").lower() == "ldss_fallback":
                fail("final_adapter != ldss_fallback", "fallback adapter used", "metadata.final_adapter", meta.get("final_adapter"))
            if str(meta.get("quality_class") or "").lower() in {"degraded", "failed"}:
                fail("quality_class not degraded/failed", "quality class degraded", "metadata.quality_class", meta.get("quality_class"))
        else:
            if str(meta.get("trace_origin") or "").lower() != "pytest":
                fail("trace_origin == pytest", "test trace origin mismatch", "metadata.trace_origin", meta.get("trace_origin"))
            if bool(meta.get("canonical_player_flow")) is not False:
                fail("canonical_player_flow == false", "test flow mismatch", "metadata.canonical_player_flow", meta.get("canonical_player_flow"))
            if float(scores.get("live_opening_contract_pass") or 0.0) != 0.0:
                fail(
                    "live_opening_contract_pass == 0",
                    "test trace has live opening pass",
                    "scores.live_opening_contract_pass",
                    scores.get("live_opening_contract_pass"),
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
            meta = _extract_metadata(row)
            scores = _extract_scores(row)
            matrix.append(
                {
                    "trace_id": row.get("id"),
                    "selected_player_role": meta.get("selected_player_role"),
                    "trace_origin": meta.get("trace_origin"),
                    "execution_tier": meta.get("execution_tier"),
                    "canonical_player_flow": meta.get("canonical_player_flow"),
                    "opening_shape_contract_pass": scores.get("opening_shape_contract_pass"),
                    "live_runtime_contract_pass": scores.get("live_runtime_contract_pass"),
                    "live_opening_contract_pass": scores.get("live_opening_contract_pass"),
                    "final_adapter": meta.get("final_adapter"),
                    "quality_class": meta.get("quality_class"),
                    "narration_summary_synthesized": meta.get("narration_summary_synthesized"),
                }
            )
        return {
            "ok": True,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "count": len(matrix),
            "rows": matrix,
        }

    return {
        "run_projection_tests": run_projection_tests,
        "fetch_langfuse_trace": fetch_langfuse_trace,
        "query_langfuse_traces": query_langfuse_traces,
        "assert_langfuse_opening_contract": assert_langfuse_opening_contract,
        "summarize_live_opening_matrix": summarize_live_opening_matrix,
    }

