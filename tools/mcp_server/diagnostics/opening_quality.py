"""Opening-quality MCP probe (durable replacement for ``scripts/_mcp_check_*``).

Drives the local ``wos-mcp`` stdio launcher in batched ``subprocess.run``
passes (no interactive Popen, no Windows pipe-buffering deadlocks) and
classifies opening / non-opening traces against the ADR-0033 live-runtime
contract:

* ``HEALTHY_LIVE_OPENING``    — opening trace, live origin, all gates pass.
* ``DEGRADED_FALLBACK_OPENING`` — live opening trace whose
                                 ``fallback_absent == 0`` AND
                                 ``non_mock_generation_pass == 0``. That gate
                                 pair is the canonical signature of an LDSS
                                 fallback per ADR-0033 §13.1 / §13.7
                                 (regression-guarded by
                                 ``world-engine/tests/test_trace_middleware.py``).
                                 Surfaced as a *contractually correct*
                                 degraded state, not an MCP probe failure.
                                 ``final_adapter == "ldss_fallback"`` is
                                 confirming evidence when present, but the
                                 MCP score tool does not expose it today,
                                 so the gate pair is authoritative.
* ``NON_OPENING_OK``          — turn.execute (or other non-opening) trace
                                 with ``is_opening_trace=false`` and
                                 ``live_opening_contract_pass`` either
                                 ``"not_applicable"`` or absent.
* ``TEST_TRACE``              — trace whose ``trace_origin`` is ``pytest``
                                 or ``execution_tier`` is ``contract_test``.
                                 The live-runtime contract does not apply;
                                 reported separately so live-stack regressions
                                 don't get masked by test traces.
* ``UNCLASSIFIED``            — payload missing the fields needed to decide,
                                 OR an opening that fails gates without the
                                 LDSS-fallback signature (real regression
                                 suspect — surfaced explicitly).

The CLI entrypoint lives in :mod:`tools.mcp_server.diagnostics.__main__`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = REPO_ROOT / "scripts" / "wos_mcp_stdio_launcher.py"
DEFAULT_REPORT_PATH = REPO_ROOT / "tests" / "reports" / "MCP_OPENING_QUALITY_PROBE.json"

PASS_VALUES: tuple[Any, ...] = (1, 1.0, True, "1", "1.0", "pass")
NA_VALUES: tuple[Any, ...] = ("not_applicable", "n/a", "na", None, "")


class Classification(str, Enum):
    HEALTHY_LIVE_OPENING = "HEALTHY_LIVE_OPENING"
    DEGRADED_FALLBACK_OPENING = "DEGRADED_FALLBACK_OPENING"
    NON_OPENING_OK = "NON_OPENING_OK"
    TEST_TRACE = "TEST_TRACE"
    UNCLASSIFIED = "UNCLASSIFIED"


_TEST_TRACE_ORIGINS = frozenset({"pytest", "test", "ci", "ai_testing"})
_TEST_EXECUTION_TIERS = frozenset({"contract_test", "test", "ai_testing"})


@dataclass
class ClassificationRow:
    trace_id: str
    trace_name: str
    is_opening_trace: bool | None
    classification: Classification
    deterministic_scores: dict[str, Any]
    final_adapter: str | None
    fallback_reason: str | None
    trace_origin: str | None = None
    execution_tier: str | None = None
    degradation_chain: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class OpeningQualityReport:
    generated_at: str
    selected_trace_ids: list[str]
    matrix: dict[str, Any]
    judges: dict[str, Any]
    query_traces: dict[str, Any] | None
    scores_by_trace: dict[str, dict[str, Any]]
    contexts_by_trace: dict[str, dict[str, Any]]
    rows: list[ClassificationRow]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "selected_trace_ids": self.selected_trace_ids,
            "matrix": self.matrix,
            "judges": self.judges,
            "query_traces": self.query_traces,
            "scores_by_trace": self.scores_by_trace,
            "contexts_by_trace": self.contexts_by_trace,
            "rows": [
                {
                    "trace_id": r.trace_id,
                    "trace_name": r.trace_name,
                    "is_opening_trace": r.is_opening_trace,
                    "classification": r.classification.value,
                    "deterministic_scores": r.deterministic_scores,
                    "final_adapter": r.final_adapter,
                    "fallback_reason": r.fallback_reason,
                    "trace_origin": r.trace_origin,
                    "execution_tier": r.execution_tier,
                    "degradation_chain": r.degradation_chain,
                    "notes": r.notes,
                }
                for r in self.rows
            ],
        }


# --- Subprocess driver -------------------------------------------------------


def _build_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    env.setdefault("WOS_MCP_OPERATING_PROFILE", "healthy")
    env.setdefault("LANGFUSE_MCP_ENABLED", "1")
    return env


def _format_input(requests: Iterable[dict]) -> str:
    return "".join(json.dumps(req) + "\n" for req in requests)


def _parse_responses(stdout: str) -> dict[int, dict]:
    """Extract id→response from a launcher stdout dump.

    The MCP server emits one JSON-RPC response per line. Notifications (no
    ``id``) and stderr-only log lines are ignored.
    """
    out: dict[int, dict] = {}
    for raw in stdout.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rid = payload.get("id")
        if isinstance(rid, int):
            out[rid] = payload
    return out


def _extract_tool_result(rpc_response: dict | None) -> dict:
    """Unwrap a ``tools/call`` response into the inner JSON payload.

    Returns ``{"_error": ..., ...}`` markers rather than raising so the
    classifier can still produce ``UNCLASSIFIED`` rows for missing data.
    """
    if not isinstance(rpc_response, dict):
        return {"_error": "non_dict_response", "raw": rpc_response}
    if "error" in rpc_response:
        return {"_error": "rpc_error", "raw": rpc_response.get("error")}
    result = rpc_response.get("result")
    if not isinstance(result, dict):
        return {"_error": "no_result", "raw": rpc_response}
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


def _run_batch(
    requests: list[dict],
    *,
    timeout: float,
    launcher_path: Path = LAUNCHER,
    env: dict[str, str] | None = None,
) -> dict[int, dict]:
    """Spawn a fresh launcher, send all requests, capture and parse stdout."""
    proc = subprocess.run(
        [sys.executable, "-u", str(launcher_path)],
        input=_format_input(requests),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env if env is not None else _build_env(),
        timeout=timeout,
    )
    return _parse_responses(proc.stdout)


# --- Trace selection ---------------------------------------------------------


def _trace_id_of(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    for key in ("trace_id", "traceId", "id"):
        v = item.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def _matrix_rows(matrix: dict | None) -> list[dict]:
    if not isinstance(matrix, dict):
        return []
    for key in ("rows", "matrix", "traces", "items", "entries", "openings", "data"):
        v = matrix.get(key)
        if isinstance(v, list) and v:
            return [r for r in v if isinstance(r, dict)]
    return []


def _query_traces_rows(query_payload: dict | None) -> list[dict]:
    if not isinstance(query_payload, dict):
        return []
    for key in ("traces", "rows", "items", "data"):
        v = query_payload.get(key)
        if isinstance(v, list) and v:
            return [r for r in v if isinstance(r, dict)]
    return []


def _select_trace_ids(
    matrix: dict,
    *,
    with_turn_execute: bool,
    query_payload: dict | None = None,
    override: list[str] | None = None,
) -> list[str]:
    """Select up to one opening trace and optionally one turn.execute trace.

    The opening matrix only carries ``session.create`` rows by design, so a
    non-opening trace_id has to come from ``query_langfuse_traces`` (passed
    as ``query_payload`` when ``with_turn_execute=True``).
    """
    if override:
        return list(override)[:2]

    selected: list[str] = []
    for row in _matrix_rows(matrix):
        tid = _trace_id_of(row)
        if tid:
            selected.append(tid)
            break

    if with_turn_execute:
        for row in _query_traces_rows(query_payload):
            name = str(row.get("name", "")).lower()
            if "turn.execute" not in name:
                continue
            tid = _trace_id_of(row)
            if tid and tid not in selected:
                selected.append(tid)
                break

    return selected[:2]


# --- Classification ----------------------------------------------------------


def _is_pass(value: Any) -> bool:
    return value in PASS_VALUES


def _is_not_applicable(value: Any) -> bool:
    return value in NA_VALUES


def _merge_deterministic_scores(scores_payload: dict, context_payload: dict) -> dict[str, Any]:
    """Take both observed shapes (top-level vs evidence.deterministic) and
    merge with score-payload keys winning."""
    from_score = scores_payload.get("deterministic_scores") if isinstance(scores_payload, dict) else None
    from_ctx_evidence = (
        ((context_payload or {}).get("evidence") or {}).get("deterministic")
        if isinstance(context_payload, dict)
        else None
    )
    merged: dict[str, Any] = {}
    if isinstance(from_ctx_evidence, dict):
        merged.update(from_ctx_evidence)
    if isinstance(from_score, dict):
        merged.update(from_score)
    return merged


def _final_adapter(scores_payload: dict, context_payload: dict) -> str | None:
    """Best-effort lookup of the committed adapter name for the trace."""
    candidates: list[Any] = []
    if isinstance(scores_payload, dict):
        candidates.extend(
            [
                scores_payload.get("final_adapter"),
                ((scores_payload.get("contract_evidence") or {}).get("final_adapter")
                 if isinstance(scores_payload.get("contract_evidence"), dict)
                 else None),
                ((scores_payload.get("path_summary") or {}).get("final_adapter")
                 if isinstance(scores_payload.get("path_summary"), dict)
                 else None),
            ]
        )
    if isinstance(context_payload, dict):
        evidence = context_payload.get("evidence") or {}
        if isinstance(evidence, dict):
            det = evidence.get("deterministic")
            if isinstance(det, dict):
                candidates.append(det.get("final_adapter"))
            ps = evidence.get("path_summary")
            if isinstance(ps, dict):
                candidates.append(ps.get("final_adapter"))
    for c in candidates:
        if isinstance(c, str) and c:
            return c.lower()
    return None


def _fallback_reason(scores_payload: dict, context_payload: dict) -> str | None:
    for src in (scores_payload, context_payload):
        if not isinstance(src, dict):
            continue
        for key in ("fallback_reason", "live_opening_failure_reason"):
            v = src.get(key)
            if isinstance(v, str) and v:
                return v
        evidence = src.get("evidence") if isinstance(src.get("evidence"), dict) else None
        if evidence:
            for key in ("fallback_reason", "live_opening_failure_reason"):
                v = evidence.get(key)
                if isinstance(v, str) and v:
                    return v
    return None


def _degradation_chain(scores_payload: dict, context_payload: dict) -> list[str]:
    for src in (scores_payload, context_payload):
        if not isinstance(src, dict):
            continue
        chain = src.get("degradation_chain")
        if isinstance(chain, list) and chain:
            return [str(x) for x in chain]
        evidence = src.get("evidence") if isinstance(src.get("evidence"), dict) else None
        if evidence:
            chain = evidence.get("degradation_chain")
            if isinstance(chain, list) and chain:
                return [str(x) for x in chain]
    return []


def _is_test_trace(scores_payload: dict, context_payload: dict) -> tuple[bool, str | None, str | None]:
    """Return ``(is_test, trace_origin, execution_tier)`` for a trace.

    A trace is a test trace if its ``trace_origin`` is in
    ``_TEST_TRACE_ORIGINS`` (e.g. ``pytest``) or its ``execution_tier`` is in
    ``_TEST_EXECUTION_TIERS`` (e.g. ``contract_test``). Test traces are
    classified separately because the live-runtime contract does not apply.
    """
    trace_origin: str | None = None
    execution_tier: str | None = None
    for src in (scores_payload, context_payload):
        if not isinstance(src, dict):
            continue
        if trace_origin is None:
            v = src.get("trace_origin")
            if isinstance(v, str) and v:
                trace_origin = v.lower()
        if execution_tier is None:
            v = src.get("execution_tier")
            if isinstance(v, str) and v:
                execution_tier = v.lower()
    is_test = (
        (trace_origin in _TEST_TRACE_ORIGINS if trace_origin else False)
        or (execution_tier in _TEST_EXECUTION_TIERS if execution_tier else False)
    )
    return is_test, trace_origin, execution_tier


def _has_ldss_fallback_signature(det: dict, final_adapter: str | None) -> bool:
    """Per ADR-0033 §13.1: an LDSS fallback opening always emits
    ``fallback_absent == 0`` AND ``non_mock_generation_pass == 0``. The
    optional ``final_adapter == "ldss_fallback"`` is confirming evidence
    when present; today no MCP tool surfaces it, so the gate-pair signature
    is authoritative.
    """
    if final_adapter == "ldss_fallback":
        return True
    fa = det.get("fallback_absent")
    nm = det.get("non_mock_generation_pass")
    fa_zero = fa == 0 or fa == 0.0
    nm_zero = nm == 0 or nm == 0.0
    return fa_zero and nm_zero


def _classify(scores_payload: dict, context_payload: dict) -> ClassificationRow:
    """Build a classification row from one trace's scores + context payloads.

    Pure function — no I/O, no Langfuse, no MCP. Synthetic-payload tests
    pin every contractual outcome.
    """
    if not isinstance(scores_payload, dict):
        scores_payload = {}
    if not isinstance(context_payload, dict):
        context_payload = {}

    trace_id = (
        scores_payload.get("trace_id")
        or context_payload.get("trace_id")
        or ""
    )
    trace_name = (
        scores_payload.get("trace_name")
        or context_payload.get("trace_name")
        or ""
    )
    is_opening = scores_payload.get("is_opening_trace")
    if is_opening is None:
        is_opening = context_payload.get("is_opening_trace")

    det = _merge_deterministic_scores(scores_payload, context_payload)
    final_adapter = _final_adapter(scores_payload, context_payload)
    fallback_reason = _fallback_reason(scores_payload, context_payload)
    chain = _degradation_chain(scores_payload, context_payload)
    is_test, trace_origin, execution_tier = _is_test_trace(scores_payload, context_payload)

    notes: list[str] = []
    if scores_payload.get("_error"):
        notes.append(f"scores_payload error: {scores_payload['_error']}")
    if context_payload.get("_error"):
        notes.append(f"context_payload error: {context_payload['_error']}")

    if is_test:
        classification = Classification.TEST_TRACE
        notes.append(
            f"Test trace (trace_origin={trace_origin!r}, "
            f"execution_tier={execution_tier!r}); live-runtime contract does not apply."
        )
    elif is_opening is True:
        soc = det.get("opening_shape_contract_pass")
        lrc = det.get("live_runtime_contract_pass")
        loc = det.get("live_opening_contract_pass")
        all_gates_pass = _is_pass(soc) and _is_pass(lrc) and _is_pass(loc)
        if all_gates_pass and final_adapter != "ldss_fallback":
            classification = Classification.HEALTHY_LIVE_OPENING
        elif _has_ldss_fallback_signature(det, final_adapter):
            classification = Classification.DEGRADED_FALLBACK_OPENING
            sig_source = (
                "final_adapter=ldss_fallback"
                if final_adapter == "ldss_fallback"
                else "fallback_absent=0 AND non_mock_generation_pass=0 (gate-pair signature)"
            )
            notes.append(
                f"Per ADR-0033 §13.1/§13.7: degraded LDSS-fallback opening "
                f"({sig_source}); contractually correct, NOT an MCP probe failure."
            )
        else:
            classification = Classification.UNCLASSIFIED
            notes.append(
                f"Opening trace did not satisfy gates and lacks the LDSS-fallback "
                f"signature (final_adapter={final_adapter!r}, "
                f"fallback_absent={det.get('fallback_absent')!r}, "
                f"non_mock_generation_pass={det.get('non_mock_generation_pass')!r}). "
                f"Live-stack regression suspected."
            )
    elif is_opening is False:
        loc = det.get("live_opening_contract_pass")
        if _is_not_applicable(loc):
            classification = Classification.NON_OPENING_OK
        else:
            classification = Classification.UNCLASSIFIED
            notes.append(
                f"Non-opening trace has live_opening_contract_pass={loc!r}; "
                "expected 'not_applicable' or absent."
            )
    else:
        classification = Classification.UNCLASSIFIED
        notes.append(f"is_opening_trace={is_opening!r} — could not classify")

    return ClassificationRow(
        trace_id=str(trace_id),
        trace_name=str(trace_name),
        is_opening_trace=is_opening,
        classification=classification,
        deterministic_scores=det,
        final_adapter=final_adapter,
        fallback_reason=fallback_reason,
        trace_origin=trace_origin,
        execution_tier=execution_tier,
        degradation_chain=chain,
        notes=notes,
    )


# --- High-level driver -------------------------------------------------------


def _pass_matrix_judges(*, matrix_limit: int, judge_limit_per_role: int) -> tuple[dict, dict]:
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
                "arguments": {"limit_per_role": judge_limit_per_role},
            },
        },
    ]
    responses = _run_batch(requests, timeout=120.0)
    return _extract_tool_result(responses.get(2)), _extract_tool_result(responses.get(3))


def _pass_query_traces(*, limit: int) -> dict:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "query_langfuse_traces",
                "arguments": {"limit": limit},
            },
        },
    ]
    responses = _run_batch(requests, timeout=120.0)
    return _extract_tool_result(responses.get(2))


def _pass_per_trace(trace_ids: list[str]) -> tuple[dict[str, dict], dict[str, dict]]:
    if not trace_ids:
        return {}, {}
    requests: list[dict] = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    ]
    plan: list[tuple[str, str]] = []
    rid = 2
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
        payload = _extract_tool_result(responses.get(expected_id))
        if kind == "scores":
            scores[tid] = payload
        else:
            contexts[tid] = payload
        expected_id += 1
    return scores, contexts


def run_opening_quality_probe(
    *,
    matrix_limit: int = 15,
    judge_limit_per_role: int = 5,
    with_turn_execute: bool = False,
    trace_id_overrides: list[str] | None = None,
    report_path: Path | None = DEFAULT_REPORT_PATH,
) -> OpeningQualityReport:
    """End-to-end opening-quality probe. See module docstring for state model."""
    matrix, judges = _pass_matrix_judges(
        matrix_limit=matrix_limit,
        judge_limit_per_role=judge_limit_per_role,
    )
    query_payload: dict | None = None
    if with_turn_execute and not trace_id_overrides:
        query_payload = _pass_query_traces(limit=100)

    trace_ids = _select_trace_ids(
        matrix,
        with_turn_execute=with_turn_execute,
        query_payload=query_payload,
        override=trace_id_overrides,
    )
    scores, contexts = _pass_per_trace(trace_ids)
    rows = [_classify(scores.get(tid, {}), contexts.get(tid, {})) for tid in trace_ids]

    report = OpeningQualityReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        selected_trace_ids=trace_ids,
        matrix=matrix if isinstance(matrix, dict) else {"_error": "matrix_not_dict"},
        judges=judges if isinstance(judges, dict) else {"_error": "judges_not_dict"},
        query_traces=query_payload,
        scores_by_trace=scores,
        contexts_by_trace=contexts,
        rows=rows,
    )

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return report
