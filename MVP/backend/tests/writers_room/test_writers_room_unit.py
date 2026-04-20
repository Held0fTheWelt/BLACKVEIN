"""Unit tests for writers_room_service pure functions and WritersRoomStore."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.services.writers_room_service import (
    _append_workflow_stage,
    _context_fingerprint,
    _langchain_preview_documents_from_context_pack,
    _norm_wr_adapter,
    _workflow_stage_ids,
)


class TestNormWrAdapter:
    """Tests for _norm_wr_adapter."""

    def test_norm_wr_adapter_strips_and_lowercases(self):
        """Strips whitespace and converts to lowercase."""
        assert _norm_wr_adapter("  OpenAI  ") == "openai"
        assert _norm_wr_adapter("ANTHROPIC") == "anthropic"
        assert _norm_wr_adapter("  MixedCase  ") == "mixedcase"

    def test_norm_wr_adapter_handles_none(self):
        """None and empty strings return empty string."""
        assert _norm_wr_adapter(None) == ""
        assert _norm_wr_adapter("") == ""
        assert _norm_wr_adapter("   ") == ""


class TestContextFingerprint:
    """Tests for _context_fingerprint."""

    def test_context_fingerprint_is_deterministic(self):
        """Same context produces same fingerprint."""
        ctx = "The quick brown fox jumps over the lazy dog."
        fp1 = _context_fingerprint(ctx)
        fp2 = _context_fingerprint(ctx)
        assert fp1 == fp2
        assert len(fp1) == 16  # SHA256[:16]

    def test_context_fingerprint_truncates_to_max_bytes(self):
        """Respects max_bytes parameter."""
        long_ctx = "x" * 10000
        fp_small = _context_fingerprint(long_ctx, max_bytes=10)
        fp_large = _context_fingerprint(long_ctx, max_bytes=1000)
        # Different truncation points should produce different fingerprints
        assert fp_small != fp_large

    def test_context_fingerprint_handles_unicode(self):
        """Handles UTF-8 encoding correctly."""
        ctx = "Hëllo wörld 世界 🌍"
        fp = _context_fingerprint(ctx)
        assert len(fp) == 16
        assert isinstance(fp, str)


class TestWorkflowStageIds:
    """Tests for _workflow_stage_ids."""

    def test_workflow_stage_ids_extracts_ids(self):
        """Extracts id from each stage dict."""
        stages = [
            {"id": "stage_1", "completed_at": "2026-01-01T00:00:00"},
            {"id": "stage_2", "completed_at": "2026-01-01T00:00:01"},
        ]
        result = _workflow_stage_ids(stages)
        assert result == ["stage_1", "stage_2"]

    def test_workflow_stage_ids_ignores_non_dict_entries(self):
        """Skips non-dict entries and missing id fields."""
        stages = [
            {"id": "stage_1"},
            "not_a_dict",
            {"completed_at": "2026-01-01T00:00:00"},  # no id
            None,
            {"id": "stage_2"},
        ]
        result = _workflow_stage_ids(stages)
        assert result == ["stage_1", "", "stage_2"]

    def test_workflow_stage_ids_empty_list(self):
        """Empty list returns empty list."""
        assert _workflow_stage_ids([]) == []


class TestAppendWorkflowStage:
    """Tests for _append_workflow_stage."""

    def test_append_workflow_stage_adds_entry_with_timestamp(self):
        """Appends stage with id and completed_at."""
        stages: list[dict] = []
        _append_workflow_stage(stages, stage_id="preflight")
        assert len(stages) == 1
        assert stages[0]["id"] == "preflight"
        assert "completed_at" in stages[0]
        assert "T" in stages[0]["completed_at"]  # ISO format

    def test_append_workflow_stage_includes_artifact_key_when_given(self):
        """Includes artifact_key when provided."""
        stages: list[dict] = []
        _append_workflow_stage(
            stages, stage_id="synthesis", artifact_key="recommendation_123"
        )
        assert len(stages) == 1
        assert stages[0]["artifact_key"] == "recommendation_123"

    def test_append_workflow_stage_omits_artifact_key_when_not_given(self):
        """Does not include artifact_key when not provided."""
        stages: list[dict] = []
        _append_workflow_stage(stages, stage_id="finalization")
        assert "artifact_key" not in stages[0]


class TestLangchainPreviewDocuments:
    """Tests for _langchain_preview_documents_from_context_pack."""

    def test_langchain_preview_documents_from_context_pack_happy_path(self):
        """Builds Document list from valid retrieval sources."""
        context_pack = {
            "sources": [
                {
                    "source_path": "docs/scene_1.txt",
                    "snippet": "Scene 1 content excerpt",
                },
                {
                    "source_path": "docs/scene_2.txt",
                    "snippet": "Scene 2 content excerpt",
                },
            ]
        }
        docs, status = _langchain_preview_documents_from_context_pack(context_pack)
        assert len(docs) > 0
        assert docs[0].metadata["source_path"] == "docs/scene_1.txt"
        assert status == "primary_context_pack"

    def test_langchain_preview_documents_from_context_pack_no_sources_returns_empty(self):
        """Returns empty list and status when sources missing."""
        context_pack = {"metadata": "but no sources"}
        docs, status = _langchain_preview_documents_from_context_pack(context_pack)
        assert docs == []
        assert status == "primary_context_pack_empty"

    def test_langchain_preview_documents_from_context_pack_skips_empty_rows(self):
        """Skips rows with neither source_path nor snippet."""
        context_pack = {
            "sources": [
                {"source_path": "docs/valid1.txt", "snippet": "content1"},
                {"other_field": "value"},  # no source_path or snippet — skipped
                {"source_path": "docs/valid2.txt", "snippet": "content2"},  # not empty
                {"source_path": "", "snippet": ""},  # empty both — skipped
            ]
        }
        # max_chunks defaults to 3, so first 3 sources are checked
        # After filtering: doc1 (valid), skip doc2 (no path/snippet), doc3 (valid)
        docs, status = _langchain_preview_documents_from_context_pack(context_pack)
        assert len(docs) == 2
        assert docs[0].metadata["source_path"] == "docs/valid1.txt"
        assert docs[1].metadata["source_path"] == "docs/valid2.txt"

    def test_langchain_preview_documents_from_context_pack_limits_to_max_chunks(self):
        """Respects max_chunks parameter."""
        context_pack = {
            "sources": [
                {"source_path": f"docs/{i}.txt", "snippet": f"content {i}"}
                for i in range(10)
            ]
        }
        docs, status = _langchain_preview_documents_from_context_pack(
            context_pack, max_chunks=3
        )
        assert len(docs) <= 3


class TestWritersRoomStoreIntegration:
    """Integration tests for WritersRoomStore (no mocking)."""

    @pytest.fixture
    def store_root(self, tmp_path: Path):
        """Temporary storage root."""
        return tmp_path / "writers_room"

    def test_writers_room_store_write_and_read_review(self, store_root: Path):
        """Store persists and retrieves review JSON."""
        # Import here to avoid circular imports
        from app.services.writers_room_service import WritersRoomStore

        store = WritersRoomStore(root=store_root)
        review_id = f"review_{uuid4().hex}"
        review_data = {
            "review_id": review_id,
            "module_id": "writers_room_001",
            "artifact_key": "manuscript_001",
            "state": "pending",
        }

        # Write
        path = store.write_review(review_id, review_data)
        assert path.exists()

        # Read back
        retrieved = store.read_review(review_id)
        assert retrieved["review_id"] == review_id
        assert retrieved["module_id"] == "writers_room_001"

    def test_writers_room_store_read_raises_file_not_found(self, store_root: Path):
        """Reading nonexistent review raises FileNotFoundError."""
        from app.services.writers_room_service import WritersRoomStore

        store = WritersRoomStore(root=store_root)
        with pytest.raises(FileNotFoundError):
            store.read_review("nonexistent_review")
