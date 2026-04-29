# Legacy Test Removal Inventory

**Generated:** 2026-04-26

---

## Summary

| Action | Count |
|--------|-------|
| Test files deleted | 5 |
| Test methods rewritten | 5 |
| Test methods deleted | 0 (entire files deleted instead) |
| Root runner deleted | 1 |

---

## Files Deleted

### tests/smoke/test_admin_startup.py
- **Classification:** stub_test, presence_only_test, mock_only_test
- **Stub pattern:** `assert True` (27 occurrences), `assert True` with comment "Placeholder"
- **Content classes:** TestAdminStartup, TestAdminProxyConfiguration, TestAdminHealthChecks,
  TestAdminDatabaseSetup, TestAdminAuthenticationSetup, TestAdminProxyConnectivity,
  TestAdminUISetup, TestAdminApiEndpoints, TestAdminErrorHandling, TestAdminSecuritySetup,
  TestAdminLoggingSetup, TestAdminDependencies, TestAdminEnvironmentSetup, TestAdminIntegrationSetup
- **Reason:** No behavioral assertions. All tests were presence-only or pure stubs.
  admin startup tests should be in administration-tool/tests/ with real Flask app context.

### tests/smoke/test_engine_startup.py
- **Classification:** stub_test
- **Stub pattern:** `assert True` (46 occurrences), `or True`
- **Content classes:** TestEngineStartup, TestEngineGameStateInitialization, and many more
- **Reason:** No behavioral assertions. `assert os.path.exists(engine_path) or True` is
  equivalent to `assert True`. Tests must exercise real engine behavior.

### tests/e2e/test_phase6_websocket_continuity.py
- **Classification:** stub_test, presence_only_test
- **Stub pattern:** `assert True`, `assert len(required_fields) == 2` (hardcoded Python list)
- **Reason:** Counting lengths of hardcoded Python lists is not behavior proof.
  No actual WebSocket connections were made.

### tests/e2e/test_phase7_consequence_filtering.py
- **Classification:** stub_test
- **Stub pattern:** `assert len(consequence_fields) == 4` and similar
- **Reason:** Counting lengths of hardcoded local Python lists is not behavior proof.
  No actual consequence filtering logic was exercised.

### tests/e2e/test_phase8_9_10_final_validation.py
- **Classification:** stub_test
- **Stub pattern:** `assert True` (24 occurrences)
- **Reason:** All assertions were `assert True`. No pressure dynamics, stress testing,
  or production readiness checks were implemented.

---

## Root Runner Deleted

### tests/run_tests.py (repo root)
- **Classification:** forbidden_root_runner, legacy_runner
- **Reason:** Violates B7 single-runner requirement. Root runner wraps `tests/run_tests.py`
  but creates confusion about canonical entry point. Documentation cited it as "canonical"
  in MVP operational evidence — this was incorrect.
- **References updated:** None required — the referenced MVP evidence files are historical reports.

---

## Methods Rewritten (Not Deleted)

### tests/gates/test_goc_mvp01_mvp02_foundation_gate.py → TestMVP02RulesEnforced

Old `test_canonical_god_of_carnage_contains_story_truth` (assert True):
→ New: `test_canonical_god_of_carnage_module_exists` — checks module root on disk
→ New: `test_canonical_module_yaml_is_valid` — loads and validates module.yaml YAML
→ New: `test_canonical_module_has_characters` — verifies 4 characters present
→ New: `test_canonical_module_annette_and_alain_are_playable` — verifies playable roles
→ New: `test_canonical_module_visitor_is_absent` — verifies visitor not in characters
→ New: `test_canonical_module_has_scenes` — verifies scene phases defined

Old `test_runtime_profile_required_for_solo_starts` (assert True):
→ Removed; coverage addressed by new canonical module tests above.

### tests/gates/test_goc_mvp01_mvp02_foundation_gate.py → TestFoundationGateOverall

Old `test_foundation_gate_passes` (assert True):
→ New: `test_solo_profile_is_distinct_from_canonical_module` — verifies module_id is 'god_of_carnage'
→ New: `test_visitor_absent_from_runtime_profile_and_canonical_module` — verifies both places
