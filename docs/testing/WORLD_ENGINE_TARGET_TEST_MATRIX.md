# World Engine Target Test Matrix

**Version**: 0.1.12
**Date**: 2026-03-25
**Purpose**: Define comprehensive test coverage structure for the FastAPI-based game runtime engine.

**WAVE 5 (Ongoing)**: Fail-fast configuration, explicit security contracts, and TicketManager hardening
- PLAY_SERVICE_SECRET: fail-fast in production mode if missing/blank
- PLAY_SERVICE_INTERNAL_API_KEY: validation function added, enforcement clarified
- Config startup: deterministic behavior, no silent degradation
- TicketManager: validates secret upfront; missing/blank → explicit TicketError (TASK 5)

---

## Executive Summary

The World Engine (`world-engine/`) is a FastAPI application providing:
- HTTP REST API for game run creation and management
- WebSocket API for real-time multiplayer gameplay
- Authentication via shared secrets and ticket-based access control
- Game runtime management with persistence and snapshots
- Game templates and content loading
- Integration with backend via API keys and internal endpoints

**Current test count**: ~165 tests across API, WebSocket, persistence, runtime, and security layers (updated WAVE 5).

**Target coverage by phase**:
- **Phase 1 (WAVE 0)**: 50 new tests (structure definition and contract tests)
- **Phase 2**: 80 additional tests (performance and advanced contracts)
- **Phase 3**: 40 additional tests (edge cases and recovery)
- **Total target**: ~320 tests

---

## Layer Architecture

### Layer 1: Configuration & Authentication
**Scope**: Environment validation, secret management, API key validation
**Type**: Unit + Contract + Security

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Config Validation | 8 | 10 | unit, contract | test_missing_play_service_secret_fails_in_production_mode, test_blank_play_service_secret_fails_in_production_mode |
| Secret Key Management | 5 | 7 | unit, security, contract | test_secret_min_32_bytes_production, test_play_service_secret_issues_warning_in_test_mode |
| Database URL Validation | 4 | 6 | unit, contract | test_sqlite_url_validates, test_postgres_url_with_auth |
| Redis URL Validation | 2 | 3 | unit, contract | test_redis_url_optional, test_redis_url_requires_netloc |
| Internal API Key Guard | 9 | 9 | security, contract, unit | test_internal_api_key_validation_accepts_valid_key, test_internal_api_key_validation_rejects_blank_when_required |
| **Layer 1 Total** | **28** | **35** | | |

**Security Guarantees**:
- PLAY_SERVICE_SECRET enforced: fail-fast if missing/blank in production mode
- PLAY_SERVICE_SECRET enforced: 32+ bytes in production
- Internal API key: validation enforced when configured (blanks rejected)
- Internal API key: optional in lenient test mode, required in production
- Invalid/missing credentials → 401 Unauthorized
- Database credentials validated but never logged
- Environment variables securely managed (no defaults in code)
- Deterministic startup: no silent degradation of security

**Negative Tests**:
- Empty secret key rejected
- Short secret key rejected in production
- Invalid database scheme rejected
- Missing internal API key → 401
- Tampered API key → 401

---

### Layer 2: HTTP API Layer
**Scope**: REST endpoints, request validation, response schemas, health checks
**Type**: Contract + Integration

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Health Check Endpoint | 2 | 3 | contract, integration | test_health_returns_ok, test_health_no_auth_required |
| Ready Endpoint | 2 | 4 | contract, integration | test_ready_includes_store_info, test_ready_includes_template_count |
| List Templates | 2 | 4 | contract, integration | test_list_templates_returns_array, test_template_fields_present |
| Get Template Details | 0 | 3 | contract, integration | test_get_template_returns_full_schema, test_unknown_template_404 |
| List Runs | 3 | 5 | contract, integration | test_list_runs_returns_array, test_run_fields_valid_types |
| Get Run Details | 3 | 5 | contract, integration | test_get_run_returns_lobby_state, test_get_nonexistent_run_404 |
| Create Run | 5 | 8 | contract, integration, security | test_create_run_returns_run_structure, test_create_run_template_id_required |
| Create Ticket | 3 | 5 | contract, integration | test_ticket_returns_valid_token, test_ticket_ttl_respected |
| Join Context (Internal) | 2 | 4 | contract, integration, security | test_join_context_requires_api_key, test_join_context_creates_seat |
| Get Snapshot | 2 | 4 | contract, integration | test_snapshot_contains_game_state, test_snapshot_for_invalid_run_404 |
| Get Transcript | 1 | 3 | contract, integration | test_transcript_contains_events, test_transcript_ordering |
| Error Responses | 2 | 4 | contract, integration | test_error_response_has_detail_field, test_error_codes_consistent |
| **Layer 2 Total** | **27** | **53** | | |

**Expected Status Codes**:
- 200: Successful operation
- 201: Resource created (if applicable)
- 400: Invalid request parameters
- 401: Missing/invalid credentials
- 403: Insufficient permissions
- 404: Resource not found
- 422: Validation error (Pydantic)
- 500: Server error

**Response Schema Contracts**:
- All responses JSON with consistent error format
- Timestamps in ISO 8601 format
- All required fields present in every response
- Type safety: strings are strings, arrays are arrays, etc.

**Negative Tests**:
- Missing required parameter → 422
- Invalid UUID → 422 or 400
- Non-existent template_id → 404
- Non-existent run_id → 404
- Malformed JSON body → 422
- Extra fields in request ignored (no error)

---

### Layer 3: WebSocket API Layer
**Scope**: WebSocket connection, message handling, real-time updates, disconnection
**Type**: Integration + Contract + Persistence

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| WebSocket Handshake | 3 | 5 | websocket, contract | test_websocket_connects_with_ticket, test_websocket_requires_valid_ticket |
| WebSocket Token Validation | 2 | 4 | websocket, security, contract | test_ws_rejects_invalid_ticket, test_ws_rejects_expired_ticket |
| WebSocket Connection State | 1 | 3 | websocket, contract | test_ws_maintains_connection_state, test_ws_participant_id_tracked |
| Message Sending | 2 | 5 | websocket, contract, integration | test_ws_send_command_to_engine, test_ws_invalid_message_type_rejected |
| Snapshot Broadcasting | 2 | 4 | websocket, contract, integration | test_ws_receives_snapshot_on_state_change, test_ws_snapshot_contains_required_fields |
| Transcript Events | 1 | 3 | websocket, contract, integration | test_ws_transcript_appended_on_event, test_ws_transcript_ordering_guaranteed |
| Graceful Disconnection | 1 | 3 | websocket, integration | test_ws_disconnect_closes_seat, test_ws_disconnect_broadcasts_leave_event |
| Concurrent Connections | 1 | 3 | websocket, integration | test_multiple_ws_connections_independent, test_broadcast_reaches_all_connected |
| Lobby Management | 2 | 4 | websocket, contract, integration | test_ws_lobby_status_transitions, test_ws_all_players_ready_starts_game |
| **Layer 3 Total** | **15** | **34** | | |

**WebSocket Message Contracts**:
- message type (event, command, error, snapshot, transcript)
- data (event/command payload)
- timestamp (ISO 8601 for events)
- required fields always present
- JSON serializable

**Security Guarantees**:
- WebSocket connection requires valid ticket token
- Expired tickets rejected at handshake
- Tampered tokens rejected
- Rate limiting on message frequency (optional)
- Participant isolation (cannot access other players' private data)

**Negative Tests**:
- No ticket in WebSocket URL → connection refused
- Invalid ticket → connection refused
- Expired ticket → connection refused
- Malformed message → error response, connection stays open
- Unknown command type → error response

---

### Layer 4: Runtime & Game Engine
**Scope**: Game loop, entity updates, command execution, state management
**Type**: Unit + Integration + Persistence

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Runtime Manager Initialization | 2 | 4 | unit, contract | test_runtime_manager_creates_instances, test_manager_lists_runs |
| Game Loop Execution | 3 | 5 | integration, unit | test_game_loop_updates_entities, test_game_loop_fixed_timestep |
| Command Execution | 4 | 8 | integration, unit | test_command_moves_character, test_invalid_command_rejected |
| Entity State Updates | 3 | 6 | unit, integration | test_entity_position_updates, test_entity_properties_persist |
| NPC Behaviors | 2 | 5 | unit, integration | test_npc_moves_on_schedule, test_npc_responds_to_player |
| Visibility Rules | 2 | 4 | unit, integration | test_player_visibility_sphere, test_npc_hidden_behind_wall |
| Collision Detection | 1 | 4 | unit, integration | test_collision_prevents_movement, test_collision_response_correct |
| Event Triggering | 2 | 4 | unit, integration | test_event_on_player_enter_room, test_event_chaining |
| Lobby Rules | 2 | 4 | unit, integration | test_min_players_enforced, test_max_players_enforced |
| Template Loading | 1 | 3 | unit, integration | test_template_loads_from_builtin, test_template_schema_valid |
| **Layer 4 Total** | **22** | **47** | | |

**Game State Contracts**:
- Instance id: unique string identifier
- Template id: string matching loaded templates
- Status: pending, lobby, running, completed, failed
- Participants: array of player objects with roles, states
- Created_at: ISO 8601 timestamp
- Consistent across all queries

**Negative Tests**:
- Invalid command type → rejected with error
- Command on invalid target (no such entity) → error
- Movement into wall → rejected or collision response
- Command from unauthorized player → rejected
- Lobby rules not met → game doesn't start

---

### Layer 5: Persistence & Storage
**Scope**: Save/load runs, snapshots, event transcripts, store backends (JSON, SQLAlchemy)
**Type**: Persistence + Integration + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| JSON Store Backend | 4 | 6 | persistence, contract, integration | test_json_store_saves_run, test_json_store_loads_run_correctly |
| SQLAlchemy Store Backend | 2 | 5 | persistence, contract, integration | test_sqlalchemy_store_saves_to_db, test_sqlalchemy_store_transaction_rollback |
| Run Snapshots | 3 | 5 | persistence, contract | test_snapshot_captures_full_state, test_snapshot_json_serializable |
| Run Recovery | 2 | 4 | persistence, integration | test_run_recovered_after_crash, test_recovered_state_consistent |
| Event Transcript | 2 | 4 | persistence, contract | test_transcript_immutable, test_transcript_replay_recreates_state |
| State Serialization | 2 | 4 | persistence, contract, unit | test_entity_state_serializable, test_nested_objects_serializable |
| Store Describe/Health | 1 | 3 | persistence, contract, integration | test_store_describe_includes_backend_type, test_store_health_check |
| Data Durability | 1 | 3 | persistence, integration | test_data_survives_process_restart, test_data_consistent_after_load |
| **Layer 5 Total** | **17** | **34** | | |

**Persistence Contracts**:
- Run data persisted immediately on creation
- Snapshots immutable and timestamped
- Event transcript append-only
- State serialization lossless and reversible
- Load from storage matches save format

**Negative Tests**:
- Corrupted snapshot file → graceful error
- Missing transcript file → run still loadable with snapshot
- Storage backend unavailable → 500 error
- Partial write on crash → recovery from last snapshot

---

### Layer 6: Security & Access Control
**Scope**: Ticket validation, authentication, authorization, input validation
**Type**: Security + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Ticket Generation | 3 | 5 | security, contract, unit | test_ticket_is_jwt, test_ticket_includes_run_id |
| Ticket Validation | 3 | 5 | security, contract, unit | test_ticket_verified_with_secret, test_ticket_signature_required |
| Ticket Expiration | 2 | 4 | security, contract, unit | test_ticket_ttl_enforced, test_expired_ticket_rejected |
| Ticket Tamper Detection | 2 | 4 | security, contract, unit | test_tampered_payload_rejected, test_wrong_secret_rejected |
| Request Validation | 3 | 5 | security, contract, unit | test_run_id_required_string, test_account_id_optional_string |
| Input Sanitization | 2 | 4 | security, contract, unit | test_display_name_sanitized, test_command_payload_validated |
| Authorization Check | 2 | 4 | security, contract, integration | test_participant_cannot_access_other_run, test_admin_bypass_not_implemented |
| Environment Security | 2 | 3 | security, contract, unit | test_secrets_not_in_error_messages, test_database_url_not_exposed |
| **Layer 6 Total** | **19** | **34** | | |

**Security Guarantees**:
- All endpoints require valid ticket or API key
- Tickets time-limited (default TTL)
- Tickets include run_id and participant_id
- No secret key exposure in errors
- Participant isolation enforced
- Input validation on all payloads

**Negative Tests**:
- Missing ticket → 401
- Invalid ticket format → 401
- Expired ticket → 401
- Tampered token → 401
- Wrong shared secret → 401
- SQL injection in display_name → sanitized
- Oversized payload → 422

---

### Layer 7: API Contracts & Advanced Scenarios
**Scope**: Pagination, filtering, sorting, idempotency, versioning, caching
**Type**: Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Response Pagination | 0 | 4 | contract | test_list_endpoints_support_limit_offset, test_pagination_cursor |
| Filtering | 0 | 3 | contract | test_list_runs_filter_by_status, test_list_templates_filter_by_kind |
| Sorting | 0 | 3 | contract | test_list_runs_sort_by_created_at, test_sort_order_ascending_descending |
| Idempotency | 0 | 3 | contract | test_create_run_idempotency_key, test_duplicate_request_same_result |
| Versioning | 0 | 2 | contract | test_api_version_header_present, test_backwards_compatibility |
| Rate Limiting | 0 | 3 | contract | test_rate_limit_headers_present, test_burst_limit_enforced |
| Caching Headers | 0 | 3 | contract | test_cache_control_headers, test_etag_support |
| Compression | 0 | 2 | contract | test_gzip_response_compression, test_accept_encoding_honored |
| CORS Headers | 0 | 2 | contract | test_cors_origins_configured, test_cors_methods_allowed |
| **Layer 7 Total** | **0** | **25** | | |

**Advanced Contract Guarantees**:
- API versioning clear in responses (version header or path)
- Pagination parameters respected (limit, offset, cursor)
- Filtering works on key fields (status, template_id, created_at)
- Sorting direction honored (asc, desc)
- Idempotency keys prevent duplicate operations
- Rate limiting headers (RateLimit-Limit, RateLimit-Remaining)
- Cache headers appropriate for data volatility
- Compression support for large payloads

---

### Layer 8: Performance & Scalability
**Scope**: Load testing, concurrency, memory usage, response times
**Type**: Integration + Slow

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Response Time SLAs | 0 | 3 | slow, integration | test_list_templates_under_100ms, test_create_run_under_500ms |
| Concurrent Connections | 0 | 4 | slow, integration, websocket | test_100_concurrent_ws_connections, test_concurrent_run_creation |
| Memory Leaks | 0 | 2 | slow, integration | test_no_memory_leak_on_repeated_runs, test_websocket_cleanup |
| Store Performance | 0 | 3 | slow, integration, persistence | test_json_store_1000_runs, test_sqlite_store_1000_runs |
| **Layer 8 Total** | **0** | **12** | | |

**Performance SLAs**:
- Health check: <10ms
- List endpoints: <100ms (small dataset)
- Get single resource: <50ms
- Create run: <500ms
- WebSocket message latency: <100ms

**Negative Tests**:
- Slow database query → timeout configured
- Memory growth unbounded → leak detected
- Concurrent writes to same run → handled correctly

---

### Layer 9: Recovery & Error Handling
**Scope**: Crash recovery, error scenarios, graceful degradation
**Type**: Integration + Persistence

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Crash Recovery | 1 | 3 | persistence, integration | test_run_recoverable_after_process_crash, test_partial_write_recovery |
| Corruption Handling | 0 | 3 | persistence, integration | test_corrupted_snapshot_fallback, test_corrupted_transcript_skip |
| Storage Unavailable | 0 | 2 | integration | test_storage_unavailable_returns_500, test_graceful_degradation |
| Error Message Quality | 0 | 2 | contract, integration | test_error_messages_helpful, test_no_stack_trace_in_response |
| **Layer 9 Total** | **1** | **10** | | |

**Recovery Guarantees**:
- Process crash → latest snapshot recoverable
- Partial write → rollback or recovery
- Corrupted data → skip and continue (if possible)
- Storage unavailable → fail fast with clear error

---

## Test Classification Summary

| Layer | Type | Current | Target | Gap |
|-------|------|---------|--------|-----|
| Config & Auth | unit, security, contract | 28 | 35 | +7 |
| HTTP API | contract, integration | 27 | 53 | +26 |
| WebSocket API | websocket, contract, integration | 15 | 34 | +19 |
| Runtime & Engine | unit, integration, persistence | 22 | 47 | +25 |
| Persistence & Storage | persistence, integration, contract | 17 | 34 | +17 |
| Security & Access | security, contract, unit | 19 | 34 | +15 |
| API Contracts | contract | 0 | 25 | +25 |
| Performance | slow, integration | 0 | 12 | +12 |
| Recovery & Errors | integration, persistence, contract | 1 | 10 | +9 |
| **TOTAL** | | **129** | **282** | **+153** |

---

## Marker Breakdown

**Currently Configured**:
```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (external deps)
    security: Security validation
    contract: API contract tests
    websocket: WebSocket tests
    persistence: Save/load and persistence tests
    slow: Slow running tests
    browser: Browser integration tests
```

**Target Test Distribution by Marker**:
- @pytest.mark.unit: ~40 tests (config, engine logic, validation)
- @pytest.mark.integration: ~150 tests (API, WebSocket, runtime, storage)
- @pytest.mark.security: ~35 tests (auth, tokens, access control)
- @pytest.mark.contract: ~195 tests (response schemas, API contracts)
- @pytest.mark.websocket: ~35 tests (connections, messages)
- @pytest.mark.persistence: ~50 tests (storage, snapshots, recovery)
- @pytest.mark.slow: ~15 tests (performance, load testing)

---

## Test Execution Profiles

### Fast Profile (Unit Only)
```bash
pytest -m unit --durations=10
# Expected: ~40 tests, <5 seconds
```

### Quick Profile (Unit + Contract)
```bash
pytest -m "unit or contract" --durations=10
# Expected: ~235 tests, <30 seconds
```

### Standard Profile (All except slow)
```bash
pytest -m "not slow" --durations=10
# Expected: ~259 tests, <60 seconds
```

### Full Profile (All Tests)
```bash
pytest --durations=20
# Expected: ~274 tests, <120 seconds
```

### Security Focus
```bash
pytest -m "security or contract" --durations=10
# Expected: ~230 tests, <40 seconds
```

### Persistence Focus
```bash
pytest -m "persistence or integration" --durations=20
# Expected: ~184 tests, <60 seconds
```

### WebSocket Focus
```bash
pytest -m websocket --durations=10
# Expected: ~35 tests, <20 seconds
```

---

## Implementation Phases

### WAVE 0 (Current)
- Define test matrix structure (this document)
- Update pytest.ini with all markers
- Verify current ~117 tests are properly marked
- Document contract guarantees and negative tests

### WAVE 1 (Phase 1)
- Implement config, auth, and HTTP API gaps (~35 new tests)
- Add WebSocket foundation tests (~10 tests)
- Security contracts complete

### WAVE 2 (Phase 2)
- Implement WebSocket advanced scenarios (~24 tests)
- Runtime and engine comprehensive coverage (~25 tests)
- Persistence and recovery contracts (~15 tests)

### WAVE 3 (Phase 3)
- Advanced API contracts (pagination, filtering, etc.) (~25 tests)
- Performance and load testing (~12 tests)
- Edge cases and error scenarios (~18 tests)

---

## File Structure

```
world-engine/
├── tests/
│   ├── conftest.py                           # Fixtures: app, client, websocket
│   ├── test_config_validation.py             # Layer 1: Config (unit, contract)
│   ├── test_config_contract.py               # Layer 1: Config contract (contract)
│   ├── test_environment_security.py          # Layer 1: Secrets (security, unit)
│   ├── test_internal_api_key_guard.py        # Layer 1: API key (security, unit)
│   ├── test_api_contracts.py                 # Layer 2: HTTP contracts (contract)
│   ├── test_api.py                           # Layer 2: HTTP integration (integration)
│   ├── test_api_security.py                  # Layer 2: HTTP security (security)
│   ├── test_http_runs.py                     # Layer 2: Run endpoints (integration)
│   ├── test_http_tickets.py                  # Layer 2: Ticket endpoints (contract)
│   ├── test_http_health_and_templates.py     # Layer 2: Health, templates (contract)
│   ├── test_http_snapshot_and_transcript.py  # Layer 2: Snapshot, transcript (contract)
│   ├── test_http_join_context.py             # Layer 2: Internal endpoints (security, contract)
│   ├── test_http_api_extended.py             # Layer 2: Advanced contracts (contract)
│   ├── test_websocket_contracts.py           # Layer 3: WebSocket contracts (websocket, contract)
│   ├── test_websocket_connections.py         # Layer 3: WebSocket connections (websocket, integration)
│   ├── test_websocket_messages.py            # Layer 3: Message handling (websocket, integration)
│   ├── test_websocket_security.py            # Layer 3: WebSocket auth (websocket, security)
│   ├── test_runtime_engine.py                # Layer 4: Game loop (unit, integration)
│   ├── test_runtime_manager.py               # Layer 4: Runtime manager (unit, integration)
│   ├── test_runtime_commands.py              # Layer 4: Commands (unit, integration)
│   ├── test_runtime_visibility.py            # Layer 4: Visibility (unit, integration)
│   ├── test_runtime_lobby_rules.py           # Layer 4: Lobby (unit, integration)
│   ├── test_runtime_open_world.py            # Layer 4: Open world (integration)
│   ├── test_runtime_npc_behaviors.py         # Layer 4: NPCs (unit, integration)
│   ├── test_store.py                         # Layer 5: Store basic (persistence)
│   ├── test_store_json.py                    # Layer 5: JSON backend (persistence)
│   ├── test_store_sqlalchemy.py              # Layer 5: SQLAlchemy backend (persistence)
│   ├── test_persistence_contracts.py         # Layer 5: Persistence contracts (persistence, contract)
│   ├── test_data_integrity.py                # Layer 5: Data durability (persistence, integration)
│   ├── test_api_security.py                  # Layer 6: Access control (security)
│   ├── test_backend_bridge_contract.py       # Layer 6: Ticket validation (security, contract)
│   ├── test_compatibility_contracts.py       # Layer 7: Compatibility (contract)
│   ├── test_api_advanced_contracts.py        # Layer 7: Advanced contracts (contract)
│   ├── test_performance_contracts.py         # Layer 8: Performance (slow, integration)
│   ├── test_recovery_contracts.py            # Layer 9: Recovery (persistence, integration)
│   └── test_error_contracts.py               # Layer 9: Error handling (contract, integration)
└── pytest.ini                                # Markers configuration
```

---

## Success Criteria

By end of WAVE 0:
- pytest.ini has all 8 markers defined
- pytest --collect-only works and shows proper marker assignments
- All current tests are marked with appropriate layer markers
- No marker warnings on test collection
- Matrix document is complete and actionable

By end of WAVE 1:
- 152 total tests in suite
- Layer 1 & 2 at 100% target coverage
- Security marker on all security-critical tests
- Contract marker on all public API contracts
- WebSocket tests establish baseline connectivity

By end of WAVE 3:
- 274 total tests in suite
- All layers at 100% target coverage
- Performance SLAs verified
- Recovery and error scenarios comprehensive
- Full test execution <120 seconds

---

## Notes for Implementation

1. **WebSocket Testing**: Use test client's WebSocket context manager; maintain connection state across multiple operations.
2. **Ticket Management**: Test both JWT generation and validation; verify TTL and expiration.
3. **Persistence Testing**: Test both JSON and SQLAlchemy backends; verify data consistency.
4. **Concurrency Testing**: Use threading/asyncio to simulate multiple players; verify no race conditions.
5. **Performance Testing**: Mark slow tests with @pytest.mark.slow; run separately in CI.
6. **Error Scenarios**: Test all error paths; verify error messages don't leak sensitive info.
7. **State Management**: Verify game state is consistent across snapshots, transcripts, and live updates.
8. **Integration Points**: Test backend bridge contracts (ticket validation with shared secret).
