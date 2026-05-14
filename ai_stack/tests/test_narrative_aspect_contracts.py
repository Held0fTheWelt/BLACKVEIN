from __future__ import annotations

from ai_stack.narrative_aspect_contracts import (
    normalize_narrative_aspect_policy,
    select_narrative_aspects,
    validate_narrative_aspects,
)


def _policy() -> dict:
    return {
        "schema_version": "narrative_aspect_policy.v1",
        "aspects": [
            {
                "id": "aspect_alpha",
                "enabled": True,
                "activation": {"state_paths_any": ["signals.alpha"]},
                "commit_impact": "diagnostic",
                "evidence": [
                    {
                        "id": "alpha_state",
                        "kind": "state_path_present",
                        "path": "signals.alpha",
                        "required": True,
                    },
                    {
                        "id": "alpha_visible",
                        "kind": "visible_origin_present",
                        "origin_aspect": "narrative_aspect",
                        "required": True,
                    },
                ],
            },
            {
                "id": "aspect_beta",
                "enabled": False,
                "activation": {"always": True},
                "evidence": [],
            },
        ],
    }


def test_narrative_aspect_policy_is_json_safe_and_module_neutral() -> None:
    policy = normalize_narrative_aspect_policy(_policy())

    assert policy["schema_version"] == "narrative_aspect_policy.v1"
    assert [row["id"] for row in policy["aspects"]] == ["aspect_alpha", "aspect_beta"]
    assert "god_of_carnage" not in str(policy)


def test_narrative_aspect_selection_uses_policy_activation_data() -> None:
    selection = select_narrative_aspects(
        narrative_aspect_policy=_policy(),
        runtime_context={"signals": {"alpha": "active"}},
    )

    assert selection.selected_aspects == ["aspect_alpha"]
    assert selection.candidate_aspects == ["aspect_alpha"]
    assert selection.selection_source == "module_policy"


def test_narrative_aspect_validation_records_visible_evidence() -> None:
    validation = validate_narrative_aspects(
        narrative_aspect_policy=_policy(),
        runtime_context={
            "signals": {"alpha": "active"},
            "visible_blocks": [
                {
                    "id": "block-1",
                    "origin_aspect": "narrative_aspect",
                    "origin_aspect_id": "aspect_alpha",
                }
            ],
        },
    )

    payload = validation.to_dict()
    assert payload["status"] == "passed"
    assert payload["selected_aspects"] == ["aspect_alpha"]
    assert payload["realized_aspects"] == ["aspect_alpha"]
    assert payload["missing_required_evidence"] == []


def test_narrative_aspect_validation_fails_only_by_policy_contract() -> None:
    validation = validate_narrative_aspects(
        narrative_aspect_policy=_policy(),
        runtime_context={"signals": {"alpha": "active"}, "visible_blocks": []},
    )

    payload = validation.to_dict()
    assert payload["status"] == "partial"
    assert payload["failure_reason"] == "missing_required_narrative_aspect_evidence"
    assert payload["missing_required_evidence"][0]["kind"] == "visible_origin_present"
