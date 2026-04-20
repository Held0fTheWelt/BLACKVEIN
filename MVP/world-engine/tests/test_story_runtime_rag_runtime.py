from __future__ import annotations

from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult
from ai_stack import ContextPackAssembler, ContextRetriever, RagIngestionPipeline

from app.story_runtime import StoryRuntimeManager


class CaptureAdapter(BaseModelAdapter):
    adapter_name = "mock"

    def __init__(self) -> None:
        self.last_prompt: str | None = None
        self.last_retrieval_context: str | None = None

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        self.last_prompt = prompt
        self.last_retrieval_context = retrieval_context
        return ModelCallResult(content="ok", success=True, metadata={"adapter": self.adapter_name})


class FailingAdapter(BaseModelAdapter):
    adapter_name = "failing"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(content="", success=False, metadata={"error": "forced_failure"})


def test_story_runtime_retrieval_context_influences_authoritative_turn(tmp_path):
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text(
        "God of Carnage scene where two families argue about their children.",
        encoding="utf-8",
    )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    assert corpus.chunks

    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={"start_scene_id": "scene_1", "scenes": []},
    )
    turn = manager.execute_turn(session_id=session.session_id, player_input="I open the door")

    assert "retrieval" in turn
    assert turn["retrieval"]["domain"] == "runtime"
    assert "status" in turn["retrieval"]
    assert turn["model_route"]["generation"]["retrieval_context_attached"] is True
    assert adapter.last_retrieval_context
    assert any(
        entry["capability_name"] == "wos.context_pack.build"
        for entry in turn["graph"]["capability_audit"]
    )
    repro = turn["graph"].get("repro_metadata") or {}
    assert repro.get("adapter_invocation_mode") == "langchain_structured_primary"
    assert repro.get("graph_path_summary") == "primary_invoke_langchain_only"


def test_story_runtime_graph_uses_fallback_branch_on_model_failure(tmp_path):
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage fallback branch test content.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    retriever = ContextRetriever(corpus)
    assembler = ContextPackAssembler()

    mock_adapter = CaptureAdapter()
    failing_adapter = FailingAdapter()
    manager = StoryRuntimeManager(
        adapters={"openai": failing_adapter, "ollama": failing_adapter, "mock": mock_adapter},
        retriever=retriever,
        context_assembler=assembler,
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={"start_scene_id": "scene_1", "scenes": []},
    )

    turn = manager.execute_turn(session_id=session.session_id, player_input="I escalate the argument")

    assert turn["graph"]["fallback_path_taken"] is True
    assert turn["graph"].get("execution_health") == "model_fallback"
    assert "fallback_model" in turn["graph"]["nodes_executed"]
    assert turn["model_route"]["generation"]["fallback_used"] is True
    repro = turn["graph"].get("repro_metadata") or {}
    assert repro.get("adapter_invocation_mode") == "raw_adapter_graph_managed_fallback"
    assert repro.get("graph_path_summary") == "used_fallback_model_node_raw_adapter"


def test_story_runtime_commits_legal_scene_progression(tmp_path):
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Story progression test corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )

    turn = manager.execute_turn(session_id=session.session_id, player_input="/move scene_2")
    state = manager.get_state(session.session_id)
    diagnostics = manager.get_diagnostics(session.session_id)

    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["committed_scene_id"] == "scene_2"
    assert nc["selected_candidate_source"] == "explicit_command"
    assert state["current_scene_id"] == "scene_2"
    assert diagnostics["diagnostics"][-1]["narrative_commit"]["committed_scene_id"] == "scene_2"


def test_story_runtime_rejects_illegal_scene_progression(tmp_path):
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Illegal progression test corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}, {"id": "scene_3"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )

    turn = manager.execute_turn(session_id=session.session_id, player_input="/move scene_3")
    state = manager.get_state(session.session_id)

    nc = turn["narrative_commit"]
    assert nc["allowed"] is False
    assert nc["commit_reason_code"] == "illegal_transition_not_allowed"
    assert nc["situation_status"] == "blocked"
    assert state["current_scene_id"] == "scene_1"


def test_story_runtime_builds_multi_turn_committed_progression(tmp_path):
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Multi-turn progression test corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}, {"id": "scene_3"}],
            "transition_hints": [
                {"from": "scene_1", "to": "scene_2"},
                {"from": "scene_2", "to": "scene_3"},
            ],
        },
    )

    first_turn = manager.execute_turn(session_id=session.session_id, player_input="/move scene_2")
    second_turn = manager.execute_turn(session_id=session.session_id, player_input="/move scene_3")
    state = manager.get_state(session.session_id)
    diagnostics = manager.get_diagnostics(session.session_id)

    assert first_turn["narrative_commit"]["allowed"] is True
    assert second_turn["narrative_commit"]["allowed"] is True
    assert state["turn_counter"] == 2
    assert state["history_count"] == 2
    assert state["current_scene_id"] == "scene_3"
    assert diagnostics["diagnostics"][-1]["narrative_commit"]["committed_scene_id"] == "scene_3"
    assert "graph" in diagnostics["diagnostics"][-1]
    assert diagnostics["authoritative_history_tail"][-1].get("committed_state_after", {}).get("current_scene_id") == "scene_3"
    assert "graph" not in diagnostics["authoritative_history_tail"][-1]
    assert "narrative_commit" in diagnostics["authoritative_history_tail"][-1]


def test_story_runtime_natural_language_with_scene_token_commits_progression(tmp_path):
    """Test that natural language input with a scene token commits progression correctly.

    Player input: "I cross the room and enter scene_2 to confront them."
    Expected: narrative_commit["allowed"] is True, current_scene_id == "scene_2"
    """
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Natural language progression test corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )

    turn = manager.execute_turn(
        session_id=session.session_id,
        player_input="I cross the room and enter scene_2 to confront them.",
    )
    state = manager.get_state(session.session_id)

    nc = turn["narrative_commit"]
    assert nc["allowed"] is True
    assert nc["committed_scene_id"] == "scene_2"
    assert nc["selected_candidate_source"] == "player_input_token_scan"
    assert state["current_scene_id"] == "scene_2"


def test_story_runtime_natural_language_without_scene_reference_leaves_current_scene_unchanged(tmp_path):
    """Test that natural language input without scene tokens leaves current scene unchanged.

    Player input: "I pause and watch their reactions carefully."
    Expected: narrative_commit commit_reason_code == "no_scene_proposal", current_scene_id unchanged
    """
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("No scene reference test corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )

    turn = manager.execute_turn(
        session_id=session.session_id,
        player_input="I pause and watch their reactions carefully.",
    )
    state = manager.get_state(session.session_id)

    assert turn["narrative_commit"]["commit_reason_code"] == "no_scene_proposal"
    assert state["current_scene_id"] == "scene_1"


def test_story_runtime_natural_language_with_invalid_scene_token_is_rejected_safely(tmp_path):
    """Test that natural language input with invalid scene token is rejected safely.

    Player input: "I try to escape through scene_99 but cannot."
    scene_99 is NOT in the runtime projection scenes.
    Expected: narrative_commit["allowed"] is False, scene stays unchanged
    """
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("Invalid scene token test corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    adapter = CaptureAdapter()
    manager = StoryRuntimeManager(
        adapters={"mock": adapter, "openai": adapter, "ollama": adapter},
        retriever=ContextRetriever(corpus),
        context_assembler=ContextPackAssembler(),
    )
    session = manager.create_session(
        module_id="god_of_carnage",
        runtime_projection={
            "start_scene_id": "scene_1",
            "scenes": [{"id": "scene_1"}, {"id": "scene_2"}],
            "transition_hints": [{"from": "scene_1", "to": "scene_2"}],
        },
    )

    turn = manager.execute_turn(
        session_id=session.session_id,
        player_input="I try to escape through scene_99 but cannot.",
    )
    state = manager.get_state(session.session_id)

    assert turn["narrative_commit"]["allowed"] is False
    assert turn["narrative_commit"]["commit_reason_code"] == "no_scene_proposal"
    assert state["current_scene_id"] == "scene_1"
