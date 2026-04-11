# AI Stack Test Coverage to 95%+ Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve ai_stack test coverage from 30-76% range to 95-100% by implementing comprehensive, real-world tests for edge cases and error paths.

**Architecture:** Coverage gaps are systematic:
- **Exception handling paths** in contract helpers (`canon_improvement_contract.py`, `research_claims.py`)
- **Edge cases in validation** (`goc_gate_evaluation.py`, `goc_dramatic_alignment.py`, `operational_profile.py`)
- **Handler dispatch** in registries (`capabilities_registry_research_canon_handlers.py`)
- **Complex business logic** in scene directors, langgraph, and research workflows

**Tech Stack:** pytest, pydantic, unittest.mock for fixtures and assertions

---

## File Structure

New and modified test files:
- **Create:** `ai_stack/tests/test_canon_improvement_contract.py` — unit tests for canon contract helpers
- **Create:** `ai_stack/tests/test_operational_profile.py` — edge case tests for cost hints
- **Create:** `ai_stack/tests/test_research_claims.py` — validation tests for claim payloads
- **Create:** `ai_stack/tests/test_goc_gate_evaluation.py` — unit tests for gate outcomes
- **Create:** `ai_stack/tests/test_goc_dramatic_alignment.py` — alignment check tests
- **Create:** `ai_stack/tests/test_capabilities_registry_handlers.py` — handler dispatch tests
- **Modify:** `ai_stack/tests/test_mcp_canonical_surface.py` — add missing edge case coverage
- **Create:** `ai_stack/tests/test_research_store_extended.py` — add missing method tests

---

## Task 1: Canon Improvement Contract (47% → 100%)

**Files:**
- Modify: `ai_stack/canon_improvement_contract.py:22-33`
- Create: `ai_stack/tests/test_canon_improvement_contract.py`

The contract helpers need exception path coverage. Currently missing: ValueError branches in ensure_issue_type() and ensure_proposal_type().

- [ ] **Step 1: Write failing test for ensure_issue_type invalid value**

```python
# ai_stack/tests/test_canon_improvement_contract.py
from __future__ import annotations

import pytest

from ai_stack.canon_improvement_contract import (
    ensure_issue_type,
    ensure_proposal_type,
    proposal_for_issue,
    ISSUE_TO_PROPOSAL_DEFAULT,
)
from ai_stack.research_contract import CanonIssueType, ImprovementProposalType


def test_ensure_issue_type_raises_on_invalid_value() -> None:
    with pytest.raises(ValueError) as exc_info:
        ensure_issue_type("INVALID_ENUM_NAME")
    assert "invalid_issue_type:INVALID_ENUM_NAME" in str(exc_info.value)


def test_ensure_issue_type_valid_by_name() -> None:
    result = ensure_issue_type("WEAK_ESCALATION")
    assert result == CanonIssueType.WEAK_ESCALATION


def test_ensure_proposal_type_raises_on_invalid_value() -> None:
    with pytest.raises(ValueError) as exc_info:
        ensure_proposal_type("FAKE_PROPOSAL")
    assert "invalid_proposal_type:FAKE_PROPOSAL" in str(exc_info.value)


def test_ensure_proposal_type_valid_by_name() -> None:
    result = ensure_proposal_type("RESTRUCTURE_PRESSURE_CURVE")
    assert result == ImprovementProposalType.RESTRUCTURE_PRESSURE_CURVE


def test_proposal_for_issue_returns_mapped_proposal() -> None:
    issue = CanonIssueType.WEAK_ESCALATION
    proposal = proposal_for_issue(issue)
    assert proposal == ISSUE_TO_PROPOSAL_DEFAULT[issue]


def test_proposal_for_issue_all_issue_types_mapped() -> None:
    for issue_type in CanonIssueType:
        proposal = proposal_for_issue(issue_type)
        assert isinstance(proposal, ImprovementProposalType)
        assert proposal in ISSUE_TO_PROPOSAL_DEFAULT.values()
```

- [ ] **Step 2: Run test to verify it passes**

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
pytest ai_stack/tests/test_canon_improvement_contract.py -xvs
```

Expected: PASSED (5 passed)

- [ ] **Step 3: Commit**

```bash
git add ai_stack/tests/test_canon_improvement_contract.py
git commit -m "test: add complete canon_improvement_contract coverage with exception paths"
```

---

## Task 2: Research Claims (75% → 100%)

**Files:**
- Modify: `ai_stack/research_claims.py:24-43`
- Create: `ai_stack/tests/test_research_claims.py`

Missing tests: edge cases in is_schema_valid_claim_payload() — empty strings, missing keys, invalid claim types, non-list anchors.

- [ ] **Step 1: Write comprehensive tests for claim validation**

```python
# ai_stack/tests/test_research_claims.py
from __future__ import annotations

import pytest

from ai_stack.research_claims import (
    RECOGNIZED_CLAIM_TYPES,
    is_recognized_claim_type,
    is_schema_valid_claim_payload,
)


def test_is_recognized_claim_type_valid() -> None:
    for claim_type in RECOGNIZED_CLAIM_TYPES:
        assert is_recognized_claim_type(claim_type) is True


def test_is_recognized_claim_type_invalid() -> None:
    assert is_recognized_claim_type("unknown_type") is False
    assert is_recognized_claim_type(123) is False
    assert is_recognized_claim_type(None) is False
    assert is_recognized_claim_type([]) is False


def test_is_schema_valid_claim_payload_valid() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "This is a valid claim",
        "evidence_anchor_ids": ["anchor_1", "anchor_2"],
        "perspective": "narrator",
    }
    assert is_schema_valid_claim_payload(payload) is True


def test_is_schema_valid_claim_payload_missing_claim_type() -> None:
    payload = {
        "statement": "text",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_missing_statement() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_missing_evidence_anchor_ids() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_missing_perspective() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": ["a"],
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_invalid_claim_type() -> None:
    payload = {
        "claim_type": "invalid_type",
        "statement": "text",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_empty_statement() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_whitespace_only_statement() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "   \t\n  ",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_empty_anchor_list() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": [],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_non_list_anchors() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": "not_a_list",
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_anchor_with_empty_string() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": ["", "anchor_2"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_anchor_with_whitespace() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": ["   ", "anchor_2"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_non_string_anchor() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": [123, "anchor_2"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_all_claim_types() -> None:
    for claim_type in RECOGNIZED_CLAIM_TYPES:
        payload = {
            "claim_type": claim_type,
            "statement": "This is a valid statement",
            "evidence_anchor_ids": ["anchor_1"],
            "perspective": "reviewer",
        }
        assert is_schema_valid_claim_payload(payload) is True
```

- [ ] **Step 2: Run test to verify they pass**

```bash
pytest ai_stack/tests/test_research_claims.py -xvs
```

Expected: PASSED (17 passed)

- [ ] **Step 3: Commit**

```bash
git add ai_stack/tests/test_research_claims.py
git commit -m "test: add comprehensive research_claims validation coverage"
```

---

## Task 3: Operational Profile (70% → 100%)

**Files:**
- Modify: `ai_stack/operational_profile.py:18-25, 62-64`
- Create: `ai_stack/tests/test_operational_profile.py`

Missing tests: edge cases in prompt_length_bucket() and build operational cost hints.

- [ ] **Step 1: Write comprehensive tests for operational profile**

```python
# ai_stack/tests/test_operational_profile.py
from __future__ import annotations

from ai_stack.operational_profile import (
    prompt_length_bucket,
    build_operational_cost_hints_for_runtime_graph,
    build_operational_cost_hints_from_retrieval,
)


def test_prompt_length_bucket_small() -> None:
    assert prompt_length_bucket(0) == "small"
    assert prompt_length_bucket(1000) == "small"
    assert prompt_length_bucket(3999) == "small"


def test_prompt_length_bucket_medium() -> None:
    assert prompt_length_bucket(4000) == "medium"
    assert prompt_length_bucket(8000) == "medium"
    assert prompt_length_bucket(15999) == "medium"


def test_prompt_length_bucket_large() -> None:
    assert prompt_length_bucket(16000) == "large"
    assert prompt_length_bucket(50000) == "large"


def test_prompt_length_bucket_negative_becomes_zero() -> None:
    assert prompt_length_bucket(-100) == "small"
    assert prompt_length_bucket(-1) == "small"


def test_build_operational_cost_hints_for_runtime_graph_all_none() -> None:
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=None,
        generation=None,
        graph_execution_health="ok",
        model_prompt=None,
        fallback_path_taken=False,
    )
    assert result["disclaimer"] == "coarse_operational_signals_not_financial_estimates"
    assert result["retrieval_route"] == ""
    assert result["retrieval_status"] == ""
    assert result["prompt_length_bucket"] == "small"
    assert result["prompt_length_chars"] == 0
    assert result["model_fallback_used"] is False


def test_build_operational_cost_hints_for_runtime_graph_with_retrieval() -> None:
    retrieval = {
        "retrieval_route": "hybrid",
        "status": "ok",
        "embedding_model_id": "text-embedding-3-large",
        "hit_count": 3,
    }
    generation = {
        "fallback_used": False,
        "attempted": True,
        "success": True,
        "metadata": {
            "adapter_invocation_mode": "forward_pass",
        },
    }
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=retrieval,
        generation=generation,
        graph_execution_health="ok",
        model_prompt="This is a test prompt",
        fallback_path_taken=False,
    )
    assert result["retrieval_route"] == "hybrid"
    assert result["retrieval_status"] == "ok"
    assert result["retrieval_hit_count"] == 3
    assert result["adapter_invocation_mode"] == "forward_pass"
    assert result["primary_generation_success"] is True
    assert result["prompt_length_bucket"] == "small"


def test_build_operational_cost_hints_for_runtime_graph_with_fallback() -> None:
    generation = {
        "fallback_used": True,
        "attempted": True,
        "success": False,
    }
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=None,
        generation=generation,
        graph_execution_health="degraded",
        model_prompt=None,
        fallback_path_taken=True,
    )
    assert result["model_fallback_used"] is True
    assert result["fallback_path_taken"] is True
    assert result["graph_execution_health"] == "degraded"


def test_build_operational_cost_hints_for_runtime_graph_large_prompt() -> None:
    large_prompt = "x" * 20000
    result = build_operational_cost_hints_for_runtime_graph(
        retrieval=None,
        generation=None,
        graph_execution_health="ok",
        model_prompt=large_prompt,
        fallback_path_taken=False,
    )
    assert result["prompt_length_chars"] == 20000
    assert result["prompt_length_bucket"] == "large"


def test_build_operational_cost_hints_from_retrieval_all_none() -> None:
    result = build_operational_cost_hints_from_retrieval(None)
    assert result["disclaimer"] == "coarse_operational_signals_not_financial_estimates"
    assert result["retrieval_route"] == ""
    assert result["retrieval_status"] == ""
    assert result["retrieval_hit_count"] is None


def test_build_operational_cost_hints_from_retrieval_with_data() -> None:
    retrieval = {
        "retrieval_route": "sparse_fallback",
        "status": "degraded",
        "embedding_model_id": "sparse-bm25",
        "hit_count": 2,
    }
    result = build_operational_cost_hints_from_retrieval(retrieval)
    assert result["retrieval_route"] == "sparse_fallback"
    assert result["retrieval_status"] == "degraded"
    assert result["retrieval_hit_count"] == 2
    assert result["embedding_model_id"] == "sparse-bm25"
    assert "retrieval_trace_schema_version" in result


def test_build_operational_cost_hints_from_retrieval_invalid_type() -> None:
    result = build_operational_cost_hints_from_retrieval("not a dict")  # type: ignore
    assert result["retrieval_route"] == ""
    assert result["retrieval_status"] == ""
```

- [ ] **Step 2: Run test to verify they pass**

```bash
pytest ai_stack/tests/test_operational_profile.py -xvs
```

Expected: PASSED (13 passed)

- [ ] **Step 3: Commit**

```bash
git add ai_stack/tests/test_operational_profile.py
git commit -m "test: add comprehensive operational_profile edge case coverage"
```

---

## Task 4: GOC Gate Evaluation (71% → 100%)

**Files:**
- Modify: `ai_stack/goc_gate_evaluation.py`
- Create: `ai_stack/tests/test_goc_gate_evaluation.py`

Missing tests: all gate functions with various state conditions.

- [ ] **Step 1: Write comprehensive gate evaluation tests**

(See implementation below in Step 2)

- [ ] **Step 2: Create test file with all gate conditions**

```python
# ai_stack/tests/test_goc_gate_evaluation.py
from __future__ import annotations

import pytest

from ai_stack.goc_gate_evaluation import (
    gate_turn_integrity,
    gate_diagnostic_sufficiency,
    gate_dramatic_quality,
    gate_slice_boundary,
)


class TestGateTurnIntegrity:
    def test_pass_all_required_nodes_present(self) -> None:
        state = {
            "graph_diagnostics": {
                "nodes_executed": [
                    "goc_resolve_canonical_content",
                    "director_assess_scene",
                    "director_select_dramatic_parameters",
                    "proposal_normalize",
                    "validate_seam",
                    "commit_seam",
                    "render_visible",
                ]
            },
            "validation_outcome": {"status": "approved"},
            "committed_result": {"commit_applied": True},
            "module_id": "god_of_carnage",
        }
        assert gate_turn_integrity(state) == "pass"

    def test_fail_missing_required_node(self) -> None:
        state = {
            "graph_diagnostics": {
                "nodes_executed": ["goc_resolve_canonical_content"],
            }
        }
        assert gate_turn_integrity(state) == "fail"

    def test_fail_no_graph_diagnostics(self) -> None:
        state = {}
        assert gate_turn_integrity(state) == "fail"

    def test_pass_god_of_carnage_no_commit(self) -> None:
        state = {
            "graph_diagnostics": {
                "nodes_executed": [
                    "goc_resolve_canonical_content",
                    "director_assess_scene",
                    "director_select_dramatic_parameters",
                    "proposal_normalize",
                    "validate_seam",
                    "commit_seam",
                    "render_visible",
                ]
            },
            "validation_outcome": {"status": "approved"},
            "committed_result": {"commit_applied": False},
            "module_id": "god_of_carnage",
        }
        assert gate_turn_integrity(state) == "pass"


class TestGateDiagnosticSufficiency:
    def test_fail_invalid_repro_type(self) -> None:
        state = {
            "graph_diagnostics": {
                "repro_metadata": "not_a_dict",
            }
        }
        assert gate_diagnostic_sufficiency(state) == "fail"

    def test_fail_missing_graph_diagnostics(self) -> None:
        state = {}
        assert gate_diagnostic_sufficiency(state) == "fail"


class TestGateDramaticQuality:
    def test_fail_rejected_dramatic_alignment(self) -> None:
        state = {
            "validation_outcome": {
                "status": "rejected",
                "reason": "dramatic_alignment_mismatch",
            }
        }
        assert gate_dramatic_quality(state) == "fail"

    def test_fail_rejected_dramatic_effect(self) -> None:
        state = {
            "validation_outcome": {
                "status": "rejected",
                "reason": "dramatic_effect_insufficient",
            }
        }
        assert gate_dramatic_quality(state) == "fail"

    def test_conditional_pass_not_approved(self) -> None:
        state = {
            "validation_outcome": {
                "status": "pending",
            }
        }
        assert gate_dramatic_quality(state) == "conditional_pass"

    def test_pass_with_truth_aligned_marker(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
        }
        assert gate_dramatic_quality(state) == "pass"

    def test_conditional_pass_short_narration_escalate(self) -> None:
        state = {
            "validation_outcome": {"status": "approved"},
            "visibility_class_markers": ["truth_aligned"],
            "selected_scene_function": "escalate_conflict",
            "visible_output_bundle": {"gm_narration": ["x"]},
        }
        assert gate_dramatic_quality(state) == "conditional_pass"


class TestGateSliceBoundary:
    def test_pass_no_failure_markers(self) -> None:
        state = {
            "failure_markers": [],
        }
        assert gate_slice_boundary(state) == "pass"

    def test_pass_missing_failure_markers(self) -> None:
        state = {}
        assert gate_slice_boundary(state) == "pass"

    def test_fail_scope_breach_marker(self) -> None:
        state = {
            "failure_markers": [
                {"failure_class": "scope_breach"},
            ]
        }
        assert gate_slice_boundary(state) == "fail"

    def test_pass_other_failure_class(self) -> None:
        state = {
            "failure_markers": [
                {"failure_class": "other_failure"},
            ]
        }
        assert gate_slice_boundary(state) == "pass"
```

- [ ] **Step 3: Run test to verify they pass**

```bash
pytest ai_stack/tests/test_goc_gate_evaluation.py -xvs
```

Expected: PASSED

- [ ] **Step 4: Commit**

```bash
git add ai_stack/tests/test_goc_gate_evaluation.py
git commit -m "test: add comprehensive goc_gate_evaluation coverage"
```

---

## Task 5: GOC Dramatic Alignment (67% → 100%)

**Files:**
- Modify: `ai_stack/goc_dramatic_alignment.py`
- Create: `ai_stack/tests/test_goc_dramatic_alignment.py`

Test the constant definitions and token coverage.

- [ ] **Step 1: Create token coverage tests**

```python
# ai_stack/tests/test_goc_dramatic_alignment.py
from __future__ import annotations

from ai_stack.goc_dramatic_alignment import (
    _FUNCTION_SUBSTRING_TOKENS,
    _MIN_CHARS_HIGH_STAKES,
    _MIN_CHARS_WITHHELD_OR_THIN,
)


def test_function_substring_tokens_coverage() -> None:
    expected_functions = {
        "escalate_conflict",
        "redirect_blame",
        "reveal_surface",
        "probe_motive",
        "repair_or_stabilize",
        "establish_pressure",
        "withhold_or_evade",
    }
    assert set(_FUNCTION_SUBSTRING_TOKENS.keys()) >= expected_functions


def test_min_char_thresholds() -> None:
    assert _MIN_CHARS_HIGH_STAKES > 0
    assert _MIN_CHARS_WITHHELD_OR_THIN > 0
    assert _MIN_CHARS_WITHHELD_OR_THIN < _MIN_CHARS_HIGH_STAKES


def test_token_lists_are_tuples() -> None:
    for func, tokens in _FUNCTION_SUBSTRING_TOKENS.items():
        assert isinstance(tokens, tuple)
        assert all(isinstance(t, str) for t in tokens)


def test_escalate_conflict_has_conflict_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("escalate_conflict", ())
    # Should contain confrontation-related tokens
    assert any(t in tokens for t in ["shout", "rage", "angry", "fight"])


def test_redirect_blame_has_blame_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("redirect_blame", ())
    assert any(t in tokens for t in ["blame", "fault", "responsib", "your"])


def test_reveal_surface_has_truth_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("reveal_surface", ())
    assert any(t in tokens for t in ["truth", "secret", "reveal", "confess"])


def test_probe_motive_has_question_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("probe_motive", ())
    assert any(t in tokens for t in ["why", "reason", "motive"])


def test_repair_or_stabilize_has_peace_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("repair_or_stabilize", ())
    assert any(t in tokens for t in ["apolog", "sorry", "peace", "calm"])


def test_establish_pressure_has_tension_tokens() -> None:
    tokens = _FUNCTION_SUBSTRING_TOKENS.get("establish_pressure", ())
    assert any(t in tokens for t in ["quiet", "tight", "wait", "still"])
```

- [ ] **Step 2: Run tests**

```bash
pytest ai_stack/tests/test_goc_dramatic_alignment.py -xvs
```

Expected: PASSED

- [ ] **Step 3: Commit**

```bash
git add ai_stack/tests/test_goc_dramatic_alignment.py
git commit -m "test: add goc_dramatic_alignment constant validation coverage"
```

---

## Task 6-12: Remaining Modules

Focus on the following with similar TDD patterns:

6. **research_store.py** — Add tests for uncovered methods
7. **mcp_canonical_surface.py** — Expand edge cases
8. **scene_director_goc.py** — Add decision path tests
9. **research_langgraph.py** — Add node execution tests
10. **capabilities_registry_research_canon_handlers.py** — Handler dispatch tests
11. **research_exploration_bounded.py** — Exploration logic tests
12. **Final coverage verification** — Report and commit

Each follows the same pattern: identify missing lines, write failing tests, verify they pass.

---

## Final Coverage Verification

- [ ] **Step 1: Generate full coverage report**

```bash
cd /mnt/c/Users/YvesT/PycharmProjects/WorldOfShadows
pytest ai_stack/tests/ --cov=ai_stack --cov-report=term-missing -q
```

- [ ] **Step 2: Verify target modules reach 95%+**

Check these specific modules:
- canon_improvement_contract.py: target 100%
- operational_profile.py: target 100%
- research_claims.py: target 100%
- goc_gate_evaluation.py: target 95%+
- goc_dramatic_alignment.py: target 95%+

- [ ] **Step 3: Final commit**

```bash
git add .
git commit -m "test: ai_stack coverage improved to 95%+ across all modules"
```

---

## Quick Reference

**Run all ai_stack tests:**
```bash
pytest ai_stack/tests/ -xvs
```

**Generate HTML coverage report:**
```bash
pytest ai_stack/tests/ --cov=ai_stack --cov-report=html
```

**Check specific module coverage:**
```bash
pytest --cov=ai_stack.module_name --cov-report=term-missing ai_stack/tests/
```

**Run single test file:**
```bash
pytest ai_stack/tests/test_module_name.py -xvs
```

