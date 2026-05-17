# MVP4 Test Gate Plan — 5 Core Contracts

**Status:** Planning  
**Date:** 2026-05-04  
**Scope:** Test organization and CI/CD integration for adr-0032 runtime contracts

---

## Overview

This document specifies **where**, **how**, and **when** the 5 Core Contracts from **adr-0032** are tested and verified in the CI/CD pipeline. It is the **canonical reference** for:

- Test file locations and naming
- Suite registration in `run_tests.py`
- CI/CD commands and exit criteria
- Team ownership and implementation timeline

---

## Suite Organization

### New Suite: `mvp4-contracts`

A dedicated suite for **MVP4 runtime contracts**. Combines tests from backend, engine, ai_stack with marker `@pytest.mark.contract`.

**Registration in `tests/run_tests.py`:**

```python
"mvp4-contracts": SuiteConfig(
    kind="pytest",
    cwd=PROJECT_ROOT,
    target="tests/gates tests/mvp4_contracts",
    supports_coverage=True,
),
```

**Run command:**

```bash
python tests/run_tests.py --suite mvp4-contracts
```

**Expected test count:** 60+ tests (15 per contract × 4 suites)

---

## Contract 1: Backend → World-Engine Story Session Handoff

### Test Files

**Location:** `backend/tests/test_mvp4_contract_backend_handoff.py`

**Test Class:** `TestBackendWorldEngineHandoffContract`

**Tests (12 total):**

```python
@pytest.mark.contract
@pytest.mark.integration
class TestBackendWorldEngineHandoffContract:
    """Verify Contract 1: Backend sends complete actor ownership to world-engine."""

    def test_create_story_session_payload_includes_human_actor_id(self):
        """POST /api/story/sessions must include the canonical human_actor_id."""
        # Live backend→world-engine call
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        assert response["runtime_projection"]["human_actor_id"] == "annette_reille"

    def test_create_story_session_payload_includes_npc_actor_ids(self):
        """POST /api/story/sessions must include npc_actor_ids."""
        session_id = self._create_story_session_alain()
        response = self._fetch_story_state(session_id)
        assert "veronique_vallon" in response["runtime_projection"]["npc_actor_ids"]
        assert "michel_longstreet" in response["runtime_projection"]["npc_actor_ids"]

    def test_create_story_session_payload_includes_actor_lanes(self):
        """POST /api/story/sessions must include actor_lanes."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        assert response["runtime_projection"]["actor_lanes"]["annette_reille"] == "human"
        assert response["runtime_projection"]["actor_lanes"]["veronique_vallon"] == "npc"

    def test_create_story_session_payload_includes_runtime_profile_id(self):
        """POST /api/story/sessions must include runtime_profile_id."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        assert response["runtime_projection"]["runtime_profile_id"] == "god_of_carnage_solo"

    def test_create_story_session_payload_includes_runtime_module_id(self):
        """POST /api/story/sessions must include runtime_module_id."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        assert "runtime_module_id" in response["runtime_projection"]
        assert response["runtime_projection"]["runtime_module_id"] is not None

    def test_create_story_session_payload_includes_content_module_id(self):
        """POST /api/story/sessions must include content_module_id."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        assert response["runtime_projection"]["content_module_id"] == "god_of_carnage"

    def test_human_actor_id_resolves_from_selected_player_role(self):
        """human_actor_id must resolve from selected_player_role through content identity."""
        expected = {"annette": "annette_reille", "alain": "alain_reille"}
        for role, actor_id in expected.items():
            session_id = self._create_story_session(role)
            response = self._fetch_story_state(session_id)
            assert response["runtime_projection"]["selected_player_role"] == role
            assert response["runtime_projection"]["human_actor_id"] == actor_id

    def test_actor_lanes_maps_all_canonical_actors(self):
        """actor_lanes must map all canonical actors, not partial set."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        lanes = response["runtime_projection"]["actor_lanes"]
        assert set(lanes.keys()) == {"annette_reille", "alain_reille", "veronique_vallon", "michel_longstreet"}

    def test_actor_lanes_exclude_visitor(self):
        """actor_lanes must NOT include visitor."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        lanes = response["runtime_projection"]["actor_lanes"]
        assert "visitor" not in lanes

    def test_backend_create_story_session_error_on_missing_actor_ownership(self):
        """If backend fails to send actor ownership, /api/story/sessions must reject with 400."""
        # Simulate backend not including human_actor_id
        payload = {
            "module_id": "god_of_carnage",
            "runtime_projection": {
                "start_scene_id": "foyer",
                "scenes": {},
                # Missing human_actor_id, npc_actor_ids, actor_lanes
            },
        }
        response = self._post_story_sessions(payload)
        assert response.status_code == 400
        assert "human_actor_id" in response.json().get("error", "")

    def test_langfuse_trace_includes_handoff_audit_log(self):
        """Langfuse trace must include handoff verification log."""
        session_id = self._create_story_session_annette()
        trace = self._fetch_langfuse_span(session_id, "backend.story_session_create")
        assert trace["runtime_projection_fields_present"] == [
            "module_id", "selected_player_role", "human_actor_id",
            "npc_actor_ids", "actor_lanes", "runtime_profile_id",
            "runtime_module_id", "content_module_id"
        ]
        assert trace["actor_lanes_visitor_present"] is False

    def test_npc_actor_ids_are_strings_not_empty(self):
        """npc_actor_ids must be list of non-empty strings."""
        session_id = self._create_story_session_annette()
        response = self._fetch_story_state(session_id)
        npc_ids = response["runtime_projection"]["npc_actor_ids"]
        assert isinstance(npc_ids, list)
        assert all(isinstance(id, str) and id.strip() for id in npc_ids)
        assert len(npc_ids) >= 2  # At least human-excluded characters
```

**Location:** `world-engine/tests/test_mvp4_contract_backend_handoff.py`

**Test Class:** `TestStoredProjectionHasActorOwnership`

**Tests (6 total):**

```python
@pytest.mark.contract
@pytest.mark.integration
class TestStoredProjectionHasActorOwnership:
    """Verify Contract 1 (world-engine side): Stored projection includes actor ownership."""

    def test_stored_session_projection_has_all_actor_fields(self):
        """After backend sends create_story_session, stored session must have actor fields."""
        session = self._create_session_via_backend(role="annette")
        assert session.runtime_projection["human_actor_id"] == "annette"
        assert "veronique" in session.runtime_projection["npc_actor_ids"]
        assert session.runtime_projection["actor_lanes"]["annette"] == "human"

    def test_extract_actor_lane_context_returns_context_not_none(self):
        """_extract_actor_lane_context must return non-None when human_actor_id present."""
        session = self._create_session_via_backend(role="alain")
        ctx = StoryRuntimeManager._extract_actor_lane_context(session)
        assert ctx is not None
        assert ctx["human_actor_id"] == "alain"

    def test_extract_actor_lane_context_has_forbidden_and_allowed(self):
        """Context must have ai_forbidden_actor_ids and ai_allowed_actor_ids."""
        session = self._create_session_via_backend(role="annette")
        ctx = StoryRuntimeManager._extract_actor_lane_context(session)
        assert "annette" in ctx["ai_forbidden_actor_ids"]
        assert "veronique" in ctx["ai_allowed_actor_ids"]
        assert "alain" in ctx["ai_allowed_actor_ids"]

    def test_missing_human_actor_id_returns_none_context(self):
        """If projection lacks human_actor_id, context must be None (not error)."""
        # Create session with content-only projection (no actor ownership)
        session = StorySession(
            session_id="test",
            module_id="god_of_carnage",
            runtime_projection={"start_scene_id": "foyer"},
        )
        ctx = StoryRuntimeManager._extract_actor_lane_context(session)
        assert ctx is None

    def test_persisted_projection_survives_storage_roundtrip(self):
        """Actor ownership fields must persist after storage and retrieval."""
        session_id = self._create_and_persist_session(role="annette")
        retrieved = self._load_session_from_store(session_id)
        assert retrieved.runtime_projection["human_actor_id"] == "annette"
        assert "actor_lanes" in retrieved.runtime_projection

    def test_all_canonical_actors_in_actor_lanes(self):
        """actor_lanes must contain all canonical actors, no partial sets."""
        session = self._create_session_via_backend(role="annette")
        lanes = session.runtime_projection["actor_lanes"]
        assert len(lanes) == 4  # annette, alain, veronique, michel
        assert all(a in lanes for a in ["annette", "alain", "veronique", "michel"])
```

---

## Contract 2: Story Session Opening Truthfulness

### Test Files

**Location:** `world-engine/tests/test_mvp4_contract_opening_truthfulness.py`

**Test Class:** `TestOpeningTruthfulnessContract`

**Tests (15 total):** (Sample shown; full test file has all 15)

```python
@pytest.mark.contract
@pytest.mark.integration
class TestOpeningTruthfulnessContract:
    """Verify Contract 2: Opening turn is non-empty and validates before commit."""

    def test_opening_turn_exists_after_create_session(self):
        """story_window.entries[0] must be present immediately after create_session."""
        session = self.manager.create_session(
            module_id="god_of_carnage",
            runtime_projection=self._complete_projection_annette(),
        )
        assert len(session.story_window.entries) >= 1
        assert session.story_window.entries[0].turn_number == 0

    def test_opening_has_kind_opening(self):
        """entries[0].kind must be 'opening'."""
        session = self.manager.create_session(...)
        assert session.story_window.entries[0].kind == "opening"

    def test_opening_has_visible_output_bundle(self):
        """Opening must have visible_output_bundle with gm_narration."""
        session = self.manager.create_session(...)
        bundle = session.story_window.entries[0].visible_output_bundle
        assert bundle.gm_narration is not None
        assert len(bundle.gm_narration.strip()) > 0

    def test_opening_has_npc_agency_plan(self):
        """Opening's diagnostics must include npc_agency_plan."""
        session = self.manager.create_session(...)
        diag = session.story_window.entries[0].diagnostics_envelope
        assert diag.npc_agency_plan is not None

    def test_opening_passes_actor_lane_validation(self):
        """Opening's proposed output must pass validate_actor_lane_blocks."""
        session = self.manager.create_session(...)
        diag = session.story_window.entries[0].diagnostics_envelope
        assert diag.validation_outcome == "approved"
        assert diag.actor_lane_validation_status != "rejected"

    def test_opening_provider_not_mock(self):
        """Opening provider must not be 'mock' (unless explicitly deterministic_ldss)."""
        session = self.manager.create_session(...)
        gen = session.story_window.entries[0].diagnostics_envelope.generation
        assert gen.provider != "mock" or session.story_window.entries[0].kind == "deterministic_ldss_bootstrap"

    def test_opening_quality_class_live_or_degraded(self):
        """Opening quality_class must be 'live' or 'degraded', not 'blocked'."""
        session = self.manager.create_session(...)
        quality = session.story_window.entries[0].diagnostics_envelope.quality_class
        assert quality in ["live", "degraded"]

    def test_opening_not_empty_on_success(self):
        """Successful opening must have actual narrative content, not placeholder."""
        session = self.manager.create_session(...)
        entries = session.story_window.entries
        assert len(entries) > 0
        narration = entries[0].visible_output_bundle.gm_narration
        assert len(narration.strip()) > 50  # Minimal content check

    # ... 7 more tests covering fallback, error handling, audit logging
```

---

## Contract 3: Frontend Playability and Empty-State Handling

### Test Files

**Location:** `backend/tests/test_mvp4_contract_playability.py`

**Test Class:** `TestFrontendPlayabilityContract`

**Tests (8 total):**

```python
@pytest.mark.contract
@pytest.mark.integration
class TestFrontendPlayabilityContract:
    """Verify Contract 3: can_execute matches story_entries state."""

    def test_can_execute_false_when_story_entries_empty(self):
        """Backend must set can_execute=False if story_entries is empty."""
        # Simulate empty story window
        bundle = self._get_player_session_bundle(session_id="empty")
        assert bundle["story_entries"] == []
        assert bundle["can_execute"] is False

    def test_can_execute_true_when_story_entries_nonempty(self):
        """Backend must set can_execute=True only if story_entries has entries."""
        # Live session with opening
        session_id = self._create_story_session_annette()
        bundle = self._get_player_session_bundle(session_id)
        assert len(bundle["story_entries"]) > 0
        assert bundle["can_execute"] is True

    def test_empty_state_includes_degradation_signals(self):
        """Empty story_entries must include degradation_signals with reason."""
        # Simulate failed opening
        bundle = self._get_player_session_bundle(session_id="failed_opening")
        assert bundle["story_entries"] == []
        assert "degradation_signals" in bundle
        assert len(bundle["degradation_signals"]) > 0
        assert any("opening" in signal for signal in bundle["degradation_signals"])

    def test_empty_state_never_shows_can_execute_true(self):
        """Empty should never have can_execute=true (gate failure if it does)."""
        for _ in range(10):  # Multiple scenarios
            session_id = self._create_failing_session()
            bundle = self._get_player_session_bundle(session_id)
            if bundle["story_entries"] == []:
                assert bundle["can_execute"] is False, "Gate violation: can_execute=true with empty entries"

    def test_degradation_signals_are_readable(self):
        """Degradation signals must be human-readable (not error codes)."""
        bundle = self._get_player_session_bundle(session_id="failed")
        signals = bundle.get("degradation_signals", [])
        for signal in signals:
            assert isinstance(signal, str)
            assert len(signal) > 5  # Not a single letter or code

    # ... 3 more tests
```

---

## Contract 4: Diagnostics and Observability Truthfulness

### Test Files

**Location:** `world-engine/tests/test_mvp4_contract_diagnostics.py`

**Test Class:** `TestDiagnosticsContract`

**Tests (12 total):** (All fields present, no swallowed exceptions, audit logging)

---

## Contract 5: Narrative Streaming Integration

### Test Files

**Location:** `backend/tests/test_mvp4_contract_streaming.py` + `frontend/tests/test_mvp4_contract_streaming.py`

**Test Classes:** `TestStreamingContract`, `TestStreamingFrontendIntegration`

**Tests (10 total):** (Narrator streaming flag, SSE routing, event delivery)

---

## CI/CD Integration

### GitHub Workflows

**File:** `.github/workflows/mvp4-contracts.yml`

```yaml
name: MVP4 Contract Tests

on: [push, pull_request]

jobs:
  contracts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: |
          docker-compose up -d backend play-service frontend
          sleep 5
      - name: Run Contract Tests
        run: |
          cd D:\WorldOfShadows
          python tests/run_tests.py --suite mvp4-contracts
      - name: Verify Langfuse Traces
        run: |
          # Check Langfuse for audit logs
          curl -s http://localhost:7600/api/traces | jq '.traces[] | select(.name == "backend.story_session_create")'
      - name: Report
        if: always()
        run: |
          python tests/run_tests.py --suite mvp4-contracts --stats
```

**Exit Criteria:**
- All 60+ tests pass (exit code 0)
- Coverage >= 85% for backend, engine, ai_stack
- Langfuse traces include all audit logs
- No exceptions swallowed in diagnostics construction

---

## Test Execution Profiles

### Development (Local)

```bash
# Run contracts during development
python tests/run_tests.py --suite mvp4-contracts --quick

# Run with coverage report
python tests/run_tests.py --suite mvp4-contracts --coverage
```

### Pre-Commit

```bash
# Fast contract check before pushing
python tests/run_tests.py --suite mvp4-contracts --quick --continue-on-failure
```

### CI/CD (GitHub)

```bash
# Full suite with coverage and reporting
python tests/run_tests.py --suite mvp4-contracts --coverage --stats
```

---

## Definition of Done

A contract is **verified** when:

1. ✅ All contract tests pass (no mocks, no stubs)
2. ✅ Tests run against live services (docker-compose stack)
3. ✅ Langfuse traces include audit logging for every operation
4. ✅ Error cases are tested (missing fields, validation failure, fallback)
5. ✅ Coverage >= 85% for modified code
6. ✅ GitHub workflow passes without warnings

---

## Timeline

| Phase | Task | Owner | Deadline |
|-------|------|-------|----------|
| Wave 1 | Create test files structure | AI | 2026-05-05 |
| Wave 1 | Implement Contract 1 tests | AI | 2026-05-05 |
| Wave 2 | Implement Contract 2 tests | AI | 2026-05-06 |
| Wave 3 | Implement Contract 3 tests | AI | 2026-05-07 |
| Wave 4 | Implement Contract 4 tests | AI | 2026-05-08 |
| Wave 5 | Implement Contract 5 tests | AI | 2026-05-09 |
| All | GitHub workflow integration | AI | 2026-05-10 |
| All | Final gate verification | User | 2026-05-11 |

---

## References

- `adr-0032-mvp4-live-runtime-setup-requirements.md` — Contract definitions and acceptance gates
- `tests/run_tests.py` — Test runner and suite configuration
- `tests/TESTING.md` — Testing guidelines and pytest markers
- `.github/workflows/` — CI/CD pipeline configuration
