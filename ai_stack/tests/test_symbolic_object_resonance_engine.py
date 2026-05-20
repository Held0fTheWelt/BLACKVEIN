from __future__ import annotations

from ai_stack.module_runtime_policy import load_module_runtime_policy
from ai_stack.contracts.symbolic_object_resonance_contracts import (
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_SOURCE_REF_MISMATCH,
    SYMBOLIC_OBJECT_RESONANCE_FAILURE_UNSELECTED_OBJECT,
    SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION,
    SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION,
    normalize_symbolic_object_resonance_policy,
)
from ai_stack.story_runtime.narrative.symbolic_object_resonance_engine import (
    build_symbolic_object_resonance_aspect_record,
    compact_symbolic_object_resonance_context,
    derive_symbolic_object_resonance,
    validate_symbolic_object_resonance_realization,
)


MODULE_ID = "god_of_carnage"


def _policy() -> dict:
    return normalize_symbolic_object_resonance_policy(
        {
            "enabled": True,
            "schema_version": SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION,
            "max_symbols_per_turn": 1,
            "require_structured_events": True,
            "default_commit_impact": "recover",
            "allowed_resonance_roles": [
                "attention_diversion",
                "departure_surface",
                "exposure_surface",
                "hospitality_surface",
                "status_surface",
                "territorial_anchor",
            ],
        }
    )


def _first_symbolic_object(policy: dict) -> tuple[str, str]:
    objects = policy["object_model"]["objects"]
    for object_id, row in objects.items():
        roles = row.get("symbolic_roles") or row.get("risk_tags") or []
        roles = [role for role in roles if role in _policy()["allowed_resonance_roles"]]
        if roles:
            return object_id, roles[0]
    raise AssertionError("fixture policy should expose at least one symbolic object")


def test_symbolic_object_resonance_selects_canonical_object_and_validates_event() -> None:
    module_policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()
    object_id, role = _first_symbolic_object(module_policy)
    policy = _policy()
    result = derive_symbolic_object_resonance(
        environment_state={"salient_object_ids": [object_id]},
        environment_model={"objects": module_policy["object_model"]["objects"]},
        module_runtime_policy={"runtime_governance_policy": {"symbolic_object_resonance": policy}},
    )

    target = result["target"]
    state = result["state"]
    compact = compact_symbolic_object_resonance_context(target)
    source_ref = target["required_source_refs"][0]
    selected_role = target["selected_resonance_roles"][0]
    validation = validate_symbolic_object_resonance_realization(
        symbolic_object_resonance_target=target,
        symbolic_object_resonance_state=state,
        structured_output={
            "symbolic_object_resonance_events": [
                {
                    "object_id": object_id,
                    "symbol_id": target["selected_symbol_ids"][0],
                    "resonance_role": selected_role,
                    "source_refs": [source_ref],
                }
            ]
        },
    )
    aspect = build_symbolic_object_resonance_aspect_record(
        target=target,
        state=state,
        validation=validation,
        policy=policy,
        source="validator",
    )

    assert target["schema_version"] == SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION
    assert target["selected_object_ids"] == [object_id]
    assert target["selected_resonance_roles"] == [selected_role]
    assert selected_role in _policy()["allowed_resonance_roles"]
    assert compact["selected_object_ids"] == [object_id]
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert aspect["status"] == "passed"
    assert aspect["selected"]["selected_object_ids"] == [object_id]


def test_symbolic_object_resonance_rejects_unselected_object_and_source_ref_mismatch() -> None:
    module_policy = load_module_runtime_policy(MODULE_ID, "solo_test").to_dict()
    object_id, role = _first_symbolic_object(module_policy)
    policy = _policy()
    result = derive_symbolic_object_resonance(
        environment_state={"salient_object_ids": [object_id]},
        environment_model={"objects": module_policy["object_model"]["objects"]},
        module_runtime_policy={"runtime_governance_policy": {"symbolic_object_resonance": policy}},
    )

    validation = validate_symbolic_object_resonance_realization(
        symbolic_object_resonance_target=result["target"],
        symbolic_object_resonance_state=result["state"],
        structured_output={
            "symbolic_object_resonance_events": [
                {
                    "object_id": f"{object_id}_unselected",
                    "resonance_role": role,
                    "source_refs": [
                        {
                            "source": "fixture",
                            "field": "not_required",
                            "value": "not_required",
                        }
                    ],
                }
            ]
        },
    )

    assert validation["status"] == "rejected"
    assert validation["contract_pass"] is False
    assert SYMBOLIC_OBJECT_RESONANCE_FAILURE_UNSELECTED_OBJECT in validation["failure_codes"]
    assert SYMBOLIC_OBJECT_RESONANCE_FAILURE_SOURCE_REF_MISMATCH in validation["failure_codes"]


def test_symbolic_object_resonance_policy_disabled_is_not_applicable() -> None:
    policy = normalize_symbolic_object_resonance_policy({"enabled": False})
    result = derive_symbolic_object_resonance(
        environment_state={"salient_object_ids": ["object_alpha"]},
        environment_model={"objects": {"object_alpha": {"symbolic_roles": ["status_surface"]}}},
        module_runtime_policy={"runtime_governance_policy": {"symbolic_object_resonance": policy}},
    )
    validation = validate_symbolic_object_resonance_realization(
        symbolic_object_resonance_target=result["target"],
        symbolic_object_resonance_state=result["state"],
        structured_output={"symbolic_object_resonance_events": []},
    )

    assert result["target"]["policy_enabled"] is False
    assert validation["status"] == "not_applicable"
    assert validation["contract_pass"] is True
