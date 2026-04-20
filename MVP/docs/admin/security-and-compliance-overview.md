# Security and compliance overview

High-level **operator and governance** view. Deep audits and code references live in `docs/security/*` and backend implementation.

## Identity and access

- **Authentication:** JWT access tokens with refresh token rotation (see `docs/security/README.md` for parameters).
- **Authorization:** role-based access control — typical roles include **user**, **moderator**, **admin**.
- **Administration tool:** separate app; must not share session cookies with player frontend.

## Transport and cookies

- Enforce **HTTPS** in production.
- Cookies should use **Secure**, **HttpOnly**, and **SameSite** policies as implemented (details in security README).

## Secrets management

- **Never** commit production secrets; use environment injection or a secret manager.
- Rotate **JWT secrets**, **play service shared secrets**, and **internal API keys** together when compromised.
- Document rotation steps in your internal ops wiki; summary env matrix in [Deployment guide](deployment-guide.md).

## Data protection

- Database **encryption at rest** and **backup encryption** are deployment responsibilities.
- Support **user data export** and **deletion** flows when exposed by the product (operator policy).

## Moderation and audit

- Forum moderation actions should leave **audit trails** where implemented; see [Forum moderation workflow](../forum/ModerationWorkflow.md).
- Admin log review procedures may be documented under `audits/` — align public operator docs with internal governance.

## Vulnerability management

- Track dependencies and apply security patches on a schedule.
- Use `docs/security/AUDIT_REPORT.md` as a dated snapshot; do not treat it as live monitoring.

## Related

- `docs/security/README.md`
- `docs/security/AUDIT_REPORT.md`
- [Operations runbook](operations-runbook.md)
