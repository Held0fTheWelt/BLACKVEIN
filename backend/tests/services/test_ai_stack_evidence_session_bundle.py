"""Tests for ai_stack_evidence_session_bundle.py."""
import pytest


class TestSessionBundleExport:
    """Test suite for re-export of assemble_session_evidence_bundle."""

    def test_assemble_session_evidence_bundle_is_importable(self):
        """Test that assemble_session_evidence_bundle can be imported from this module."""
        from app.services.ai_stack_evidence_session_bundle import (
            assemble_session_evidence_bundle,
        )

        assert assemble_session_evidence_bundle is not None
        assert callable(assemble_session_evidence_bundle)

    def test_module_all_exports(self):
        """Test that __all__ correctly lists exported names."""
        import app.services.ai_stack_evidence_session_bundle as bundle_module

        assert hasattr(bundle_module, "__all__")
        assert "assemble_session_evidence_bundle" in bundle_module.__all__

    def test_assemble_session_evidence_bundle_is_callable(self):
        """Test that the exported function is callable."""
        from app.services.ai_stack_evidence_session_bundle import (
            assemble_session_evidence_bundle,
        )

        assert callable(assemble_session_evidence_bundle)
