"""God of Carnage structured setting YAML — bundle exposure and cross-layer consistency."""

from __future__ import annotations

from pathlib import Path

from ai_stack.goc_yaml_authority import (
    clear_goc_yaml_slice_cache,
    load_goc_apartment_layout_yaml,
    load_goc_scene_affordances_block,
    load_goc_scene_affordances_yaml_inner,
    load_goc_yaml_slice_bundle,
)
from ai_stack.langgraph_runtime_executor import RuntimeTurnGraphExecutor


def setup_module(_m: object) -> None:
    clear_goc_yaml_slice_cache()


def test_yaml_slice_bundle_exposes_structured_setting_keys() -> None:
    clear_goc_yaml_slice_cache()
    bundle = load_goc_yaml_slice_bundle()
    for key in (
        "character_documents",
        "scene_graph",
        "locations",
        "content_access_policy",
        "scene_affordances",
        "apartment_layout",
        "apartment_objects",
        "premise_and_backstory",
        "actor_pressure_profiles",
        "phase_beat_policy",
        "narrator_sensory_palette",
        "opening_scene_sequence",
        "hard_forbidden_rules",
    ):
        assert key in bundle
    assert bundle["opening_scene_sequence"].get("id") == "goc_opening_sequence_v1"
    assert "hard_forbidden" in (bundle.get("hard_forbidden_rules") or {})
    assert len((bundle.get("scene_graph") or {}).get("nodes") or []) > 10
    assert (bundle.get("locations") or {}).get("places")
    assert (bundle.get("content_access_policy") or {}).get("blocked_entities")
    assert set((bundle.get("character_documents") or {}).keys()) == {"veronique", "michel", "annette", "alain"}
    assert bundle["apartment_layout"].get("setting_id") == "vallon_paris_evening_apartment"
    assert "phase_1" in (bundle.get("phase_beat_policy") or {}).get("phases", {})


def test_scene_affordances_aligns_layout_room_ids() -> None:
    inner = load_goc_scene_affordances_yaml_inner()
    layout = load_goc_apartment_layout_yaml()
    loc_ids = {str(x.get("id")) for x in (inner.get("locations") or []) if isinstance(x, dict)}
    layout_room_ids = {r.get("id") for r in (layout.get("rooms") or []) if isinstance(r, dict)}
    assert {"bathroom", "kitchen", "hallway"}.issubset(loc_ids)
    assert layout_room_ids.issuperset({"bathroom", "kitchen", "hallway", "vallon_living_room"})


def _read_yaml(path):
    """Read a YAML file as a dict; used by locale-boundary and consistency audits."""
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _has_german_authoring_string(value) -> str | None:
    """Return a flagged substring if the value contains German-looking authoring text.

    Detects characteristic German-only orthography (ä/ö/ü/ß) embedded in authoring text.
    Comments are stripped by yaml parsing, so this only inspects authored values.
    """
    if isinstance(value, str):
        text = value.strip()
        if any(ch in text for ch in "äöüÄÖÜß"):
            return text[:80]
        return None
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and k.lower() in {"de", "german", "de_de"}:
                continue  # legitimate locale subkey
            hit = _has_german_authoring_string(v)
            if hit:
                return hit
        return None
    if isinstance(value, list):
        for item in value:
            hit = _has_german_authoring_string(item)
            if hit:
                return hit
    return None


def test_p2_1_english_only_knowledge_files_contain_no_german_authoring_strings() -> None:
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P2.1: locale boundary — English-authored knowledge
    files must not contain German authoring strings outside explicit locale subkeys.

    The locale layer (``locale/scene_affordances.yaml``) is intentionally excluded.
    """
    from pathlib import Path

    knowledge_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage" / "knowledge"
    english_only_files = [
        knowledge_dir / "opening_scene_sequence.yaml",
        knowledge_dir / "hard_forbidden_rules.yaml",
        knowledge_dir / "content_access_policy.yaml",
        knowledge_dir / "premise_and_backstory.yaml",
        knowledge_dir / "narrator_sensory_palette.yaml",
        knowledge_dir.parent / "locations.yaml",
        knowledge_dir.parent / "scene_graph.yaml",
        knowledge_dir.parent / "apartment_layout.yaml",
        knowledge_dir.parent / "actor_pressure_profiles.yaml",
        knowledge_dir.parent / "phase_beat_policy.yaml",
    ]
    failures: list[str] = []
    for path in english_only_files:
        if not path.is_file():
            continue
        data = _read_yaml(path)
        hit = _has_german_authoring_string(data)
        if hit:
            failures.append(f"{path.name}: '{hit}'")
    assert not failures, f"German authoring strings found in English-only knowledge: {failures}"


def test_p2_2_direction_and_knowledge_opening_handovers_are_consistent() -> None:
    """GOC-KNOWLEDGE-RUNTIME-INTEGRATION P2.2: direction/opening_sequence.yaml and
    knowledge/opening_scene_sequence.yaml must agree on the phase-1 handover so the
    runtime is not torn between two contracts."""
    from pathlib import Path

    module_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage"
    direction_data = _read_yaml(module_dir / "direction" / "opening_sequence.yaml")
    knowledge_data = _read_yaml(module_dir / "knowledge" / "opening_scene_sequence.yaml")

    knowledge_opening = knowledge_data.get("opening_scene_sequence") or {}
    knowledge_handover = None
    for event in (knowledge_opening.get("narrative_events") or []):
        if isinstance(event, dict) and event.get("handover_to_scene_phase"):
            knowledge_handover = event["handover_to_scene_phase"]
            break
    assert knowledge_handover == "phase_1", (
        f"knowledge/opening_scene_sequence handover expected phase_1, got {knowledge_handover}"
    )

    # Direction file may declare handover via either ``handover_to_phase`` or by referencing
    # phase_1 in its parts; both paths are valid as long as nothing points elsewhere.
    direction_text = (module_dir / "direction" / "opening_sequence.yaml").read_text(encoding="utf-8")
    assert "phase_1" in direction_text, "direction/opening_sequence.yaml should reference phase_1"
    # The direction file must reference the canonical knowledge contract so the relationship is explicit.
    assert "knowledge/opening_scene_sequence.yaml" in direction_text, (
        "direction/opening_sequence.yaml must point at knowledge/opening_scene_sequence.yaml"
    )


def test_opening_incident_content_is_concrete_in_direction_and_knowledge() -> None:
    module_dir = Path(__file__).resolve().parents[2] / "content" / "modules" / "god_of_carnage"
    opening_doc = (module_dir / "direction" / "opening.md").read_text(encoding="utf-8").lower()
    direction_text = (module_dir / "direction" / "opening_sequence.yaml").read_text(encoding="utf-8").lower()
    knowledge_text = (module_dir / "knowledge" / "opening_scene_sequence.yaml").read_text(encoding="utf-8").lower()
    premise_text = (module_dir / "knowledge" / "premise_and_backstory.yaml").read_text(encoding="utf-8").lower()

    for token in ("paris park", "basketball", "bicycle", "stick"):
        assert token in opening_doc
        assert token in direction_text
        assert token in knowledge_text or token in premise_text


def test_scene_graph_and_modular_character_documents_are_primary_surfaces() -> None:
    clear_goc_yaml_slice_cache()
    bundle = load_goc_yaml_slice_bundle()
    graph = bundle.get("scene_graph") or {}
    docs = bundle.get("character_documents") or {}
    locations = bundle.get("locations") or {}
    access = bundle.get("content_access_policy") or {}

    nodes = graph.get("nodes") or []
    assert len(nodes) >= 12
    assert graph.get("default_start_node_id") == "prologue_park_edge"
    assert graph.get("first_playable_node_id") == "first_playable_courtesy_gap"
    assert all(isinstance(row, dict) and row.get("location_id") for row in nodes)
    assert set(docs) == {"veronique", "michel", "annette", "alain"}
    assert all((doc.get("scene_usage") or {}) for doc in docs.values())
    assert {doc.get("runtime_actor_id") for doc in docs.values()} == {
        "veronique_vallon",
        "michel_longstreet",
        "annette_reille",
        "alain_reille",
    }
    assert (bundle.get("characters") or {}).get("annette", {}).get("actor_id") == "annette_reille"
    assert {row.get("id") for row in (locations.get("places") or [])}.issuperset(
        {"park_edge", "basketball_court", "vallon_living_room", "bathroom", "kitchen"}
    )
    assert set(access.get("scopes") or []).issuperset({"action", "location", "object", "scene_node"})


def test_goc_resolve_canonical_content_projects_structured_knowledge_onto_state() -> None:
    """P0.1: _goc_resolve_canonical_content surfaces all 9 knowledge keys + _loaded flags onto runtime state."""
    clear_goc_yaml_slice_cache()
    graph = object.__new__(RuntimeTurnGraphExecutor)
    update = graph._goc_resolve_canonical_content({"module_id": "god_of_carnage"})

    assert update["goc_slice_active"] is True
    assert isinstance(update.get("opening_scene_sequence"), dict) and update["opening_scene_sequence"]
    assert isinstance(update.get("hard_forbidden_rules"), dict) and update["hard_forbidden_rules"]
    for key in (
        "character_documents",
        "scene_graph",
        "locations",
        "content_access_policy",
        "apartment_layout",
        "apartment_objects",
        "premise_and_backstory",
        "actor_pressure_profiles",
        "phase_beat_policy",
        "narrator_sensory_palette",
        "scene_affordances",
    ):
        assert isinstance(update.get(key), dict) and update[key], f"state missing {key}"

    loaded = update.get("knowledge_runtime_loaded")
    assert isinstance(loaded, dict)
    for flag in (
        "opening_scene_sequence_loaded",
        "hard_forbidden_rules_loaded",
        "character_documents_loaded",
        "scene_graph_loaded",
        "locations_loaded",
        "content_access_policy_loaded",
        "apartment_layout_loaded",
        "apartment_objects_loaded",
        "premise_and_backstory_loaded",
        "actor_pressure_profiles_loaded",
        "phase_beat_policy_loaded",
        "narrator_sensory_palette_loaded",
        "scene_affordances_loaded",
    ):
        assert loaded.get(flag) is True, f"flag {flag} not True"

    contract = update.get("goc_runtime_knowledge_contract")
    assert isinstance(contract, dict)
    assert contract.get("opening_scene_sequence_id") == "goc_opening_sequence_v1"


def test_narrator_fixture_surface_has_german_runtime_cues_for_bathroom_kitchen_window() -> None:
    block = load_goc_scene_affordances_block()
    sa = block.get("scene_affordances") or {}
    locs = {str(x.get("id")): x for x in (sa.get("locations") or []) if isinstance(x, dict)}
    objs = {str(x.get("id")): x for x in (sa.get("objects") or []) if isinstance(x, dict)}
    kitchen = locs.get("kitchen") or {}
    bathroom = locs.get("bathroom") or {}
    assert "de" in ((kitchen.get("entry_sensory_detail") or {}) or {})
    assert "en" in ((kitchen.get("entry_sensory_detail") or {}) or {})
    de_bath = ((bathroom.get("entry_sensory_detail") or {}) or {}).get("de", "")
    en_bath = ((bathroom.get("entry_sensory_detail") or {}) or {}).get("en", "")
    assert de_bath and en_bath and de_bath != en_bath
    win = objs.get("window") or {}
    aliases = win.get("aliases") if isinstance(win.get("aliases"), list) else []
    assert aliases
    detail = win.get("perception_detail") or {}
    assert detail.get("de") and detail.get("en")
    assert detail["de"] != detail["en"]
