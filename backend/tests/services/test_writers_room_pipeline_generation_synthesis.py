"""Tests for writers_room_pipeline_generation_synthesis.py - Generation synthesis routing."""
from unittest.mock import MagicMock, patch
import pytest

from app.services.writers_room.writers_room_pipeline_generation_synthesis import (
    _norm_wr_adapter,
    route_synthesis_and_build_generation_shell,
    fill_generation_from_primary_adapter,
    apply_generation_mock_fallback,
    attach_synthesis_routing_evidence,
)
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    TaskKind,
    WorkflowPhase,
)


class TestNormWrAdapter:
    """Tests for _norm_wr_adapter function."""

    def test_norm_adapter_simple(self):
        """Test normalizing simple adapter name."""
        result = _norm_wr_adapter("MyAdapter")
        assert result == "myadapter"

    def test_norm_adapter_with_spaces(self):
        """Test normalizing adapter with spaces."""
        result = _norm_wr_adapter("  MyAdapter  ")
        assert result == "myadapter"

    def test_norm_adapter_none(self):
        """Test normalizing None."""
        result = _norm_wr_adapter(None)
        assert result == ""

    def test_norm_adapter_empty(self):
        """Test normalizing empty string."""
        result = _norm_wr_adapter("")
        assert result == ""

    def test_norm_adapter_mixed_case(self):
        """Test normalizing mixed case."""
        result = _norm_wr_adapter("MiXeD_CaSe_AdApTeR")
        assert result == "mixed_case_adapter"


class TestRouteSynthesisAndBuildGenerationShell:
    """Tests for route_synthesis_and_build_generation_shell function."""

    def test_route_synthesis_basic(self):
        """Test basic synthesis routing and generation shell building."""
        specs = [
            MagicMock(adapter_name="adapter1"),
            MagicMock(adapter_name="adapter2"),
        ]
        preflight_trace = {"preflight": "data"}

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.route_model") as mock_route:
            mock_decision = MagicMock()
            mock_decision.selected_adapter_name = "adapter1"
            mock_decision.model_dump.return_value = {"decision": "data"}
            mock_route.return_value = mock_decision

            syn_decision, syn_req, syn_trace, generation = route_synthesis_and_build_generation_shell(
                specs=specs,
                preflight_trace=preflight_trace,
            )

            assert syn_decision == mock_decision
            assert syn_trace["stage"] == "synthesis"
            assert syn_trace["workflow_phase"] == WorkflowPhase.generation.value
            assert syn_trace["task_kind"] == TaskKind.narrative_formulation.value
            assert generation["provider"] == "adapter1"
            assert generation["success"] is False
            assert generation["content"] == ""
            assert "preflight" in generation["task_2a_routing"]
            assert "synthesis" in generation["task_2a_routing"]

    def test_route_synthesis_no_adapter_defaults_to_mock(self):
        """Test that missing adapter defaults to mock."""
        specs = []
        preflight_trace = {}

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.route_model") as mock_route:
            mock_decision = MagicMock()
            mock_decision.selected_adapter_name = None
            mock_decision.model_dump.return_value = {}
            mock_route.return_value = mock_decision

            syn_decision, syn_req, syn_trace, generation = route_synthesis_and_build_generation_shell(
                specs=specs,
                preflight_trace=preflight_trace,
            )

            assert generation["provider"] == "mock"


class TestFillGenerationFromPrimaryAdapter:
    """Tests for fill_generation_from_primary_adapter function."""

    def test_fill_no_adapter(self):
        """Test when adapter is not available."""
        generation = {"success": False, "error": None}

        fill_generation_from_primary_adapter(
            generation=generation,
            adapter=None,
            module_id="mod1",
            focus="focus1",
            retrieval_text="text",
            selected_provider="provider1",
        )

        assert generation["error"] == "adapter_not_registered:provider1"
        assert generation["raw_fallback_reason"] == "primary_adapter_missing"
        assert generation["success"] is False

    def test_fill_with_successful_adapter(self):
        """Test with successful adapter invocation."""
        generation = {"success": False, "error": None, "metadata": {}}
        mock_adapter = MagicMock()

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.invoke_writers_room_adapter_with_langchain") as mock_invoke:
            mock_result = MagicMock()
            mock_result.call.success = True
            mock_result.call.content = "Generated content"
            mock_result.call.metadata = {}
            mock_result.parsed_output = None
            mock_result.parser_error = None
            mock_invoke.return_value = mock_result

            fill_generation_from_primary_adapter(
                generation=generation,
                adapter=mock_adapter,
                module_id="mod1",
                focus="focus1",
                retrieval_text="text",
                selected_provider="provider1",
            )

            assert generation["success"] is True
            assert generation["error"] is None
            assert generation["content"] == "Generated content"
            assert generation["adapter_invocation_mode"] == "langchain_structured_primary"

    def test_fill_with_structured_output(self):
        """Test with structured output from adapter."""
        generation = {"success": False, "error": None, "metadata": {}}
        mock_adapter = MagicMock()

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.invoke_writers_room_adapter_with_langchain") as mock_invoke:
            mock_parsed = MagicMock()
            mock_parsed.review_notes = "Review notes"
            mock_parsed.model_dump.return_value = {"structured": "data"}

            mock_result = MagicMock()
            mock_result.call.success = True
            mock_result.call.content = "Content"
            mock_result.parsed_output = mock_parsed
            mock_invoke.return_value = mock_result

            fill_generation_from_primary_adapter(
                generation=generation,
                adapter=mock_adapter,
                module_id="mod1",
                focus="focus1",
                retrieval_text="text",
                selected_provider="provider1",
            )

            assert generation["success"] is True
            assert generation["content"] == "Review notes"
            assert "structured_output" in generation["metadata"]

    def test_fill_with_failed_adapter(self):
        """Test with failed adapter invocation."""
        generation = {"success": False, "error": None, "metadata": {}}
        mock_adapter = MagicMock()

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.invoke_writers_room_adapter_with_langchain") as mock_invoke:
            mock_result = MagicMock()
            mock_result.call.success = False
            mock_result.call.metadata = {"error": "Adapter error"}
            mock_result.parsed_output = None
            mock_result.parser_error = "Parser error"
            mock_invoke.return_value = mock_result

            fill_generation_from_primary_adapter(
                generation=generation,
                adapter=mock_adapter,
                module_id="mod1",
                focus="focus1",
                retrieval_text="text",
                selected_provider="provider1",
            )

            assert generation["success"] is False
            assert generation["error"] == "Adapter error"


class TestApplyGenerationMockFallback:
    """Tests for apply_generation_mock_fallback function."""

    def test_fallback_when_success(self):
        """Test that fallback is skipped when generation already succeeded."""
        generation = {"success": True, "content": "Already successful"}
        adapters = {"mock": MagicMock()}

        apply_generation_mock_fallback(
            generation=generation,
            adapters=adapters,
            module_id="mod1",
            focus="focus1",
            retrieval_text="text",
        )

        # Generation should not be modified
        assert generation["success"] is True
        assert generation["content"] == "Already successful"

    def test_fallback_with_mock_adapter_available(self):
        """Test fallback when mock adapter is available."""
        generation = {
            "success": False,
            "content": "",
            "provider": "primary",
            "error": None,
        }
        mock_adapter = MagicMock()
        mock_call = MagicMock()
        mock_call.success = True
        mock_call.content = "Fallback content"
        mock_call.metadata = {}
        mock_adapter.generate.return_value = mock_call
        adapters = {"mock": mock_adapter}

        apply_generation_mock_fallback(
            generation=generation,
            adapters=adapters,
            module_id="mod1",
            focus="focus1",
            retrieval_text="text",
        )

        assert generation["provider"] == "mock"
        assert generation["success"] is True
        assert generation["content"] == "Fallback content"
        assert generation["adapter_invocation_mode"] == "raw_adapter_fallback"
        assert generation["raw_fallback_reason"] is not None

    def test_fallback_without_mock_adapter(self):
        """Test fallback when mock adapter is not available."""
        generation = {
            "success": False,
            "content": "",
            "error": None,
        }
        adapters = {}

        apply_generation_mock_fallback(
            generation=generation,
            adapters=adapters,
            module_id="mod1",
            focus="focus1",
            retrieval_text="text",
        )

        # Generation should not be modified if no mock adapter
        assert generation["success"] is False

    def test_fallback_with_failed_mock(self):
        """Test fallback when mock adapter also fails."""
        generation = {
            "success": False,
            "content": "",
            "error": "Primary failed",
            "raw_fallback_reason": None,
        }
        mock_adapter = MagicMock()
        mock_call = MagicMock()
        mock_call.success = False
        mock_call.content = ""
        mock_call.metadata = {"error": "Mock also failed"}
        mock_adapter.generate.return_value = mock_call
        adapters = {"mock": mock_adapter}

        apply_generation_mock_fallback(
            generation=generation,
            adapters=adapters,
            module_id="mod1",
            focus="focus1",
            retrieval_text="text",
        )

        assert generation["provider"] == "mock"
        assert generation["success"] is False
        assert generation["error"] == "Mock also failed"


class TestAttachSynthesisRoutingEvidence:
    """Tests for attach_synthesis_routing_evidence function."""

    def test_attach_evidence_matching_adapters(self):
        """Test attaching evidence when executed and routed adapters match."""
        generation = {
            "provider": "adapter1",
            "adapter_invocation_mode": "langchain_structured_primary",
            "raw_fallback_reason": None,
            "task_2a_routing": {"synthesis": {}},
        }
        syn_req = MagicMock()
        syn_decision = MagicMock()
        syn_decision.selected_adapter_name = "Adapter1"

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.attach_stage_routing_evidence") as mock_attach:
            attach_synthesis_routing_evidence(
                generation=generation,
                synthesis_req=syn_req,
                syn_decision=syn_decision,
            )

            mock_attach.assert_called_once()
            # Verify execution_deviation_note is None when adapters match
            call_args = mock_attach.call_args
            assert call_args[1]["execution_deviation_note"] is None

    def test_attach_evidence_mismatched_adapters(self):
        """Test attaching evidence when adapters differ."""
        generation = {
            "provider": "adapter1",
            "adapter_invocation_mode": "raw_adapter_fallback",
            "raw_fallback_reason": "primary_failed",
            "task_2a_routing": {"synthesis": {}},
        }
        syn_req = MagicMock()
        syn_decision = MagicMock()
        syn_decision.selected_adapter_name = "Adapter2"

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.attach_stage_routing_evidence") as mock_attach:
            attach_synthesis_routing_evidence(
                generation=generation,
                synthesis_req=syn_req,
                syn_decision=syn_decision,
            )

            mock_attach.assert_called_once()
            # Verify execution_deviation_note contains fallback reason
            call_args = mock_attach.call_args
            assert call_args[1]["execution_deviation_note"] == "primary_failed"

    def test_attach_evidence_no_adapter_executed(self):
        """Test attaching evidence when no adapter was executed."""
        generation = {
            "provider": None,
            "adapter_invocation_mode": None,
            "task_2a_routing": {"synthesis": {}},
        }
        syn_req = MagicMock()
        syn_decision = MagicMock()
        syn_decision.selected_adapter_name = "Adapter1"

        with patch("app.services.writers_room.writers_room_pipeline_generation_synthesis.attach_stage_routing_evidence") as mock_attach:
            attach_synthesis_routing_evidence(
                generation=generation,
                synthesis_req=syn_req,
                syn_decision=syn_decision,
            )

            mock_attach.assert_called_once()
            # Verify executed_adapter_name is None
            call_args = mock_attach.call_args
            assert call_args[1]["executed_adapter_name"] is None
