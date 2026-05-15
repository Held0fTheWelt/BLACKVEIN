"""Compatibility entrypoint for ADR-0039 gate naming without the underscore."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _canonical_module():
    path = Path(__file__).with_name("test_adr_0039_pi_scope.py")
    spec = importlib.util.spec_from_file_location("adr_0039_pi_scope_canonical", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adr0039_alias_runs_canonical_pi_scope_gate() -> None:
    module = _canonical_module()

    module.test_all_pi_labeled_tests_are_in_adr0039_scope_manifest()
    module.test_adr0039_pi_scope_manifest_entries_are_current_and_meaningful()
    module.test_production_runtime_vocabulary_has_no_active_pi_control_tokens()
    module.test_adr0039_links_current_matrix_and_live_gate_docs()
    module.test_current_truth_docs_do_not_embed_machine_local_paths()
    module.test_verification_log_labels_local_absolute_paths_as_local_only()
    module.test_mcp_projection_verification_declares_local_only_evidence_scope()
