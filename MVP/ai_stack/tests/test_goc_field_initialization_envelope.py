"""Canonical goc_uninitialized_field_envelope_v1 shape (roadmap G3)."""

from __future__ import annotations

import pytest

from ai_stack.goc_field_initialization_envelope import (
    ALLOWED_SETTER_SURFACES,
    GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID,
    assert_goc_uninitialized_field_envelope,
    goc_uninitialized_field_envelope,
    is_goc_uninitialized_field_envelope,
)

_ENVELOPE_KEYS = frozenset(
    {
        "envelope_schema_id",
        "initialization_state",
        "initialization_issue_kind",
        "setter_surface",
        "expected_source",
    }
)


def test_builder_produces_exact_five_key_shape() -> None:
    env = goc_uninitialized_field_envelope(
        setter_surface="runtime_host_session",
        expected_source="RuntimeTurnGraphExecutor.run",
    )
    assert set(env.keys()) == _ENVELOPE_KEYS
    assert env["envelope_schema_id"] == GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID
    assert env["initialization_state"] == "uninitialized"
    assert env["initialization_issue_kind"] == "pending_initialization"
    assert env["setter_surface"] == "runtime_host_session"
    assert env["expected_source"] == "RuntimeTurnGraphExecutor.run"


def test_rejects_invalid_setter_surface() -> None:
    with pytest.raises(ValueError):
        goc_uninitialized_field_envelope(setter_surface="custom_team_surface", expected_source="x")


def test_rejects_empty_expected_source() -> None:
    with pytest.raises(ValueError):
        goc_uninitialized_field_envelope(setter_surface="runtime_host_session", expected_source="  ")


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"envelope_schema_id": GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID},
        {
            "envelope_schema_id": GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID,
            "initialization_state": "uninitialized",
            "initialization_issue_kind": "pending_initialization",
            "setter_surface": "runtime_host_session",
            "expected_source": "ok",
            "extra_key": True,
        },
        {
            "envelope_schema_id": "wrong_schema",
            "initialization_state": "uninitialized",
            "initialization_issue_kind": "pending_initialization",
            "setter_surface": "runtime_host_session",
            "expected_source": "ok",
        },
        {
            "envelope_schema_id": GOC_UNINITIALIZED_FIELD_ENVELOPE_SCHEMA_ID,
            "initialization_state": "unknown",
            "initialization_issue_kind": "pending_initialization",
            "setter_surface": "runtime_host_session",
            "expected_source": "ok",
        },
    ],
)
def test_is_goc_uninitialized_field_envelope_rejects_ad_hoc_shapes(bad: dict) -> None:
    assert is_goc_uninitialized_field_envelope(bad) is False
    with pytest.raises(AssertionError):
        assert_goc_uninitialized_field_envelope(bad)


def test_all_allowed_setter_surfaces_build_valid_envelopes() -> None:
    for s in sorted(ALLOWED_SETTER_SURFACES):
        env = goc_uninitialized_field_envelope(setter_surface=s, expected_source=f"source_for_{s}")
        assert is_goc_uninitialized_field_envelope(env)
