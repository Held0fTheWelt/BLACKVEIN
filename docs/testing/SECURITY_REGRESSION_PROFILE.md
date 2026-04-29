# Security Regression Profile

**Version**: 1.0
**Date**: 2026-03-25
**Status**: ACTIVE

This document defines security-focused test profiles and regression gates to prevent security vulnerabilities from being introduced during development.

---

## Purpose

Security regression testing focuses on:
1. **Authentication**: User login, session management, token validation
2. **Authorization**: Permission checking, privilege escalation prevention
3. **Data Protection**: Password hashing, encryption, secure storage
4. **Input Validation**: Prevention of injection attacks, XSS, CSRF
5. **Rate Limiting**: Brute force prevention, DoS mitigation
6. **API Security**: Endpoint access control, response validation

---

## Security Test Profile

### Quick Command

Run all security tests:
```bash
pytest -m security -v --tb=short
```

### Test Breakdown

**Total Security Tests**: 219+

| Suite | Count | Focus | Status |
|-------|-------|-------|--------|
| World Engine | 114+ | Game security, player data isolation | ✓ Passing |
| Admin Tool | 56+ | Admin access control, privilege escalation | ✓ Passing |
| Backend | 49+ | Auth, permissions, data protection | ✓ Passing |

---

## Authentication Security Tests

### Backend Authentication (20+ tests)

```bash
cd backend && pytest -m security -k auth -v
```

**Tests Cover**:
- User login with valid credentials
- Login fails with invalid credentials
- Password comparison uses secure hash
- Session tokens are properly validated
- JWT tokens are properly signed
- Token expiration is enforced
- Multiple login attempts tracked (rate limiting prep)

**Key Tests**:
- `test_login_requires_valid_credentials`
- `test_password_stored_as_hash_not_plaintext`
- `test_session_token_validated_on_request`
- `test_expired_token_rejected`
- `test_invalid_signature_token_rejected`

---

### Admin Tool Authentication (15+ tests)

```bash
cd administration-tool && pytest -m security -k auth -v
```

**Tests Cover**:
- Admin login requires valid credentials
- Admin sessions properly managed
- Session fixation prevented
- Cross-site request forgery (CSRF) prevented
- Admin privilege level checked on sensitive actions

**Key Tests**:
- `test_admin_login_requires_credentials`
- `test_session_fixation_prevented`
- `test_csrf_token_validated`
- `test_privilege_escalation_blocked`

---

### Engine Authentication (12+ tests)

```bash
cd world-engine && pytest -m security -k auth -v
```

**Tests Cover**:
- Player authentication from backend tokens
- WebSocket connection authentication
- Player session validation
- Token refresh mechanism

---

## Authorization Security Tests

### Backend Authorization (15+ tests)

```bash
cd backend && pytest -m security -k "auth or permission" -v
```

**Tests Cover**:
- User endpoint accessible only by authenticated users
- Admin endpoints only accessible by admins
- Role-based access control enforced
- Permission checks on resource modification
- Cannot modify other users' data
- Cannot delete own admin account

**Key Tests**:
- `test_user_endpoint_requires_auth`
- `test_admin_endpoint_requires_admin_role`
- `test_cannot_modify_other_users`
- `test_privilege_escalation_prevented`
- `test_cannot_delete_self_as_admin`

---

### Admin Tool Authorization (20+ tests)

```bash
cd administration-tool && pytest -m security -k permission -v
```

**Tests Cover**:
- Admin actions require admin role
- Moderation actions require moderator+ role
- User management restricted to super_admin
- Admin cannot grant themselves higher privileges
- Audit trail records all admin actions

**Key Tests**:
- `test_user_deletion_requires_super_admin`
- `test_role_modification_restricted`
- `test_cannot_escalate_own_privileges`
- `test_audit_trail_records_actions`

---

### Engine Authorization (12+ tests)

```bash
cd world-engine && pytest -m security -k permission -v
```

**Tests Cover**:
- Player can only access own character
- Admin players have elevated privileges
- Player data isolation enforced
- Cannot modify other player data

---

## Data Protection Security Tests

### Password Security (8+ tests)

```bash
cd backend && pytest -m security -k password -v
```

**Tests Cover**:
- Passwords hashed using strong algorithm (bcrypt/Argon2)
- Plain text passwords never logged
- Password changed requires old password
- Password reset tokens expire
- Password history prevents reuse

**Key Tests**:
- `test_password_stored_as_hash`
- `test_password_never_logged`
- `test_password_change_requires_old_password`
- `test_password_reset_token_expires`

---

### Sensitive Data Protection (10+ tests)

**Tests Cover**:
- API responses don't include sensitive data
- Email addresses properly hashed where appropriate
- Session data encrypted
- Database connections use encryption
- Secrets not hardcoded in code

---

### Secure Storage (6+ tests)

```bash
cd backend && pytest -m security -k "storage or encrypt" -v
```

**Tests Cover**:
- Passwords stored with salt
- Encryption keys properly managed
- Sensitive data masked in logs
- Database backups encrypted

---

## Input Validation Security Tests

### SQL Injection Prevention (5+ tests)

```bash
cd backend && pytest -m security -k injection -v
```

**Tests Cover**:
- SQL queries use parameterized statements
- User input sanitized before DB queries
- ORM prevents SQL injection

---

### XSS Prevention (5+ tests)

**Tests Cover**:
- User input escaped in responses
- Script tags filtered from user content
- HTML entities properly encoded

---

### CSRF Prevention (3+ tests)

```bash
cd administration-tool && pytest -m security -k csrf -v
```

**Tests Cover**:
- CSRF tokens required for state-changing requests
- Token validated before processing
- Invalid/missing tokens rejected

---

## Rate Limiting Security Tests

### Brute Force Prevention (8+ tests)

```bash
pytest -m "security and rate_limit" -v
```

**Tests Cover**:
- Login attempts rate limited
- Failed attempts tracked per user
- Account lockout after N failures
- Lockout timeout configured
- IP-based rate limiting

---

## API Security Tests

### Endpoint Access Control (10+ tests)

```bash
cd backend && pytest -m "security and api" -v
```

**Tests Cover**:
- Public endpoints don't require auth
- Private endpoints require auth
- Admin endpoints check role
- Invalid auth headers rejected
- Missing auth headers rejected

---

### Response Validation (5+ tests)

**Tests Cover**:
- API responses properly formatted
- No sensitive data in responses
- Error messages don't leak information
- Response headers secure (X-Frame-Options, etc.)

---

## Security Test Markers

Add markers to tests for security categorization:

```python
@pytest.mark.security  # All security tests
@pytest.mark.security
@pytest.mark.authentication  # Auth-specific
def test_login_validation():
    pass

@pytest.mark.security
@pytest.mark.authorization  # Authz-specific
def test_role_check():
    pass

@pytest.mark.security
@pytest.mark.data_protection  # Data protection
def test_password_hashing():
    pass

@pytest.mark.security
@pytest.mark.input_validation  # Input validation
def test_sql_injection_prevention():
    pass

@pytest.mark.security
@pytest.mark.rate_limiting  # Rate limiting
def test_brute_force_prevention():
    pass
```

---

## pytest.ini Configuration

Add security markers to `pytest.ini`:

```ini
[pytest]
markers =
    security: Security-related tests
    authentication: Authentication tests
    authorization: Authorization tests
    data_protection: Data protection tests
    input_validation: Input validation tests
    rate_limiting: Rate limiting tests
```

---

## Security Regression Gate

### When to Run

- Before every merge to master
- After any auth/security code changes
- After any API changes
- During security audit
- Before releasing to production

### Command

```bash
# Quick security check (all suites)
pytest -m security -v --tb=short

# With coverage reporting
pytest -m security -v --cov=app --cov-report=term-missing

# By category
pytest -m "security and authentication" -v
pytest -m "security and authorization" -v
pytest -m "security and data_protection" -v
```

### Acceptance Criteria

**MUST PASS**:
- All 219+ security tests
- 100% pass rate (0 failures)
- No authentication bypasses
- No authorization violations
- No injection vulnerabilities detected

**CANNOT MERGE IF**:
- Any security test fails
- Coverage drops below baseline
- New vulnerability detected
- Existing waiver broken

---

## Security Issues and Waivers

### Known Security Issues

**NONE DOCUMENTED** - All current tests passing.

### Security Waivers

Waivers for security tests are rare and require:
1. Security team approval (required)
2. Risk assessment (required)
3. Mitigation plan (required)
4. Expiration date (required)
5. Executive sign-off (for critical)

### Waiver Process

1. Identify security issue
2. File security issue: `[SECURITY] Issue: <description>`
3. Provide risk assessment
4. Propose mitigation
5. Get security team approval
6. Document in XFAIL_POLICY.md
7. Set expiration date (e.g., 30 days)
8. Remove waiver after fix or expiration

---

## Security Best Practices

### For Developers

1. **Run security tests locally** before committing
2. **Review security test output** for new findings
3. **Update tests** when adding new features
4. **Validate input** at boundaries (user input, API calls)
5. **Use parameterized queries** for database
6. **Hash passwords** immediately on storage
7. **Avoid logging** sensitive data
8. **Use HTTPS** for all connections
9. **Validate tokens** on every request
10. **Check permissions** before data access

### For Code Review

1. **Review authentication logic** carefully
2. **Check input validation** for injections
3. **Verify permission checks** present
4. **Look for sensitive data** in logs
5. **Check for hardcoded secrets** or tokens
6. **Validate error messages** don't leak info
7. **Ensure rate limiting** configured
8. **Check CSRF protection** on forms
9. **Verify encryption** used appropriately
10. **Test privilege escalation** prevention

---

## Security Testing Workflow

### Development

```bash
# 1. Before committing
pytest -m security -v

# 2. After auth/security changes
pytest -m "security and authentication" -v

# 3. Full test suite
python run_tests.py --suite all --quick
```

### Pre-Deployment

```bash
# 1. Security regression gate
pytest -m security -v --tb=short

# 2. Full validation
python run_tests.py --suite all --coverage

# 3. Check coverage maintained
# Backend should be 85%+
```

### Post-Deployment

1. Monitor for security alerts
2. Review audit logs daily
3. Watch for unusual access patterns
4. Run security tests in production periodically

---

## Security Monitoring

### Automated Checks

- **PR checks**: Security tests run on every PR
- **Scheduled**: Full security audit weekly
- **Alerts**: Immediate notification on failure
- **Logs**: All security events logged

### Manual Review

- **Weekly**: Review security test results
- **Monthly**: Security audit of code
- **Quarterly**: Penetration testing
- **As-needed**: Incident response

---

## Updating Security Tests

When new security concerns arise:

1. **Write test** that catches the vulnerability
2. **Verify test fails** with vulnerable code
3. **Fix code** to make test pass
4. **Add to security profile** for future
5. **Document in security_issues.md** if critical
6. **Update procedures** to prevent recurrence

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-25 | Initial security regression profile; 219+ tests |
