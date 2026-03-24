# Administration Tool Target Test Matrix

## Test Layers

### Unit Tests
- **Coverage Goal**: 80%+ of business logic
- **Rationale**: Validate individual functions/classes in isolation
- **Examples**:
  - `test_config_loads_valid_yaml`
  - `test_user_validator_rejects_invalid_email`
  - `test_route_handler_returns_200_on_success`
- **Type**: Target-contract (new behavior)

### Integration Tests
- **Coverage Goal**: All external service interactions
- **Rationale**: Validate component interactions (DB, API, auth)
- **Examples**:
  - `test_db_connection_pool_reuses_connections`
  - `test_auth_middleware_validates_jwt`
  - `test_template_rendering_with_context`
- **Type**: Mix (contract + existing behavior)

### Security Tests
- **Coverage Goal**: 100% of security-critical paths
- **Rationale**: Validate OWASP compliance, authZ/authN
- **Examples**:
  - `test_proxy_forbidden_paths_returns_403`
  - `test_csrf_token_required_on_stateful_requests`
  - `test_sql_injection_prevented_in_queries`
- **Type**: Target-contract (critical)

### Contract Tests
- **Coverage Goal**: All public API endpoints
- **Rationale**: Validate interface stability, versioning
- **Examples**:
  - `test_api_version_header_present`
  - `test_error_response_schema_valid`
  - `test_rate_limit_headers_present`
- **Type**: Target-contract (interface stability)

## Test Classification

| Test Type | Target-Contract | Existing Behavior |
|-----------|-----------------|-------------------|
| Unit      | 60%             | 40%               |
| Integration | 40%           | 60%               |
| Security  | 80%             | 20%               |
| Contract  | 100%            | 0%                |

## Rationale Summary
- **Unit**: Fast feedback, isolate logic bugs
- **Integration**: Catch wiring issues, external deps
- **Security**: Prevent vulnerabilities, compliance
- **Contract**: Ensure API stability, consumer contracts
