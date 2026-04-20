"""Lightweight smoke tests for contract documents and canonical schemas."""

import json
from pathlib import Path


class TestContractDocs:
    """Validate contract documents exist and are non-empty."""

    def test_mvp_definition_exists(self):
        path = Path(__file__).parent.parent.parent / "docs" / "architecture" / "mvp_definition.md"
        assert path.exists(), f"mvp_definition.md not found at {path}"
        assert path.stat().st_size > 500, "mvp_definition.md is too small or empty"

    def test_god_of_carnage_contract_exists(self):
        path = Path(__file__).parent.parent.parent / "docs" / "architecture" / "god_of_carnage_module_contract.md"
        assert path.exists(), f"god_of_carnage_module_contract.md not found at {path}"
        assert path.stat().st_size > 500, "god_of_carnage_module_contract.md is too small or empty"

    def test_ai_story_contract_exists(self):
        path = Path(__file__).parent.parent.parent / "docs" / "architecture" / "ai_story_contract.md"
        assert path.exists(), f"ai_story_contract.md not found at {path}"
        assert path.stat().st_size > 500, "ai_story_contract.md is too small or empty"

    def test_session_runtime_contract_exists(self):
        path = Path(__file__).parent.parent.parent / "docs" / "architecture" / "session_runtime_contract.md"
        assert path.exists(), f"session_runtime_contract.md not found at {path}"
        assert path.stat().st_size > 500, "session_runtime_contract.md is too small or empty"


class TestSchemas:
    """Validate canonical schema files exist and are well-formed JSON."""

    def _load_schema(self, schema_name):
        path = Path(__file__).parent.parent.parent / "schemas" / schema_name
        assert path.exists(), f"Schema {schema_name} not found at {path}"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _assert_schema_valid(self, schema, require_required=True):
        assert "$schema" in schema, "Schema missing $schema field"
        assert "title" in schema, "Schema missing title field"
        assert "type" in schema, "Schema missing type field"
        if require_required:
            assert "required" in schema, "Schema missing required field"
            assert isinstance(schema["required"], list), "required must be an array"
        assert "properties" in schema, "Schema missing properties field"
        assert isinstance(schema["properties"], dict), "properties must be an object"

    def test_content_module_schema_exists(self):
        schema = self._load_schema("content_module.schema.json")
        self._assert_schema_valid(schema)
        assert "module_id" in schema["required"], "content_module.schema.json missing module_id in required"
        assert "characters" in schema["required"], "content_module.schema.json missing characters in required"

    def test_ai_story_output_schema_exists(self):
        schema = self._load_schema("ai_story_output.schema.json")
        self._assert_schema_valid(schema)
        required = schema["required"]
        assert "scene_interpretation" in required, "ai_story_output.schema.json missing scene_interpretation"
        assert "detected_triggers" in required, "ai_story_output.schema.json missing detected_triggers"
        assert "proposed_state_deltas" in required, "ai_story_output.schema.json missing proposed_state_deltas"
        assert "dialogue_impulses" in required, "ai_story_output.schema.json missing dialogue_impulses"
        assert "conflict_vector" in required, "ai_story_output.schema.json missing conflict_vector"

    def test_session_state_schema_exists(self):
        schema = self._load_schema("session_state.schema.json")
        self._assert_schema_valid(schema)
        required = schema["required"]
        assert "session_id" in required, "session_state.schema.json missing session_id"
        assert "module_id" in required, "session_state.schema.json missing module_id"
        assert "current_scene" in required, "session_state.schema.json missing current_scene"
        assert "turn_number" in required, "session_state.schema.json missing turn_number"
        assert "session_active" in required, "session_state.schema.json missing session_active"

    def test_state_delta_schema_exists(self):
        schema = self._load_schema("state_delta.schema.json")
        self._assert_schema_valid(schema, require_required=False)
        assert schema["type"] == "object", "state_delta.schema.json type must be object"
        assert "additionalProperties" in schema, "state_delta.schema.json missing additionalProperties"
