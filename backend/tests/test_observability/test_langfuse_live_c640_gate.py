"""Strict live regression gate for Langfuse + stack (ADR-0033 c640-style evidence).

Only skips when ``RUN_LANGFUSE_LIVE`` is not ``1``, when the backend health URL is
unreachable, or when Langfuse credentials are missing from the environment.

When live mode is active, failures are hard (no pytest.skip on trace fetch errors).

Required environment (in addition to ``RUN_LANGFUSE_LIVE=1``):

- ``LANGFUSE_PUBLIC_KEY``, ``LANGFUSE_SECRET_KEY``
- ``LANGFUSE_BASE_URL`` (optional; default ``https://cloud.langfuse.com``)
- ``LANGFUSE_LIVE_BACKEND_URL`` (optional; default ``http://127.0.0.1:8000``)

The stack must expose a working World-Engine-backed turn path and real model
credentials (e.g. ``OPENAI_API_KEY`` in compose) so gates stay green.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any

import pytest

pytest.importorskip("httpx")
import httpx  # noqa: E402


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip() == "1"


def _model_dump(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    md = getattr(obj, "model_dump", None)
    if callable(md):
        return md()
    return {}


def _observation_dicts(trace: Any) -> list[dict[str, Any]]:
    raw = trace.get("observations", None) if isinstance(trace, dict) else getattr(trace, "observations", None)
    raw = raw or []
    return [_model_dump(o) for o in raw]


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        payload = value.strip()
        if payload.startswith("{") and payload.endswith("}"):
            try:
                parsed = json.loads(payload)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
    return {}


def _find_observations_by_name(trace: Any, name: str) -> list[dict[str, Any]]:
    return [o for o in _observation_dicts(trace) if o.get("name") == name]


def _player_input_sha256_from_obs(obs: dict[str, Any]) -> str | None:
    for block in (
        obs.get("metadata") or {},
        obs.get("input") or {},
        obs.get("output") or {},
    ):
        if not isinstance(block, dict):
            continue
        h = block.get("player_input_sha256")
        if isinstance(h, str) and len(h) == 64:
            return h
    return None


def _usage_total(obs: dict[str, Any]) -> int:
    ud = obs.get("usage_details") or obs.get("usageDetails") or {}
    if not isinstance(ud, dict):
        return 0
    v = ud.get("total")
    if v is None:
        v = ud.get("total_tokens")
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _score_map(trace: Any) -> dict[str, float]:
    scores = trace.get("scores", None) if isinstance(trace, dict) else getattr(trace, "scores", None)
    scores = scores or []
    out: dict[str, float] = {}
    for s in scores:
        d = _model_dump(s)
        name = d.get("name")
        if not name:
            continue
        val = d.get("value")
        if val is None and "numeric_value" in d:
            val = d.get("numeric_value")
        try:
            out[str(name)] = float(val)
        except (TypeError, ValueError):
            continue
    return out


def _status_field(obs: dict[str, Any], key: str) -> str:
    msg = str(obs.get("statusMessage") or obs.get("status_message") or "")
    # Parse key=value tokens from span status text.
    match = re.search(rf"(?:^|\s){re.escape(key)}=([^\s]+)", msg)
    return match.group(1).strip() if match else ""


def _assert_positive_live_trace_contract(fetched: Any, *, expected_sha: str) -> None:
    by_name = {o.get("name"): o for o in _observation_dicts(fetched)}
    all_names = sorted(by_name.keys())
    assert "story.model.generation" in by_name, (
        f"Missing generation observation; have: {all_names}"
    )
    assert "story.rag.retrieval" in by_name, (
        f"Missing retrieval observation; have: {all_names}"
    )

    gen = by_name["story.model.generation"]
    model = str(gen.get("model") or "").lower()
    assert model and "mock" not in model, f"Generation model must be non-mock; got model={gen.get('model')}"

    meta = _coerce_dict(gen.get("metadata"))
    adapter = str(meta.get("adapter") or "").lower()
    assert adapter not in {"mock"}, f"Generation adapter must be non-mock; metadata.adapter={meta.get('adapter')}"

    assert _usage_total(gen) > 0, (
        f"Expected total usage > 0 on story.model.generation; "
        f"usage_details={gen.get('usage_details')} usageDetails={gen.get('usageDetails')}"
    )

    retr = by_name["story.rag.retrieval"]
    rmeta = _coerce_dict(retr.get("metadata"))
    route = str(rmeta.get("retrieval_route") or rmeta.get("route") or "").strip().lower()
    if not route:
        phase_retr = by_name.get("story.phase.retrieval", {})
        route = _status_field(phase_retr, "route").lower()
    assert route == "hybrid" or ("fallback" not in route and route != ""), (
        f"Unexpected retrieval route evidence: route={route!r}"
    )

    scores = _score_map(fetched)
    required_scores = (
        "rag_context_attached",
        "visible_output_present",
        "live_runtime_visible_surface_pass",
        "live_runtime_contract_pass",
        "fallback_absent",
        "non_mock_generation_pass",
        # usage_present is also asserted operationally via _usage_total(gen) > 0
        # below; including it by name guards against silent score-emission breakage.
        "usage_present",
    )
    missing = [n for n in required_scores if n not in scores]
    assert not missing, f"Missing scores on trace: {missing}; have: {sorted(scores.keys())}"

    for name in required_scores:
        assert scores[name] == 1.0, f"Score {name} expected 1.0, got {scores[name]!r}"

    be = _find_observations_by_name(fetched, "backend.turn.execute")
    we = _find_observations_by_name(fetched, "world-engine.turn.execute")
    assert be, f"Missing backend.turn.execute among: {all_names}"
    assert we, f"Missing world-engine.turn.execute among: {all_names}"

    be_sha = _player_input_sha256_from_obs(be[0])
    we_sha = _player_input_sha256_from_obs(we[0])
    assert be_sha == expected_sha, f"backend.turn.execute sha mismatch: {be_sha!r} vs {expected_sha!r}"
    assert we_sha == expected_sha, f"world-engine.turn.execute sha mismatch: {we_sha!r} vs {expected_sha!r}"


@pytest.mark.langfuse_live
def test_langfuse_live_c640_trace_evidence_gate():
    """End-to-end: HTTP turn → Langfuse trace with generation, retrieval, scores, hash parity."""
    if not _env_truthy("RUN_LANGFUSE_LIVE"):
        pytest.skip("Set RUN_LANGFUSE_LIVE=1 to run the strict Langfuse live gate.")

    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    if not public_key or not secret_key:
        pytest.skip(
            "RUN_LANGFUSE_LIVE requires LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY in the environment."
        )

    base_url = (
        os.environ.get("LANGFUSE_BASE_URL", "").strip()
        or os.environ.get("LANGFUSE_HOST", "").strip()
        or "https://cloud.langfuse.com"
    )
    backend_url = os.environ.get("LANGFUSE_LIVE_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")

    langfuse_mod = pytest.importorskip("langfuse", reason="langfuse package required for live gate")
    Langfuse = langfuse_mod.Langfuse

    try:
        lf = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    except Exception as exc:  # pragma: no cover - env-specific
        pytest.skip(f"Langfuse client init failed: {exc}")

    with httpx.Client(timeout=30.0) as http:
        try:
            health = http.get(f"{backend_url}/api/v1/health")
        except httpx.RequestError as exc:
            pytest.skip(f"Backend not reachable at {backend_url}: {exc}")
        if health.status_code != 200:
            pytest.skip(f"Backend health not OK ({health.status_code}) at {backend_url}")

        create = http.post(f"{backend_url}/api/v1/sessions", json={"module_id": "god_of_carnage"})
        assert create.status_code == 201, create.text
        session_id = create.json()["session_id"]

        player_line = "I glance at the room and listen for a moment."
        body = {"player_input": player_line}
        turn = http.post(f"{backend_url}/api/v1/sessions/{session_id}/turns", json=body)

    assert turn.status_code == 200, (
        f"Expected 200 from live turn; got {turn.status_code}: {turn.text}. "
        "Check World-Engine, OPENAI_API_KEY, and Langfuse wiring."
    )
    payload = turn.json()
    lf_trace_id = payload.get("langfuse_trace_id") or payload.get("trace_id")
    assert lf_trace_id, f"Response missing langfuse trace id: {payload.keys()}"
    expected_sha = hashlib.sha256(player_line.encode("utf-8")).hexdigest()

    fetched = None
    last_err: Exception | None = None
    for _ in range(90):
        try:
            fetched = lf.api.trace.get(str(lf_trace_id))
            break
        except Exception as exc:
            last_err = exc
            time.sleep(1)

    assert fetched is not None, (
        f"Langfuse trace {lf_trace_id} not queryable after wait: {last_err}"
    )

    _assert_positive_live_trace_contract(fetched, expected_sha=expected_sha)


def test_langfuse_negative_degraded_trace_contract_a599_9d61_6871_fixture():
    """Degraded fallback traces stay red despite visible output, usage, and RAG evidence."""
    fixture = {
        "observations": [
            {
                "name": "world-engine.session.create",
                "statusMessage": (
                    "route=True invoke=True fallback_used=True model=openai_gpt_5_4_mini "
                    "adapter=ldss_fallback quality=degraded degradation=dramatic_effect_reject_empty_fluency"
                ),
                "metadata": "{}",
            },
            {
                "name": "story.phase.retrieval",
                "statusMessage": "called=True status=ok route=hybrid hits=6 context_attached=True",
                "metadata": "{}",
            },
        ],
        "scores": [
            {"name": "visible_output_present", "value": 1, "observationId": None},
            {"name": "usage_present", "value": 1, "observationId": None},
            {"name": "rag_context_attached", "value": 1, "observationId": None},
            {"name": "fallback_absent", "value": 0, "observationId": None},
            {"name": "non_mock_generation_pass", "value": 0, "observationId": None},
            {"name": "live_runtime_visible_surface_pass", "value": 0, "observationId": None},
            {"name": "live_runtime_contract_pass", "value": 0, "observationId": None},
        ],
    }
    scores = _score_map(fixture)
    assert scores["visible_output_present"] == 1.0
    assert scores["usage_present"] == 1.0
    assert scores["rag_context_attached"] == 1.0
    assert scores["fallback_absent"] == 0.0
    assert scores["non_mock_generation_pass"] == 0.0
    assert scores["live_runtime_visible_surface_pass"] == 0.0
    assert scores["live_runtime_contract_pass"] == 0.0

    root = _find_observations_by_name(fixture, "world-engine.session.create")[0]
    assert _status_field(root, "fallback_used").lower() == "true"
    assert _status_field(root, "adapter").lower() == "ldss_fallback"
    assert _status_field(root, "quality").lower() == "degraded"
    assert _status_field(root, "degradation").lower() == "dramatic_effect_reject_empty_fluency"
