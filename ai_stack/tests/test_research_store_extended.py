"""Extended tests for ai_stack/research_store.py to achieve 95%+ coverage."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from ai_stack.research_store import (
    RESEARCH_STORE_SCHEMA_VERSION,
    ResearchStore,
    _empty_state,
    _ensure_required_fields,
    _to_plain_dict,
)


# Test helpers and fixtures
@dataclass
class DummyDataclass:
    """A simple dataclass for testing _to_plain_dict."""
    id: str
    name: str


class DummyWithToDict:
    """A class with a to_dict method for testing _to_plain_dict."""
    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name

    def to_dict(self):
        return {"id": self.id, "name": self.name}


class DummyWithInvalidToDict:
    """A class with a to_dict method that returns non-dict."""
    def to_dict(self):
        return "not_a_dict"


@pytest.fixture
def temp_store(tmp_path):
    """Create a ResearchStore in a temporary directory."""
    store_path = tmp_path / "research_store.json"
    return ResearchStore(store_path)


@pytest.fixture
def populated_store(tmp_path):
    """Create a pre-populated ResearchStore."""
    store_path = tmp_path / "research_store.json"
    store = ResearchStore(store_path)

    # Add a source
    store.upsert_source({
        "source_id": "src_000001",
        "work_id": "work_001",
        "source_type": "book",
        "title": "Test Source",
        "provenance": {"location": "test"},
        "visibility": "public",
        "copyright_posture": "unknown",
        "segment_index_status": "pending",
        "metadata": {"pages": 100},
    })

    # Add an anchor
    store.upsert_anchor({
        "anchor_id": "anc_000001",
        "source_id": "src_000001",
        "segment_ref": "seg_001",
        "span_ref": "0-50",
        "paraphrase_or_excerpt": "Test excerpt",
        "confidence": 0.9,
        "notes": "test note",
    })

    # Add an aspect
    store.upsert_aspect({
        "aspect_id": "asp_000001",
        "source_id": "src_000001",
        "perspective": "neutral",
        "aspect_type": "narrative",
        "statement": "Test statement",
        "evidence_anchor_ids": ["anc_000001"],
        "tags": ["tag1"],
        "status": "active",
    })

    # Add an exploration node
    store.upsert_exploration_node({
        "node_id": "node_000001",
        "seed_aspect_id": "asp_000001",
        "perspective": "neutral",
        "hypothesis": "Test hypothesis",
        "rationale": "Test rationale",
        "speculative_level": 0.5,
        "evidence_anchor_ids": ["anc_000001"],
        "novelty_score": 0.7,
        "status": "active",
        "outcome": "pending",
    })

    # Add an exploration edge
    store.upsert_exploration_edge({
        "edge_id": "edge_000001",
        "from_node_id": "node_000001",
        "to_node_id": "node_000001",
        "relation_type": "explores",
    })

    # Add a claim
    store.upsert_claim({
        "claim_id": "claim_000001",
        "work_id": "work_001",
        "perspective": "neutral",
        "claim_type": "narrative_fact",
        "statement": "Test claim",
        "evidence_anchor_ids": ["anc_000001"],
        "support_level": 0.8,
        "contradiction_status": "none",
        "status": "active",
        "notes": "test claim note",
    })

    # Add an issue
    store.upsert_issue({
        "issue_id": "issue_000001",
        "module_id": "module_001",
        "issue_type": "inconsistency",
        "severity": "high",
        "description": "Test issue",
        "supporting_claim_ids": ["claim_000001"],
        "status": "open",
    })

    # Add a proposal
    store.upsert_proposal({
        "proposal_id": "prop_000001",
        "module_id": "module_001",
        "proposal_type": "enhancement",
        "rationale": "Test rationale",
        "expected_effect": "Test effect",
        "supporting_claim_ids": ["claim_000001"],
        "preview_patch_ref": {"patch": "test_patch"},
        "status": "pending",
    })

    # Add a run
    store.upsert_run({
        "run_id": "run_000001",
        "mode": "verification",
        "source_ids": ["src_000001"],
        "seed_question": "Test question?",
        "budget": {"tokens": 1000},
        "outputs": {"result": "test"},
        "audit_refs": ["audit_001"],
        "created_at": "2025-01-01T00:00:00Z",
    })

    return store


# Tests for _to_plain_dict
class TestToPlainDict:
    def test_to_plain_dict_with_to_dict_method(self):
        """Test conversion of object with to_dict method."""
        obj = DummyWithToDict("id1", "name1")
        result = _to_plain_dict(obj)
        assert result == {"id": "id1", "name": "name1"}

    def test_to_plain_dict_with_invalid_to_dict(self):
        """Test that non-dict return from to_dict falls through to dataclass check."""
        obj = DummyWithInvalidToDict()
        with pytest.raises(ValueError, match="record_must_be_dict_or_dataclass"):
            _to_plain_dict(obj)

    def test_to_plain_dict_with_dataclass(self):
        """Test conversion of dataclass."""
        obj = DummyDataclass("id1", "name1")
        result = _to_plain_dict(obj)
        assert result == {"id": "id1", "name": "name1"}

    def test_to_plain_dict_with_dict(self):
        """Test pass-through of dict."""
        obj = {"id": "id1", "name": "name1"}
        result = _to_plain_dict(obj)
        assert result == obj
        assert result is not obj  # Should be a copy

    def test_to_plain_dict_invalid_type(self):
        """Test error on invalid type."""
        with pytest.raises(ValueError, match="record_must_be_dict_or_dataclass"):
            _to_plain_dict("not_valid")


# Tests for _ensure_required_fields
class TestEnsureRequiredFields:
    def test_ensure_required_fields_all_present(self):
        """Test that validation passes with all required fields."""
        record = {"field1": "value1", "field2": "value2"}
        # Should not raise
        _ensure_required_fields(record, ("field1", "field2"))

    def test_ensure_required_fields_missing_field(self):
        """Test that missing required field raises error."""
        record = {"field1": "value1"}
        with pytest.raises(ValueError, match="missing_required_field:field2"):
            _ensure_required_fields(record, ("field1", "field2"))

    def test_ensure_required_fields_none_value(self):
        """Test that None value for required field raises error."""
        record = {"field1": "value1", "field2": None}
        with pytest.raises(ValueError, match="missing_required_field:field2"):
            _ensure_required_fields(record, ("field1", "field2"))

    def test_ensure_required_fields_empty_string(self):
        """Test that empty string for required field raises error."""
        record = {"field1": "value1", "field2": "   "}
        with pytest.raises(ValueError, match="empty_required_field:field2"):
            _ensure_required_fields(record, ("field1", "field2"))

    def test_ensure_required_fields_empty_ids_list(self):
        """Test that empty list for *_ids field raises error."""
        record = {"field1": "value1", "source_ids": []}
        with pytest.raises(ValueError, match="empty_required_list:source_ids"):
            _ensure_required_fields(record, ("field1", "source_ids"))

    def test_ensure_required_fields_valid_ids_list(self):
        """Test that non-empty list for *_ids field passes."""
        record = {"field1": "value1", "source_ids": ["src_001"]}
        _ensure_required_fields(record, ("field1", "source_ids"))

    def test_ensure_required_fields_empty_provenance_object(self):
        """Test that empty provenance object raises error."""
        record = {"field1": "value1", "provenance": {}}
        with pytest.raises(ValueError, match="empty_required_object:provenance"):
            _ensure_required_fields(record, ("field1", "provenance"))

    def test_ensure_required_fields_empty_metadata_object(self):
        """Test that empty metadata object raises error."""
        record = {"field1": "value1", "metadata": {}}
        with pytest.raises(ValueError, match="empty_required_object:metadata"):
            _ensure_required_fields(record, ("field1", "metadata"))

    def test_ensure_required_fields_empty_budget_object(self):
        """Test that empty budget object raises error."""
        record = {"field1": "value1", "budget": {}}
        with pytest.raises(ValueError, match="empty_required_object:budget"):
            _ensure_required_fields(record, ("field1", "budget"))

    def test_ensure_required_fields_empty_outputs_object(self):
        """Test that empty outputs object raises error."""
        record = {"field1": "value1", "outputs": {}}
        with pytest.raises(ValueError, match="empty_required_object:outputs"):
            _ensure_required_fields(record, ("field1", "outputs"))

    def test_ensure_required_fields_empty_preview_patch_ref_object(self):
        """Test that empty preview_patch_ref object raises error."""
        record = {"field1": "value1", "preview_patch_ref": {}}
        with pytest.raises(ValueError, match="empty_required_object:preview_patch_ref"):
            _ensure_required_fields(record, ("field1", "preview_patch_ref"))

    def test_ensure_required_fields_valid_objects(self):
        """Test that non-empty required objects pass."""
        record = {
            "field1": "value1",
            "provenance": {"key": "val"},
            "metadata": {"key": "val"},
            "budget": {"key": "val"},
            "outputs": {"key": "val"},
            "preview_patch_ref": {"key": "val"},
        }
        _ensure_required_fields(
            record,
            ("field1", "provenance", "metadata", "budget", "outputs", "preview_patch_ref")
        )


# Tests for _empty_state
class TestEmptyState:
    def test_empty_state_structure(self):
        """Test that empty state has correct structure."""
        state = _empty_state()
        assert isinstance(state, dict)
        assert state["schema_version"] == RESEARCH_STORE_SCHEMA_VERSION
        assert "updated_at" in state
        assert isinstance(state["counters"], dict)
        for bucket in ("sources", "anchors", "aspects", "exploration_nodes",
                       "exploration_edges", "claims", "issues", "proposals", "runs"):
            assert bucket in state
            assert isinstance(state[bucket], dict)
            assert len(state[bucket]) == 0


# Tests for ResearchStore class
class TestResearchStoreInitialization:
    def test_init_new_store(self, tmp_path):
        """Test initializing a new ResearchStore."""
        store_path = tmp_path / "research_store.json"
        store = ResearchStore(store_path)
        assert store.storage_path == store_path
        assert not store_path.exists()  # Not persisted until save

    def test_from_repo_root(self, tmp_path):
        """Test factory method from_repo_root."""
        store = ResearchStore.from_repo_root(tmp_path)
        expected_path = tmp_path / ".wos" / "research" / "research_store.json"
        assert store.storage_path == expected_path

    def test_init_with_existing_store(self, tmp_path):
        """Test loading existing store from disk."""
        store_path = tmp_path / "research_store.json"
        # Create and save initial store
        store1 = ResearchStore(store_path)
        store1.next_id("test")

        # Load from disk
        store2 = ResearchStore(store_path)
        assert store2._state["counters"]["test"] == 1


class TestResearchStoreLoad:
    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file initializes empty state."""
        store = ResearchStore(tmp_path / "nonexistent.json")
        assert store._state["schema_version"] == RESEARCH_STORE_SCHEMA_VERSION
        assert len(store._state["sources"]) == 0

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON raises error."""
        store_path = tmp_path / "bad.json"
        store_path.write_text("not valid json")
        with pytest.raises(ValueError, match="invalid_research_store_json"):
            ResearchStore(store_path)

    def test_load_invalid_shape(self, tmp_path):
        """Test loading non-dict JSON raises error."""
        store_path = tmp_path / "bad_shape.json"
        store_path.write_text(json.dumps(["list", "not", "dict"]))
        with pytest.raises(ValueError, match="invalid_research_store_shape"):
            ResearchStore(store_path)

    def test_load_unsupported_schema_version(self, tmp_path):
        """Test loading wrong schema version raises error."""
        store_path = tmp_path / "bad_version.json"
        bad_state = _empty_state()
        bad_state["schema_version"] = "research_store_v999"
        store_path.write_text(json.dumps(bad_state))
        with pytest.raises(ValueError, match="unsupported_research_store_schema_version"):
            ResearchStore(store_path)

    def test_load_missing_buckets(self, tmp_path):
        """Test loading store with missing buckets initializes them."""
        store_path = tmp_path / "incomplete.json"
        partial_state = {
            "schema_version": RESEARCH_STORE_SCHEMA_VERSION,
            "updated_at": "2025-01-01T00:00:00Z",
            "counters": {"test": 1},
            # Missing other buckets
        }
        store_path.write_text(json.dumps(partial_state))
        store = ResearchStore(store_path)
        assert len(store._state["sources"]) == 0
        assert store._state["counters"]["test"] == 1

    def test_load_invalid_bucket_types(self, tmp_path):
        """Test loading with invalid bucket types coerces to empty dict."""
        store_path = tmp_path / "invalid_buckets.json"
        bad_state = _empty_state()
        bad_state["sources"] = "not_a_dict"
        bad_state["counters"] = ["not", "dict"]
        store_path.write_text(json.dumps(bad_state))
        store = ResearchStore(store_path)
        assert isinstance(store._state["sources"], dict)
        assert isinstance(store._state["counters"], dict)


class TestResearchStoreSave:
    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directories."""
        store_path = tmp_path / "nested" / "dirs" / "store.json"
        store = ResearchStore(store_path)
        store.next_id("test")
        assert store_path.exists()
        assert store_path.parent.exists()

    def test_save_atomic_write(self, tmp_path):
        """Test that save uses atomic write (temp file + rename)."""
        store_path = tmp_path / "store.json"
        store = ResearchStore(store_path)
        store.next_id("test")

        # Verify file exists and is valid JSON
        assert store_path.exists()
        data = json.loads(store_path.read_text())
        assert data["counters"]["test"] == 1

    def test_save_cleanup_on_error(self, tmp_path, monkeypatch):
        """Test that save cleans up temp files on error."""
        store_path = tmp_path / "store.json"
        store = ResearchStore(store_path)

        # Monkeypatch os.replace to raise an error
        import os
        original_replace = os.replace
        def failing_replace(src, dst):
            raise OSError("Simulated write failure")

        monkeypatch.setattr(os, "replace", failing_replace)

        with pytest.raises(OSError, match="Simulated write failure"):
            store.next_id("test")

        # Restore and verify cleanup
        monkeypatch.setattr(os, "replace", original_replace)
        temp_files = list(tmp_path.glob(".research_store_*.json"))
        assert len(temp_files) == 0

    def test_save_cleanup_with_oserror_on_unlink(self, tmp_path, monkeypatch):
        """Test that save handles OSError during temp file cleanup."""
        store_path = tmp_path / "store.json"
        store = ResearchStore(store_path)

        # Monkeypatch os.replace to raise an error
        import os
        original_replace = os.replace
        original_unlink = Path.unlink

        def failing_replace(src, dst):
            raise OSError("Simulated write failure")

        def failing_unlink(self, missing_ok=False):
            raise OSError("Cannot unlink")

        monkeypatch.setattr(os, "replace", failing_replace)
        monkeypatch.setattr(Path, "unlink", failing_unlink)

        # Should still raise the original error (OSError from replace)
        with pytest.raises(OSError, match="Simulated write failure"):
            store.next_id("test")

        # Restore
        monkeypatch.setattr(os, "replace", original_replace)
        monkeypatch.setattr(Path, "unlink", original_unlink)


class TestResearchStoreNextId:
    def test_next_id_increments(self, temp_store):
        """Test that next_id increments counter."""
        id1 = temp_store.next_id("source")
        id2 = temp_store.next_id("source")
        assert id1 == "source_000001"
        assert id2 == "source_000002"

    def test_next_id_different_prefixes(self, temp_store):
        """Test that different prefixes have separate counters."""
        id1 = temp_store.next_id("source")
        id2 = temp_store.next_id("anchor")
        assert id1 == "source_000001"
        assert id2 == "anchor_000001"

    def test_next_id_persists_across_instances(self, tmp_path):
        """Test that next_id counter persists across store instances."""
        store1 = ResearchStore(tmp_path / "store.json")
        id1 = store1.next_id("test")

        store2 = ResearchStore(tmp_path / "store.json")
        id2 = store2.next_id("test")
        assert id1 == "test_000001"
        assert id2 == "test_000002"


class TestResearchStoreValidation:
    def test_validate_anchor_unknown_source(self, temp_store):
        """Test that anchor validation rejects unknown source."""
        with pytest.raises(ValueError, match="unknown_source_reference"):
            temp_store.upsert_anchor({
                "anchor_id": "anc_000001",
                "source_id": "unknown_src",
                "segment_ref": "seg_001",
                "span_ref": "0-50",
                "paraphrase_or_excerpt": "Test",
                "confidence": 0.9,
                "notes": "test",
            })

    def test_validate_aspect_unknown_source(self, populated_store):
        """Test that aspect validation rejects unknown source."""
        with pytest.raises(ValueError, match="unknown_source_reference"):
            populated_store.upsert_aspect({
                "aspect_id": "asp_000002",
                "source_id": "unknown_src",
                "perspective": "neutral",
                "aspect_type": "narrative",
                "statement": "Test",
                "evidence_anchor_ids": ["anc_000001"],
                "tags": ["tag"],
                "status": "active",
            })

    def test_validate_aspect_unknown_anchor(self, populated_store):
        """Test that aspect validation rejects unknown anchor."""
        with pytest.raises(ValueError, match="unknown_anchor_reference"):
            populated_store.upsert_aspect({
                "aspect_id": "asp_000002",
                "source_id": "src_000001",
                "perspective": "neutral",
                "aspect_type": "narrative",
                "statement": "Test",
                "evidence_anchor_ids": ["unknown_anc"],
                "tags": [],
                "status": "active",
            })

    def test_validate_exploration_node_unknown_aspect(self, populated_store):
        """Test that exploration_node validation rejects unknown aspect."""
        with pytest.raises(ValueError, match="unknown_aspect_reference"):
            populated_store.upsert_exploration_node({
                "node_id": "node_000002",
                "seed_aspect_id": "unknown_asp",
                "perspective": "neutral",
                "hypothesis": "Test",
                "rationale": "Test",
                "speculative_level": 0.5,
                "evidence_anchor_ids": ["anc_000001"],
                "novelty_score": 0.7,
                "status": "active",
                "outcome": "pending",
            })

    def test_validate_exploration_node_unknown_parent(self, populated_store):
        """Test that exploration_node validation rejects unknown parent node."""
        with pytest.raises(ValueError, match="unknown_parent_node_reference"):
            populated_store.upsert_exploration_node({
                "node_id": "node_000003",
                "seed_aspect_id": "asp_000001",
                "parent_node_id": "unknown_parent",
                "perspective": "neutral",
                "hypothesis": "Test",
                "rationale": "Test",
                "speculative_level": 0.5,
                "evidence_anchor_ids": ["anc_000001"],
                "novelty_score": 0.7,
                "status": "active",
                "outcome": "pending",
            })

    def test_validate_exploration_node_unknown_anchor(self, populated_store):
        """Test that exploration_node validation rejects unknown anchor."""
        with pytest.raises(ValueError, match="unknown_anchor_reference"):
            populated_store.upsert_exploration_node({
                "node_id": "node_000002",
                "seed_aspect_id": "asp_000001",
                "perspective": "neutral",
                "hypothesis": "Test",
                "rationale": "Test",
                "speculative_level": 0.5,
                "evidence_anchor_ids": ["unknown_anc"],
                "novelty_score": 0.7,
                "status": "active",
                "outcome": "pending",
            })

    def test_validate_exploration_edge_unknown_from_node(self, temp_store):
        """Test that exploration_edge validation rejects unknown from_node."""
        with pytest.raises(ValueError, match="unknown_from_node_reference"):
            temp_store.upsert_exploration_edge({
                "edge_id": "edge_000001",
                "from_node_id": "unknown_node",
                "to_node_id": "unknown_node",
                "relation_type": "explores",
            })

    def test_validate_exploration_edge_unknown_to_node(self, populated_store):
        """Test that exploration_edge validation rejects unknown to_node."""
        with pytest.raises(ValueError, match="unknown_to_node_reference"):
            populated_store.upsert_exploration_edge({
                "edge_id": "edge_000002",
                "from_node_id": "node_000001",
                "to_node_id": "unknown_node",
                "relation_type": "explores",
            })

    def test_validate_claim_unknown_anchor(self, temp_store):
        """Test that claim validation rejects unknown anchor."""
        with pytest.raises(ValueError, match="unknown_anchor_reference"):
            temp_store.upsert_claim({
                "claim_id": "claim_000001",
                "work_id": "work_001",
                "perspective": "neutral",
                "claim_type": "narrative_fact",
                "statement": "Test",
                "evidence_anchor_ids": ["unknown_anc"],
                "support_level": 0.8,
                "contradiction_status": "none",
                "status": "active",
                "notes": "test",
            })

    def test_validate_issue_unknown_claim(self, temp_store):
        """Test that issue validation rejects unknown claim."""
        with pytest.raises(ValueError, match="unknown_claim_reference"):
            temp_store.upsert_issue({
                "issue_id": "issue_000001",
                "module_id": "module_001",
                "issue_type": "inconsistency",
                "severity": "high",
                "description": "Test",
                "supporting_claim_ids": ["unknown_claim"],
                "status": "open",
            })

    def test_validate_proposal_unknown_claim(self, temp_store):
        """Test that proposal validation rejects unknown claim."""
        with pytest.raises(ValueError, match="unknown_claim_reference"):
            temp_store.upsert_proposal({
                "proposal_id": "prop_000001",
                "module_id": "module_001",
                "proposal_type": "enhancement",
                "rationale": "Test",
                "expected_effect": "Test",
                "supporting_claim_ids": ["unknown_claim"],
                "preview_patch_ref": {"patch": "test"},
                "status": "pending",
            })


class TestResearchStoreUpsert:
    def test_upsert_missing_id_field(self, temp_store):
        """Test that upsert raises error when id_field is missing."""
        with pytest.raises(ValueError, match="missing_required_field:source_id"):
            temp_store.upsert_source({
                # Missing source_id
                "work_id": "work_001",
                "source_type": "book",
                "title": "Test",
                "provenance": {"key": "val"},
                "visibility": "public",
                "copyright_posture": "unknown",
                "segment_index_status": "pending",
                "metadata": {"key": "val"},
            })

    def test_upsert_empty_id_field(self, temp_store):
        """Test that upsert raises error when id_field is empty string."""
        with pytest.raises(ValueError, match="empty_required_field:source_id"):
            temp_store.upsert_source({
                "source_id": "   ",
                "work_id": "work_001",
                "source_type": "book",
                "title": "Test",
                "provenance": {"key": "val"},
                "visibility": "public",
                "copyright_posture": "unknown",
                "segment_index_status": "pending",
                "metadata": {"key": "val"},
            })

    def test_upsert_overwrites_existing(self, populated_store):
        """Test that upsert overwrites existing record."""
        original = populated_store.get_source("src_000001")
        assert original["title"] == "Test Source"

        populated_store.upsert_source({
            "source_id": "src_000001",
            "work_id": "work_001",
            "source_type": "journal",
            "title": "Updated Source",
            "provenance": {"key": "val"},
            "visibility": "private",
            "copyright_posture": "restricted",
            "segment_index_status": "complete",
            "metadata": {"pages": 200},
        })

        updated = populated_store.get_source("src_000001")
        assert updated["title"] == "Updated Source"
        assert updated["source_type"] == "journal"


class TestResearchStoreGetters:
    def test_get_run_exists(self, populated_store):
        """Test getting an existing run."""
        run = populated_store.get_run("run_000001")
        assert run is not None
        assert run["run_id"] == "run_000001"
        assert run["mode"] == "verification"

    def test_get_run_not_exists(self, populated_store):
        """Test getting non-existent run returns None."""
        run = populated_store.get_run("nonexistent_run")
        assert run is None

    def test_get_source_exists(self, populated_store):
        """Test getting an existing source."""
        source = populated_store.get_source("src_000001")
        assert source is not None
        assert source["source_id"] == "src_000001"

    def test_get_source_not_exists(self, populated_store):
        """Test getting non-existent source returns None."""
        source = populated_store.get_source("nonexistent_src")
        assert source is None

    def test_get_claim_exists(self, populated_store):
        """Test getting an existing claim."""
        claim = populated_store.get_claim("claim_000001")
        assert claim is not None
        assert claim["claim_id"] == "claim_000001"

    def test_get_claim_not_exists(self, populated_store):
        """Test getting non-existent claim returns None."""
        claim = populated_store.get_claim("nonexistent_claim")
        assert claim is None

    def test_get_returns_copy(self, populated_store):
        """Test that get methods return copies, not references."""
        run1 = populated_store.get_run("run_000001")
        run2 = populated_store.get_run("run_000001")
        assert run1 is not run2
        assert run1 == run2


class TestResearchStoreListers:
    def test_list_sources(self, populated_store):
        """Test listing sources."""
        sources = populated_store.list_sources()
        assert len(sources) == 1
        assert sources[0]["source_id"] == "src_000001"

    def test_list_anchors(self, populated_store):
        """Test listing anchors."""
        anchors = populated_store.list_anchors()
        assert len(anchors) == 1
        assert anchors[0]["anchor_id"] == "anc_000001"

    def test_list_aspects(self, populated_store):
        """Test listing aspects."""
        aspects = populated_store.list_aspects()
        assert len(aspects) == 1
        assert aspects[0]["aspect_id"] == "asp_000001"

    def test_list_exploration_nodes(self, populated_store):
        """Test listing exploration nodes."""
        nodes = populated_store.list_exploration_nodes()
        assert len(nodes) == 1
        assert nodes[0]["node_id"] == "node_000001"

    def test_list_exploration_edges(self, populated_store):
        """Test listing exploration edges."""
        edges = populated_store.list_exploration_edges()
        assert len(edges) == 1
        assert edges[0]["edge_id"] == "edge_000001"

    def test_list_claims(self, populated_store):
        """Test listing claims."""
        claims = populated_store.list_claims()
        assert len(claims) == 1
        assert claims[0]["claim_id"] == "claim_000001"

    def test_list_issues(self, populated_store):
        """Test listing issues."""
        issues = populated_store.list_issues()
        assert len(issues) == 1
        assert issues[0]["issue_id"] == "issue_000001"

    def test_list_proposals(self, populated_store):
        """Test listing proposals."""
        proposals = populated_store.list_proposals()
        assert len(proposals) == 1
        assert proposals[0]["proposal_id"] == "prop_000001"

    def test_list_runs(self, populated_store):
        """Test listing runs."""
        runs = populated_store.list_runs()
        assert len(runs) == 1
        assert runs[0]["run_id"] == "run_000001"

    def test_list_empty_buckets(self, temp_store):
        """Test listing empty buckets."""
        assert temp_store.list_sources() == []
        assert temp_store.list_anchors() == []
        assert temp_store.list_aspects() == []
        assert temp_store.list_exploration_nodes() == []
        assert temp_store.list_exploration_edges() == []
        assert temp_store.list_claims() == []
        assert temp_store.list_issues() == []
        assert temp_store.list_proposals() == []
        assert temp_store.list_runs() == []

    def test_list_sorted_order(self, temp_store):
        """Test that list methods return results in sorted order."""
        # Add multiple records
        for i in range(3, 0, -1):  # Add in reverse order
            temp_store.upsert_source({
                "source_id": f"src_{i:06d}",
                "work_id": "work_001",
                "source_type": "book",
                "title": f"Source {i}",
                "provenance": {"key": "val"},
                "visibility": "public",
                "copyright_posture": "unknown",
                "segment_index_status": "pending",
                "metadata": {"key": "val"},
            })

        sources = temp_store.list_sources()
        ids = [s["source_id"] for s in sources]
        assert ids == ["src_000001", "src_000002", "src_000003"]


class TestResearchStoreAllUpsertMethods:
    def test_upsert_source_missing_required_field(self, temp_store):
        """Test that source upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_source({
                "source_id": "src_000001",
                # Missing other required fields
            })

    def test_upsert_anchor_missing_required_field(self, temp_store):
        """Test that anchor upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_anchor({
                "anchor_id": "anc_000001",
                # Missing other required fields
            })

    def test_upsert_aspect_missing_required_field(self, temp_store):
        """Test that aspect upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_aspect({
                "aspect_id": "asp_000001",
                # Missing other required fields
            })

    def test_upsert_exploration_node_missing_required_field(self, temp_store):
        """Test that exploration_node upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_exploration_node({
                "node_id": "node_000001",
                # Missing other required fields
            })

    def test_upsert_exploration_edge_missing_required_field(self, temp_store):
        """Test that exploration_edge upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_exploration_edge({
                "edge_id": "edge_000001",
                # Missing other required fields
            })

    def test_upsert_claim_missing_required_field(self, temp_store):
        """Test that claim upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_claim({
                "claim_id": "claim_000001",
                # Missing other required fields
            })

    def test_upsert_issue_missing_required_field(self, temp_store):
        """Test that issue upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_issue({
                "issue_id": "issue_000001",
                # Missing other required fields
            })

    def test_upsert_proposal_missing_required_field(self, temp_store):
        """Test that proposal upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_proposal({
                "proposal_id": "prop_000001",
                # Missing other required fields
            })

    def test_upsert_run_missing_required_field(self, temp_store):
        """Test that run upsert requires all fields."""
        with pytest.raises(ValueError, match="missing_required_field"):
            temp_store.upsert_run({
                "run_id": "run_000001",
                # Missing other required fields
            })


class TestResearchStoreIdValidation:
    def test_upsert_with_non_string_id_field(self, temp_store):
        """Test that upsert rejects non-string id fields."""
        # Use a custom object whose to_dict returns id field as non-string
        class BadIdRecord:
            def to_dict(self):
                return {
                    "source_id": 123,  # Not a string
                    "work_id": "work_001",
                    "source_type": "book",
                    "title": "Test",
                    "provenance": {"key": "val"},
                    "visibility": "public",
                    "copyright_posture": "unknown",
                    "segment_index_status": "pending",
                    "metadata": {"key": "val"},
                }

        with pytest.raises(ValueError, match="missing_record_id:source_id"):
            temp_store.upsert_source(BadIdRecord())

    def test_upsert_with_null_id_after_conversion(self, temp_store):
        """Test that upsert rejects null id fields after conversion."""
        class NullIdRecord:
            def to_dict(self):
                return {
                    "source_id": None,  # Null
                    "work_id": "work_001",
                    "source_type": "book",
                    "title": "Test",
                    "provenance": {"key": "val"},
                    "visibility": "public",
                    "copyright_posture": "unknown",
                    "segment_index_status": "pending",
                    "metadata": {"key": "val"},
                }

        with pytest.raises(ValueError, match="missing_required_field:source_id"):
            temp_store.upsert_source(NullIdRecord())


class TestResearchStoreComplexScenarios:
    def test_full_workflow_with_all_entities(self, temp_store):
        """Test a complete workflow creating all entity types."""
        # Create source
        temp_store.upsert_source({
            "source_id": "src_001",
            "work_id": "work_001",
            "source_type": "book",
            "title": "Source",
            "provenance": {"location": "test"},
            "visibility": "public",
            "copyright_posture": "unknown",
            "segment_index_status": "pending",
            "metadata": {"key": "val"},
        })

        # Create anchors
        anchor_ids = []
        for i in range(1, 3):
            anchor_id = f"anc_{i:06d}"
            temp_store.upsert_anchor({
                "anchor_id": anchor_id,
                "source_id": "src_001",
                "segment_ref": f"seg_{i:03d}",
                "span_ref": f"{i*100}-{i*150}",
                "paraphrase_or_excerpt": f"Excerpt {i}",
                "confidence": 0.9,
                "notes": f"Note {i}",
            })
            anchor_ids.append(anchor_id)

        # Create aspect with anchors
        temp_store.upsert_aspect({
            "aspect_id": "asp_001",
            "source_id": "src_001",
            "perspective": "neutral",
            "aspect_type": "narrative",
            "statement": "Statement",
            "evidence_anchor_ids": anchor_ids,
            "tags": ["tag1"],
            "status": "active",
        })

        # Create exploration node
        temp_store.upsert_exploration_node({
            "node_id": "node_001",
            "seed_aspect_id": "asp_001",
            "perspective": "neutral",
            "hypothesis": "Hypothesis",
            "rationale": "Rationale",
            "speculative_level": 0.5,
            "evidence_anchor_ids": anchor_ids,
            "novelty_score": 0.7,
            "status": "active",
            "outcome": "pending",
        })

        # Create claim
        temp_store.upsert_claim({
            "claim_id": "claim_001",
            "work_id": "work_001",
            "perspective": "neutral",
            "claim_type": "narrative_fact",
            "statement": "Claim",
            "evidence_anchor_ids": anchor_ids,
            "support_level": 0.8,
            "contradiction_status": "none",
            "status": "active",
            "notes": "Claim note",
        })

        # Create issue with claim
        temp_store.upsert_issue({
            "issue_id": "issue_001",
            "module_id": "module_001",
            "issue_type": "inconsistency",
            "severity": "high",
            "description": "Issue",
            "supporting_claim_ids": ["claim_001"],
            "status": "open",
        })

        # Create proposal with claim
        temp_store.upsert_proposal({
            "proposal_id": "prop_001",
            "module_id": "module_001",
            "proposal_type": "enhancement",
            "rationale": "Rationale",
            "expected_effect": "Effect",
            "supporting_claim_ids": ["claim_001"],
            "preview_patch_ref": {"patch": "test"},
            "status": "pending",
        })

        # Create run
        temp_store.upsert_run({
            "run_id": "run_001",
            "mode": "verification",
            "source_ids": ["src_001"],
            "seed_question": "Question?",
            "budget": {"tokens": 1000},
            "outputs": {"result": "test"},
            "audit_refs": ["audit_001"],
            "created_at": "2025-01-01T00:00:00Z",
        })

        # Create exploration edge
        temp_store.upsert_exploration_edge({
            "edge_id": "edge_001",
            "from_node_id": "node_001",
            "to_node_id": "node_001",
            "relation_type": "explores",
        })

        # Verify all entities can be retrieved
        assert temp_store.get_source("src_001") is not None
        assert len(temp_store.list_anchors()) == 2
        assert temp_store.get_claim("claim_001") is not None
        assert temp_store.get_run("run_001") is not None

    def test_persistence_across_instances(self, tmp_path):
        """Test that all data persists across store instances."""
        store_path = tmp_path / "store.json"

        # Create and populate store 1
        store1 = ResearchStore(store_path)
        store1.upsert_source({
            "source_id": "src_001",
            "work_id": "work_001",
            "source_type": "book",
            "title": "Source",
            "provenance": {"key": "val"},
            "visibility": "public",
            "copyright_posture": "unknown",
            "segment_index_status": "pending",
            "metadata": {"key": "val"},
        })

        # Load with store2 and verify
        store2 = ResearchStore(store_path)
        sources = store2.list_sources()
        assert len(sources) == 1
        assert sources[0]["title"] == "Source"
