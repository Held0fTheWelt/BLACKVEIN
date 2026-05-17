# ADR-0051: Storage-layer encryption governance

## Status

Accepted

## Date

2026-05-17

## Intellectual property rights

Repository authorship and licensing: see project **LICENSE**; contact maintainers for clarification.

## Privacy and confidentiality

This ADR contains no personal data and no secret values. Storage evidence may reference provider console paths, KMS key identifiers, volume-driver settings, backup job ids, and restore-test records, but it must not include raw keys, recovery material, passwords, bearer tokens, or personal data.

## Related ADRs

- [ADR-0047](adr-0047-at-rest-encryption-evidence-boundary.md) - at-rest encryption evidence boundary.
- [ADR-0050](adr-0050-security-governance-browser-mutation-boundaries.md) - existing security governance control plane.

## Context

ADR-0047 established that the repository must not claim full at-rest encryption until every persisted surface has documented encryption evidence. That decision left a practical gap: operators needed a first-class place to record, review, and diagnose the storage-layer evidence pack.

The persisted surfaces include backend SQLite, Redis AOF, world-engine runtime stores, Langfuse Postgres, ClickHouse, MinIO, Langfuse Redis, and backups/snapshots. Some deployments may satisfy these with managed encrypted services, others with encrypted hosts or Docker volume drivers, and some local-only surfaces may be explicitly marked not applicable.

The application cannot encrypt a host disk or prove cloud KMS state by itself from inside the admin browser. It can, however, provide a governed evidence contract, validate coverage, and make the missing pieces visible in diagnosis.

## Decision

1. Extend `security_governance.v1` with storage-layer encryption policy and evidence fields:
   - `storage_encryption_profile`
   - `require_storage_encryption_evidence`
   - `require_backup_encryption_evidence`
   - `require_storage_key_custody_evidence`
   - `require_storage_restore_test_evidence`
   - `storage_encryption_evidence`

2. Persist the evidence pack in `site_settings.security_governance_config`, the same backend-owned governance record used by the Security Governance Administration page.

3. Require evidence for these surface ids before a full at-rest claim is considered complete:
   - `backend_sqlite`
   - `backend_redis_aof`
   - `world_engine_json_run_store`
   - `world_engine_sqlalchemy_run_store`
   - `langfuse_postgres`
   - `langfuse_clickhouse`
   - `langfuse_minio`
   - `langfuse_redis`
   - `backups_snapshots`

4. Each evidence object records `status`, `control_type`, `evidence_ref`, `key_ref`, `last_verified_at`, `restore_test_ref`, and `notes`. Active encryption controls require an evidence reference and key-custody/KMS reference. Backup evidence also requires a restore-test reference when restore-test evidence is enabled.

5. The Administration Tool must expose storage-layer governance on `/manage/security-governance`, including policy switches, status, coverage, gate checks, and editable evidence JSON.

6. The backend API for this contract is `GET/PATCH /api/v1/admin/security/governance`.

7. The system diagnosis endpoint must expose a non-critical `storage_layer_encryption` check. It reports `running` only when required storage-layer evidence is complete; otherwise it reports `initialized` with the failing required-check count.

8. This governance does not replace deployment controls. Host full-disk encryption, Docker volume-driver encryption, managed-service encryption, server-side object storage encryption, backup encryption, and restore testing remain deployment/operator responsibilities.

9. The world-engine JSON store has a supported app-managed encryption path for deployments that do not replace it with SQL storage: `RUN_STORE_BACKEND=json_aead` writes AES-256-GCM `*.json.enc` envelopes using `WORLD_ENGINE_JSON_AEAD_KEY`. Production should still prefer SQL-backed managed encrypted storage when available; the AEAD JSON path exists for controlled single-node/self-hosted deployments and requires secret-store key custody plus backup evidence.

## Consequences

**Positive:**

- Operators have a concrete place to prove storage-layer encryption instead of relying on prose outside the product.
- Diagnosis makes incomplete evidence visible without blocking local development.
- The backend view can distinguish "governance implemented" from "every deployment storage layer is encrypted."
- The evidence pack is auditable through one existing admin API.

**Negative / risks:**

- Evidence correctness still depends on operator-maintained references and deployment records.
- The product cannot independently verify every external KMS, volume, or backup setting without provider-specific integrations.
- Evidence JSON is flexible but requires disciplined review.

## Testing

- `backend/tests/test_security_governance_routes.py` verifies default storage evidence fields, PATCH persistence, and validation.
- `backend/tests/test_system_diagnosis.py` verifies the `storage_layer_encryption` diagnosis check is emitted.
- `administration-tool/tests/test_manage_security_governance.py` verifies the admin page and JavaScript expose storage-layer controls.
- `tests/test_at_rest_encryption_documentation.py` verifies this ADR and the at-rest evidence document stay linked.
- `world-engine/tests/test_aead_json_persistence.py` verifies AEAD JSON run-store and story-session persistence do not write plaintext JSON payloads.
- `backend/tests/test_backend_info_routes.py::test_security_features_page_explains_local_evidence_boundary` verifies `/backend/security-features` exposes the Storage-Layer Governance path.

## References

- [docs/security/AT_REST_ENCRYPTION.md](../security/AT_REST_ENCRYPTION.md)
- [docs/admin/security-governance.md](../admin/security-governance.md)
- `backend/app/services/security_governance_service.py`
- `backend/app/services/system_diagnosis_service.py`
- `world-engine/app/runtime/json_at_rest.py`
- `world-engine/app/runtime/store.py`
- `administration-tool/templates/manage/security_governance.html`
- `administration-tool/static/manage_security_governance.js`
