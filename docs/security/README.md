# Security Documentation

Security policies, threat models, vulnerability management, and compliance.

## 🔐 Security Overview

### [Security Audit Report](./AUDIT_REPORT.md)
Latest security assessment and remediation status.

### [At-rest encryption evidence](./AT_REST_ENCRYPTION.md)
Current evidence, known gaps, and the completion plan for database, runtime-store, Docker-volume, and backup encryption.

### [Rate-limit inventory](./rate-limit-inventory.md)
Shared route/tool inventory for API, Auth, admin-sensitive route policy, and MCP rate limits.

### [Security governance administration](../admin/security-governance.md)
Admin operator surface for CSRF matrix policy, cookie posture, same-origin proxy boundaries, secret-store policy, Redis hardening evidence, storage-layer encryption evidence, and the `security_governance.v1` payload.

### [Provider credential governance](./PROVIDER_CREDENTIAL_GOVERNANCE.md)
Provider-key ownership, governed runtime access, and the `local_only` boundary for local Langfuse evaluator evidence.

**Current Status:**
- ✅ Authentication hardened (JWT + refresh tokens)
- ✅ Session security improved (secure cookie flags and explicit CSRF matrix)
- ✅ Central rate-limit inventory visible across API, Auth, MCP, and Security info surfaces
- ✅ Security governance policy and storage-layer evidence visible in the administration tool
- ⚠️ Production rate-limit tuning needs live/staging telemetry before limit changes are claimed
- ✅ CORS configured appropriately
- ✅ Input validation implemented
- ✅ Provider access routed through backend governance / secret-manager boundaries
- ✅ Local evaluator scores marked as `local_only`
- ⚠️ Full at-rest encryption not established; see the evidence plan
- ⚠️ TLS enforcement review needed

## 🛡️ Core Security Features

### Authentication
- **Type:** JWT-based with refresh tokens
- **Tokens:**
  - Access token: 24-hour lifetime
  - Refresh token: 7-day lifetime (stored in database)
- **Revocation:** Refresh tokens can be revoked immediately
- **Password:** Salted PBKDF2 hashing
- **Implementation:** See [Backend API reference](../api/REFERENCE.md) and [Service boundaries](../technical/architecture/service-boundaries.md)

### Authorization
- **Model:** Role-based access control (RBAC)
- **Roles:**
  - `user` - Regular user
  - `moderator` - Forum moderation
  - `admin` - Full system access
- **Enforcement:** Service-level checks on all protected endpoints

### Session Management
- **Cookies:** HttpOnly with SameSite policies (`Lax` for Flask session cookies; stricter per-flow cookies where configured)
- **HTTPS:** Enforced in production deployments
- **CSRF:** Explicitly split between CSRF-protected web routes and Bearer-token JSON APIs
- **Matrix:** See [CSRF Matrix](csrf-matrix.md) for every mutating cookie-relevant flow
- **Governance:** Operators can review and edit target security policy in [Security governance administration](../admin/security-governance.md); enforcement boundaries remain code/deployment-owned
- **Timeout:** Admin tool sessions are configured for a one-hour lifetime

### Rate Limiting
- **HTTP/API routes:** Flask-Limiter decorators and defaults, exposed through the API catalog and info pages
- **Auth routes:** Auth-specific route limits visible in the Auth info surface
- **MCP tools:** Shared conservative JSON-RPC dispatch limit mirrored into `tools/list`
- **Production tuning:** Requires `rate_limit_hits_total`, quota utilization, retry/backoff, and edge throttle telemetry with hashed limiter keys
- **Inventory:** See [Rate-limit inventory](./rate-limit-inventory.md)

### Data Protection
- **In Transit:** HTTPS/TLS (enforced in production)
- **At Rest:** Partial only. Governed provider credentials use field-level envelope encryption and encrypted exports are available when explicitly requested. Storage-layer evidence is governed in the Administration Tool, but local SQLite, JSON stores, Redis AOF, Langfuse Docker volumes, and backups need complete evidence before a full at-rest claim is valid.
- **Detailed status:** [At-rest encryption evidence and completion plan](./AT_REST_ENCRYPTION.md)
- **Provider credentials:** Direct provider API keys must not be treated as Compose-owned runtime configuration. Use [Provider credential governance](./PROVIDER_CREDENTIAL_GOVERNANCE.md) for the governed credential path and local evaluator evidence rules.
- **Sensitive Fields:**
  - Passwords: Never logged or returned in API responses
  - Tokens: Stored hashed in database
  - Email: Only exposed to user and admins

## 🚨 Security Best Practices

### For Developers
1. **Never commit secrets** - Use local environment variables and `.env`/`.env.local` for development only
2. **Validate all input** - Use SQLAlchemy ORM to prevent SQL injection
3. **Sanitize output** - Escape HTML in templates (Jinja2 does this by default)
4. **Use HTTPS** - All production traffic must be encrypted
5. **Log security events** - Login attempts, permission denials, etc.
6. **Test security** - Include security test cases in test suite
7. **Keep dependencies updated** - Regular security updates

### For Operations
1. **Backup encryption keys** - Store separately from backups
2. **Monitor access logs** - Set up alerting for suspicious patterns
3. **Rotate credentials** - Regular password and API key rotation
4. **Patch immediately** - Critical security patches within 24 hours
5. **Audit permissions** - Quarterly review of who has access to what
6. **Incident response plan** - Clear escalation procedures
7. **Use a production secret store** - Production secrets should come from a dedicated store with rotation, audit, and access separation, not from a committed or hand-managed `.env`
8. **Record security governance** - Use the Administration Tool Security Governance page to document desired posture and review drift without storing raw secret values
9. **Keep local evaluator evidence local** - Judge scores from local Langfuse must stay marked as `local_only` unless a production/staging evidence path is explicitly documented

## 📋 Vulnerability Management

### Reporting Security Issues
**Do not** create public issues for security vulnerabilities.

Instead:
1. Email security team: `security@worldofshadows.com`
2. Include: Vulnerability description, reproduction steps, impact
3. Response time: Within 24 hours

### Vulnerability Disclosure Policy
- We follow responsible disclosure
- 90-day fix deadline for critical issues
- Public disclosure only after patch released
- Credit given to reporters (optional)

## 🔍 Threat Model

### Assets at Risk
- **User Accounts:** Passwords, email, profile data
- **Game State:** Run data, player positions
- **Community Content:** Forum posts, wiki pages
- **Administrative Data:** System configuration, user permissions

### Threat Scenarios

#### 1. Unauthorized Access
- **Threat:** Attacker gains user credentials
- **Mitigation:** Strong password requirements, 2FA (future)
- **Detection:** Login attempt monitoring, impossible travel detection

#### 2. SQL Injection
- **Threat:** Malicious input in database queries
- **Mitigation:** SQLAlchemy ORM (parameterized queries), input validation
- **Detection:** Query logging, anomaly detection

#### 3. Cross-Site Scripting (XSS)
- **Threat:** Malicious JavaScript in user content
- **Mitigation:** HTML sanitization, Content-Security-Policy header
- **Detection:** CSP violation reports

#### 4. Cross-Site Request Forgery (CSRF)
- **Threat:** Forged requests from user's browser
- **Mitigation:** Global Flask-WTF CSRF for backend web routes, SameSite cookies, and Bearer-token-only backend API calls
- **Detection:** Regression tests pin the explicit [CSRF Matrix](csrf-matrix.md), including cookie stripping on proxies

#### 5. Distributed Denial of Service (DDoS)
- **Threat:** Overwhelming service with requests
- **Mitigation:** Rate limiting, WAF (CDN in production)
- **Detection:** Traffic pattern analysis

## 🔧 Security Configuration

### Environment Variables (Required in Production)

Use these variable names as the runtime contract. In production, materialize them through your deployment secret store or orchestrator-native secrets before the services start; keep repository `.env` usage for local `docker-up.py` workflows.

```bash
# Authentication
SECRET_KEY=<random-string-32-chars>
JWT_SECRET_KEY=<random-string-32-chars>

# Deployment
HTTPS_ONLY=1                    # Enforce HTTPS
SECURITY_HEADERS=1              # Add security headers

# Database
DATABASE_URI=postgresql://...   # Use PostgreSQL in production

# Session
SESSION_COOKIE_SECURE=1         # HTTPS only
SESSION_COOKIE_HTTPONLY=1       # No JavaScript access
SESSION_COOKIE_SAMESITE='Lax'
```

### Security Headers (Implemented)
```
Strict-Transport-Security: max-age=31536000
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'
```

## 📊 Security Testing

### Test Coverage
- ✅ Authentication tests (login, logout, refresh)
- ✅ Authorization tests (role-based access)
- ✅ Session security tests (cookie flags)
- ✅ Input validation tests (XSS, SQL injection)
- ✅ CSRF matrix tests for web routes, Bearer APIs, and same-origin proxies
- ✅ Rate-limit inventory tests for API/Auth/MCP info surfaces and MCP tool metadata
- ✅ Production-tuning telemetry contract rendered in the Security Features info view

### Running Security Tests
```bash
# Security-focused test suite
python run_tests.py --suite all  # Includes security tests

# Security profile only
pytest tests/ -m security -v

# Coverage report
pytest tests/ --cov=app --cov-report=html
```

**See:** [Testing Guide](../testing/README.md)

## 🚀 Security Roadmap

### Phase 1 (Current)
- ✅ Authentication hardening
- ✅ Session security
- ✅ Input validation
- ✅ CORS configuration

### Phase 2 (Q2 2026)
- 🔄 Complete at-rest encryption evidence for database, runtime-store, volume, and backup surfaces
- 🔄 Two-factor authentication (2FA)
- 🔄 Security event logging

### Phase 3 (Q3 2026)
- 📋 OAuth2/OIDC integration
- 📋 Hardware security keys
- 📋 Advanced threat detection

## Related Documentation

- [At-rest encryption evidence and completion plan](./AT_REST_ENCRYPTION.md)
- [Rate-limit inventory](./rate-limit-inventory.md)
- [Provider credential governance and local evaluator evidence](./PROVIDER_CREDENTIAL_GOVERNANCE.md)
- [ADR-0047: At-rest encryption evidence boundary](../ADR/adr-0047-at-rest-encryption-evidence-boundary.md)
- [ADR-0048: Central route and MCP rate-limit inventory](../ADR/adr-0048-central-route-and-mcp-rate-limit-inventory.md)
- [ADR-0049: Provider credential governance and local evaluator evidence](../ADR/adr-0049-provider-credential-governance-and-local-evaluator-evidence.md)
- [Security governance administration](../admin/security-governance.md)
- [ADR-0050: Security governance for browser mutation boundaries](../ADR/adr-0050-security-governance-browser-mutation-boundaries.md)
- [ADR-0051: Storage-layer encryption governance](../ADR/adr-0051-storage-layer-encryption-governance.md)
- [ADR-0052: Security Governance Admin Control Plane](../ADR/adr-0052-security-governance-admin-control-plane.md)
- [Architecture overview](../technical/architecture/architecture-overview.md) · [Architecture redirect](../architecture/README.md)
- [API Security](../api/README.md#authentication--authorization)
- [Development Best Practices](../development/README.md#security-best-practices)
- [Operations Security](../operations/README.md#-security-operations)

## External References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

**Security concern?** Email security@worldofshadows.com (do not use public issue tracker)
