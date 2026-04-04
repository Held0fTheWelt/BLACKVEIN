# AI Stack Release Readiness Checklist

Use this checklist before calling the unified AI stack **production-grade**. Items are concrete and verifiable; partial credit should be documented explicitly.

## 1. Observability coverage

- [ ] **Story path**: A single `X-WoS-Trace-Id` can be followed from backend session turn through World-Engine HTTP to `repro_metadata.trace_id` on the latest turn diagnostics.
- [ ] **Workflows**: Writers-Room and improvement endpoints attach `trace_id` (header or body) and emit `workflow.run` audit events.
- [ ] **Logs**: `wos.audit` and `wos.world_engine.audit` are consumed by your environment (aggregator, log shipper, or stdout collection)—not only visible in dev consoles.

## 2. Trace continuity

- [ ] Backend internal httpx calls to World-Engine story endpoints send `X-WoS-Trace-Id` when a trace exists.
- [ ] World-Engine echoes the same id on responses.
- [ ] LangGraph `repro_metadata` includes the trace id and graph version.

## 3. Audit completeness

- [ ] Session turn bridge successes and failures emit `world_engine.bridge` with `failure_class` when applicable.
- [ ] World-Engine emits `story.turn.execute` for each turn (hashed input).
- [ ] Graph execution exceptions emit `story.runtime.failure` before propagating.

## 4. Governance surface availability

- [ ] `GET /api/v1/admin/ai-stack/session-evidence/<session_id>` returns real bundle or explicit `backend_session_not_found`.
- [ ] When World-Engine is down, bundle includes `bridge_errors` with `world_engine_unreachable`.
- [ ] Session evidence includes repaired-layer signals for runtime, tool usage, and available writers-room/improvement artifacts.
- [ ] `GET /api/v1/admin/ai-stack/release-readiness` reports `partial` whenever repaired-path evidence is missing.
- [ ] Administration-tool **AI Stack** page loads and can call the APIs when JWT + feature access are present.

## 5. Secrets and privacy compliance

- [ ] Spot-check audit and diagnostics JSON for absent JWTs, keys, and internal shared secrets.
- [ ] Confirm production log retention and access controls for diagnostics that may contain player text.

## 6. Test health

- [ ] `backend/tests/test_m11_ai_stack_observability.py` passes.
- [ ] `backend/tests/test_observability.py` passes.
- [ ] `wos_ai_stack/tests/test_langgraph_runtime.py` passes.
- [ ] `world-engine/tests/test_trace_middleware.py` and `world-engine/tests/test_story_runtime_api.py` pass.
- [ ] Run broader `pytest` in CI or locally when feasible; document skipped scopes.

## 7. Critical proof flows

- [ ] **God of Carnage**: World-Engine story session + turn tests succeed (`module_id: god_of_carnage`).
- [ ] Improvement loop: create variant → run experiment → list recommendations.
- [ ] Writers-Room review endpoint returns retrieval + capability audit.

## 8. Known blockers and rollback

- [ ] Document any environment dependency (play service URL, internal API key, model provider availability).
- [ ] Rollback: revert M11 commit; disable AI Stack admin nav if UI-only rollback needed; World-Engine and backend remain backward compatible on story API shape (additive fields).

## Sign-off

| Role | Name | Date | Notes |
|------|------|------|-------|
| Engineering | | | |
| Security / Privacy | | | |
