"""Drive the wos-mcp stdio launcher to verify opening-quality contracts.

Sequence:
    1. initialize
    2. tools/call summarize_live_opening_matrix
    3. tools/call summarize_opening_judge_scores
    4. tools/call run_projection_tests
    5. for each opening trace returned by step 2:
         - tools/call fetch_langfuse_trace_scores
         - tools/call build_opening_quality_context

Validates the user-stated expectations:
    * Turn 0 / session.create  -> is_opening_trace=True,
                                  opening_shape_contract_pass=1,
                                  live_runtime_contract_pass=1,
                                  live_opening_contract_pass=1
    * Turn 1+ / turn.execute   -> is_opening_trace=False,
                                  live_opening_contract_pass=not_applicable

Outputs human-readable summary to stdout and full JSON dump to
``tests/reports/MCP_OPENING_QUALITY_PROBE.json`` for archival.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
LAUNCHER = REPO / "scripts" / "wos_mcp_stdio_launcher.py"
REPORT_PATH = REPO / "tests" / "reports" / "MCP_OPENING_QUALITY_PROBE.json"


class StdioRpcClient:
    """Minimal newline-JSON RPC client over a child process stdio pair."""

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc
        self._next_id = 1

    def call(self, method: str, params: dict | None = None) -> dict:
        rid = self._next_id
        self._next_id += 1
        msg = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or {}}
        line = json.dumps(msg) + "\n"
        assert self._proc.stdin is not None and self._proc.stdout is not None
        self._proc.stdin.write(line)
        self._proc.stdin.flush()
        while True:
            raw = self._proc.stdout.readline()
            if not raw:
                raise RuntimeError(f"Server closed stdout while waiting for id={rid}")
            try:
                resp = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if resp.get("id") == rid:
                return resp


def call_tool(client: StdioRpcClient, name: str, arguments: dict | None = None) -> Any:
    resp = client.call("tools/call", {"name": name, "arguments": arguments or {}})
    if "error" in resp:
        raise RuntimeError(f"tools/call {name} failed: {resp['error']}")
    result = resp.get("result", {})
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict) and first.get("type") == "text":
            text = first.get("text", "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"_raw_text": text}
    return result


def find_opening_trace_ids(matrix_payload: Any) -> list[str]:
    """Pick exactly two trace_ids from the live opening matrix:
    the most recent ``is_opening_trace=true`` and the most recent
    ``is_opening_trace=false``. Falls back to first two distinct ids if the
    matrix doesn't carry the opening flag.
    """
    if not isinstance(matrix_payload, dict):
        return []
    bag: list[Any] = []
    for k in ("rows", "matrix", "traces", "items", "entries", "openings", "data"):
        v = matrix_payload.get(k)
        if isinstance(v, list):
            bag.extend(v)
            if v:
                break

    def _tid(item: dict) -> str | None:
        for key in ("trace_id", "traceId", "id"):
            v = item.get(key)
            if isinstance(v, str) and v:
                return v
        return None

    opening_id: str | None = None
    non_opening_id: str | None = None
    fallback: list[str] = []
    for item in bag:
        if not isinstance(item, dict):
            continue
        tid = _tid(item)
        if not tid:
            continue
        if tid not in fallback:
            fallback.append(tid)
        flag = item.get("is_opening_trace")
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


_PASS_VALUES = (1, 1.0, True, "1", "1.0")
_NA_VALUES = ("not_applicable", "n/a", "na", None)


def _is_pass(value: Any) -> bool:
    return value in _PASS_VALUES


def _is_not_applicable(value: Any) -> bool:
    return value in _NA_VALUES


def assess(report: dict) -> tuple[bool, list[str]]:
    """Return (ok, reasons) by combining fetch_langfuse_trace_scores (top-level
    deterministic_scores) and build_opening_quality_context (top-level
    is_opening_trace + evidence.deterministic) per trace.
    """
    issues: list[str] = []
    score_payloads = report.get("langfuse_trace_scores", {})
    context_payloads = report.get("opening_quality_contexts", {})
    if not score_payloads and not context_payloads:
        issues.append("no per-trace payloads collected")
        return False, issues

    for tid in report.get("selected_trace_ids", []) or list(score_payloads.keys()):
        score = score_payloads.get(tid) or {}
        ctx = context_payloads.get(tid) or {}
        det_from_score = score.get("deterministic_scores") or {}
        det_from_ctx = (ctx.get("evidence") or {}).get("deterministic") or {}
        det = {**det_from_ctx, **det_from_score}  # score data wins

        is_opening = score.get("is_opening_trace")
        if is_opening is None:
            is_opening = ctx.get("is_opening_trace")
        trace_name = score.get("trace_name") or ctx.get("trace_name") or ""

        soc = det.get("opening_shape_contract_pass")
        lrc = det.get("live_runtime_contract_pass")
        loc = det.get("live_opening_contract_pass")
        is_session_create = (
            is_opening is True
            or "session.create" in str(trace_name).lower()
        )

        if is_session_create:
            if is_opening is not True:
                issues.append(f"{tid} [{trace_name}]: expected is_opening_trace=true (got {is_opening!r})")
            if not _is_pass(soc):
                issues.append(f"{tid} [{trace_name}]: expected opening_shape_contract_pass=1 (got {soc!r})")
            if not _is_pass(lrc):
                issues.append(f"{tid} [{trace_name}]: expected live_runtime_contract_pass=1 (got {lrc!r})")
            if not _is_pass(loc):
                issues.append(f"{tid} [{trace_name}]: expected live_opening_contract_pass=1 (got {loc!r})")
        else:
            if is_opening is not False:
                issues.append(f"{tid} [{trace_name}]: expected is_opening_trace=false (got {is_opening!r})")
            if not _is_not_applicable(loc):
                issues.append(
                    f"{tid} [{trace_name}]: expected live_opening_contract_pass='not_applicable' (got {loc!r})"
                )
    return (not issues), issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-ids", nargs="*", default=None,
                        help="Override trace ids (skip matrix lookup)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Limit for summarize_live_opening_matrix")
    parser.add_argument("--skip-projection-tests", action="store_true",
                        help="Skip run_projection_tests (it is slow)")
    args = parser.parse_args()

    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    proc = subprocess.Popen(
        [sys.executable, str(LAUNCHER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=tempfile.gettempdir(),
        env=env,
        bufsize=1,
    )
    try:
        client = StdioRpcClient(proc)
        init = client.call("initialize", {})
        report: dict[str, Any] = {"initialize": init.get("result")}

        matrix = call_tool(client, "summarize_live_opening_matrix", {"limit": args.limit})
        report["summarize_live_opening_matrix"] = matrix
        judges = call_tool(client, "summarize_opening_judge_scores", {})
        report["summarize_opening_judge_scores"] = judges
        if not args.skip_projection_tests:
            projections = call_tool(client, "run_projection_tests", {})
            report["run_projection_tests"] = projections

        trace_ids = args.trace_ids or find_opening_trace_ids(matrix)
        report["selected_trace_ids"] = trace_ids

        scores: dict[str, Any] = {}
        contexts: dict[str, Any] = {}
        for tid in trace_ids:
            scores[tid] = call_tool(
                client, "fetch_langfuse_trace_scores",
                {"trace_id": tid, "allow_non_live": True},
            )
            contexts[tid] = call_tool(
                client, "build_opening_quality_context",
                {"trace_id": tid, "include_raw_reasoning": False},
            )
        report["langfuse_trace_scores"] = scores
        report["opening_quality_contexts"] = contexts

        ok, issues = assess(report)
        report["assessment"] = {"ok": ok, "issues": issues}

        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

        print(f"trace_ids selected: {trace_ids}")
        print(f"assessment ok      : {ok}")
        for issue in issues:
            print(f"  - {issue}")
        print(f"full report        : {REPORT_PATH}")
        return 0 if ok else 3
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())
