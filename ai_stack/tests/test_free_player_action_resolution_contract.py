"""PR-A acceptance tests for ``free_player_action_resolution.v1``.

These tests assert that ``ai_stack.player_action_resolution.resolve_player_action``
emits the closed-enum contract dict on every return path (meta-control,
semantic-resolution-required, speech-only, main inference path). Assertions
are over contract field names, closed enum values, and structural properties
-- never over the raw input string. Multiple paraphrased inputs per action
class prove that the path properties hold across registers.

Per ADR-0039 and PR-A's PIV:

* No exact-string fixture coupling. The semantic ``interpreted_input`` dict
  the test builds simulates an upstream AI semantic payload; the raw text is
  the surface label. Different raw strings paired with structurally
  equivalent semantic payloads must yield structurally equivalent contracts.
* No active Pi / Pi-numbered runtime keys in the new resolver module or the
  contract module under test.
* PR-A must not implement PR-B / PR-C symbols.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from ai_stack.free_player_action_resolution_contracts import (
    ACTION_COMMIT_POLICIES,
    ACTION_COMMIT_POLICY_COMMIT_ACTION,
    ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION,
    AFFORDANCE_STATUSES,
    AFFORDANCE_STATUS_ALLOWED,
    AFFORDANCE_STATUS_UNKNOWN_TARGET,
    CANON_SAFETY_VALUES,
    CANONICAL_RISKS,
    CANONICAL_RISK_LOW,
    CANONICAL_RISK_MEDIUM,
    PRESENCE_AUTHORITY_DIRECTOR_FINAL,
    PRESENCE_PROVENANCE_PRELIMINARY,
    REQUIRED_CONTRACT_KEYS,
    RESOLVED_TARGET_TYPES,
    RESOLVED_TARGET_TYPE_ACTOR,
    RESOLVED_TARGET_TYPE_LOCATION,
    RESOLVED_TARGET_TYPE_NONE,
    RESOLVED_TARGET_TYPE_OBJECT,
    SCHEMA_VERSION,
)
from ai_stack.player_action_resolution import resolve_player_action
from story_runtime_core.language_adapter import clear_language_adapter_caches


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clear_language_adapter_caches() -> None:
    clear_language_adapter_caches()
    yield
    clear_language_adapter_caches()


def _runtime_projection() -> dict:
    return {
        "human_actor_id": "annette_reille",
        "selected_player_role": "annette_reille",
        "npc_actor_ids": ["alain_reille", "veronique_vallon", "michel_longstreet"],
        "actor_lanes": {
            "annette_reille": "human",
            "alain_reille": "npc",
            "veronique_vallon": "npc",
            "michel_longstreet": "npc",
        },
    }


def _content_root() -> Path:
    return Path(__file__).resolve().parents[2] / "content" / "modules"


def _semantic_interpreted(
    *,
    target_id: str | None,
    target_type: str | None,
    target_query: str | None,
    verb: str,
    action_kind: str,
    actor_id: str = "annette_reille",
    commit_policy: str = "commit_action",
    player_input_kind: str = "action",
    extra_semantic: dict | None = None,
) -> dict:
    semantic = {
        "player_input_kind": player_input_kind,
        "verb": verb,
        "action_kind": action_kind,
        "target_query": target_query,
        "resolved_target_id": target_id,
        "resolved_target_type": target_type,
        "commit_policy": commit_policy,
        "confidence": "high" if target_id else "low",
    }
    if isinstance(extra_semantic, dict):
        semantic.update(extra_semantic)
    return {
        "player_input_kind": player_input_kind,
        "narrator_response_expected": True,
        "npc_response_expected": False,
        "actor_id": actor_id,
        "semantic_action": semantic,
    }


def _resolve(interpreted_input: dict, raw_text: str = "input under test") -> dict:
    return resolve_player_action(
        raw_text=raw_text,
        interpreted_input=interpreted_input,
        module_id="god_of_carnage",
        runtime_projection=_runtime_projection(),
        content_modules_root=_content_root(),
    )


def _contract(resolution: dict) -> dict:
    contract = resolution.get("free_player_action_resolution")
    assert isinstance(contract, dict), (
        "resolver must emit a free_player_action_resolution dict"
    )
    return contract


# ---------------------------------------------------------------------------
# Required-field completeness across all return paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "interpreted_input",
    [
        # main inference path: known movement
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        ),
        # main inference path: unknown target
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="undisclosed-place",
            target_id=None,
            target_type=None,
        ),
        # speech-only short circuit
        {
            "player_input_kind": "speech",
            "narrator_response_expected": False,
            "npc_response_expected": True,
            "actor_id": "annette_reille",
        },
        # semantic-required (action without AI semantics)
        {
            "player_input_kind": "action",
            "narrator_response_expected": True,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
        # meta short-circuit
        {
            "player_input_kind": "meta",
            "narrator_response_expected": False,
            "npc_response_expected": False,
            "actor_id": "annette_reille",
        },
    ],
    ids=[
        "main_inference_known_location",
        "main_inference_unknown_target",
        "speech_only_short_circuit",
        "semantic_required_short_circuit",
        "meta_short_circuit",
    ],
)
def test_every_return_path_emits_required_contract_keys(interpreted_input: dict) -> None:
    resolution = _resolve(interpreted_input)
    contract = _contract(resolution)
    for key in REQUIRED_CONTRACT_KEYS:
        assert key in contract, f"contract must carry required key: {key}"
    assert contract["schema_version"] == SCHEMA_VERSION


def test_contract_is_also_embedded_in_player_action_frame() -> None:
    resolution = _resolve(
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        )
    )
    frame = resolution["player_action_frame"]
    assert "free_player_action_resolution" in frame
    assert frame["free_player_action_resolution"] is resolution["free_player_action_resolution"]


# ---------------------------------------------------------------------------
# Closed-enum invariants
# ---------------------------------------------------------------------------


def test_contract_enums_are_closed() -> None:
    paraphrases: list[dict] = [
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        ),
        _semantic_interpreted(
            verb="examine",
            action_kind="perception",
            target_query="window",
            target_id=None,
            target_type="object",
            extra_semantic={
                "inference_mode": "canon_safe_plausible_affordance",
                "canon_safety": "content_silent_mundane",
                "canonical_risk": "low",
                "inferred_target_id": "inferred_local_window",
            },
        ),
        _semantic_interpreted(
            verb="address",
            action_kind="actor_interaction",
            target_query="Alain",
            target_id="alain_reille",
            target_type="actor",
        ),
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="impossible-place",
            target_id=None,
            target_type=None,
        ),
        _semantic_interpreted(
            verb="draw",
            action_kind="weapon_interaction",
            target_query="hidden weapon",
            target_id=None,
            target_type="object",
            extra_semantic={
                "canon_safety": "hidden_or_load_bearing_fact",
                "canonical_risk": "high",
            },
        ),
    ]
    for interpreted in paraphrases:
        contract = _contract(_resolve(interpreted))
        assert contract["resolved_target_type"] in RESOLVED_TARGET_TYPES
        assert contract["affordance_status"] in AFFORDANCE_STATUSES
        assert contract["action_commit_policy"] in ACTION_COMMIT_POLICIES
        assert contract["canonical_risk"] in CANONICAL_RISKS
        safety = contract["canon_safety"]
        assert safety is None or safety in CANON_SAFETY_VALUES


# ---------------------------------------------------------------------------
# Movement: paraphrased DE inputs across registers
# ---------------------------------------------------------------------------


# Each row pairs a paraphrased DE raw_text with a semantic payload an upstream
# LLM would produce for that paraphrase. Tests assert the same path properties
# across registers (umgangssprachlich / formell / elliptisch / imperativisch
# / iterativ). The raw_text is the surface label; the semantic dict is the
# resolution input the resolver actually consumes.
_MOVEMENT_PARAPHRASES_KITCHEN = [
    ("Ich gehe in die Küche.", "Go to the kitchen"),
    ("Geh in die Küche.", "Go to the kitchen"),
    ("Küche.", "kitchen"),
    ("Ab in die Küche.", "Move to the kitchen"),
    ("Ich möchte mal eben in der Küche schauen.", "Go to the kitchen briefly"),
    ("In die Küche, kurz.", "Move briefly to the kitchen"),
]


@pytest.mark.parametrize(
    ("raw_text", "english_normalization"),
    _MOVEMENT_PARAPHRASES_KITCHEN,
    ids=[f"register_{i}" for i in range(len(_MOVEMENT_PARAPHRASES_KITCHEN))],
)
def test_movement_paraphrases_produce_stable_location_contract(
    raw_text: str,
    english_normalization: str,
) -> None:
    interpreted = _semantic_interpreted(
        verb="move_to",
        action_kind="movement",
        target_query="kitchen",
        target_id="kitchen",
        target_type="location",
        extra_semantic={"normalized_english_text": english_normalization},
    )
    contract = _contract(_resolve(interpreted, raw_text=raw_text))
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_LOCATION
    assert contract["resolved_target_id"] == "kitchen"
    assert contract["target_location"] == "kitchen"
    assert contract["affordance_status"] == AFFORDANCE_STATUS_ALLOWED
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_COMMIT_ACTION
    assert contract["canonical_risk"] == CANONICAL_RISK_LOW


def test_movement_paraphrases_yield_identical_contract_projection() -> None:
    contracts: list[dict] = []
    for raw_text, normalization in _MOVEMENT_PARAPHRASES_KITCHEN:
        interpreted = _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
            extra_semantic={"normalized_english_text": normalization},
        )
        contracts.append(_contract(_resolve(interpreted, raw_text=raw_text)))
    projection_keys = (
        "resolved_target_type",
        "resolved_target_id",
        "target_location",
        "affordance_status",
        "action_commit_policy",
    )
    projections = {tuple((c[k]) for k in projection_keys) for c in contracts}
    assert len(projections) == 1, (
        "different DE paraphrases must produce structurally identical "
        "contract projections (no register-based drift)"
    )


# ---------------------------------------------------------------------------
# Object interaction
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_text",
    [
        "Ich öffne den Fahrstuhl.",
        "Den Fahrstuhl bitte öffnen.",
        "Fahrstuhl auf.",
    ],
    ids=["formell", "imperativ", "elliptisch"],
)
def test_object_interaction_produces_object_or_unknown_target(raw_text: str) -> None:
    interpreted = _semantic_interpreted(
        verb="open",
        action_kind="object_interaction",
        target_query="elevator",
        target_id="elevator",
        target_type="object",
        commit_policy="no_commit",
    )
    contract = _contract(_resolve(interpreted, raw_text=raw_text))
    # Object id known in the catalog -- resolved_target_type stays "object";
    # commit_policy "no_commit" projects to needs_clarification + unknown_target.
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_OBJECT
    assert contract["resolved_target_id"] == "elevator"
    # target_location remains None for object targets (no containing hint here).
    assert contract["target_location"] is None
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION
    assert contract["affordance_status"] == AFFORDANCE_STATUS_UNKNOWN_TARGET


def test_object_interaction_with_explicit_containing_location_hint() -> None:
    interpreted = _semantic_interpreted(
        verb="examine",
        action_kind="object_interaction",
        target_query="unlisted detail in the room",
        target_id=None,
        target_type="object",
        extra_semantic={
            "inference_mode": "canon_safe_plausible_affordance",
            "canon_safety": "content_silent_mundane",
            "canonical_risk": "low",
            "inferred_target_id": "inferred_local_room_detail",
            "target_location": "vallon_living_room",
        },
    )
    contract = _contract(_resolve(interpreted, raw_text="Ich sehe mich kurz im Raum um."))
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_OBJECT
    assert contract["target_location"] == "vallon_living_room"
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_COMMIT_ACTION


def test_object_interaction_target_location_is_null_or_container() -> None:
    interpreted = _semantic_interpreted(
        verb="open",
        action_kind="object_interaction",
        target_query="generic container",
        target_id=None,
        target_type="object",
        extra_semantic={
            "inference_mode": "canon_safe_plausible_affordance",
            "canon_safety": "content_silent_mundane",
            "canonical_risk": "low",
            "inferred_target_id": "inferred_local_container",
        },
    )
    contract = _contract(_resolve(interpreted, raw_text="Ich öffne einen Behälter."))
    # PR-A: object inference does not synthesize a target_location unless the
    # semantic payload provides one.
    assert contract["target_location"] is None
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_OBJECT


# ---------------------------------------------------------------------------
# Actor-directed input
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_text",
    [
        "Ich spreche Alain an.",
        "Alain.",
        "An Alain gewandt: hör zu.",
    ],
    ids=["formell", "elliptisch", "gestisch"],
)
def test_actor_directed_input_produces_actor_semantics(raw_text: str) -> None:
    interpreted = _semantic_interpreted(
        verb="address",
        action_kind="actor_interaction",
        target_query="Alain",
        target_id="alain_reille",
        target_type="actor",
    )
    contract = _contract(_resolve(interpreted, raw_text=raw_text))
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_ACTOR
    assert contract["resolved_target_id"] == "alain_reille"


def test_actor_directed_input_target_location_is_null() -> None:
    interpreted = _semantic_interpreted(
        verb="address",
        action_kind="actor_interaction",
        target_query="Veronique",
        target_id="veronique_vallon",
        target_type="actor",
    )
    contract = _contract(_resolve(interpreted, raw_text="Veronique?"))
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_ACTOR
    assert contract["target_location"] is None


# ---------------------------------------------------------------------------
# Fail-closed: unknown / impossible / criminal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw_text",
    [
        "Ich gehe nach Mordor.",
        "Auf nach Atlantis.",
        "Zum Schloss Neuschwanstein, jetzt.",
    ],
    ids=["fiktional_1", "fiktional_2", "fiktional_3"],
)
def test_unknown_target_fails_closed_with_classification_reason(raw_text: str) -> None:
    interpreted = _semantic_interpreted(
        verb="move_to",
        action_kind="movement",
        target_query="off_canon_place",
        target_id=None,
        target_type=None,
    )
    contract = _contract(_resolve(interpreted, raw_text=raw_text))
    assert contract["affordance_status"] == AFFORDANCE_STATUS_UNKNOWN_TARGET
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION
    assert contract["resolved_target_id"] is None
    assert contract["target_location"] is None
    # PR-A invariant: classification_reason is non-empty when id is null.
    assert contract["classification_reason"], (
        "classification_reason must be populated when resolved_target_id is null"
    )


def test_unknown_target_canonical_risk_is_medium_or_high() -> None:
    interpreted = _semantic_interpreted(
        verb="move_to",
        action_kind="movement",
        target_query="off_canon_place",
        target_id=None,
        target_type=None,
    )
    contract = _contract(_resolve(interpreted, raw_text="Ich verschwinde irgendwohin."))
    assert contract["canonical_risk"] in {CANONICAL_RISK_MEDIUM, "high"}
    assert contract["canonical_risk"] != CANONICAL_RISK_LOW


@pytest.mark.parametrize(
    ("raw_text", "semantic_extra"),
    [
        (
            "Ich greife zur Waffe.",
            {
                "canon_safety": "weapons_or_threat_objects",
                "canonical_risk": "high",
            },
        ),
        (
            "Ich entwickle Superkräfte.",
            {
                "canon_safety": "non_mundane_capability",
                "canonical_risk": "high",
            },
        ),
        (
            "Ich finde den entscheidenden Beweis.",
            {
                "canon_safety": "hidden_or_load_bearing_fact",
                "canonical_risk": "high",
            },
        ),
    ],
    ids=["weapon", "superpower", "hidden_evidence"],
)
def test_criminal_or_impossible_action_stays_clarification(
    raw_text: str,
    semantic_extra: dict,
) -> None:
    interpreted = _semantic_interpreted(
        verb="risk_action",
        action_kind="object_interaction",
        target_query="risk-bearing target",
        target_id=None,
        target_type="object",
        extra_semantic=semantic_extra,
    )
    contract = _contract(_resolve(interpreted, raw_text=raw_text))
    assert contract["affordance_status"] == AFFORDANCE_STATUS_UNKNOWN_TARGET
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION
    # canon_safety enum is closed; risk-band tokens project to None and the
    # risk is carried by canonical_risk.
    assert contract["canon_safety"] is None
    assert contract["canonical_risk"] in {CANONICAL_RISK_MEDIUM, "high"}


# ---------------------------------------------------------------------------
# presence_breaks_gathering: Director-final discipline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "interpreted_input",
    [
        _semantic_interpreted(
            verb="move_to",
            action_kind="movement",
            target_query="kitchen",
            target_id="kitchen",
            target_type="location",
        ),
        _semantic_interpreted(
            verb="examine",
            action_kind="perception",
            target_query="window",
            target_id=None,
            target_type="object",
        ),
        _semantic_interpreted(
            verb="address",
            action_kind="actor_interaction",
            target_query="Alain",
            target_id="alain_reille",
            target_type="actor",
        ),
    ],
    ids=["movement", "perception", "actor"],
)
def test_presence_breaks_gathering_is_preliminary_resolver_signal(
    interpreted_input: dict,
) -> None:
    contract = _contract(_resolve(interpreted_input))
    # Director final authority: PR-A always emits False; PR-C composes the
    # final value.
    assert contract["presence_breaks_gathering"] is False
    assert contract["presence_breaks_gathering_authority"] == PRESENCE_AUTHORITY_DIRECTOR_FINAL
    assert (
        contract["presence_breaks_gathering_provenance"]
        == PRESENCE_PROVENANCE_PRELIMINARY
    )
    evidence = contract["presence_breaks_gathering_evidence"]
    assert isinstance(evidence, dict)
    for key in ("target_location", "participation_relevance", "visibility_audibility"):
        assert key in evidence


def test_presence_evidence_carries_participation_and_visibility_when_provided() -> None:
    interpreted = _semantic_interpreted(
        verb="turn_away",
        action_kind="gesture",
        target_query="window",
        target_id=None,
        target_type=None,
        extra_semantic={
            "participation_relevance": "broken",
            "visibility_audibility": "still_audible",
        },
    )
    contract = _contract(_resolve(interpreted, raw_text="Ich drehe mich demonstrativ weg."))
    evidence = contract["presence_breaks_gathering_evidence"]
    assert evidence["participation_relevance"] == "broken"
    assert evidence["visibility_audibility"] == "still_audible"
    # PR-A still does not own the final bool.
    assert contract["presence_breaks_gathering"] is False


# ---------------------------------------------------------------------------
# Meta short-circuit
# ---------------------------------------------------------------------------


def test_meta_short_circuit_emits_none_target_type() -> None:
    interpreted = {
        "player_input_kind": "meta",
        "narrator_response_expected": False,
        "npc_response_expected": False,
        "actor_id": "annette_reille",
    }
    contract = _contract(_resolve(interpreted, raw_text="/help"))
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_NONE
    assert contract["resolved_target_id"] is None
    assert contract["target_location"] is None
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION
    assert contract["classification_reason"]


# ---------------------------------------------------------------------------
# Speech-only short circuit
# ---------------------------------------------------------------------------


def test_speech_only_short_circuit_emits_none_target_type() -> None:
    interpreted = {
        "player_input_kind": "speech",
        "narrator_response_expected": False,
        "npc_response_expected": True,
        "actor_id": "annette_reille",
    }
    contract = _contract(_resolve(interpreted, raw_text="Gibt es hier ein Bad?"))
    assert contract["resolved_target_type"] == RESOLVED_TARGET_TYPE_NONE
    # Speech is "commit_speech" upstream, which projects to "needs_clarification"
    # because the contract enum is {commit_action, needs_clarification}; the
    # commit_speech branch keeps its own canonical handling elsewhere.
    assert contract["action_commit_policy"] == ACTION_COMMIT_POLICY_NEEDS_CLARIFICATION


# ---------------------------------------------------------------------------
# Vocabulary / governance guardrails on the new module
# ---------------------------------------------------------------------------


_CONTRACT_MODULE_PATH = (
    REPO_ROOT / "ai_stack" / "free_player_action_resolution_contracts.py"
)
_RESOLVER_MODULE_PATH = REPO_ROOT / "ai_stack" / "player_action_resolution.py"

_ACTIVE_PI_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])pi_\d+\b|(?<![A-Za-z0-9])pi\d+_[A-Za-z0-9_]+\b|\u03a0\d+\b",
    re.IGNORECASE,
)

_PR_B_C_FORBIDDEN_DEFS = (
    re.compile(r"\bdef\s+compute_gathering_state\b"),
    re.compile(r"\bclass\s+compute_gathering_state\b"),
    re.compile(r"\bdef\s+presence_breaks_gathering\b"),
    re.compile(r"\bclass\s+presence_breaks_gathering\b"),
    re.compile(r"\bdef\s+gathering_paused\b"),
    re.compile(r"\bclass\s+gathering_paused\b"),
)


def test_new_contract_module_has_no_active_pi_runtime_keys() -> None:
    text = _CONTRACT_MODULE_PATH.read_text(encoding="utf-8")
    assert not _ACTIVE_PI_TOKEN_RE.search(text), (
        "free_player_action_resolution_contracts.py must use semantic capability names only"
    )


def test_resolver_module_has_no_active_pi_runtime_keys() -> None:
    text = _RESOLVER_MODULE_PATH.read_text(encoding="utf-8")
    assert not _ACTIVE_PI_TOKEN_RE.search(text), (
        "player_action_resolution.py must use semantic capability names only"
    )


def test_pr_a_does_not_implement_pr_b_pr_c_runtime_symbols() -> None:
    for path in (_CONTRACT_MODULE_PATH, _RESOLVER_MODULE_PATH):
        text = path.read_text(encoding="utf-8")
        for pattern in _PR_B_C_FORBIDDEN_DEFS:
            assert not pattern.search(text), (
                f"{path.name} must not define PR-B / PR-C runtime symbol "
                f"matching {pattern.pattern}"
            )


def test_contract_module_does_not_import_diagnostic_snapshot_stub() -> None:
    text = _CONTRACT_MODULE_PATH.read_text(encoding="utf-8")
    forbidden = re.compile(
        r"from\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b|"
        r"import\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b"
    )
    assert not forbidden.search(text), (
        "PR-A must not wire the PR-0 diagnostic snapshot stub into production"
    )


def test_resolver_module_does_not_import_diagnostic_snapshot_stub() -> None:
    text = _RESOLVER_MODULE_PATH.read_text(encoding="utf-8")
    forbidden = re.compile(
        r"from\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b|"
        r"import\s+ai_stack\.runtime_diagnostic_snapshot_contracts\b"
    )
    assert not forbidden.search(text), (
        "PR-A must not wire the PR-0 diagnostic snapshot stub into production"
    )
