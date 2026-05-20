"""ADR-0041 authority bridge: explicit mapping between ``run_validation_seam`` and local validators.

This module can emit non-mutating scoped authority decisions and readiness policy
artifacts (preview, enforcement, aggregation). It does **not** change
``validation_outcome``, commit gates, prompts, or story generation.
"""

from __future__ import annotations

from typing import Any

from ai_stack.capabilities.capability_validator_registry import (
    KNOWN_TURN_CLASSES,
    TURN_CLASS_ENFORCED_VALIDATORS,
    TURN_CLASS_OPENING_SCENE,
    normalize_turn_class_key,
)

from ai_stack.goc_seam_mirror_validator_adapters import (
    ACTOR_LANE_FORBIDDEN_CONTRACT,
    DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
    HARD_FORBIDDEN_RUNTIME_CONTRACT,
    MODEL_GENERATION_PRECHECK_CONTRACT,
    NPC_TRANSCRIPT_SHELL_CONTRACT,
    OPENING_EVENT_COVERAGE_CONTRACT,
    PROPOSED_EFFECTS_SHAPE_CONTRACT,
)

VALIDATION_AUTHORITY_BRIDGE_SCHEMA_VERSION = "validation_authority_bridge.v5"
VALIDATION_CO_AUTHORITY_DECISION_SCHEMA_VERSION = "validation_co_authority_decision.v1"
READINESS_CO_AUTHORITY_PREVIEW_SCHEMA_VERSION = "readiness_co_authority_preview.v1"

# Drift labels align with ``runtime_aspect_ledger.classify_adr0041_validation_authority_drift`` (no cyclic import).
_DRIFT_ALIGNED = "aligned"

AUTHORITY_CLASSIFICATION_MIRROR = "adr0041_deterministic_mirror"
AUTHORITY_CLASSIFICATION_SEAM_OWNED = "seam_owned"
AUTHORITY_CLASSIFICATION_CANDIDATE = "adr0041_candidate"
AUTHORITY_CLASSIFICATION_REQUIRES_NEW = "requires_new_validator"
AUTHORITY_CLASSIFICATION_NOT_SAFE_YET = "not_safe_for_adr0041_yet"

# Machine-readable seam area ↔ ADR-0041 relationship (gates / contract consumers).
SEAM_AREA_REL_MIRRORED_FULL = "mirrored_by_adr0041"
SEAM_AREA_REL_MIRRORED_PARTIAL = "partially_mirrored_by_adr0041"
SEAM_AREA_REL_SEAM_OWNED = "seam_owned"
SEAM_AREA_REL_MIGRATION_CANDIDATE = "migration_candidate"
SEAM_AREA_REL_NOT_SAFE = "not_safe_to_migrate"

HANDOFF_RECOMMENDED_SEAM_CANONICAL = "seam_canonical"
HANDOFF_RECOMMENDED_ADR0041_CANDIDATE = "adr0041_candidate"
HANDOFF_RECOMMENDED_SHADOW_READY = "adr0041_ready_for_shadow_authority"
HANDOFF_RECOMMENDED_BLOCKED = "blocked"

CO_AUTHORITY_STAGE_SCOPED = "scoped_co_authority"
CO_AUTHORITY_DECISION_READY = "validation_co_authority_ready"
CO_AUTHORITY_LEGACY_SEAM = "run_validation_seam"
CO_AUTHORITY_COMMITMENT_SEAM = "ai_stack.goc_turn_seams.run_validation_seam"

READINESS_POLICY_SHADOW_ONLY = "shadow_only"
READINESS_POLICY_PREVIEW_CANDIDATE = "readiness_preview_candidate"
READINESS_POLICY_PREVIEW_ALLOW = "readiness_preview_allow"
READINESS_POLICY_PREVIEW_BLOCK = "readiness_preview_block"
READINESS_POLICY_NOT_ELIGIBLE = "not_eligible"

READINESS_ENFORCEMENT_SCHEMA_VERSION = "readiness_co_authority_enforcement.v1"
READINESS_AGGREGATION_SCHEMA_VERSION = "readiness_aggregation_decision.v1"

# Declarative map: canonical seam concern IDs (see ``ai_stack.goc_turn_seams.run_validation_seam``)
# Seam concerns that must be explicitly delegated before ADR-0041 could share gate authority.
CRITICAL_SEAM_CONCERN_IDS: frozenset[str] = frozenset(
    {
        "actor_lane_forbidden_output",
        "dramatic_effect_gate",
        "hard_forbidden_runtime",
        "opening_event_coverage",
    }
)

SEAM_CONCERN_SPECS: dict[str, dict[str, Any]] = {
    "actor_lane_forbidden_output": {
        "label": "Human/forbidden actor may not be spoken for by AI in structured output",
        "seam_anchor": "goc_turn_seams.run_validation_seam:actor_lane_context + _check_human_actor_violations",
        "related_adr0041_validators": (ACTOR_LANE_FORBIDDEN_CONTRACT,),
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": (
            "Local ``actor_lane_forbidden_contract`` calls the same ``_check_human_actor_violations`` "
            "helper as the seam (non-commit mirror)."
        ),
    },
    "authoritative_action_resolution_surface": {
        "label": "Waive dramatic gate when authoritative action-resolution surface is active",
        "seam_anchor": "goc_turn_seams.run_validation_seam:authoritative_action_resolution",
        "related_adr0041_validators": ("action_resolution_contract",),
        "authority_classification": AUTHORITY_CLASSIFICATION_SEAM_OWNED,
        "coverage_note": (
            "Early seam waiver branch; ``action_resolution_contract`` overlaps affordance surfaces "
            "but does not implement the waiver precondition."
        ),
    },
    "npc_lane_transcript_cap": {
        "label": "NPC spoken/action lane blob length cap (transcript shell)",
        "seam_anchor": "goc_turn_seams._check_npc_spoken_action_lane_blob_cap",
        "related_adr0041_validators": (NPC_TRANSCRIPT_SHELL_CONTRACT,),
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": (
            "Local ``npc_transcript_shell_contract`` uses the same transcript-shell cap helper."
        ),
    },
    "intent_surface_npc_narrated_player_action": {
        "label": "NPC narrated player action violation diagnostic",
        "seam_anchor": "goc_turn_seams.run_validation_seam:_detect_npc_narrated_player_action_violation",
        "related_adr0041_validators": ("player_intent_contract", "voice_consistency_contract"),
        "authority_classification": AUTHORITY_CLASSIFICATION_CANDIDATE,
        "coverage_note": (
            "Seam diagnostic is authoritative; contracts provide related aspect checks only."
        ),
    },
    "hard_forbidden_runtime": {
        "label": "Hard forbidden / opening knowledge runtime text+structured gates",
        "seam_anchor": "goc_turn_seams.run_validation_seam:detect_hard_forbidden_runtime",
        "related_adr0041_validators": (
            HARD_FORBIDDEN_RUNTIME_CONTRACT,
            "environment_state_contract",
            "information_disclosure_contract",
        ),
        # Partial-transfer scope: deterministic mirror calling the same seam helper; supplemental
        # contracts remain narrative/aspect slices, not required for scoped readiness.
        "partial_transfer_required_validators_by_turn_class": {
            "opening_scene": (HARD_FORBIDDEN_RUNTIME_CONTRACT,),
            "normal_player_turn": (HARD_FORBIDDEN_RUNTIME_CONTRACT,),
            "npc_conflict_turn": (HARD_FORBIDDEN_RUNTIME_CONTRACT,),
        },
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": (
            "``hard_forbidden_runtime_contract`` calls ``detect_hard_forbidden_runtime``; "
            "environment/disclosure contracts remain supplemental aspect slices."
        ),
    },
    "proposed_effects_shape": {
        "label": "Proposed state effects must be well-formed dicts with description/effect_type",
        "seam_anchor": "goc_turn_seams.run_validation_seam:proposed_state_effects loop",
        "related_adr0041_validators": (PROPOSED_EFFECTS_SHAPE_CONTRACT,),
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": "Local shape check mirrors the seam loop logic.",
    },
    "opening_event_coverage": {
        "label": "Opening-event coverage / first playable (opening turn_input_class)",
        "seam_anchor": "goc_turn_seams.run_validation_seam:evaluate_opening_event_coverage",
        "related_adr0041_validators": (
            OPENING_EVENT_COVERAGE_CONTRACT,
            "narrator_authority_contract",
            "environment_state_contract",
        ),
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": (
            "``opening_event_coverage_contract`` calls ``evaluate_opening_event_coverage``; "
            "narrator/environment contracts remain narrative-adjacent supplements."
        ),
        "partial_transfer_required_validators_by_turn_class": {
            "opening_scene": (OPENING_EVENT_COVERAGE_CONTRACT,),
        },
    },
    "dramatic_effect_gate": {
        "label": "Dramatic effect evaluation gate (fluency, plausibility, scene function, continuity)",
        "seam_anchor": "goc_turn_seams.run_validation_seam:evaluate_dramatic_effect_gate",
        "related_adr0041_validators": (
            DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
            "scene_energy_contract",
            "action_resolution_contract",
            "player_intent_contract",
        ),
        # Narrow enforced overlap per turn class: opening is narrator-led (no player-intent slice).
        # NPC conflict uses agency/voice/energy aspects adjacent to the gate; mirror still uses defaults
        # unless dispatch supplies full dramatic packet fields.
        "partial_transfer_required_validators_by_turn_class": {
            "opening_scene": (DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT, "scene_energy_contract"),
            "normal_player_turn": (
                DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
                "scene_energy_contract",
                "action_resolution_contract",
                "player_intent_contract",
            ),
            "npc_conflict_turn": (
                DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT,
                "scene_energy_contract",
                "voice_consistency_contract",
                "npc_agency_contract",
            ),
        },
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": (
            "``dramatic_effect_gate_mirror_contract`` best-effort mirrors ``evaluate_dramatic_effect_gate``; "
            "may default evaluation context fields when graph dispatch omits seam fields; "
            "aspect contracts are partial slices."
        ),
    },
    "model_generation_success": {
        "label": "Generation.success / model error short-circuit",
        "seam_anchor": "goc_turn_seams.run_validation_seam:generation success/error",
        "related_adr0041_validators": (MODEL_GENERATION_PRECHECK_CONTRACT,),
        "authority_classification": AUTHORITY_CLASSIFICATION_MIRROR,
        "coverage_note": "``model_generation_precheck_contract`` mirrors the seam pre-check.",
    },
}

_RECOMMENDED_AUTHORITY_SEAM_CANONICAL = "seam_canonical"
_AUTHORITY_NOTES_DEFAULT = (
    "Commitment authority remains ``run_validation_seam``; ADR-0041 bridge is local-only observation."
)


def _turn_class_enforced_set(turn_class: str) -> frozenset[str]:
    key = normalize_turn_class_key(turn_class)
    return frozenset(TURN_CLASS_ENFORCED_VALIDATORS[key])


def _concern_coverage_for_turn_class(turn_class: str) -> dict[str, Any]:
    enforced = _turn_class_enforced_set(turn_class)
    covered: list[str] = []
    partial: list[str] = []
    uncovered: list[str] = []
    for cid, spec in SEAM_CONCERN_SPECS.items():
        related = frozenset(str(v) for v in (spec.get("related_adr0041_validators") or ()))
        if not related:
            uncovered.append(cid)
            continue
        overlap = related & enforced
        if not overlap:
            uncovered.append(cid)
        elif overlap == related:
            covered.append(cid)
        else:
            partial.append(cid)
            covered.append(cid)
    return {
        "enforced_validator_ids": sorted(enforced),
        "covered_seam_concern_ids": covered,
        "partially_covered_seam_concern_ids": partial,
        "uncovered_seam_concern_ids": uncovered,
    }


def _adr0041_aggregate_status(validator_dispatch_report: dict[str, Any]) -> dict[str, Any]:
    mode = str(validator_dispatch_report.get("mode") or "").strip().lower()
    if mode != "plan_enforced":
        return {
            "engagement": "not_engaged",
            "executed_validator_ids": [],
            "unavailable_validator_ids": [],
            "validators_would_run": list(validator_dispatch_report.get("validators_would_run") or []),
            "local_evidence": "absent",
        }
    executed = [str(x) for x in (validator_dispatch_report.get("actually_executed") or []) if str(x)]
    unavailable = [str(x) for x in (validator_dispatch_report.get("validators_unavailable") or []) if str(x)]
    would = [str(x) for x in (validator_dispatch_report.get("validators_would_run") or []) if str(x)]

    entries = validator_dispatch_report.get("entries") or []
    evidences: list[dict[str, Any]] = []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict):
            evidences.append(ev)

    if unavailable and not executed:
        local_evidence = "blocked_unavailable"
    elif not evidences:
        local_evidence = "no_rows"
    elif all(bool(e.get("passed")) for e in evidences):
        local_evidence = "all_pass"
    else:
        local_evidence = "some_failed"

    return {
        "engagement": "plan_enforced",
        "executed_validator_ids": executed,
        "unavailable_validator_ids": unavailable,
        "validators_would_run": would,
        "local_evidence": local_evidence,
    }


def _migration_readiness(
    *,
    drift_classification: str,
    adr0041: dict[str, Any],
    unavailable_count: int,
) -> str:
    if adr0041.get("engagement") != "plan_enforced":
        return "not_engaged"
    if adr0041.get("local_evidence") == "blocked_unavailable":
        return "blocked_validator_unavailable"
    if unavailable_count > 0:
        return "partial_unavailable_validators"
    if drift_classification in ("conflicting_result",):
        return "drift_conflicting_requires_review"
    if drift_classification in ("adr0041_stricter", "seam_stricter"):
        return "drift_asymmetric_requires_review"
    if drift_classification == "missing_context":
        return "blocked_missing_runtime_context"
    return "observation_ready"


def _collect_blockers(
    *,
    turn_class: str,
    preview: dict[str, Any],
    adr0041: dict[str, Any],
    drift_classification: str,
) -> list[str]:
    blockers: list[str] = []
    cov = _concern_coverage_for_turn_class(turn_class)
    tc = normalize_turn_class_key(turn_class)
    for cid in cov["uncovered_seam_concern_ids"]:
        if tc not in _concern_turn_class_scope(cid):
            continue
        spec = SEAM_CONCERN_SPECS.get(cid) or {}
        if str(spec.get("authority_classification") or "") == AUTHORITY_CLASSIFICATION_SEAM_OWNED:
            continue
        blockers.append(f"seam_concern_no_adr0041_overlap:{cid}")
    for vid in adr0041.get("unavailable_validator_ids") or []:
        blockers.append(f"adr0041_validator_unavailable:{vid}")
    if drift_classification == "missing_context":
        blockers.append("drift:missing_context_all_planned_unavailable")
    elif drift_classification == "unavailable_validator":
        blockers.append("drift:unavailable_validator_partial")
    elif drift_classification == "conflicting_result":
        blockers.append("drift:conflicting_result")
    elif drift_classification == "adr0041_stricter":
        blockers.append("drift:adr0041_stricter_vs_seam")
    elif drift_classification == "seam_stricter":
        blockers.append("drift:seam_stricter_vs_adr0041")
    # De-dupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out


_PARTIAL_TRANSFER_DISCLAIMERS: tuple[str, ...] = (
    "Partial-transfer readiness is diagnostic-only: ``run_validation_seam`` remains canonical for "
    "``validation_outcome`` and commit/readiness.",
    "``actor_lane_forbidden_output``, ``hard_forbidden_runtime``, ``opening_event_coverage``, and "
    "``dramatic_effect_gate`` are the only scoped co-authority concerns considered in this phase; "
    "opening coverage is scoped to ``opening_scene`` only.",
    "``dramatic_effect_gate`` mirror may still rely on defaulted evaluation fields unless the graph "
    "dispatch supplies the same structured context as the commitment seam; evidence flag "
    "``dramatic_effect_mirror_fidelity=partial_defaults`` blocks ``partial_transfer_ready`` even on pass.",
    "``hard_forbidden_runtime`` partial-transfer scope is the deterministic ``detect_hard_forbidden_runtime`` "
    "mirror only; supplemental environment/disclosure contracts are not required for scoped readiness.",
)


def _concern_turn_class_scope(concern_id: str) -> tuple[str, ...]:
    if concern_id == "opening_event_coverage":
        return (normalize_turn_class_key(TURN_CLASS_OPENING_SCENE),)
    return tuple(normalize_turn_class_key(k) for k in KNOWN_TURN_CLASSES)


def _critical_concerns_for_turn_class(turn_class_key: str) -> frozenset[str]:
    tc_key = normalize_turn_class_key(turn_class_key)
    return frozenset(
        cid for cid in CRITICAL_SEAM_CONCERN_IDS if tc_key in _concern_turn_class_scope(cid)
    )


def _partial_transfer_required_for_concern(concern_id: str, turn_class_key: str) -> frozenset[str]:
    spec = SEAM_CONCERN_SPECS.get(concern_id) or {}
    by_tc = spec.get("partial_transfer_required_validators_by_turn_class")
    if isinstance(by_tc, dict) and turn_class_key in by_tc:
        return frozenset(str(x) for x in by_tc[turn_class_key])
    return frozenset(str(x) for x in (spec.get("related_adr0041_validators") or ()))


def _registry_satisfies_partial_transfer(turn_class_key: str) -> tuple[bool, list[str]]:
    enforced = _turn_class_enforced_set(turn_class_key)
    blockers: list[str] = []
    for cid in _critical_concerns_for_turn_class(turn_class_key):
        req = _partial_transfer_required_for_concern(cid, turn_class_key)
        missing = sorted(req - enforced)
        if missing:
            blockers.append(
                f"partial_transfer:registry_gap:{cid}:missing_enforced:{','.join(missing)}"
            )
    return not blockers, blockers


def _partial_transfer_union_required(turn_class_key: str) -> frozenset[str]:
    out: set[str] = set()
    for cid in _critical_concerns_for_turn_class(turn_class_key):
        out.update(_partial_transfer_required_for_concern(cid, turn_class_key))
    return frozenset(out)


def _execution_satisfies_partial_transfer(
    *,
    turn_class_key: str,
    selected_turn_class: str,
    validator_dispatch_report: dict[str, Any],
) -> tuple[bool, list[str]]:
    if normalize_turn_class_key(turn_class_key) != normalize_turn_class_key(selected_turn_class):
        return False, [
            "partial_transfer:execution_not_observed_for_this_snapshot "
            f"(bridge_selected_turn_class={normalize_turn_class_key(selected_turn_class)!r})"
        ]
    adr = _adr0041_aggregate_status(validator_dispatch_report)
    if adr.get("engagement") != "plan_enforced":
        return False, ["partial_transfer:not_plan_enforced"]
    req = _partial_transfer_union_required(turn_class_key)
    executed = frozenset(str(x) for x in (adr.get("executed_validator_ids") or []))
    unavailable = frozenset(str(x) for x in (adr.get("unavailable_validator_ids") or []))
    missing_exec = sorted(req - executed)
    if missing_exec:
        return False, [f"partial_transfer:validators_not_executed:{','.join(missing_exec)}"]
    blocked = sorted(req & unavailable)
    if blocked:
        return False, [f"partial_transfer:validators_unavailable:{','.join(blocked)}"]
    if adr.get("local_evidence") != "all_pass":
        return False, [f"partial_transfer:local_evidence_not_all_pass:{adr.get('local_evidence')}"]

    entries = validator_dispatch_report.get("entries") or []
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        vid = str(ent.get("validator_id") or "")
        if vid not in req:
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict) and ev.get("dramatic_effect_mirror_fidelity") == "partial_defaults":
            return False, ["partial_transfer:dramatic_mirror_fidelity_partial_defaults"]
    return True, []


def _turn_class_migration_snapshot(
    turn_class: str,
    *,
    selected_turn_class: str,
    validator_dispatch_report: dict[str, Any],
) -> dict[str, Any]:
    tc_key = normalize_turn_class_key(turn_class)
    cov = _concern_coverage_for_turn_class(turn_class)
    overlap_count = len(set(cov["covered_seam_concern_ids"]))
    total = len(SEAM_CONCERN_SPECS)
    active_critical = _critical_concerns_for_turn_class(tc_key)
    critical_gaps = [
        c for c in active_critical if c in cov["uncovered_seam_concern_ids"]
    ]
    critical_partial = [
        c for c in active_critical if c in cov["partially_covered_seam_concern_ids"]
    ]
    registry_ok, reg_blockers = _registry_satisfies_partial_transfer(tc_key)
    exec_ok, exec_blockers = _execution_satisfies_partial_transfer(
        turn_class_key=tc_key,
        selected_turn_class=selected_turn_class,
        validator_dispatch_report=validator_dispatch_report,
    )
    partial_transfer_blocked: list[str] = []
    seen_b: set[str] = set()
    for b in (*reg_blockers, *exec_blockers):
        if b not in seen_b:
            seen_b.add(b)
            partial_transfer_blocked.append(b)
    partial_transfer_ready = bool(registry_ok and exec_ok)

    missing: list[str] = []
    if "actor_lane_forbidden_output" in cov["uncovered_seam_concern_ids"]:
        missing.append("Actor-lane concern has no enforced overlap with seam-mirror validator ids.")
    if "dramatic_effect_gate" in cov["uncovered_seam_concern_ids"] or (
        "dramatic_effect_gate" in cov["partially_covered_seam_concern_ids"]
    ):
        missing.append(
            "Catalog coverage: dramatic concern still marked partial or uncovered under broad "
            "related-validator list; see partial_transfer_* fields for narrower bounded scope."
        )
    if "hard_forbidden_runtime" in cov["uncovered_seam_concern_ids"] or (
        "hard_forbidden_runtime" in cov["partially_covered_seam_concern_ids"]
    ):
        missing.append(
            "Catalog coverage: hard-forbidden concern partial under broad related list; "
            "``hard_forbidden_runtime_contract`` alone may still satisfy partial-transfer scope."
        )
    if "npc_lane_transcript_cap" in cov["uncovered_seam_concern_ids"]:
        missing.append("NPC transcript shell concern not covered by enforced validators.")
    if "proposed_effects_shape" in cov["uncovered_seam_concern_ids"]:
        missing.append("Proposed-effect shape concern not covered by enforced validators.")

    concern_scope: dict[str, Any] = {}
    for cid in active_critical:
        concern_scope[cid] = {
            "partial_transfer_required_validators": sorted(_partial_transfer_required_for_concern(cid, tc_key)),
        }

    return {
        "turn_class": tc_key,
        "covered_seam_concern_ids": cov["covered_seam_concern_ids"],
        "uncovered_seam_concern_ids": cov["uncovered_seam_concern_ids"],
        "partially_covered_seam_concern_ids": cov["partially_covered_seam_concern_ids"],
        "critical_seam_concern_gaps": critical_gaps + [f"{c}:partial" for c in critical_partial],
        "complete_enough_for_future_seam_partial_transfer": registry_ok,
        "partial_transfer_scope_registry_satisfied": registry_ok,
        "partial_transfer_ready": partial_transfer_ready,
        "partial_transfer_blocked": partial_transfer_blocked,
        "partial_transfer_disclaimers": list(_PARTIAL_TRANSFER_DISCLAIMERS),
        "partial_transfer_critical_scope": dict(sorted(concern_scope.items())),
        "missing_adapter_or_context_notes": missing,
        "coverage_ratio": {"covered_distinct": overlap_count, "total_seam_concerns": total},
    }


def _seam_area_relationship_for_concern(
    concern_id: str,
    spec: dict[str, Any],
    enforced: frozenset[str],
) -> str:
    ac = str(spec.get("authority_classification") or "")
    if ac == AUTHORITY_CLASSIFICATION_SEAM_OWNED:
        return SEAM_AREA_REL_SEAM_OWNED
    if ac == AUTHORITY_CLASSIFICATION_CANDIDATE:
        return SEAM_AREA_REL_MIGRATION_CANDIDATE
    if ac in (AUTHORITY_CLASSIFICATION_REQUIRES_NEW, AUTHORITY_CLASSIFICATION_NOT_SAFE_YET):
        return SEAM_AREA_REL_NOT_SAFE
    related = frozenset(str(v) for v in (spec.get("related_adr0041_validators") or ()))
    if not related:
        return SEAM_AREA_REL_NOT_SAFE
    overlap = related & enforced
    if not overlap:
        return SEAM_AREA_REL_NOT_SAFE
    if overlap == related:
        return SEAM_AREA_REL_MIRRORED_FULL
    return SEAM_AREA_REL_MIRRORED_PARTIAL


def _coverage_status_for_concern(
    concern_id: str,
    spec: dict[str, Any],
    enforced: frozenset[str],
) -> str:
    ac = str(spec.get("authority_classification") or "")
    if ac == AUTHORITY_CLASSIFICATION_SEAM_OWNED:
        return "seam_owned"
    related = frozenset(str(v) for v in (spec.get("related_adr0041_validators") or ()))
    if not related:
        return "uncovered"
    overlap = related & enforced
    if not overlap:
        return "uncovered"
    if overlap == related:
        return "covered"
    return "partial"


def _concern_bounded_scope_satisfied(
    concern_id: str,
    *,
    turn_class: str,
    validator_dispatch_report: dict[str, Any],
    partial_transfer_ready: bool,
) -> bool:
    tc_key = normalize_turn_class_key(turn_class)
    if concern_id not in CRITICAL_SEAM_CONCERN_IDS:
        return False
    if tc_key not in _concern_turn_class_scope(concern_id):
        return False
    if not partial_transfer_ready:
        return False
    req = _partial_transfer_required_for_concern(concern_id, tc_key)
    entries_list = validator_dispatch_report.get("entries") or []
    by_id: dict[str, dict[str, Any]] = {}
    for ent in entries_list:
        if isinstance(ent, dict) and ent.get("validator_id"):
            by_id[str(ent["validator_id"])] = ent
    for vid in req:
        ent = by_id.get(vid)
        if not ent or not ent.get("actually_executed") or ent.get("unavailable"):
            return False
        ev = ent.get("local_execution_evidence")
        if not isinstance(ev, dict) or not ev.get("passed"):
            return False
        if (
            vid == DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT
            and ev.get("dramatic_effect_mirror_fidelity") == "partial_defaults"
        ):
            return False
    return True


def _authority_transfer_status_for_concern(
    concern_id: str,
    spec: dict[str, Any],
    *,
    turn_class: str,
    relationship: str,
    coverage_status: str,
    partial_transfer_ready: bool,
    validator_dispatch_report: dict[str, Any],
) -> str:
    ac = str(spec.get("authority_classification") or "")
    if ac == AUTHORITY_CLASSIFICATION_SEAM_OWNED:
        return "excluded_seam_owned_branch"
    if ac == AUTHORITY_CLASSIFICATION_CANDIDATE:
        return "migration_adjacent_requires_seam_diagnostic"
    if concern_id in CRITICAL_SEAM_CONCERN_IDS:
        if _concern_bounded_scope_satisfied(
            concern_id,
            turn_class=turn_class,
            validator_dispatch_report=validator_dispatch_report,
            partial_transfer_ready=partial_transfer_ready,
        ):
            return "bounded_partial_transfer_scope_met"
        if partial_transfer_ready:
            return "critical_scope_observed_transfer_bundle_ok_concern_not_focus"
        return "bounded_partial_transfer_scope_not_met"
    if relationship in (SEAM_AREA_REL_MIRRORED_FULL, SEAM_AREA_REL_MIRRORED_PARTIAL):
        return "local_mirror_non_authority"
    if coverage_status == "uncovered":
        return "no_enforced_overlap"
    return "not_eligible_for_authority_transfer"


def build_seam_concern_coverage(
    *,
    selected_turn_class: str,
    validator_dispatch_report: dict[str, Any],
    partial_transfer_ready: bool,
) -> dict[str, Any]:
    """Per seam concern: coverage, validators, scope, transfer status, blockers (JSON-safe)."""
    tc_key = normalize_turn_class_key(selected_turn_class)
    enforced = _turn_class_enforced_set(tc_key)
    out: dict[str, Any] = {}
    for cid, spec in SEAM_CONCERN_SPECS.items():
        scope = _concern_turn_class_scope(cid)
        if tc_key not in scope:
            out[cid] = {
                "coverage_status": "not_applicable_turn_class",
                "validator_ids": sorted(str(v) for v in (spec.get("related_adr0041_validators") or ())),
                "turn_class_scope": list(scope),
                "seam_area_adr0041_relationship": SEAM_AREA_REL_NOT_SAFE,
                "authority_transfer_status": "not_applicable_turn_class",
                "blockers": [f"concern_not_in_scope_for_turn_class:{tc_key}"],
            }
            continue
        rel = _seam_area_relationship_for_concern(cid, spec, enforced)
        cov = _coverage_status_for_concern(cid, spec, enforced)
        transfer = _authority_transfer_status_for_concern(
            cid,
            spec,
            turn_class=tc_key,
            relationship=rel,
            coverage_status=cov,
            partial_transfer_ready=partial_transfer_ready,
            validator_dispatch_report=validator_dispatch_report,
        )
        blockers: list[str] = []
        if cov == "uncovered":
            blockers.append(f"no_adr0041_enforced_overlap:{cid}")
        if transfer == "bounded_partial_transfer_scope_not_met" and cid in CRITICAL_SEAM_CONCERN_IDS:
            blockers.append(f"bounded_partial_transfer_not_met:{cid}")
        out[cid] = {
            "coverage_status": cov,
            "validator_ids": sorted(str(v) for v in (spec.get("related_adr0041_validators") or ())),
            "seam_area_adr0041_relationship": rel,
            "turn_class_scope": list(scope),
            "authority_transfer_status": transfer,
            "blockers": blockers,
        }
    return out


def build_authority_handoff_candidate(
    *,
    selected_turn_class: str,
    validator_dispatch_report: dict[str, Any],
    migration_readiness: str,
    drift_classification: str,
    partial_transfer_ready: bool,
    partial_transfer_blocked: list[str],
    bridge_blockers: list[str],
) -> dict[str, Any]:
    """Structured next-step signal: never commit/readiness authority (local-only proof)."""
    adr = _adr0041_aggregate_status(validator_dispatch_report)
    handoff_blockers: list[str] = []
    scope: list[str] = []
    candidate = False
    recommended = HANDOFF_RECOMMENDED_SEAM_CANONICAL
    reason: str
    safe_next_step: str
    active_scope = sorted(_critical_concerns_for_turn_class(selected_turn_class))

    if adr.get("engagement") != "plan_enforced":
        reason = "ADR-0041 plan-enforced dispatch not engaged; ledger remains dry-run observation."
        safe_next_step = "Set ADR0041_VALIDATOR_DISPATCH_MODE=plan_enforced and attach graph dispatch context when evaluating shadow routing only."
        return {
            "candidate": False,
            "scope": scope,
            "recommended_authority": HANDOFF_RECOMMENDED_SEAM_CANONICAL,
            "reason": reason,
            "blockers": list(bridge_blockers),
            "safe_next_step": safe_next_step,
            "affects_commit": False,
            "affects_readiness": False,
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
        }

    unavailable = [str(x) for x in (adr.get("unavailable_validator_ids") or []) if str(x)]
    if unavailable:
        handoff_blockers.append(f"validators_unavailable:{','.join(sorted(unavailable))}")
    if partial_transfer_blocked:
        handoff_blockers.extend(str(b) for b in partial_transfer_blocked if str(b))
    drift = str(drift_classification or "").strip()
    if drift and drift != _DRIFT_ALIGNED:
        handoff_blockers.append(f"drift_classification:{drift}")
    if migration_readiness != "observation_ready":
        handoff_blockers.append(f"migration_readiness:{migration_readiness}")

    if (
        partial_transfer_ready
        and migration_readiness == "observation_ready"
        and drift == _DRIFT_ALIGNED
        and not unavailable
    ):
        candidate = True
        recommended = HANDOFF_RECOMMENDED_SHADOW_READY
        scope = active_scope
        reason = (
            "Bounded partial-transfer scope for this turn class passed locally with drift aligned "
            "vs seam echo; shadow governance candidate only."
        )
        safe_next_step = (
            "Governance-only: review mirror fidelity + seam parity before any promotion; "
            "keep run_validation_seam canonical for validation_outcome."
        )
    elif adr.get("local_evidence") == "all_pass" and migration_readiness == "observation_ready" and drift == _DRIFT_ALIGNED:
        recommended = HANDOFF_RECOMMENDED_ADR0041_CANDIDATE
        reason = (
            "Local validators all-pass with aligned drift, but bounded partial-transfer scope is not satisfied "
            "for authority handoff."
        )
        safe_next_step = "Close partial_transfer_blocked items (missing context, mirror fidelity, or registry gaps)."
    elif migration_readiness.startswith("drift_") or drift in (
        "adr0041_stricter",
        "seam_stricter",
        "conflicting_result",
    ):
        recommended = HANDOFF_RECOMMENDED_BLOCKED
        reason = "Drift or conflicting seam vs ADR-0041 evidence blocks shadow authority candidate."
        safe_next_step = "Reconcile seam outcome vs local validator evidence under governance before revisiting handoff."
        handoff_blockers.extend([b for b in bridge_blockers if str(b).startswith("drift:")])
    elif migration_readiness in (
        "blocked_validator_unavailable",
        "partial_unavailable_validators",
        "blocked_missing_runtime_context",
    ):
        recommended = HANDOFF_RECOMMENDED_BLOCKED
        reason = "Missing dispatch context or unavailable validators; ADR-0041 cannot honest-complete local scope."
        safe_next_step = "Provide required dispatch_context fields or register validators; do not treat unavailable as pass."
    elif adr.get("local_evidence") == "some_failed":
        recommended = HANDOFF_RECOMMENDED_BLOCKED
        reason = "Local validator failures present; no authority handoff candidate."
        safe_next_step = "Fix failing deterministic validators or accept seam rejection path; handoff remains blocked."
    else:
        reason = (
            f"Observation-only bundle for turn class {normalize_turn_class_key(selected_turn_class)}; "
            "seam_canonical remains the commitment seam."
        )
        safe_next_step = "Continue shadow observation under plan_enforced; no handoff until partial_transfer_ready."

    seen_h: set[str] = set()
    handoff_blockers_dedup: list[str] = []
    for b in handoff_blockers + list(bridge_blockers):
        t = str(b).strip()
        if t and t not in seen_h:
            seen_h.add(t)
            handoff_blockers_dedup.append(t)

    if candidate and handoff_blockers_dedup:
        candidate = False
        recommended = HANDOFF_RECOMMENDED_BLOCKED
        reason = "Inconsistent state: would-be candidate blocked by residual handoff blockers."

    return {
        "candidate": candidate,
        "scope": sorted(scope),
        "recommended_authority": recommended,
        "reason": reason,
        "blockers": handoff_blockers_dedup,
        "safe_next_step": safe_next_step,
        "affects_commit": False,
        "affects_readiness": False,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
    }


def _dramatic_mirror_fidelity(validator_dispatch_report: dict[str, Any]) -> str | None:
    for ent in validator_dispatch_report.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        if ent.get("validator_id") != DRAMATIC_EFFECT_GATE_MIRROR_CONTRACT:
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict):
            raw = ev.get("dramatic_effect_mirror_fidelity")
            return str(raw) if raw is not None else None
    return None


def build_validation_co_authority_decision(
    *,
    validation_authority_bridge: dict[str, Any],
    validator_dispatch_report: dict[str, Any],
    selected_turn_class: str,
    feature_flag_name: str,
    feature_flag_enabled: bool,
) -> dict[str, Any] | None:
    """Return a non-mutating scoped co-authority decision when the bounded scope is ready."""
    if not feature_flag_enabled:
        return None
    bridge = validation_authority_bridge if isinstance(validation_authority_bridge, dict) else {}
    raw_turn_class = str(selected_turn_class or bridge.get("selected_turn_class") or "").strip()
    if not raw_turn_class:
        return None
    tc_key = normalize_turn_class_key(raw_turn_class)
    per_tc = bridge.get("per_turn_class") if isinstance(bridge.get("per_turn_class"), dict) else {}
    snap = per_tc.get(tc_key) if isinstance(per_tc.get(tc_key), dict) else {}
    handoff = (
        bridge.get("authority_handoff_candidate")
        if isinstance(bridge.get("authority_handoff_candidate"), dict)
        else {}
    )
    if not (
        bool(snap.get("partial_transfer_ready"))
        and handoff.get("candidate") is True
        and bridge.get("migration_readiness") == "observation_ready"
        and bridge.get("drift_classification") == _DRIFT_ALIGNED
    ):
        return None

    scope = sorted(_critical_concerns_for_turn_class(tc_key))
    if not scope:
        return None
    coverage = (
        bridge.get("seam_concern_coverage")
        if isinstance(bridge.get("seam_concern_coverage"), dict)
        else {}
    )
    concern_decisions: list[dict[str, Any]] = []
    for cid in scope:
        cov = coverage.get(cid) if isinstance(coverage.get(cid), dict) else {}
        if cov.get("authority_transfer_status") != "bounded_partial_transfer_scope_met":
            return None
        concern_decisions.append(
            {
                "concern_id": cid,
                "decision": "ready_for_scoped_co_authority",
                "authority_transfer_status": cov.get("authority_transfer_status"),
                "required_validators": sorted(_partial_transfer_required_for_concern(cid, tc_key)),
                "bounded_scope_satisfied": True,
            }
        )

    seam_status = bridge.get("seam_status") if isinstance(bridge.get("seam_status"), dict) else {}
    dramatic_fidelity = _dramatic_mirror_fidelity(validator_dispatch_report)
    return {
        "schema_version": VALIDATION_CO_AUTHORITY_DECISION_SCHEMA_VERSION,
        "authority_stage": CO_AUTHORITY_STAGE_SCOPED,
        "decision": CO_AUTHORITY_DECISION_READY,
        "selected_turn_class": tc_key,
        "scope": scope,
        "concern_decisions": concern_decisions,
        "readiness_preview": {
            "status": "ready_for_scoped_co_authority",
            "partial_transfer_ready": True,
            "may_influence_readiness_preview": True,
            "allowed_effect": "preview_only",
        },
        "validation_preview": {
            "status": "ready_for_validation_co_authority",
            "legacy_seam_status": seam_status.get("status"),
            "legacy_seam_reason": seam_status.get("reason"),
            "may_influence_validation_preview": True,
            "allowed_effect": "preview_only",
        },
        "authority_basis": [
            "explicit_feature_flag_enabled",
            "partial_transfer_ready",
            "migration_readiness_observation_ready",
            "drift_aligned_with_run_validation_seam_echo",
            "deterministic_local_validators_all_pass",
            "dramatic_effect_mirror_fidelity_sufficient",
        ],
        "dramatic_effect_mirror_fidelity": dramatic_fidelity,
        "dramatic_effect_mirror_fidelity_sufficient": dramatic_fidelity != "partial_defaults",
        "legacy_canonical_authority": CO_AUTHORITY_LEGACY_SEAM,
        "legacy_fallback_authority": CO_AUTHORITY_LEGACY_SEAM,
        "canonical_commitment_seam": CO_AUTHORITY_COMMITMENT_SEAM,
        "authority_limits": [
            "does_not_block_commit",
            "does_not_overwrite_validation_outcome",
            "does_not_replace_run_validation_seam",
            "readiness_preview_only",
        ],
        "must_not_override_validation_outcome": True,
        "validation_outcome_changed": False,
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "affects_commit": False,
        "affects_readiness": False,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
        "feature_flag": feature_flag_name,
        "feature_flag_enabled": True,
    }


def build_readiness_co_authority_preview(
    *,
    validation_authority_bridge: dict[str, Any],
    validator_dispatch_report: dict[str, Any],
    selected_turn_class: str,
    validation_co_authority_decision: dict[str, Any] | None,
    feature_flag_name: str,
    feature_flag_enabled: bool,
) -> dict[str, Any]:
    """Build policy-grade, non-mutating readiness co-authority preview."""
    bridge = validation_authority_bridge if isinstance(validation_authority_bridge, dict) else {}
    report = validator_dispatch_report if isinstance(validator_dispatch_report, dict) else {}
    tc_key = normalize_turn_class_key(str(selected_turn_class or bridge.get("selected_turn_class") or ""))
    adr = _adr0041_aggregate_status(report)
    seam_status = bridge.get("seam_status") if isinstance(bridge.get("seam_status"), dict) else {}
    handoff = bridge.get("authority_handoff_candidate")
    handoff = handoff if isinstance(handoff, dict) else {}
    per_tc = bridge.get("per_turn_class") if isinstance(bridge.get("per_turn_class"), dict) else {}
    snap = per_tc.get(tc_key) if isinstance(per_tc.get(tc_key), dict) else {}

    scope = sorted(_critical_concerns_for_turn_class(tc_key))
    drift_classification = str(bridge.get("drift_classification") or "").strip() or None
    dramatic_fidelity = _dramatic_mirror_fidelity(report)
    unavailable_validators = [str(x) for x in (adr.get("unavailable_validator_ids") or []) if str(x)]
    failed_validators: list[str] = []
    for ent in report.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        if not ent.get("actually_executed") or ent.get("unavailable"):
            continue
        ev = ent.get("local_execution_evidence")
        if isinstance(ev, dict) and ev.get("passed") is False:
            vid = str(ent.get("validator_id") or "")
            if vid and vid not in failed_validators:
                failed_validators.append(vid)
    partial_blocked = [str(x) for x in (snap.get("partial_transfer_blocked") or []) if str(x)]

    blockers: list[str] = []
    if adr.get("engagement") != "plan_enforced":
        blockers.append("no_sidecar_or_not_plan_enforced")
    if dramatic_fidelity == "partial_defaults":
        blockers.append("partial_defaults")
    if unavailable_validators:
        blockers.append("unavailable_validator")
    if drift_classification == "missing_context" or any("missing_context" in b for b in partial_blocked):
        blockers.append("missing_context")
    if drift_classification and drift_classification != _DRIFT_ALIGNED:
        blockers.append("drift_not_aligned")
    if failed_validators:
        blockers.append("failed_validator")
    has_scoped_decision = isinstance(validation_co_authority_decision, dict)
    if not has_scoped_decision and adr.get("engagement") == "plan_enforced":
        blockers.append("no_scoped_co_authority_decision")

    blocker_seen: set[str] = set()
    blocker_out: list[str] = []
    for row in blockers:
        text = str(row).strip()
        if text and text not in blocker_seen:
            blocker_seen.add(text)
            blocker_out.append(text)

    policy_stage = READINESS_POLICY_SHADOW_ONLY
    candidate = False
    would_allow_readiness = False
    would_block_readiness = False
    status = "shadow_only"
    if "no_sidecar_or_not_plan_enforced" in blocker_out:
        policy_stage = READINESS_POLICY_NOT_ELIGIBLE
        status = "not_eligible"
    elif any(x in blocker_out for x in ("missing_context", "unavailable_validator", "partial_defaults")):
        policy_stage = READINESS_POLICY_NOT_ELIGIBLE
        status = "not_eligible"
    elif has_scoped_decision and not blocker_out:
        policy_stage = READINESS_POLICY_PREVIEW_ALLOW
        status = "readiness_preview_allow"
        candidate = True
        would_allow_readiness = True
    elif has_scoped_decision:
        policy_stage = READINESS_POLICY_PREVIEW_CANDIDATE
        status = "readiness_preview_candidate"
        candidate = True
        would_block_readiness = True
    elif blocker_out:
        policy_stage = READINESS_POLICY_PREVIEW_BLOCK
        status = "readiness_preview_block"
        would_block_readiness = True

    return {
        "schema_version": READINESS_CO_AUTHORITY_PREVIEW_SCHEMA_VERSION,
        "mode": "shadow_readiness_preview",
        "policy_stage": policy_stage,
        "status": status,
        "candidate": candidate,
        "would_allow_readiness": would_allow_readiness,
        "would_block_readiness": would_block_readiness,
        "scope": scope,
        "turn_class": tc_key,
        "source": (
            "adr0041_validation_co_authority_decision"
            if has_scoped_decision
            else "adr0041_validation_authority_bridge"
        ),
        "run_validation_seam_status": seam_status.get("status"),
        "run_validation_seam_reason": seam_status.get("reason"),
        "adr0041_status": adr.get("engagement"),
        "drift_classification": drift_classification,
        "blockers": blocker_out,
        "evidence": {
            "partial_transfer_ready": bool(snap.get("partial_transfer_ready")),
            "handoff_candidate": handoff.get("candidate") is True,
            "mirror_fidelity_gate_passed": dramatic_fidelity != "partial_defaults",
            "unavailable_validators": unavailable_validators,
            "failed_validators": failed_validators,
            "partial_transfer_blocked": partial_blocked,
        },
        "authority_limits": [
            "readiness_preview_only",
            "does_not_mutate_commit_gate",
            "does_not_mutate_readiness_gate",
            "does_not_overwrite_validation_outcome",
            "run_validation_seam_remains_canonical",
        ],
        "affects_commit": False,
        "affects_readiness": False,
        "validation_outcome_changed": False,
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
        "feature_flag": feature_flag_name,
        "feature_flag_enabled": bool(feature_flag_enabled),
    }


def build_readiness_co_authority_enforcement(
    *,
    readiness_co_authority_preview: dict[str, Any] | None,
    validator_dispatch_report: dict[str, Any],
    selected_turn_class: str,
    feature_flag_name: str,
    feature_flag_enabled: bool,
) -> dict[str, Any]:
    """Build scoped readiness enforcement pilot output (still non-mutating)."""
    report = validator_dispatch_report if isinstance(validator_dispatch_report, dict) else {}
    preview = (
        readiness_co_authority_preview
        if isinstance(readiness_co_authority_preview, dict)
        else {}
    )
    tc_key = normalize_turn_class_key(str(selected_turn_class or preview.get("turn_class") or ""))
    scope = (
        [str(x) for x in (preview.get("scope") or []) if str(x)]
        if isinstance(preview.get("scope"), list)
        else sorted(_critical_concerns_for_turn_class(tc_key))
    )
    evidence = preview.get("evidence") if isinstance(preview.get("evidence"), dict) else {}
    policy_stage = str(preview.get("policy_stage") or "").strip()
    drift = str(preview.get("drift_classification") or "").strip()
    blockers = [str(x) for x in (preview.get("blockers") or []) if str(x)]
    unavailable = [
        str(x) for x in (evidence.get("unavailable_validators") or []) if str(x)
    ]
    failed = [str(x) for x in (evidence.get("failed_validators") or []) if str(x)]
    partial_defaults = "partial_defaults" in blockers or not bool(
        evidence.get("mirror_fidelity_gate_passed", True)
    )
    entries = report.get("entries") if isinstance(report.get("entries"), list) else []
    judges_executed = False
    judge_ids = frozenset({"narrative_coherence_judge", "dramatic_quality_judge", "consistency_judge"})
    for ent in entries:
        if not isinstance(ent, dict):
            continue
        if str(ent.get("validator_id") or "") in judge_ids and ent.get("actually_executed"):
            judges_executed = True
            break

    readiness_input = "no_decision"
    reason = "enforcement_flag_disabled_or_preview_missing"
    if feature_flag_enabled and preview:
        allow = (
            policy_stage == READINESS_POLICY_PREVIEW_ALLOW
            and preview.get("would_allow_readiness") is True
            and preview.get("would_block_readiness") is False
            and drift == _DRIFT_ALIGNED
            and not unavailable
            and not failed
            and not partial_defaults
            and not judges_executed
        )
        block = (
            preview.get("would_block_readiness") is True
            or drift not in {"", _DRIFT_ALIGNED}
            or bool(unavailable)
            or bool(failed)
            or partial_defaults
            or "missing_context" in blockers
        )
        if allow:
            readiness_input = "allow"
            reason = "all_scoped_enforcement_preconditions_met"
        elif block:
            readiness_input = "block"
            reason = "scoped_readiness_enforcement_blocked_by_policy_evidence"
        else:
            readiness_input = "no_decision"
            reason = "pilot_enabled_but_no_explicit_allow_or_block_signal"

    return {
        "schema_version": READINESS_ENFORCEMENT_SCHEMA_VERSION,
        "mode": "scoped_readiness_enforcement",
        "enabled": bool(feature_flag_enabled),
        "enforcement_stage": "pilot",
        "would_affect_readiness": readiness_input in {"allow", "block"},
        "readiness_input": readiness_input,
        "scope": scope,
        "turn_class": tc_key,
        "source": "adr0041_readiness_co_authority_preview",
        "policy_stage": policy_stage or None,
        "drift_classification": drift or None,
        "reason": reason,
        "blockers": blockers,
        "evidence": evidence,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
        "validation_outcome_changed": False,
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "affects_commit": False,
        "affects_readiness": False,
        "feature_flag": feature_flag_name,
        "feature_flag_enabled": bool(feature_flag_enabled),
    }


def classify_seam_readiness_for_aggregation(
    validation_seam_summary: dict[str, Any] | None,
) -> str:
    """Map seam summary to coarse readiness for aggregation (allow / reject / unknown)."""
    seam = validation_seam_summary if isinstance(validation_seam_summary, dict) else {}
    status = str(seam.get("status") or "").strip().lower()
    if status in {"approved", "passed", "ok"}:
        return "allow"
    if status in {"rejected", "failed", "error"}:
        return "reject"
    return "unknown"


def aggregate_runtime_readiness_with_adr0041(
    *,
    seam_readiness: str,
    adr0041_readiness_input: str,
) -> tuple[str, bool, bool, str]:
    """Combine seam canonical readiness with ADR-0041 policy input (veto-only).

    Rules:
    - ``run_validation_seam`` outcome is canonical for allow vs reject.
    - ADR-0041 may **block** an otherwise seam-allowed readiness (veto).
    - ADR-0041 must **never** upgrade a seam reject into allow.

    Returns:
        ``(aggregated_readiness, adr0041_veto_applied, adr0041_can_upgrade_seam_reject, reason)``
        where ``aggregated_readiness`` is ``allow | block | unchanged``.
    """
    sr = str(seam_readiness or "").strip().lower()
    if sr not in {"allow", "reject", "unknown"}:
        sr = "unknown"
    adr = str(adr0041_readiness_input or "").strip().lower()
    if adr not in {"allow", "block", "no_decision"}:
        adr = "no_decision"

    can_upgrade = False
    veto = False
    agg = "unchanged"
    reason = "aggregation_baseline"

    if sr == "allow":
        if adr == "block":
            agg, veto, reason = "block", True, "adr0041_scoped_readiness_veto_over_seam_allow"
        elif adr == "allow":
            agg, reason = "allow", "seam_allow_and_adr0041_allow"
        else:
            agg, reason = "allow", "seam_allow_adr0041_no_decision"
    elif sr == "reject":
        if adr == "allow":
            agg, reason = "unchanged", "seam_reject_adr0041_allow_no_upgrade"
        elif adr == "block":
            agg, reason = "block", "seam_reject_with_adr0041_block"
        else:
            agg, reason = "block", "seam_reject_adr0041_no_decision"
    else:
        if adr == "block":
            agg, reason = "block", "adr0041_block_seam_readiness_unknown"
        elif adr == "allow":
            agg, reason = "unchanged", "seam_unknown_adr0041_allow_conservative_no_upgrade"
        else:
            agg, reason = "unchanged", "seam_unknown_adr0041_no_decision"

    return agg, veto, can_upgrade, reason


def build_readiness_aggregation_decision(
    *,
    validation_seam_summary: dict[str, Any] | None,
    readiness_policy_input: dict[str, Any],
) -> dict[str, Any]:
    """Scoped readiness aggregation pilot: seam canonical + ADR-0041 veto-only."""
    policy = readiness_policy_input if isinstance(readiness_policy_input, dict) else {}
    seam_rd = classify_seam_readiness_for_aggregation(validation_seam_summary)
    adr_in = str(policy.get("readiness_input") or "no_decision").strip().lower()
    if adr_in not in {"allow", "block", "no_decision"}:
        adr_in = "no_decision"
    scope = [str(x) for x in (policy.get("scope") or []) if str(x)] if isinstance(
        policy.get("scope"), list
    ) else []
    blockers = [str(x) for x in (policy.get("blockers") or []) if str(x)] if isinstance(
        policy.get("blockers"), list
    ) else []

    agg, veto, can_upgrade, reason = aggregate_runtime_readiness_with_adr0041(
        seam_readiness=seam_rd,
        adr0041_readiness_input=adr_in,
    )

    return {
        "schema_version": READINESS_AGGREGATION_SCHEMA_VERSION,
        "mode": "scoped_readiness_aggregation",
        "enabled": True,
        "source": "adr0041_readiness_policy_input",
        "seam_readiness": seam_rd,
        "adr0041_readiness_input": adr_in,
        "aggregated_readiness": agg,
        "adr0041_veto_applied": bool(veto),
        "adr0041_can_upgrade_seam_reject": bool(can_upgrade),
        "scope": scope,
        "reason": reason,
        "blockers": list(blockers),
        "validation_outcome_changed": False,
        "commit_gate_changed": False,
        "readiness_gate_changed": False,
        "affects_commit": False,
        "affects_readiness": False,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
    }


def _invert_seam_area_buckets(rel_map: dict[str, str]) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        SEAM_AREA_REL_MIRRORED_FULL: [],
        SEAM_AREA_REL_MIRRORED_PARTIAL: [],
        SEAM_AREA_REL_SEAM_OWNED: [],
        SEAM_AREA_REL_MIGRATION_CANDIDATE: [],
        SEAM_AREA_REL_NOT_SAFE: [],
    }
    for cid, rel in rel_map.items():
        if rel in buckets:
            buckets[rel].append(cid)
    return buckets


def build_validation_authority_bridge(
    *,
    validation_seam_summary: dict[str, Any],
    validator_dispatch_report: dict[str, Any],
    validation_authority_preview: dict[str, Any],
    selected_turn_class: str,
    retrieval_observation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build structured bridge payload (JSON-safe dict)."""
    seam = validation_seam_summary if isinstance(validation_seam_summary, dict) else {}
    preview = validation_authority_preview if isinstance(validation_authority_preview, dict) else {}
    drift_block = preview.get("drift_vs_validation_seam")
    drift_classification = ""
    if isinstance(drift_block, dict):
        drift_classification = str(drift_block.get("classification") or "").strip()

    adr0041 = _adr0041_aggregate_status(validator_dispatch_report)
    tc_key = normalize_turn_class_key(selected_turn_class)
    blockers = _collect_blockers(
        turn_class=tc_key,
        preview=preview,
        adr0041=adr0041,
        drift_classification=drift_classification,
    )

    unavailable_count = len(adr0041.get("unavailable_validator_ids") or [])
    mig = _migration_readiness(
        drift_classification=drift_classification,
        adr0041=adr0041,
        unavailable_count=unavailable_count,
    )

    per_tc = {
        k: _turn_class_migration_snapshot(
            k,
            selected_turn_class=tc_key,
            validator_dispatch_report=validator_dispatch_report,
        )
        for k in KNOWN_TURN_CLASSES
    }

    selected_snap = per_tc[tc_key]
    partial_transfer_ready = bool(selected_snap.get("partial_transfer_ready"))
    partial_blocked = list(selected_snap.get("partial_transfer_blocked") or [])

    seam_concern_coverage = build_seam_concern_coverage(
        selected_turn_class=tc_key,
        validator_dispatch_report=validator_dispatch_report,
        partial_transfer_ready=partial_transfer_ready,
    )
    seam_area_relationship: dict[str, str] = {
        cid: str(entry.get("seam_area_adr0041_relationship") or SEAM_AREA_REL_NOT_SAFE)
        for cid, entry in seam_concern_coverage.items()
        if isinstance(entry, dict) and "seam_area_adr0041_relationship" in entry
    }
    for cid, spec in SEAM_CONCERN_SPECS.items():
        seam_area_relationship.setdefault(
            cid,
            _seam_area_relationship_for_concern(cid, spec, _turn_class_enforced_set(tc_key)),
        )

    handoff = build_authority_handoff_candidate(
        selected_turn_class=tc_key,
        validator_dispatch_report=validator_dispatch_report,
        migration_readiness=mig,
        drift_classification=drift_classification,
        partial_transfer_ready=partial_transfer_ready,
        partial_transfer_blocked=partial_blocked,
        bridge_blockers=blockers,
    )

    classification_index = {
        cid: str(spec.get("authority_classification") or "") for cid, spec in SEAM_CONCERN_SPECS.items()
    }
    buckets: dict[str, list[str]] = {
        AUTHORITY_CLASSIFICATION_MIRROR: [],
        AUTHORITY_CLASSIFICATION_SEAM_OWNED: [],
        AUTHORITY_CLASSIFICATION_CANDIDATE: [],
        AUTHORITY_CLASSIFICATION_REQUIRES_NEW: [],
        AUTHORITY_CLASSIFICATION_NOT_SAFE_YET: [],
    }
    for cid, spec in SEAM_CONCERN_SPECS.items():
        ac = str(spec.get("authority_classification") or "")
        if ac in buckets:
            buckets[ac].append(cid)
    retrieval_auth = (
        retrieval_observation.get("retrieval_authority")
        if isinstance(retrieval_observation, dict)
        and isinstance(retrieval_observation.get("retrieval_authority"), dict)
        else {}
    )
    retrieval_authority_level = str(retrieval_auth.get("authority_level") or "").strip().lower()
    retrieval_observation_only = retrieval_authority_level in {
        "",
        "retrieved_unverified",
        "diagnostic_only",
    }

    return {
        "schema_version": VALIDATION_AUTHORITY_BRIDGE_SCHEMA_VERSION,
        "seam_status": {
            "status": seam.get("status"),
            "reason": seam.get("reason"),
            "validator_lane": seam.get("validator_lane"),
            "dramatic_quality_gate": seam.get("dramatic_quality_gate"),
            "error_code": seam.get("error_code"),
        },
        "adr0041_status": adr0041,
        "drift_classification": drift_classification or None,
        "recommended_authority": _RECOMMENDED_AUTHORITY_SEAM_CANONICAL,
        "authority_notes": _AUTHORITY_NOTES_DEFAULT,
        "migration_readiness": mig,
        "blockers": blockers,
        "selected_turn_class": tc_key,
        "per_turn_class": per_tc,
        "authority_classification_index": classification_index,
        "authority_classification_buckets": buckets,
        "seam_concern_catalog": SEAM_CONCERN_SPECS,
        "seam_concern_coverage": seam_concern_coverage,
        "seam_area_adr0041_relationship": seam_area_relationship,
        "seam_area_adr0041_relationship_buckets": _invert_seam_area_buckets(seam_area_relationship),
        "authority_handoff_candidate": handoff,
        "retrieval_observation_only": retrieval_observation_only,
        "retrieval_authority_level": retrieval_authority_level or "unknown",
        "authority_critical_consumers_require_canonical_provenance": True,
        "affects_commit": False,
        "affects_readiness": False,
        "proof_level": "local_only",
        "live_or_staging_evidence": False,
    }


def seam_concerns_covered_by_adr0041_validators(
    validator_ids: set[str],
) -> dict[str, Any]:
    """Return which seam concerns have at least one related validator in ``validator_ids``."""
    covered: list[str] = []
    not_covered: list[str] = []
    for cid, spec in SEAM_CONCERN_SPECS.items():
        related = {str(v) for v in (spec.get("related_adr0041_validators") or ())}
        if related & validator_ids:
            covered.append(cid)
        else:
            not_covered.append(cid)
    return {"covered_seam_concern_ids": covered, "uncovered_seam_concern_ids": not_covered}
