# Security Documentation

Security policies, threat models, vulnerability management, and compliance.

## 🔐 Security Overview

### [Security Audit Report](./AUDIT_REPORT.md)
Latest security assessment and remediation status.

**Current Status:**
- ✅ Authentication hardened (JWT + refresh tokens)
- ✅ Session security improved (secure cookie flags)
- ✅ CORS configured appropriately
- ✅ Input validation implemented
- ⚠️ Database encryption pending (Phase 2)
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
- **Cookies:** Secure flag, HttpOnly, SameSite=Strict
- **HTTPS:** Enforced in production
- **CSRF:** Token-based protection on state-changing operations
- **Timeout:** 24-hour inactivity timeout

### Data Protection
- **In Transit:** HTTPS/TLS (enforced in production)
- **At Rest:** SQLite (no encryption), migration to PostgreSQL recommended
- **Sensitive Fields:**
  - Passwords: Never logged or returned in API responses
  - Tokens: Stored hashed in database
  - Email: Only exposed to user and admins

## 🚨 Security Best Practices

### For Developers
1. **Never commit secrets** - Use environment variables and `.env.local`
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
- **Mitigation:** CSRF tokens, SameSite cookies
- **Detection:** Token validation on all state-changing operations

#### 5. Distributed Denial of Service (DDoS)
- **Threat:** Overwhelming service with requests
- **Mitigation:** Rate limiting, WAF (CDN in production)
- **Detection:** Traffic pattern analysis

## 🔧 Security Configuration

### Environment Variables (Required in Production)
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
SESSION_COOKIE_SAMESITE='Strict'
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
- ✅ CSRF token validation tests

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
- 🔄 Database encryption at rest
- 🔄 Two-factor authentication (2FA)
- 🔄 Security event logging

### Phase 3 (Q3 2026)
- 📋 OAuth2/OIDC integration
- 📋 Hardware security keys
- 📋 Advanced threat detection

## Related Documentation

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
