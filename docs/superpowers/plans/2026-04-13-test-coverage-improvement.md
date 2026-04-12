# Test Coverage Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve test coverage across 36+ files to reach 92%+ coverage in all test suites (100% where implementation is straightforward).

**Architecture:** Organize coverage improvements into three tiers by impact and implementation effort:
- **Tier 1 (Zero Coverage)**: 5 files with 0% coverage — smallest/quickest wins first
- **Tier 2 (Critical Services)**: 5 high-impact files (auth, AI generation, game service) — close existing gaps
- **Tier 3 (Medium Priority)**: 26 files at 70-90% coverage — final push to 92%+ across all suites

**Tech Stack:** pytest, Flask test client, SQLAlchemy fixtures, existing test infrastructure at `backend/tests/conftest.py`

---

## File Structure

**Test organization follows source structure:**
- Source: `backend/app/runtime/<module>.py` → Tests: `backend/tests/runtime/test_<module>.py`
- Source: `backend/app/services/<module>.py` → Tests: `backend/tests/services/test_<module>.py`
- Source: `backend/app/web/<module>.py` → Tests: `backend/tests/web/test_<module>.py`

**Existing fixtures available:**
- `app`: Flask app with test config and clean DB
- `client`: test client for HTTP requests
- `test_user`, `auth_headers`: user fixtures
- `admin_user`, `moderator_user`: role-based fixtures

**Run tests with:** `python run_tests.py --suite backend` or individual test files with `pytest backend/tests/services/test_<module>.py -v`

---

## TIER 1: Zero Coverage Files (5 files, ~150 total statements)

These files have 0% coverage and need complete test suites. Start here for quick wins.

### Task 1: Test `ai_stack_evidence_session_bundle.py` (3 statements, 0%)

**Files:**
- Source: `backend/app/services/ai_stack_evidence_session_bundle.py`
- Create: `backend/tests/services/test_ai_stack_evidence_session_bundle.py`

- [ ] **Step 1: Read the source file to understand its public API**

Run: `head -30 backend/app/services/ai_stack_evidence_session_bundle.py`

Expected: View the module structure, class/function signatures, and imports.

- [ ] **Step 2: Write tests for each public function/class**

```python
"""Tests for ai_stack_evidence_session_bundle.py."""
import pytest
from app.services.ai_stack_evidence_session_bundle import (
    # Import each public class/function here
)


class TestSessionBundleFunction:
    """Test suite for SessionBundle functionality."""

    def test_session_bundle_initialization(self):
        """Test creating a session bundle with required parameters."""
        # Write a minimal test that exercises the main public API
        pass

    def test_session_bundle_state_access(self):
        """Test accessing bundle state after creation."""
        pass
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest backend/tests/services/test_ai_stack_evidence_session_bundle.py -v`

Expected: FAILED — the test exists but the implementation is missing or incomplete

- [ ] **Step 4: Write minimal implementation to satisfy tests**

Update the test file with actual test logic (not placeholder), based on the source file's actual behavior.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest backend/tests/services/test_ai_stack_evidence_session_bundle.py -v`

Expected: PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/tests/services/test_ai_stack_evidence_session_bundle.py
git commit -m "test: add comprehensive tests for ai_stack_evidence_session_bundle (100% coverage)"
```

---

### Task 2: Test `debug_presenter_sections.py` (37 statements, 0%)

**Files:**
- Source: `backend/app/runtime/debug_presenter_sections.py`
- Create: `backend/tests/runtime/test_debug_presenter_sections.py`

- [ ] **Step 1: Read the source file**

Run: `wc -l backend/app/runtime/debug_presenter_sections.py && head -50 backend/app/runtime/debug_presenter_sections.py`

Expected: Understand the module's purpose, classes, and methods.

- [ ] **Step 2: Identify main classes and public methods**

List all non-private methods that should be tested (those not starting with `_`).

- [ ] **Step 3: Write test class structure**

```python
"""Tests for debug_presenter_sections.py."""
import pytest
from app.runtime.debug_presenter_sections import (
    # Import classes/functions
)


class TestDebugPresenterSections:
    """Tests for debug presenter section generation."""

    @pytest.fixture
    def section_generator(self):
        """Create a debug section generator instance."""
        # Initialize with required dependencies
        pass

    def test_section_generation_basic(self, section_generator):
        """Test basic section generation."""
        pass

    def test_section_formatting(self, section_generator):
        """Test that sections are properly formatted."""
        pass

    def test_empty_section_handling(self, section_generator):
        """Test handling of empty data."""
        pass
```

- [ ] **Step 4: Implement actual test cases with assertions**

Replace `pass` statements with real test logic based on the source code behavior.

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/runtime/test_debug_presenter_sections.py -v`

Expected: All tests PASSED, coverage report shows 100%

- [ ] **Step 6: Commit**

```bash
git add backend/tests/runtime/test_debug_presenter_sections.py
git commit -m "test: add comprehensive tests for debug_presenter_sections (100% coverage)"
```

---

### Task 3: Test `debug_presenter.py` (46 statements, 0%)

**Files:**
- Source: `backend/app/runtime/debug_presenter.py`
- Create: `backend/tests/runtime/test_debug_presenter.py`

- [ ] **Step 1: Read source and understand dependencies**

Run: `head -60 backend/app/runtime/debug_presenter.py`

Expected: Identify classes, methods, and what `debug_presenter_sections.py` it depends on.

- [ ] **Step 2: Create test class with fixtures**

```python
"""Tests for debug_presenter.py."""
import pytest
from app.runtime.debug_presenter import (
    # Import public classes
)


class TestDebugPresenter:
    """Tests for the debug presenter."""

    @pytest.fixture
    def presenter(self):
        """Create a debug presenter instance."""
        pass

    def test_presenter_initialization(self, presenter):
        """Test presenter can be initialized."""
        assert presenter is not None

    def test_presenter_rendering(self, presenter):
        """Test rendering debug output."""
        pass

    def test_presenter_section_aggregation(self, presenter):
        """Test that sections are properly aggregated."""
        pass
```

- [ ] **Step 3: Fill in test implementations based on source behavior**

Write actual test logic for each method, focusing on:
- Initialization with various parameters
- Output format validation
- Edge cases (empty input, None values)

- [ ] **Step 4: Run and verify tests pass**

Run: `pytest backend/tests/runtime/test_debug_presenter.py -v`

Expected: PASSED with 100% coverage

- [ ] **Step 5: Commit**

```bash
git add backend/tests/runtime/test_debug_presenter.py
git commit -m "test: add comprehensive tests for debug_presenter (100% coverage)"
```

---

### Task 4: Test `history_presenter.py` (42 statements, 0%)

**Files:**
- Source: `backend/app/runtime/history_presenter.py`
- Create: `backend/tests/runtime/test_history_presenter.py`

- [ ] **Step 1: Read the source file**

Run: `head -60 backend/app/runtime/history_presenter.py`

Expected: Understand how history is presented, what data it works with.

- [ ] **Step 2: Create comprehensive test suite**

```python
"""Tests for history_presenter.py."""
import pytest
from app.runtime.history_presenter import (
    # Import public API
)


class TestHistoryPresenter:
    """Tests for history presentation."""

    @pytest.fixture
    def history_data(self):
        """Create sample history data for testing."""
        # Return realistic history entries/objects
        pass

    @pytest.fixture
    def presenter(self):
        """Create a history presenter instance."""
        pass

    def test_presenter_initialization(self, presenter):
        """Test presenter initialization."""
        assert presenter is not None

    def test_history_rendering(self, presenter, history_data):
        """Test rendering history entries."""
        pass

    def test_history_ordering(self, presenter):
        """Test that history is ordered correctly."""
        pass

    def test_empty_history_handling(self, presenter):
        """Test handling of empty history."""
        pass

    def test_history_truncation(self, presenter):
        """Test truncation of long histories."""
        pass
```

- [ ] **Step 3: Implement test logic based on source code**

Use actual data structures and expected outputs from the source.

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/runtime/test_history_presenter.py -v`

Expected: PASSED with 100% coverage

- [ ] **Step 5: Commit**

```bash
git add backend/tests/runtime/test_history_presenter.py
git commit -m "test: add comprehensive tests for history_presenter (100% coverage)"
```

---

### Task 5: Test `pipeline_decision_guards.py` (70 statements, 0%)

**Files:**
- Source: `backend/app/runtime/pipeline_decision_guards.py`
- Create: `backend/tests/runtime/test_pipeline_decision_guards.py`

- [ ] **Step 1: Analyze the source file structure**

Run: `grep -n "^def\|^class" backend/app/runtime/pipeline_decision_guards.py`

Expected: List of all classes and functions to test.

- [ ] **Step 2: Create test suite framework**

```python
"""Tests for pipeline_decision_guards.py."""
import pytest
from app.runtime.pipeline_decision_guards import (
    # Import all guard functions/classes
)


class TestPipelineDecisionGuards:
    """Tests for pipeline decision guard logic."""

    @pytest.fixture
    def pipeline_context(self):
        """Create a mock pipeline context for testing."""
        # Create context with required attributes
        pass

    def test_guard_allows_valid_state(self, pipeline_context):
        """Test that guard allows valid pipeline state."""
        pass

    def test_guard_blocks_invalid_state(self, pipeline_context):
        """Test that guard blocks invalid state."""
        pass

    def test_guard_with_edge_cases(self, pipeline_context):
        """Test guard behavior with edge cases."""
        pass

    def test_guard_error_messaging(self, pipeline_context):
        """Test that guards provide meaningful error messages."""
        pass
```

- [ ] **Step 3: Write specific tests for each guard function**

For each function/class in the source, create 2-3 test cases covering:
- Success path (condition is met)
- Failure path (condition is not met)
- Edge cases

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/runtime/test_pipeline_decision_guards.py -v`

Expected: PASSED with 100% coverage

- [ ] **Step 5: Commit**

```bash
git add backend/tests/runtime/test_pipeline_decision_guards.py
git commit -m "test: add comprehensive tests for pipeline_decision_guards (100% coverage)"
```

---

## TIER 2: Critical Services & Small Files (5 files, ~350 total statements)

These files are high-impact (authentication, AI routing, game logic). Fill major gaps.

### Task 6: Improve `auth.py` coverage (55 statements, 31.17% → 100%)

**Files:**
- Source: `backend/app/web/auth.py`
- Modify: `backend/tests/web/test_auth.py` (create if doesn't exist)

- [ ] **Step 1: Read current auth.py implementation**

Run: `wc -l backend/app/web/auth.py && cat backend/app/web/auth.py`

Expected: Full source of all auth functions/decorators.

- [ ] **Step 2: Check for existing test file**

Run: `ls -la backend/tests/web/test_auth.py 2>/dev/null || echo "File not found"`

Expected: Either find existing tests or identify this as a new file.

- [ ] **Step 3: Write comprehensive auth tests**

```python
"""Tests for auth.py authentication decorators and functions."""
import pytest
from flask import Flask
from app.web.auth import (
    # Import each public function/decorator
)


class TestAuthFunctions:
    """Tests for authentication utility functions."""

    @pytest.fixture
    def app_with_auth(self, app):
        """Ensure app has auth routes registered."""
        return app

    @pytest.fixture
    def client_with_user(self, client, test_user):
        """Client with authenticated user."""
        username, password = test_user
        response = client.post('/auth/login', json={
            'username': username,
            'password': password
        })
        return client, response.json.get('token')

    def test_login_success(self, client, test_user):
        """Test successful login returns token."""
        username, password = test_user
        response = client.post('/auth/login', json={
            'username': username,
            'password': password
        })
        assert response.status_code == 200
        assert 'token' in response.json

    def test_login_invalid_credentials(self, client, test_user):
        """Test login with wrong password fails."""
        username, _ = test_user
        response = client.post('/auth/login', json={
            'username': username,
            'password': 'wrongpassword'
        })
        assert response.status_code == 401

    def test_protected_route_requires_token(self, client):
        """Test that protected routes require authentication."""
        # Call a protected route without token
        response = client.get('/api/protected')
        assert response.status_code == 401

    def test_protected_route_with_valid_token(self, client_with_user):
        """Test protected route accepts valid token."""
        client, token = client_with_user
        response = client.get('/api/protected',
            headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200

    def test_token_refresh(self, client_with_user):
        """Test token refresh endpoint."""
        client, token = client_with_user
        response = client.post('/auth/refresh',
            headers={'Authorization': f'Bearer {token}'})
        assert response.status_code == 200
        assert 'token' in response.json
```

- [ ] **Step 4: Identify uncovered branches in auth.py**

Run: `grep -n "if\|else\|except\|raise" backend/app/web/auth.py`

Expected: List of conditional branches to test.

- [ ] **Step 5: Add edge case tests for each branch**

Add test cases for:
- Invalid token format
- Expired tokens
- Missing authorization header
- Malformed request body

- [ ] **Step 6: Run tests with coverage report**

Run: `pytest backend/tests/web/test_auth.py --cov=app.web.auth --cov-report=term-missing -v`

Expected: 100% coverage, all tests PASSED

- [ ] **Step 7: Commit**

```bash
git add backend/tests/web/test_auth.py
git commit -m "test: improve auth.py coverage to 100% (from 31.17%)"
```

---

### Task 7: Improve `ai_turn_generation.py` coverage (27 statements, 10% → 100%)

**Files:**
- Source: `backend/app/runtime/ai_turn_generation.py`
- Create: `backend/tests/runtime/test_ai_turn_generation.py`

- [ ] **Step 1: Read source and dependencies**

Run: `cat backend/app/runtime/ai_turn_generation.py`

Expected: Full source code of the AI turn generation module.

- [ ] **Step 2: Create test fixtures for AI turn generation**

```python
"""Tests for ai_turn_generation.py."""
import pytest
from app.runtime.ai_turn_generation import (
    # Import public API
)


class TestAITurnGeneration:
    """Tests for AI turn generation logic."""

    @pytest.fixture
    def game_state(self):
        """Create a mock game state for AI turn generation."""
        # Create realistic game state object
        pass

    @pytest.fixture
    def ai_generator(self):
        """Create an AI turn generator instance."""
        pass

    def test_turn_generation_basic(self, ai_generator, game_state):
        """Test generating a basic AI turn."""
        pass

    def test_turn_generation_with_constraints(self, ai_generator, game_state):
        """Test turn generation respects game constraints."""
        pass

    def test_turn_validation(self, ai_generator, game_state):
        """Test generated turns are valid."""
        pass

    def test_turn_generation_randomness(self, ai_generator, game_state):
        """Test that turns have appropriate variation."""
        pass
```

- [ ] **Step 3: Write specific test cases for each uncovered line**

For lines 3, 27->54, 29-31, 41-51 (from coverage report):
- Line 3 (import/init)
- Lines 27-54 (main generation logic)
- Lines 29-31 (validation)
- Lines 41-51 (fallback/error handling)

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/runtime/test_ai_turn_generation.py --cov=app.runtime.ai_turn_generation --cov-report=term-missing -v`

Expected: 100% coverage

- [ ] **Step 5: Commit**

```bash
git add backend/tests/runtime/test_ai_turn_generation.py
git commit -m "test: add comprehensive tests for ai_turn_generation (100% coverage)"
```

---

### Task 8: Improve `ai_turn_routing_builders.py` coverage (36 statements, 8% → 100%)

**Files:**
- Source: `backend/app/runtime/ai_turn_routing_builders.py`
- Create: `backend/tests/runtime/test_ai_turn_routing_builders.py`

- [ ] **Step 1: Read source file**

Run: `cat backend/app/runtime/ai_turn_routing_builders.py`

Expected: Understand the routing builder implementation.

- [ ] **Step 2: Analyze routing builder patterns**

Identify:
- Builder class methods
- Routing logic branches
- Edge cases (invalid routes, missing dependencies)

- [ ] **Step 3: Create test suite**

```python
"""Tests for ai_turn_routing_builders.py."""
import pytest
from app.runtime.ai_turn_routing_builders import (
    # Import router builders
)


class TestAITurnRoutingBuilders:
    """Tests for AI turn routing builder functionality."""

    @pytest.fixture
    def routing_builder(self):
        """Create a routing builder instance."""
        pass

    def test_builder_initialization(self, routing_builder):
        """Test builder can be initialized."""
        assert routing_builder is not None

    def test_builder_add_route(self, routing_builder):
        """Test adding a route to the builder."""
        pass

    def test_builder_route_validation(self, routing_builder):
        """Test that invalid routes are rejected."""
        pass

    def test_builder_build_router(self, routing_builder):
        """Test building a complete router."""
        pass

    def test_routing_decisions(self, routing_builder):
        """Test that routing produces correct decisions."""
        pass

    def test_route_priority(self, routing_builder):
        """Test that routes are evaluated in correct priority."""
        pass
```

- [ ] **Step 4: Write tests for uncovered lines (25-28, 32, 37-40, 43-46)**

Add specific test cases for each uncovered branch.

- [ ] **Step 5: Run tests**

Run: `pytest backend/tests/runtime/test_ai_turn_routing_builders.py --cov=app.runtime.ai_turn_routing_builders --cov-report=term-missing -v`

Expected: 100% coverage

- [ ] **Step 6: Commit**

```bash
git add backend/tests/runtime/test_ai_turn_routing_builders.py
git commit -m "test: add comprehensive tests for ai_turn_routing_builders (100% coverage)"
```

---

### Task 9: Improve `game_service.py` coverage (221 statements, 76.83% → 92%+)

**Files:**
- Source: `backend/app/services/game_service.py`
- Modify: `backend/tests/services/test_game_service.py`

- [ ] **Step 1: Check existing tests**

Run: `ls -la backend/tests/services/test_game_service.py && wc -l backend/tests/services/test_game_service.py`

Expected: Review existing test coverage.

- [ ] **Step 2: Identify uncovered lines from coverage report**

Missing lines from report: 36, 39, 44, 46, 56, 59, 64, 66, 69, 72, 74, 77, 90, 92, 94, 96, 98, 144->146, 177-178, 182->184, 189-192, 199->204, 269-270, 332, 337-346, 350-353, 357-360, 364-367

- [ ] **Step 3: Read uncovered sections**

Run: `sed -n '36p;39p;44p;46p;56p;59p;64p;66p;69p;72p;74p;77p;90p;92p;94p;96p;98p;144,146p;177,178p;182,184p;189,192p;199,204p;269,270p;332p;337,346p;350,353p;357,360p;364,367p' backend/app/services/game_service.py`

Expected: View the uncovered logic to understand what tests are needed.

- [ ] **Step 4: Add tests for uncovered branches**

Add to `backend/tests/services/test_game_service.py`:

```python
def test_game_initialization_with_custom_config(self):
    """Test game initialization with custom configuration."""
    # Tests for lines 36, 39, 44, 46
    pass

def test_game_state_transitions(self):
    """Test all game state transitions."""
    # Tests for lines 56, 59, 64, 66, 69, 72, 74, 77
    pass

def test_game_action_validation(self):
    """Test that invalid actions are rejected."""
    # Tests for uncovered validation branches
    pass

def test_game_event_handling(self):
    """Test game event processing."""
    # Tests for event handling branches
    pass

def test_game_cleanup_on_error(self):
    """Test proper cleanup when errors occur."""
    # Tests for error handling branches
    pass
```

- [ ] **Step 5: Implement specific test cases for each missing branch**

Reference the actual code and write tests that exercise the missing paths.

- [ ] **Step 6: Run coverage check**

Run: `pytest backend/tests/services/test_game_service.py --cov=app.services.game_service --cov-report=term-missing -v`

Expected: Coverage ≥ 92%

- [ ] **Step 7: Commit**

```bash
git add backend/tests/services/test_game_service.py
git commit -m "test: improve game_service.py coverage to 92%+ (from 76.83%)"
```

---

## TIER 3: Fill Remaining Gaps (26 files, ~1400 statements)

These files are at 70-90% coverage. Add targeted tests for uncovered lines to push each to 92%+.

### Task 10: Improve `play_service_control_service.py` coverage (314 statements, 86% → 92%+)

**Files:**
- Source: `backend/app/services/play_service_control_service.py`
- Modify: `backend/tests/services/test_play_service_control_service.py`

- [ ] **Step 1: Identify coverage gaps**

Run: `grep -n "86\|Missing" despaghettify/reports/latest_check_with_metrics.json | grep play_service`

Expected: List of missing lines from coverage report.

- [ ] **Step 2: Add targeted tests for missing branches**

Focus on uncovered lines:
- 64-65, 67, 71 (initialization variants)
- 99-100, 107-109, 111, 121, 125 (state management)
- 146->148, 150-151 (event handling)
- 191-193, 213-214, 227, 237, 296, 298, 300, 302 (control logic)
- 311->314, 340-341, 345->351, 353->369, 370->376, 397, 403, 456 (error handling)
- 465-471, 491-514, 531-532, 542-548, 555-567 (complex flows)

- [ ] **Step 3: Write test cases**

```python
def test_play_service_initialization_variations(self):
    """Test various initialization paths."""
    pass

def test_play_service_state_transitions(self):
    """Test all state transitions."""
    pass

def test_play_service_event_processing(self):
    """Test event processing and propagation."""
    pass

def test_play_service_error_recovery(self):
    """Test error recovery mechanisms."""
    pass

def test_play_service_complex_workflows(self):
    """Test complex multi-step workflows."""
    pass
```

- [ ] **Step 4: Run coverage check**

Run: `pytest backend/tests/services/test_play_service_control_service.py --cov=app.services.play_service_control_service --cov-report=term-missing -v`

Expected: Coverage ≥ 92%

- [ ] **Step 5: Commit**

```bash
git add backend/tests/services/test_play_service_control_service.py
git commit -m "test: improve play_service_control_service.py coverage to 92%+ (from 86%)"
```

---

### Tasks 11-36: Improve Remaining Services to 92%+

For each of these 26 files, follow the same pattern as Task 10:

**Files to cover (in priority order):**

1. `app/services/ai_stack_evidence_service.py` (167 statements, 80.09%)
2. `app/services/system_diagnosis_service.py` (218 statements, 86.33%)
3. `app/services/writers_room_pipeline_generation_synthesis.py` (56 statements, 77.14%)
4. `app/services/inspector_turn_projection_service.py` (61 statements, 78.65%)
5. `app/services/user_service_update_guards.py` (56 statements, 79.35%)
6. `app/services/inspector_projection_turn_view.py` (61 statements, 75.28%)
7. `app/services/ai_stack_closure_cockpit_parsing.py` (102 statements, 84.03%)
8. `app/services/inspector_turn_projection_sections_semantic.py` (64 statements, 76.42%)
9. `app/services/inspector_turn_projection_sections_provenance_entries.py` (71 statements, 66.99%)
10. `app/services/system_diagnosis_play_http.py` (30 statements, 71.43%)
11. `app/services/log_utils.py` (38 statements, 89.29%)
12. `app/services/user_service_account_guards.py` (51 statements, 84.27%)
13. `app/services/inspector_projection_shared.py` (13 statements, 76.47%)
14. `app/services/inspector_projection_service.py` (58 statements, 80.56%)
15. `app/services/writers_room_pipeline_generation_preflight.py` (26 statements, 75.00%)
16. `app/services/writers_room_pipeline_packaging_recommendation_bundling.py` (18 statements, 67.86%)
17. `app/services/inspector_projection_comparison.py` (34 statements, 81.25%)
18. `app/services/inspector_projection_coverage_health.py` (21 statements, 80.00%)
19. `app/services/inspector_projection_coverage_health_distribution.py` (80 statements, 85.19%)
20. `app/services/inspector_projection_provenance_raw_entries.py` (29 statements, 74.36%)
21. `app/runtime/narrative_threads.py` (73 statements, 81.05%)
22. `app/runtime/area2_operational_state.py` (93 statements, 62.41%)
23. `app/runtime/area2_validation_commands.py` (30 statements, 75.00%)
24. `app/runtime/area2_no_eligible_operator_meaning.py` (37 statements, 57.38%)

**Each file requires ONE task following this template:**

```markdown
### Task N: Improve `<filename>` coverage (<current>% → 92%+)

**Files:**
- Source: `backend/app/services/<filename>.py`
- Modify: `backend/tests/services/test_<filename>.py`

- [ ] **Step 1: Get coverage gap analysis**

Run: `grep -A 20 "<filename>" despaghettify/reports/latest_check_with_metrics.json | grep "Missing"`

Expected: List of uncovered line numbers.

- [ ] **Step 2: Read uncovered sections**

Run: `sed -n '<line_ranges>p' backend/app/services/<filename>.py`

Expected: View the uncovered code.

- [ ] **Step 3: Write tests for uncovered branches**

Add test cases to `backend/tests/services/test_<filename>.py` targeting each uncovered line or branch.

- [ ] **Step 4: Run coverage check**

Run: `pytest backend/tests/services/test_<filename>.py --cov=app.services.<filename> --cov-report=term-missing -v`

Expected: Coverage ≥ 92%

- [ ] **Step 5: Commit**

```bash
git add backend/tests/services/test_<filename>.py
git commit -m "test: improve <filename> coverage to 92%+ (from <current>%)"
```
```

---

## Final Validation (Single Task)

### Task 37: Verify All Suites Reach 92%+ Coverage

- [ ] **Step 1: Run full test suite with coverage**

Run: `python run_tests.py --suite backend --cov=app --cov-report=term-missing`

Expected: All files in `app/runtime/`, `app/services/`, `app/web/` show ≥ 92% coverage

- [ ] **Step 2: Generate coverage report**

Run: `pytest backend/ --cov=app --cov-report=html && python -m webbrowser htmlcov/index.html`

Expected: Visual confirmation all target files are at 92%+

- [ ] **Step 3: Review for 100% files**

Check which files reached 100% coverage (all TIER 1 + easy implementations).

- [ ] **Step 4: Final commit with summary**

```bash
git add -A
git commit -m "test: achieve 92%+ coverage across all test suites

- Tier 1 (0%→100%): 5 files with zero coverage now fully tested
- Tier 2 (30-80%→92%+): Auth, AI generation, game service improved
- Tier 3 (70-90%→92%+): 26 service files reach target coverage
- Total new test cases: 400+
- Total statements covered: 2,000+"
```

- [ ] **Step 5: Update Task.md if provided**

Update your Task.md with final coverage numbers showing all suites at 92%+.

---

## Execution Strategy

**Recommended approach: Subagent-Driven Development**

1. Start with TIER 1 (zero-coverage files) — quick wins build momentum
2. Move to TIER 2 (critical services) — high impact, medium effort
3. Complete TIER 3 (medium-priority services) — systematic grinding
4. Run final validation (Task 37)

Each task is independent and can be executed by a fresh subagent with two-stage review between tasks.

**Time estimate per task:**
- TIER 1 tasks (5): ~15 minutes each = 75 minutes
- TIER 2 tasks (5): ~20 minutes each = 100 minutes
- TIER 3 tasks (26): ~10 minutes each = 260 minutes
- Final validation: ~5 minutes
- **Total: ~440 minutes (~7-8 hours)** across all tasks

---

## Notes for Implementation

**Do not:**
- Write tests that only check code exists (assert `func is not None`)
- Mock external dependencies unless necessary — use real fixtures
- Create tests that pass trivially — test actual behavior

**Do:**
- Test error conditions and edge cases
- Use existing fixtures from `conftest.py` to reduce setup
- Write isolated, focused test functions (one assertion per test where possible)
- Verify behavior matches source code intent
- Commit frequently (after each 2-3 test files complete)

**Pytest tips:**
- Run with `-v` for verbose output
- Use `--cov=app.<module>` to see exactly which lines are missing
- Use `-k <pattern>` to run specific test subsets
- Parametrize tests with `@pytest.mark.parametrize` for multiple similar cases

