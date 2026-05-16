from __future__ import annotations

import json
from pathlib import Path

from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from ai_stack import ContextRetriever, RagIngestionPipeline
from ai_stack.langchain_integration import (
    build_capability_tool_bridge,
    build_langchain_retriever_bridge,
    bridges,
    invoke_runtime_adapter_with_langchain,
    invoke_writers_room_adapter_with_langchain,
)


class JsonAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content='{"narrative_response":"ok","proposed_scene_id":"scene_2","intent_summary":"advance"}',
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class WritersRoomJsonAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content=(
                '{"review_notes":"Canon alignment looks sound.","recommendations":'
                '["Tighten beat three","Check door continuity"]}'
            ),
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class NonJsonSuccessAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content="plain text, not json",
            success=True,
            metadata={"adapter": self.adapter_name},
        )


class ActorSchemaJsonAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content=(
                '{"narration_summary":"The room tightens around Annette\'s reply.",'
                '"narrative_response":"The room tightens around Annette\'s reply.",'
                '"primary_responder_id":"annette_reille",'
                '"secondary_responder_ids":["alain_reille"],'
                '"spoken_lines":[{"speaker_id":"annette_reille","text":"Enough.","tone":"cutting"}],'
                '"action_lines":[{"actor_id":"annette_reille","text":"She leans toward the table."}],'
                '"initiative_events":[{"actor_id":"annette_reille","type":"interrupt","reason":"pressure spike"}],'
                '"state_effects":[{"effect_type":"pressure_shift","target":"scene","value":"escalated"}],'
                '"proposed_scene_id":"scene_2",'
                '"intent_summary":"Annette seizes initiative"}'
            ),
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class LegacyResponderScopeAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content=(
                '{"narration_summary":"Annette answers with clipped precision.",'
                '"responder_id":"annette_reille",'
                '"responder_actor_ids":["annette_reille","alain_reille"],'
                '"spoken_lines":[{"speaker_id":"annette_reille","text":"No."}],'
                '"proposed_scene_id":"scene_2"}'
            ),
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class NarrationSummaryListAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": ["Intro beat one.", "Role anchor two.", "Scene setup three."],
            "narrative_response": "Intro beat one.\n\nRole anchor two.\n\nScene setup three.",
            "primary_responder_id": "veronique_vallon",
            "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "Welcome."}],
            "action_lines": [],
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class NarrationSummaryJsonStringListAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "schema_version": "runtime_actor_turn_v1",
            "narration_summary": '["A beat", "B beat", "C beat"]',
            "primary_responder_id": "veronique_vallon",
            "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "Hi."}],
            "action_lines": [],
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name, "prompt_length": len(prompt)},
        )


class RecordingCapabilityRegistry:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def invoke(self, *, name: str, mode: str, actor: str, payload: dict) -> dict:
        self.calls.append({"name": name, "mode": mode, "actor": actor, "payload": payload})
        return {"ok": True, "payload": payload}


def test_langchain_prompt_templates_are_module_singletons() -> None:
    rt = bridges._RUNTIME_PROMPT_TEMPLATE
    wr = bridges._WRITERS_ROOM_PROMPT_TEMPLATE
    adapter = JsonAdapter()
    invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="x",
        interpreted_input={"kind": "speech"},
        retrieval_context="ctx",
        timeout_seconds=5.0,
    )
    assert bridges._RUNTIME_PROMPT_TEMPLATE is rt
    wadapter = WritersRoomJsonAdapter()
    invoke_writers_room_adapter_with_langchain(
        adapter=wadapter,
        module_id="m",
        focus="f",
        retrieval_context="c",
        timeout_seconds=5.0,
    )
    assert bridges._WRITERS_ROOM_PROMPT_TEMPLATE is wr


def test_langchain_runtime_invocation_parses_structured_output() -> None:
    adapter = JsonAdapter()
    result = invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="I move to scene_2",
        interpreted_input={"kind": "action"},
        retrieval_context="scene context",
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is not None
    assert result.parsed_output.proposed_scene_id == "scene_2"
    assert result.parser_error is None


def test_langchain_runtime_invocation_parses_actor_level_schema_fields() -> None:
    adapter = ActorSchemaJsonAdapter()
    result = invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="I keep my answer short.",
        interpreted_input={"kind": "speech"},
        retrieval_context="high-pressure dinner argument",
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is not None
    assert result.parsed_output.narration_summary == "The room tightens around Annette's reply."
    assert result.parsed_output.effective_narration_summary() == "The room tightens around Annette's reply."
    assert result.parsed_output.primary_responder_id == "annette_reille"
    assert result.parsed_output.secondary_responder_ids == ["alain_reille"]
    assert result.parsed_output.spoken_lines
    first_spoken = result.parsed_output.spoken_lines[0]
    if isinstance(first_spoken, str):
        assert "Enough." in first_spoken
    else:
        assert first_spoken.text == "Enough."
    assert result.parsed_output.action_lines
    first_action = result.parsed_output.action_lines[0]
    if isinstance(first_action, str):
        assert "leans toward the table" in first_action
    else:
        assert first_action.text == "She leans toward the table."
    assert result.parsed_output.initiative_events[0].type == "interrupt"
    assert result.parsed_output.state_effects[0].effect_type == "pressure_shift"
    assert result.parser_error is None


def test_runtime_structured_output_preserves_opening_gate_evidence() -> None:
    payload = {
        "schema_version": "runtime_actor_turn_v1",
        "narration_summary": ["A park incident.", "The adults meet.", "The room waits."],
        "opening_event_ids": ["event_01_triggering_incident", "event_02_adult_consequence"],
        "opening_must_establish_coverage": ["triggering_incident", "adult_consequence"],
        "opening_render_policy_evidence": {"summary_only": False},
        "runtime_gate_detections": [],
        "spoken_lines": [],
        "action_lines": [],
    }

    parsed = bridges.RuntimeTurnStructuredOutput.model_validate(payload)
    dumped = parsed.model_dump(mode="json")

    assert dumped["opening_event_ids"] == [
        "event_01_triggering_incident",
        "event_02_adult_consequence",
    ]
    assert dumped["opening_must_establish_coverage"] == [
        "triggering_incident",
        "adult_consequence",
    ]
    assert dumped["opening_render_policy_evidence"] == {"summary_only": False}


def test_langchain_runtime_invocation_normalizes_legacy_and_new_responder_fields() -> None:
    adapter = LegacyResponderScopeAdapter()
    result = invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="I keep still.",
        interpreted_input={"kind": "silence"},
        retrieval_context="continuity context",
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is not None
    assert result.parsed_output.narration_summary == "Annette answers with clipped precision."
    assert result.parsed_output.narrative_response == "Annette answers with clipped precision."
    assert result.parsed_output.primary_responder_id == "annette_reille"
    assert result.parsed_output.responder_id == "annette_reille"
    assert result.parsed_output.secondary_responder_ids == ["alain_reille"]


def test_langchain_writers_room_invocation_parses_structured_output() -> None:
    adapter = WritersRoomJsonAdapter()
    result = invoke_writers_room_adapter_with_langchain(
        adapter=adapter,
        module_id="god_of_carnage",
        focus="canon",
        retrieval_context="scene notes",
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is not None
    assert "Canon" in result.parsed_output.review_notes
    assert "Tighten beat three" in result.parsed_output.recommendations
    assert result.parser_error is None


def test_langchain_writers_room_invocation_keeps_raw_content_on_parser_error() -> None:
    adapter = NonJsonSuccessAdapter()
    result = invoke_writers_room_adapter_with_langchain(
        adapter=adapter,
        module_id="m1",
        focus="structure",
        retrieval_context=None,
        timeout_seconds=5.0,
    )
    assert result.call.success is True
    assert result.parsed_output is None
    assert result.parser_error
    assert result.call.content == "plain text, not json"


def test_langchain_retriever_bridge_returns_documents(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage retriever bridge context.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = bridge.get_runtime_documents(query="carnage context", module_id="god_of_carnage", max_chunks=2)
    assert docs
    assert docs[0].metadata.get("source_path")
    assert docs[0].metadata.get("chunk_id")
    assert docs[0].metadata.get("source_version")
    assert docs[0].metadata.get("index_version")


def test_langchain_retriever_bridge_writers_room_domain(tmp_path: Path) -> None:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Writers room canon review corpus line.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = bridge.get_writers_room_documents(
        query="canon review",
        module_id="god_of_carnage",
        max_chunks=2,
    )
    assert docs
    assert docs[0].metadata.get("domain") == "writers_room"


def test_langchain_tool_bridge_invokes_capability_registry() -> None:
    registry = RecordingCapabilityRegistry()
    tool = build_capability_tool_bridge(
        capability_registry=registry,
        capability_name="wos.review_bundle.build",
        mode="writers_room",
        actor="writers_room:test",
    )
    result = tool.invoke(
        {
            "module_id": "god_of_carnage",
            "summary": "s",
            "recommendations": ["r1"],
            "evidence_sources": ["content/god_of_carnage.md"],
        }
    )
    assert result["ok"] is True
    assert registry.calls
    assert registry.calls[-1]["name"] == "wos.review_bundle.build"


def test_all_three_bridge_types_are_functional_in_same_run(tmp_path: Path) -> None:
    """Cross-path test: proves runtime adapter, retriever, and capability bridges all work together."""
    # 1. runtime adapter bridge
    adapter = JsonAdapter()
    runtime_result = invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="I push the door open",
        interpreted_input={"kind": "movement"},
        retrieval_context="scene_1 context: a locked corridor",
        timeout_seconds=5.0,
    )
    assert runtime_result.call.success is True
    assert runtime_result.parsed_output is not None
    assert runtime_result.parser_error is None

    # 2. retriever bridge
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage corridor conflict scene.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever_bridge = build_langchain_retriever_bridge(ContextRetriever(corpus))
    docs = retriever_bridge.get_runtime_documents(query="corridor conflict", module_id="god_of_carnage", max_chunks=2)
    assert docs
    assert docs[0].metadata.get("source_path")

    # 3. capability tool bridge
    registry = RecordingCapabilityRegistry()
    tool = build_capability_tool_bridge(
        capability_registry=registry,
        capability_name="wos.review_bundle.build",
        mode="improvement",
        actor="improvement:test",
    )
    cap_result = tool.invoke(
        {
            "module_id": "god_of_carnage",
            "summary": "corridor scene tension",
            "recommendations": ["slow pacing"],
            "evidence_sources": ["content/god_of_carnage.md"],
        }
    )
    assert cap_result["ok"] is True
    assert registry.calls[-1]["name"] == "wos.review_bundle.build"


# ---------------------------------------------------------------------------
# PARSER-ROBUSTNESS-01 — model-family fixtures and tolerant-parse tests
# ---------------------------------------------------------------------------

def _full_actor_output_json(**overrides) -> str:
    """Base clean structured output dict, serialised to JSON."""
    base = {
        "schema_version": "runtime_actor_turn_v1",
        "narration_summary": "Véronique breaks the silence in the Paris salon.",
        "narrative_response": "Véronique breaks the silence in the Paris salon.",
        "primary_responder_id": "veronique_vallon",
        "secondary_responder_ids": ["michel_longstreet"],
        "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "Let us be direct.", "tone": "firm"}],
        "action_lines": [{"actor_id": "michel_longstreet", "text": "folds his hands on the table"}],
        "initiative_events": [{"actor_id": "veronique_vallon", "type": "interrupt", "reason": "pressure spike"}],
        "state_effects": [{"effect_type": "pressure_shift", "target": "scene", "value": "escalated"}],
        "proposed_scene_id": "scene_1",
    }
    base.update(overrides)
    return json.dumps(base)


class Gpt5StyleCleanAdapter(BaseModelAdapter):
    """Simulates GPT-5.x: clean JSON, no markdown, no deviations."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        return ModelCallResult(content=_full_actor_output_json(), success=True, metadata={"adapter": "openai"})


class Gpt4MiniMarkdownFenceAdapter(BaseModelAdapter):
    """Simulates GPT-4.1-mini: valid JSON wrapped in a markdown code fence."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        content = (
            "Here is the structured actor output:\n\n"
            "```json\n"
            + _full_actor_output_json()
            + "\n```\n\n"
            "I hope this helps with the scene."
        )
        return ModelCallResult(content=content, success=True, metadata={"adapter": "openai"})


class Gpt4MiniProseBeforeJsonAdapter(BaseModelAdapter):
    """Simulates GPT-4.1-mini: prose prefix, then bare JSON (no fence)."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        content = "Generating actor response for the opening turn.\n\n" + _full_actor_output_json()
        return ModelCallResult(content=content, success=True, metadata={"adapter": "openai"})


class Gpt4MiniStringSpokenLinesAdapter(BaseModelAdapter):
    """Simulates GPT-4.1-mini: spoken_lines returned as a JSON-serialised string instead of list."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        data = json.loads(_full_actor_output_json())
        data["spoken_lines"] = json.dumps(data["spoken_lines"])  # stringified list
        data["action_lines"] = json.dumps(data["action_lines"])  # stringified list too
        return ModelCallResult(content=json.dumps(data), success=True, metadata={"adapter": "openai"})


class MissingSchemaVersionAdapter(BaseModelAdapter):
    """Simulates output where schema_version is absent but structure clearly matches."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        data = json.loads(_full_actor_output_json())
        del data["schema_version"]
        return ModelCallResult(content=json.dumps(data), success=True, metadata={"adapter": "openai"})


class MissingNarrationSummaryAdapter(BaseModelAdapter):
    """Simulates output with approved actor lanes but no narration_summary."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        data = json.loads(_full_actor_output_json())
        data["narration_summary"] = ""
        data["narrative_response"] = ""
        return ModelCallResult(content=json.dumps(data), success=True, metadata={"adapter": "openai"})


class MalformedJsonAdapter(BaseModelAdapter):
    """Simulates output that is structurally unrecoverable — must still fail."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        return ModelCallResult(
            content='This is a spoken line by Veronique. She says: {broken json here...',
            success=True,
            metadata={"adapter": "openai"},
        )


class ActorLaneViolationAdapter(BaseModelAdapter):
    """Simulates valid JSON where the human actor appears as AI responder — parser should accept,
    actor_lane_validation (downstream) must reject."""
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context=None) -> ModelCallResult:
        data = json.loads(_full_actor_output_json())
        data["primary_responder_id"] = "annette_reille"  # human actor — forbidden for AI
        data["spoken_lines"] = [{"speaker_id": "annette_reille", "text": "I agree with you."}]
        return ModelCallResult(content=json.dumps(data), success=True, metadata={"adapter": "openai"})


def _invoke(adapter):
    return invoke_runtime_adapter_with_langchain(
        adapter=adapter,
        player_input="The room waits.",
        interpreted_input={"kind": "silence"},
        retrieval_context="Paris salon, two couples, unresolved blame.",
        timeout_seconds=5.0,
    )


# --- Fixture tests ---

def test_PR01_gpt5_style_clean_output_passes_without_repair() -> None:
    """PARSER-ROBUSTNESS-01: GPT-5.x style clean JSON parses with empty repair_log."""
    result = _invoke(Gpt5StyleCleanAdapter())
    assert result.parsed_output is not None
    assert result.parser_error is None
    assert result.repair_log == [], f"Expected no repairs, got: {result.repair_log}"
    assert result.parsed_output.primary_responder_id == "veronique_vallon"
    assert result.parsed_output.spoken_lines


def test_PR01_gpt4_mini_markdown_fence_repaired_and_passes() -> None:
    """PARSER-ROBUSTNESS-01: JSON inside markdown fence parses cleanly.

    LangChain's PydanticOutputParser.parse() handles markdown fences natively via
    parse_json_markdown, so the fast path succeeds without repair_log entries.
    """
    result = _invoke(Gpt4MiniMarkdownFenceAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    assert result.parsed_output.primary_responder_id == "veronique_vallon"
    assert result.parsed_output.narration_summary


def test_PR01_gpt4_mini_prose_before_json_repaired_and_passes() -> None:
    """PARSER-ROBUSTNESS-01: JSON with prose prefix is extracted and parsed successfully."""
    result = _invoke(Gpt4MiniProseBeforeJsonAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    assert "extracted_from_prose_context" in result.repair_log
    assert result.parsed_output.primary_responder_id == "veronique_vallon"


def test_PR01_gpt4_mini_string_spoken_lines_repaired_and_passes() -> None:
    """PARSER-ROBUSTNESS-01: spoken_lines/action_lines as JSON strings are coerced to lists."""
    result = _invoke(Gpt4MiniStringSpokenLinesAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    assert any("coerced_str_to_list:spoken_lines" in r for r in result.repair_log)
    assert any("coerced_str_to_list:action_lines" in r for r in result.repair_log)
    assert result.parsed_output.spoken_lines


def test_PR01_missing_schema_version_defaulted_and_passes() -> None:
    """PARSER-ROBUSTNESS-01: schema_version absent → Pydantic default fills it on fast path.

    RuntimeTurnStructuredOutput.schema_version has default="runtime_actor_turn_v1",
    so PydanticOutputParser handles this without the tolerant repair path.
    """
    result = _invoke(MissingSchemaVersionAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    assert result.parsed_output.schema_version == "runtime_actor_turn_v1"


def test_PR01_missing_narration_summary_parses_with_actor_lanes() -> None:
    """PARSER-ROBUSTNESS-01: empty narration_summary with actor lanes parses — downstream synthesis handles it."""
    result = _invoke(MissingNarrationSummaryAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    # narration_summary defaults to "" — Pydantic model allows this
    assert result.parsed_output.narration_summary == ""
    assert result.parsed_output.spoken_lines  # actor lanes present


def test_PR01_narration_summary_native_list_parses() -> None:
    """Opening-friendly: narration_summary may be a JSON array of strings."""
    result = _invoke(NarrationSummaryListAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    assert isinstance(result.parsed_output.narration_summary, list)
    assert len(result.parsed_output.narration_summary) == 3
    assert "Intro beat one." in result.parsed_output.effective_narration_summary()


def test_PR01_narration_summary_json_string_list_coerced() -> None:
    """Tolerant path: narration_summary as a JSON-encoded string array is coerced to list."""
    result = _invoke(NarrationSummaryJsonStringListAdapter())
    assert result.parsed_output is not None, f"Parse failed: {result.parser_error}"
    assert result.parser_error is None
    assert isinstance(result.parsed_output.narration_summary, list)
    assert result.parsed_output.narration_summary[0] == "A beat"
    assert any("coerced_str_to_list:narration_summary" in r for r in result.repair_log)


def test_PR01_malformed_json_still_fails_with_parser_error() -> None:
    """PARSER-ROBUSTNESS-01: structurally unrecoverable output must still return parser_error."""
    result = _invoke(MalformedJsonAdapter())
    assert result.parsed_output is None
    assert result.parser_error is not None
    assert result.repair_log == []  # no repairs succeeded


def test_PR01_repair_log_empty_on_clean_parse() -> None:
    """PARSER-ROBUSTNESS-01: repair_log is empty on unrepaired (fast-path) parse."""
    result = _invoke(ActorSchemaJsonAdapter())  # existing clean fixture
    assert result.parser_error is None
    assert result.repair_log == []


def test_PR01_actor_lane_violation_parses_structurally_parser_does_not_repair_semantics() -> None:
    """PARSER-ROBUSTNESS-01: actor-lane violations are not filtered or repaired by the parser.

    The parser's job is structural: parse valid JSON into a Pydantic object.
    Semantic constraints (forbidden human actor in AI slot) are enforced downstream
    by actor_lane_validation in validate_seam. The parser must not attempt to
    substitute or drop actor IDs.
    """
    result = _invoke(ActorLaneViolationAdapter())
    assert result.parsed_output is not None, "Parser must accept structurally valid output"
    assert result.parser_error is None
    # The violation is preserved as-is — actor_lane_validation will catch it
    assert result.parsed_output.primary_responder_id == "annette_reille"
    assert result.repair_log == []  # no repair attempted; the JSON was clean
