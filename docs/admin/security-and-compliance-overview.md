# Security and compliance overview

High-level **operator and governance** view. Deep audits and code references live in `docs/security/*` and backend implementation.

## Identity and access

- **Authentication:** JWT access tokens with refresh token rotation (see `docs/security/README.md` for parameters).
- **Authorization:** role-based access control — typical roles include **user**, **moderator**, **admin**.
- **Administration tool:** separate app; must not share session cookies with player frontend.

## Transport and cookies

- Enforce **HTTPS** in production.
- Cookies should use **Secure**, **HttpOnly**, and **SameSite** policies as implemented (details in security README).
- Mutating browser/cookie flows are tracked in the [CSRF matrix](../security/csrf-matrix.md); JSON APIs should use Bearer tokens instead of cookie authentication.

## Security governance

- Administration operators can review and edit the security governance policy at `/manage/security-governance`; see [Security governance administration](security-governance.md).
- The backend governance API is `/api/v1/admin/security/governance` and persists policy in `site_settings.security_governance_config`.
- Governance policy is not a hidden enforcement switch: CSRF exemption, proxy cookie stripping, route authentication, cookie config, secret-store materialization, Redis TLS/ACL files, and storage-layer encryption materialization remain code/deployment-owned boundaries.
- Storage-layer evidence is governed through the same page and is surfaced in system diagnosis as `storage_layer_encryption`.
- Architecture decision: [ADR-0050: Security governance for browser mutation boundaries](../ADR/adr-0050-security-governance-browser-mutation-boundaries.md).

## Secrets management

- **Never** commit production secrets; inject them from a dedicated secret store with rotation, audit, and access separation.
- Keep repository `.env` usage for local bootstrap and `docker-up.py`; production secret-store integration should not block that local path.
- Provider API keys for backend/play-service runtime access must use backend AI Runtime Governance or a production secret-manager path, not direct Compose-owned provider key injection. See [Provider credential governance](../security/PROVIDER_CREDENTIAL_GOVERNANCE.md).
- Rotate **JWT secrets**, **play service shared secrets**, and **internal API keys** together when compromised.
- Document rotation steps in your internal ops wiki; summary env matrix in [Deployment guide](deployment-guide.md).

## Data protection

- Full **encryption at rest** is **not** proven by the local repository/Compose setup alone. Current code provides field-level encryption for governed credentials, optional encrypted exports, and storage-layer evidence governance; SQLite files, runtime JSON stores, Redis AOF, Langfuse volumes, and backups require complete deployment evidence. See [At-rest encryption evidence and completion plan](../security/AT_REST_ENCRYPTION.md).
- Database **encryption at rest** and **backup encryption** are deployment responsibilities until the chosen storage layer and evidence pack are documented.
- Local Langfuse evaluator scores are diagnostic evidence only. Treat `local_only: true`, `proof_level=local_only`, or `evidence_scope=local_langfuse` as non-production evidence.
- Support **user data export** and **deletion** flows when exposed by the product (operator policy).

## Moderation and audit

- Forum moderation actions should leave **audit trails** where implemented; see [Forum moderation workflow](../forum/ModerationWorkflow.md).
- Admin log review procedures may be documented under `audits/` — align public operator docs with internal governance.

## Vulnerability management

- Track dependencies and apply security patches on a schedule.
- Use `docs/security/AUDIT_REPORT.md` as a dated snapshot; do not treat it as live monitoring.

## Related

- `docs/security/README.md`
- `docs/security/AT_REST_ENCRYPTION.md`
- `docs/admin/security-governance.md`
- `docs/ADR/adr-0051-storage-layer-encryption-governance.md`
- `docs/ADR/adr-0050-security-governance-browser-mutation-boundaries.md`
- `docs/security/PROVIDER_CREDENTIAL_GOVERNANCE.md`
- `docs/security/AUDIT_REPORT.md`
- [Operations runbook](operations-runbook.md)
