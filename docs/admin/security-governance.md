# Security governance

The Administration Tool exposes `/manage/security-governance` as the operator surface for security policy visibility and review. It is a governance control plane: it stores desired policy, shows observed runtime posture, and calls out non-editable boundaries.

It is not a browser-based secret manager. Production secrets still belong in a dedicated secret store with rotation, audit, and access separation. Local `.env` remains the supported bootstrap path for `docker-up.py`.

Do not paste secrets, bearer tokens, cookie values, KMS material, Redis passwords, Vault paths that reveal secrets, or user personal data into operator notes.

## Admin and API surface

| Surface | Purpose |
|---------|---------|
| `/manage/security-governance` | Administration Tool page for operators |
| `GET /api/v1/admin/security/governance` | Read policy, observed posture, warnings, CSRF matrix, secret governance, Redis governance, and storage-layer encryption evidence |
| `PATCH /api/v1/admin/security/governance` | Persist editable operator policy |
| `site_settings.security_governance_config` | `SiteSetting` key that stores the JSON policy |

The API is implemented in `backend/app/api/v1/security_governance_routes.py`, returns schema `security_governance.v1`, and requires an authenticated admin JWT with the `manage.ai_runtime_governance` feature permission.

## Editable policy

| Group | Settings |
|-------|----------|
| Review | `review_status`, `operator_notes` |
| Cookies and CSRF | `target_session_samesite`, `require_backend_web_csrf`, `require_bearer_for_json_api`, `require_proxy_cookie_stripping`, `require_csrf_regression_tests` |
| Secret store | `production_secret_store_required`, `secret_store_mode`, `secret_store_provider`, `secret_rotation_interval_days`, `secret_store_audit_required`, `secret_store_access_separation_required`, `preserve_docker_up_local_bootstrap` |
| Redis hardening | `redis_hardening_profile`, `require_production_redis_hardening`, `require_redis_tls`, `require_redis_acl_users`, `require_redis_instance_separation`, `require_redis_no_host_ports`, `require_redis_validation_gate` |
| Storage-layer encryption | `storage_encryption_profile`, `require_storage_encryption_evidence`, `require_backup_encryption_evidence`, `require_storage_key_custody_evidence`, `require_storage_restore_test_evidence`, `storage_encryption_evidence` |

The page also displays effective posture from runtime configuration, warnings for drift, the CSRF matrix, Redis production checks, storage-layer evidence coverage, and a full JSON payload for audit review.

Editable settings are policy targets and review flags. They do not directly reconfigure Flask CSRF, proxy stripping, cookie flags, secret-store providers, Redis instances, TLS certificates, ACL files, host disks, Docker volumes, managed services, or backup jobs at runtime.

## Secret-management policy

Use the governance page to record the production secret-store policy, not the secrets themselves.

Production deployments should:

1. Materialize runtime env vars from a dedicated provider such as Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault, 1Password, Doppler, or deployment-managed secrets.
2. Rotate JWT secrets, play-service shared secrets, internal API keys, database credentials, Redis passwords, Langfuse secrets, and provider credentials through that provider.
3. Keep provider audit logs and access policies outside the repository as deployment evidence.
4. Preserve local `.env` bootstrap for `python docker-up.py init-env`, `python docker-up.py up`, `python docker-up.py build`, and `python docker-up.py restart`.

The governance invariant is simple: production needs a real secret store; local `docker-up.py` must not require Vault, KMS, cloud login, or production secret-store access.

## Non-editable boundaries

The admin page deliberately does not flip these behaviors:

- `/api/v1` CSRF exemption is code-owned.
- Backend web-route CSRF behavior is controlled by Flask-WTF app configuration and tests.
- Same-origin admin proxy cookie stripping is code-owned in the proxy route registration.
- Mutating JSON APIs use `Authorization: Bearer`, not browser cookies.
- Redis TLS certificates, ACL files, and generated passwords are materialized host-side by `docker-up.py` or by the production deployment platform.
- Storage-layer encryption evidence is operator-owned; the admin page records evidence but does not encrypt host disks, Docker volumes, managed services, or backups.
- Production secret-store rotation and audit enforcement are provider/deployment responsibilities.

## Operator workflow

1. Open `/manage/security-governance` in the Administration Tool.
2. Confirm the review status and target cookie/CSRF posture.
3. Confirm production secret-store policy:
   - `production_secret_store_required` enabled
   - `secret_store_mode=production_secret_store`
   - provider recorded
   - rotation interval set
   - audit and access separation enabled
   - `preserve_docker_up_local_bootstrap` enabled
4. Review Redis hardening checks before production:
   - TLS via `rediss://`
   - named ACL users and passwords
   - separate app and Langfuse Redis instances
   - no host-published Redis ports
   - validation gate documented
5. Review storage-layer encryption evidence before a full at-rest claim:
   - evidence exists for `backend_sqlite`, Redis AOF, world-engine stores, Langfuse volumes, and backups/snapshots
   - production DB/Redis surfaces point to encrypted managed services or encrypted volume-backed storage
   - world-engine JSON persistence is replaced by `RUN_STORE_BACKEND=sqlalchemy` on encrypted storage, or encrypted with `RUN_STORE_BACKEND=json_aead` and `WORLD_ENGINE_JSON_AEAD_KEY`
   - every active encryption control has an `evidence_ref` and `key_ref`
   - backup evidence includes `restore_test_ref`
   - `/api/v1/admin/system-diagnosis` reports `storage_layer_encryption` as running
6. Save the policy and capture the JSON payload in release or audit notes when needed.

## Verification

Security-governance contract tests:

```bash
python -m pytest backend/tests/test_security_governance_routes.py administration-tool/tests/test_manage_security_governance.py -q
```

Production Redis validation commands:

```bash
python docker-up.py init-production-redis
python docker-up.py validate-production-redis
python docker-up.py --production-redis up
```

Local secret bootstrap remains:

```bash
python docker-up.py init-env
python docker-up.py up
```

## Related

- [Security and compliance overview](security-and-compliance-overview.md)
- [Deployment guide](deployment-guide.md)
- [CSRF matrix](../security/csrf-matrix.md)
- [At-rest encryption evidence](../security/AT_REST_ENCRYPTION.md)
- [ADR-0050: Security governance for browser mutation boundaries](../ADR/adr-0050-security-governance-browser-mutation-boundaries.md)
- [ADR-0051: Storage-layer encryption governance](../ADR/adr-0051-storage-layer-encryption-governance.md)
- [ADR-0052: Security Governance Admin Control Plane](../ADR/adr-0052-security-governance-admin-control-plane.md)
