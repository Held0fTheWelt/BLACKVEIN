"""Opening-quality MCP probe (batch-subprocess driver).

Two-pass design:
    Pass 1: send ``initialize`` + ``summarize_live_opening_matrix`` +
            ``summarize_opening_judge_scores`` to a fresh launcher
            instance, close stdin, read all responses, pick trace_ids.
    Pass 2: spawn a fresh launcher, send ``initialize`` plus one
            ``fetch_langfuse_trace_scores`` and one
            ``build_opening_quality_context`` per selected trace_id,
            close stdin, read all responses.

Each pass uses ``subprocess.run`` with a 90-second hard timeout, which
avoids the Popen-poll deadlocks the previous interactive driver hit on
Windows when Langfuse responses lagged. The server side already flushes
stdout after every response (see tools/mcp_server/server.py), so closing
stdin once all requests are sent causes the server to drain, write its
final response, hit EOF, and exit cleanly.

Outputs:
    - Plain-text summary on stdout (visible in Cursor terminal)
    - Full structured report at tests/reports/MCP_OPENING_QUALITY_PROBE.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "scripts" / "wos_mcp_stdio_launcher.py"
REPORT_PATH = REPO / "tests" / "reports" / "MCP_OPENING_QUALITY_PROBE.json"


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    env.setdefault("WOS_MCP_OPERATING_PROFILE", "healthy")
    env.setdefault("LANGFUSE_MCP_ENABLED", "1")
    env.setdefault("WOS_AI_AGENT_TESTING", "1")
    return env


def _format_input(requests: list[dict]) -> str:
    return "".join(json.dumps(req) + "\n" for req in requests)


def _run_batch(requests: list[dict], timeout: float) -> dict[int, dict]:
    proc = subprocess.run(
        [sys.executable, "-u", str(LAUNCHER)],
        input=_format_input(requests),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=_build_env(),
        timeout=timeout,
    )
    responses: dict[int, dict] = {}
    for raw in proc.stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rid = payload.get("id")
        if isinstance(rid, int):
            responses[rid] = payload
    return responses


def _tool_result(resp: dict) -> dict:
    """Extract the structured payload from a tools/call response.

    MCP framing nests the JSON dict inside ``result.content[0].text`` (a
    JSON string). If anything is off, return the raw response with an
    ``_error`` marker so the assessment can still proceed.
    """
    if not isinstance(resp, dict):
        return {"_error": "non_dict_response", "raw": resp}
    if "error" in resp:
        return {"_error": "rpc_error", "raw": resp.get("error")}
    result = resp.get("result")
    if not isinstance(result, dict):
        return {"_error": "no_result", "raw": resp}
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"_error": "result_text_not_json", "text": text}
    return result


def _pass1(matrix_limit: int) -> tuple[dict, dict]:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "summarize_live_opening_matrix",
                "arguments": {"limit": matrix_limit},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "summarize_opening_judge_scores",
                "arguments": {"limit_per_role": 5},
            },
        },
    ]
    responses = _run_batch(requests, timeout=120.0)
    matrix = _tool_result(responses.get(2, {}))
    judges = _tool_result(responses.get(3, {}))
    return matrix, judges


def _pass2(trace_ids: list[str]) -> tuple[dict[str, dict], dict[str, dict]]:
    requests: list[dict] = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    ]
    rid = 2
    plan: list[tuple[str, str]] = []  # (trace_id, kind)
    for tid in trace_ids:
        requests.append(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "method": "tools/call",
                "params": {
                    "name": "fetch_langfuse_trace_scores",
                    "arguments": {"trace_id": tid, "allow_non_live": True},
                },
            }
        )
        plan.append((tid, "scores"))
        rid += 1
        requests.append(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "method": "tools/call",
                "params": {
                    "name": "build_opening_quality_context",
                    "arguments": {"trace_id": tid, "include_raw_reasoning": False},
                },
            }
        )
        plan.append((tid, "context"))
        rid += 1
    responses = _run_batch(requests, timeout=180.0)
    scores: dict[str, dict] = {}
    contexts: dict[str, dict] = {}
    expected_id = 2
    for tid, kind in plan:
        resp = responses.get(expected_id, {})
        payload = _tool_result(resp)
        if kind == "scores":
            scores[tid] = payload
        else:
            contexts[tid] = payload
        expected_id += 1
    return scores, contexts


def _select_trace_ids(matrix: dict, override: list[str]) -> list[str]:
    if override:
        return override[:2]
    bag: list[Any] = []
    for k in ("rows", "matrix", "traces", "items", "entries", "openings", "data"):
        v = matrix.get(k) if isinstance(matrix, dict) else None
        if isinstance(v, list) and v:
            bag = v
            break

    def _tid(item: Any) -> str | None:
        if not isinstance(item, dict):
            return None
        for key in ("trace_id", "traceId", "id"):
            v = item.get(key)
            if isinstance(v, str) and v:
                return v
        return None

    opening_id: str | None = None
    non_opening_id: str | None = None
    fallback: list[str] = []
    for item in bag:
        tid = _tid(item)
        if not tid:
            continue
        if tid not in fallback:
            fallback.append(tid)
        flag = item.get("is_opening_trace") if isinstance(item, dict) else None
        if flag is True and opening_id is None:
            opening_id = tid
        elif flag is False and non_opening_id is None:
            non_opening_id = tid
        if opening_id and non_opening_id:
            break
    selected = [t for t in (opening_id, non_opening_id) if t]
    if len(selected) < 2:
        for t in fallback:
            if t not in selected:
                selected.append(t)
            if len(selected) >= 2:
                break
    return selected[:2]


_PASS_VALUES = (1, 1.0, True, "1", "1.0", "pass")
_NA_VALUES = ("not_applicable", "n/a", "na", None)


def _assess(report: dict) -> tuple[bool, list[str], list[dict]]:
    issues: list[str] = []
    rows: list[dict] = []
    score_payloads = report.get("langfuse_trace_scores", {}) or {}
    context_payloads = report.get("opening_quality_contexts", {}) or {}
    selected = report.get("selected_trace_ids", []) or list(score_payloads.keys())
    if not selected:
        return False, ["no trace_ids selected"], []

    for tid in selected:
        score = score_payloads.get(tid) or {}
        ctx = context_payloads.get(tid) or {}
        det_score = score.get("deterministic_scores") or {}
        det_ctx = (ctx.get("evidence") or {}).get("deterministic") or {}
        det = {**det_ctx, **det_score}

        is_opening = score.get("is_opening_trace")
        if is_opening is None:
            is_opening = ctx.get("is_opening_trace")
        trace_name = score.get("trace_name") or ctx.get("trace_name") or ""

        soc = det.get("opening_shape_contract_pass")
        lrc = det.get("live_runtime_contract_pass")
        loc = det.get("live_opening_contract_pass")

        row = {
            "trace_id": tid,
            "trace_name": trace_name,
            "is_opening_trace": is_opening,
            "opening_shape_contract_pass": soc,
            "live_runtime_contract_pass": lrc,
            "live_opening_contract_pass": loc,
        }
        rows.append(row)

        if is_opening is True:
            if soc not in _PASS_VALUES:
                issues.append(f"{tid}: opening_shape_contract_pass={soc!r} (expected 1)")
            if lrc not in _PASS_VALUES:
                issues.append(f"{tid}: live_runtime_contract_pass={lrc!r} (expected 1)")
            if loc not in _PASS_VALUES:
                issues.append(f"{tid}: live_opening_contract_pass={loc!r} (expected 1)")
        elif is_opening is False:
            if loc not in _NA_VALUES:
                issues.append(
                    f"{tid}: live_opening_contract_pass={loc!r} "
                    f"(expected 'not_applicable')"
                )
        else:
            issues.append(f"{tid}: is_opening_trace={is_opening!r} (could not classify)")

    return (not issues), issues, rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-limit", type=int, default=15)
    parser.add_argument("--trace-id", action="append", default=[])
    args = parser.parse_args()

    print("[pass 1] initialize + summarize_live_opening_matrix + summarize_opening_judge_scores ...", flush=True)
    matrix, judges = _pass1(args.matrix_limit)
    print(f"[pass 1] matrix keys: {sorted(matrix.keys()) if isinstance(matrix, dict) else type(matrix).__name__}", flush=True)
    print(f"[pass 1] judges keys: {sorted(judges.keys()) if isinstance(judges, dict) else type(judges).__name__}", flush=True)

    trace_ids = _select_trace_ids(matrix, args.trace_id)
    print(f"[pass 1] selected trace_ids: {trace_ids}", flush=True)
    if not trace_ids:
        print("FAIL: no trace_ids returned by matrix; nothing to assess.", file=sys.stderr)
        return 2

    print(f"[pass 2] fetch_langfuse_trace_scores + build_opening_quality_context for {len(trace_ids)} trace(s) ...", flush=True)
    scores, contexts = _pass2(trace_ids)

    report = {
        "selected_trace_ids": trace_ids,
        "summarize_live_opening_matrix": matrix,
        "summarize_opening_judge_scores": judges,
        "langfuse_trace_scores": scores,
        "opening_quality_contexts": contexts,
    }
    ok, issues, rows = _assess(report)
    report["assessment"] = {"ok": ok, "issues": issues, "rows": rows}

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print()
    print("=== ASSESSMENT ===")
    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    print(f"\nok       : {ok}")
    for issue in issues:
        print(f"  - {issue}")
    print(f"\nfull report: {REPORT_PATH}")
    return 0 if ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
