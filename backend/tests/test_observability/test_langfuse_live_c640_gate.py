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


# ADR-0033 §13.8 Stage B: positive live trace must surface a real actor-lane
# verdict. Anything outside this whitelist (missing, "unknown", "rejected",
# empty string) fails the positive gate even if actor_lane_safety_pass==1.
ACTOR_LANE_LIVE_OK: frozenset[str] = frozenset({"approved", "not_applicable"})


def _actor_lane_status_from_validation_span(trace: Any) -> str:
    """Read ``actor_lane=...`` token from ``story.phase.validation`` evidence.

    Falls back to span ``output``/``metadata`` dicts when the token is absent
    from ``statusMessage``. Returns ``""`` if no validation span exists at all
    (which itself fails the positive gate).
    """
    spans = _find_observations_by_name(trace, "story.phase.validation")
    if not spans:
        return ""
    span = spans[0]
    token = _status_field(span, "actor_lane").strip().lower()
    if token:
        return token
    for block_key in ("output", "metadata"):
        block = _coerce_dict(span.get(block_key))
        raw = block.get("actor_lane_validation_status")
        if isinstance(raw, str) and raw.strip():
            return raw.strip().lower()
    return ""


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

    # ADR-0033 §13.8 Stage B: actor-lane whitelist on positive live trace.
    # actor_lane_safety_pass=1 alone is not sufficient; the validation evidence
    # must positively name the lane verdict so silent ``unknown`` cannot pass.
    actor_lane = _actor_lane_status_from_validation_span(fetched)
    assert actor_lane in ACTOR_LANE_LIVE_OK, (
        f"Positive live gate requires actor_lane in {sorted(ACTOR_LANE_LIVE_OK)}; "
        f"got actor_lane={actor_lane!r} from story.phase.validation evidence"
    )


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


def _build_positive_live_trace_fixture(
    *,
    actor_lane_status: str | None,
    expected_sha: str,
) -> dict[str, Any]:
    """Build a positive live trace fixture exercising every existing condition.

    ``actor_lane_status`` controls only the ``actor_lane=...`` token on the
    ``story.phase.validation`` span; pass ``None`` to omit the validation span
    entirely (simulates a regression where validation evidence is missing).
    All other requirements (generation, retrieval, hash parity, scores) are
    already satisfied so the test isolates the actor-lane whitelist enforcement.
    """
    observations: list[dict[str, Any]] = [
        {
            "name": "story.model.generation",
            "model": "openai_gpt_5_4_mini",
            "metadata": {"adapter": "openai"},
            "usage_details": {"input": 100, "output": 50, "total": 150},
        },
        {
            "name": "story.rag.retrieval",
            "metadata": {"retrieval_route": "hybrid"},
        },
        {
            "name": "backend.turn.execute",
            "metadata": {"player_input_sha256": expected_sha},
        },
        {
            "name": "world-engine.turn.execute",
            "metadata": {"player_input_sha256": expected_sha},
        },
    ]
    if actor_lane_status is not None:
        observations.append(
            {
                "name": "story.phase.validation",
                "statusMessage": (
                    f"called=True status=approved actor_lane={actor_lane_status} "
                    "passive_factors=0"
                ),
                "metadata": {},
            }
        )
    scores = [
        {"name": n, "value": 1}
        for n in (
            "rag_context_attached",
            "visible_output_present",
            "live_runtime_visible_surface_pass",
            "live_runtime_contract_pass",
            "fallback_absent",
            "non_mock_generation_pass",
            "usage_present",
        )
    ]
    return {"observations": observations, "scores": scores}


def test_positive_live_trace_contract_passes_with_approved_actor_lane():
    """ADR-0033 §13.8 Stage B: ``approved`` is a healthy positive verdict."""
    expected_sha = "0" * 64
    fixture = _build_positive_live_trace_fixture(
        actor_lane_status="approved", expected_sha=expected_sha
    )
    _assert_positive_live_trace_contract(fixture, expected_sha=expected_sha)


def test_positive_live_trace_contract_passes_with_not_applicable_actor_lane():
    """ADR-0033 §13.8 Stage B: ``not_applicable`` is the explicit no-actor-lane verdict."""
    expected_sha = "0" * 64
    fixture = _build_positive_live_trace_fixture(
        actor_lane_status="not_applicable", expected_sha=expected_sha
    )
    _assert_positive_live_trace_contract(fixture, expected_sha=expected_sha)


def test_positive_live_trace_contract_rejects_unknown_actor_lane():
    """ADR-0033 §13.8 Stage B: ``unknown`` must fail the positive live gate.

    Even when ``actor_lane_safety_pass`` would still treat ``None`` as silent
    pass on the producer side, the trace contract surfaces the omission.
    """
    expected_sha = "0" * 64
    fixture = _build_positive_live_trace_fixture(
        actor_lane_status="unknown", expected_sha=expected_sha
    )
    with pytest.raises(AssertionError, match="actor_lane"):
        _assert_positive_live_trace_contract(fixture, expected_sha=expected_sha)


def test_positive_live_trace_contract_rejects_missing_validation_span():
    """ADR-0033 §13.8 Stage B: no validation span at all also fails the gate."""
    expected_sha = "0" * 64
    fixture = _build_positive_live_trace_fixture(
        actor_lane_status=None, expected_sha=expected_sha
    )
    with pytest.raises(AssertionError, match="actor_lane"):
        _assert_positive_live_trace_contract(fixture, expected_sha=expected_sha)


def test_positive_live_trace_contract_rejects_rejected_actor_lane():
    """ADR-0033 §13.8 Stage B: ``rejected`` must fail (live path = no rejections)."""
    expected_sha = "0" * 64
    fixture = _build_positive_live_trace_fixture(
        actor_lane_status="rejected", expected_sha=expected_sha
    )
    with pytest.raises(AssertionError, match="actor_lane"):
        _assert_positive_live_trace_contract(fixture, expected_sha=expected_sha)


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
