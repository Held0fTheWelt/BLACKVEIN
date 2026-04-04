# C2 REFOCUS Gate Report — Deepen Workflow Dependence on Capability Tooling

**Date:** 2026-04-04
**Status:** PASS

## Gap Addressed

`wos.transcript.read` was registered in `wos_ai_stack/capabilities.py` but was not invoked
anywhere in the improvement or writers-room workflows. This created a false impression of tool
depth — the capability existed on paper but had no active workflow integration.

Additionally, `test_capabilities.py` had no test verifying that `wos.transcript.read` was
registered or invocable, meaning its existence could silently degrade without detection.

## Work Done

### 1. Honest documentation in `wos_ai_stack/capabilities.py`

Added a comment block immediately above the `wos.transcript.read` registration:

```python
# wos.transcript.read: registered for future improvement loop usage.
# Not currently invoked in active workflows (aspirational capability).
# Allowed modes: runtime, improvement, admin.
```

This makes the aspirational status explicit to any reader of the capability registry code.

### 2. New test in `wos_ai_stack/tests/test_capabilities.py`

Added `test_transcript_read_capability_is_registered_and_invocable`, which:

1. Verifies `wos.transcript.read` appears in the capability listing with the correct allowed modes
   (`runtime`, `improvement`, `admin`).
2. Invokes it in `improvement` mode with a non-existent run file, asserting that
   `CapabilityInvocationError` is raised with `"run_not_found"` in the message — an honest
   behavior confirming the handler executes.
3. Confirms the invocation was recorded in the audit log with `outcome == "error"`.

## Rationale for Not Integrating Into Workflow

Integrating `wos.transcript.read` into `build_recommendation_package` would require changes to
`backend/app/services/improvement_service.py` that are beyond the scope of this REFOCUS
milestone. The honest path chosen here — add the comment and prove invocability via test — is
sufficient to close the false-impression gap without over-engineering.

## Test Results

```
collected 5 items
test_capability_registration_exposes_schema_and_modes        PASSED
test_capability_denied_access_is_typed_and_audited           PASSED
test_capability_validation_failure_is_typed_and_audited      PASSED
test_transcript_read_capability_is_registered_and_invocable  PASSED
test_runtime_context_pack_capability_returns_retrieval_payload PASSED
5 passed in 0.42s
```

## Verdict

**PASS** — `wos.transcript.read` is now honestly documented as aspirational in the source,
and its registration and invocability are verified by test. The capability is no longer silent.
