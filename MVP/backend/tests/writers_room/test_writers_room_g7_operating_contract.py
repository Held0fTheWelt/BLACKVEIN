"""Gate G7: canonical artifact taxonomy, §7.3 metadata, terminal HITL exclusivity."""

from __future__ import annotations

import pytest

from app.contracts.writers_room_artifact_class import (
    WRITERS_ROOM_OPERATING_METADATA_KEYS,
    WritersRoomArtifactClass,
    normalize_writers_room_artifact_class,
)

_ALLOWED = {c.value for c in WritersRoomArtifactClass}


def _assert_operating_metadata(obj: dict, *, path: str) -> None:
    missing = WRITERS_ROOM_OPERATING_METADATA_KEYS - set(obj.keys())
    assert not missing, f"missing §7.3 keys at {path}: {sorted(missing)}"


def test_normalize_writers_room_artifact_class_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unknown"):
        normalize_writers_room_artifact_class("not_a_class")


def test_normalize_writers_room_artifact_class_accepts_enum_values() -> None:
    assert normalize_writers_room_artifact_class("analysis_artifact") == WritersRoomArtifactClass.analysis_artifact


def test_governance_outcome_absent_until_terminal_decision(client, auth_headers) -> None:
    r = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "g7 absence probe"},
    )
    assert r.status_code == 200
    payload = r.get_json()
    assert "governance_outcome_artifact" not in payload
    for ra in payload.get("recommendation_artifacts") or []:
        _assert_operating_metadata(ra, path="recommendation_artifacts[]")
        assert ra.get("artifact_class") == "analysis_artifact"
    pp = payload.get("proposal_package") or {}
    _assert_operating_metadata(pp, path="proposal_package")


def test_terminal_accept_exclusive_governance_outcome(client, auth_headers) -> None:
    c = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "g7 accept"},
    )
    review_id = c.get_json()["review_id"]
    d = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "accept", "note": "ok"},
    )
    assert d.status_code == 200
    body = d.get_json()
    assert "governance_outcome_artifact" in body
    goa = body["governance_outcome_artifact"]
    assert isinstance(goa, dict)
    assert goa.get("artifact_class") == "approved_authored_artifact"
    assert goa.get("artifact_class") != "rejected_artifact"
    _assert_operating_metadata(goa, path="governance_outcome_artifact")
    assert goa.get("approval_state") == "accepted"


def test_terminal_reject_exclusive_governance_outcome(client, auth_headers) -> None:
    c = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "g7 reject"},
    )
    review_id = c.get_json()["review_id"]
    d = client.post(
        f"/api/v1/writers-room/reviews/{review_id}/decision",
        headers=auth_headers,
        json={"decision": "reject", "note": "no"},
    )
    assert d.status_code == 200
    body = d.get_json()
    goa = body.get("governance_outcome_artifact") or {}
    assert goa.get("artifact_class") == "rejected_artifact"
    assert goa.get("artifact_class") != "approved_authored_artifact"
    assert goa.get("approval_state") == "rejected"


def test_manifest_lists_only_roadmap_artifact_classes(client, auth_headers) -> None:
    r = client.post(
        "/api/v1/writers-room/reviews",
        headers=auth_headers,
        json={"module_id": "god_of_carnage", "focus": "g7 manifest"},
    )
    manifest = (r.get_json() or {}).get("writers_room_artifact_manifest") or []
    assert manifest
    for row in manifest:
        assert row.get("artifact_class") in _ALLOWED
