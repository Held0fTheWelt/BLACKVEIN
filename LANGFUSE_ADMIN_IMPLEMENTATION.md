# Langfuse Observability Administration Tool Integration

**Status**: Implementation Plan (Ready for Development)  
**Date**: 2026-04-24  
**Pattern**: Reuses AI Provider credential management pattern for consistency

---

## Executive Summary

Langfuse observability configuration must be administered through the Administration Tool, **NOT** through `.env` files alone. This ensures:

- ✅ Operator-facing UI for Langfuse settings
- ✅ Secret key storage with encryption identical to AI provider API keys
- ✅ Write-only masked password fields in Administration Tool UI
- ✅ No plaintext secrets in logs, diagnostics, or readiness reports
- ✅ Consistent with existing AI provider credential governance
- ✅ Support for credential rotation and update without restart (where possible)

---

## Audit Results: Answers to 10 Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | How are AI keys administered? | Via `/manage/operational-governance/providers` page; password-type input |
| 2 | Where stored? | `ai_provider_credentials` table, encrypted with AES-256-GCM |
| 3 | How masked in UI? | Password field (hidden), only fingerprint shown after save |
| 4 | Which routes? | `POST /api/v1/admin/provider/{id}/credential` (write), calls `write_provider_credential()` |
| 5 | Which service consumes? | `governance_runtime_service.get_provider_credential_for_runtime(provider_id)` decrypts live |
| 6 | Can Langfuse reuse? | **Partially** - encryption pattern yes; but need separate observability models (not AI provider) |
| 7 | What extension? | Create `ObservabilityConfig` and `ObservabilityCredential` models (follow provider pattern) |
| 8 | Config propagation? | Startup: `.env` + config classes; Runtime: Admin API → DB → service refresh |
| 9 | Restart vs. live-reload? | `LANGFUSE_ENABLED`: restart required; keys/host/settings: live-reload supported |
| 10 | Secret display? | Show fingerprint only (e.g., "sk_...8f9a"), never plaintext key |

---

## Database Models

### New: `ObservabilityConfig` (like `AIProviderConfig`)

```python
class ObservabilityConfig(db.Model):
    """Langfuse observability service configuration."""
    
    __tablename__ = "observability_configs"
    
    service_id = db.Column(db.String(64), primary_key=True)  # "langfuse"
    service_type = db.Column(db.String(64), nullable=False)  # "langfuse"
    display_name = db.Column(db.String(128), nullable=False)  # "Langfuse"
    base_url = db.Column(db.String(512), nullable=False)  # "https://cloud.langfuse.com"
    is_enabled = db.Column(db.Boolean, nullable=False, default=False)  # False by default
    
    # Public configuration (NOT secrets)
    environment = db.Column(db.String(64), nullable=False, default="development")
    release = db.Column(db.String(128), nullable=False, default="unknown")
    sample_rate = db.Column(db.Float, nullable=False, default=1.0)
    
    # Capture toggles
    capture_prompts = db.Column(db.Boolean, nullable=False, default=True)
    capture_outputs = db.Column(db.Boolean, nullable=False, default=True)
    capture_retrieval = db.Column(db.Boolean, nullable=False, default=False)
    
    # Redaction policy
    redaction_mode = db.Column(db.String(32), nullable=False, default="strict")
    
    # Credential tracking
    credential_configured = db.Column(db.Boolean, nullable=False, default=False)
    credential_fingerprint = db.Column(db.String(256), nullable=True)
    
    # Health and testing
    health_status = db.Column(db.String(32), nullable=False, default="unknown")
    last_tested_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
```

### New: `ObservabilityCredential` (like `AIProviderCredential`)

```python
class ObservabilityCredential(db.Model):
    """Encrypted write-only credentials for observability services."""
    
    __tablename__ = "observability_credentials"
    
    credential_id = db.Column(db.String(128), primary_key=True)
    service_id = db.Column(db.String(64), db.ForeignKey("observability_configs.service_id"), nullable=False, index=True)
    
    # Secret names
    secret_name = db.Column(db.String(128), nullable=False)  # "public_key" or "secret_key"
    
    # Encrypted storage (identical to AIProviderCredential)
    encrypted_secret = db.Column(db.LargeBinary(), nullable=False)
    encrypted_dek = db.Column(db.LargeBinary(), nullable=False)
    secret_nonce = db.Column(db.LargeBinary(), nullable=False)
    dek_nonce = db.Column(db.LargeBinary(), nullable=False)
    dek_algorithm = db.Column(db.String(64), nullable=False, default="AES-256-GCM")
    kek_key_id = db.Column(db.String(128), nullable=True)
    
    # Fingerprint for display (never the actual secret)
    secret_fingerprint = db.Column(db.String(256), nullable=False, index=True)
    
    # Versioning
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    rotation_in_progress = db.Column(db.Boolean, nullable=False, default=False)
    rotated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    
    # Audit
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
```

---

## Backend API Routes

Add to `backend/app/api/v1/observability_governance_routes.py` (NEW FILE):

### GET /api/v1/admin/observability/status
Returns current Langfuse configuration status.

**Response**:
```json
{
  "service_id": "langfuse",
  "service_type": "langfuse",
  "display_name": "Langfuse",
  "is_enabled": false,
  "base_url": "https://cloud.langfuse.com",
  "environment": "development",
  "release": "unknown",
  "sample_rate": 1.0,
  "capture_prompts": true,
  "capture_outputs": true,
  "capture_retrieval": false,
  "redaction_mode": "strict",
  "credential_configured": false,
  "credential_fingerprint": null,
  "health_status": "unknown",
  "last_tested_at": null
}
```

### POST /api/v1/admin/observability/update
Update Langfuse public configuration (non-secret settings).

**Payload**:
```json
{
  "is_enabled": false,
  "base_url": "https://cloud.langfuse.com",
  "environment": "staging",
  "release": "1.2.3",
  "sample_rate": 0.5,
  "capture_prompts": true,
  "capture_outputs": true,
  "capture_retrieval": false,
  "redaction_mode": "strict"
}
```

**Validation Rules**:
- `base_url` must start with http:// or https://
- `sample_rate` must be 0.0–1.0
- `environment` must be one of: development, staging, production
- `redaction_mode` must be one of: strict, relaxed, none
- If `is_enabled` changes from false→true: require credential_configured=true

**Response**:
```json
{
  "updated": true,
  "service_id": "langfuse",
  "requires_restart": false
}
```

### POST /api/v1/admin/observability/credential
Write/update Langfuse secret credentials (public_key and secret_key).

**Payload**:
```json
{
  "public_key": "pk_xxx...",
  "secret_key": "sk_yyy..."
}
```

**Validation Rules**:
- At least one of public_key or secret_key must be provided
- Keys must be non-empty strings
- Both must be valid format (no spaces)

**Response**:
```json
{
  "credential_written": true,
  "public_key_fingerprint": "pk_...8f9a",
  "secret_key_fingerprint": "sk_...d3e2",
  "rotated_at": "2026-04-24T15:30:45Z"
}
```

**Secret Masking**: Response returns only fingerprints, never the actual keys.

### POST /api/v1/admin/observability/test-connection
Test Langfuse connection health.

**Response**:
```json
{
  "health_status": "healthy",
  "message": "Successfully connected to Langfuse",
  "tested_at": "2026-04-24T15:30:45Z",
  "details": {
    "base_url": "https://cloud.langfuse.com",
    "auth": "configured"
  }
}
```

### DELETE /api/v1/admin/observability/disable
Disable Langfuse and clear configuration.

**Response**:
```json
{
  "disabled": true,
  "message": "Langfuse observability disabled"
}
```

---

## Service Layer: `observability_governance_service.py` (NEW FILE)

```python
def get_observability_config() -> dict:
    """Get current Langfuse configuration (non-secret values only)."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        return _default_observability_config()
    
    return {
        "service_id": config.service_id,
        "service_type": config.service_type,
        "display_name": config.display_name,
        "is_enabled": config.is_enabled,
        "base_url": config.base_url,
        "environment": config.environment,
        "release": config.release,
        "sample_rate": config.sample_rate,
        "capture_prompts": config.capture_prompts,
        "capture_outputs": config.capture_outputs,
        "capture_retrieval": config.capture_retrieval,
        "redaction_mode": config.redaction_mode,
        "credential_configured": config.credential_configured,
        "credential_fingerprint": config.credential_fingerprint,
        "health_status": config.health_status,
        "last_tested_at": config.last_tested_at.isoformat() if config.last_tested_at else None,
    }


def update_observability_config(updates: dict, actor: str) -> dict:
    """Update Langfuse public configuration."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        config = ObservabilityConfig(service_id="langfuse", service_type="langfuse", display_name="Langfuse")
        db.session.add(config)
    
    # Validation
    if "base_url" in updates and updates["base_url"]:
        if not updates["base_url"].startswith(("http://", "https://")):
            raise governance_error("invalid_url", "base_url must start with http:// or https://", 400, {})
    
    if "sample_rate" in updates:
        sr = float(updates["sample_rate"])
        if not (0.0 <= sr <= 1.0):
            raise governance_error("invalid_sample_rate", "sample_rate must be 0.0–1.0", 400, {})
    
    if "environment" in updates:
        if updates["environment"] not in ["development", "staging", "production"]:
            raise governance_error("invalid_environment", "environment must be development|staging|production", 400, {})
    
    if "redaction_mode" in updates:
        if updates["redaction_mode"] not in ["strict", "relaxed", "none"]:
            raise governance_error("invalid_redaction_mode", "redaction_mode must be strict|relaxed|none", 400, {})
    
    # Update fields
    for key in ["is_enabled", "base_url", "environment", "release", "sample_rate", 
                "capture_prompts", "capture_outputs", "capture_retrieval", "redaction_mode"]:
        if key in updates:
            setattr(config, key, updates[key])
    
    config.updated_at = utc_now()
    db.session.commit()
    
    _audit("observability_config_updated", "observability", "langfuse", actor, f"Config updated", updates)
    
    return {"updated": True, "service_id": "langfuse", "requires_restart": False}


def write_observability_credential(public_key: str = None, secret_key: str = None, actor: str = "system") -> dict:
    """Write/rotate Langfuse credentials."""
    config = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if not config:
        config = ObservabilityConfig(service_id="langfuse", service_type="langfuse", display_name="Langfuse")
        db.session.add(config)
    
    result = {}
    
    # Handle public_key
    if public_key is not None:
        if not public_key.strip():
            raise governance_error("invalid_public_key", "public_key cannot be empty", 400, {})
        
        # Deactivate old public_key credentials
        old_pk = ObservabilityCredential.query.filter_by(
            service_id="langfuse", secret_name="public_key", is_active=True
        ).first()
        if old_pk:
            old_pk.is_active = False
        
        # Create new public_key credential
        record = encrypt_secret(public_key)
        cred = ObservabilityCredential(
            credential_id=f"obs_cred_{uuid4().hex}",
            service_id="langfuse",
            secret_name="public_key",
            encrypted_secret=record.encrypted_secret,
            encrypted_dek=record.encrypted_dek,
            secret_nonce=record.secret_nonce,
            dek_nonce=record.dek_nonce,
            dek_algorithm=record.dek_algorithm,
            secret_fingerprint=record.secret_fingerprint,
            is_active=True,
            rotated_at=utc_now(),
        )
        db.session.add(cred)
        result["public_key_fingerprint"] = record.secret_fingerprint
    
    # Handle secret_key
    if secret_key is not None:
        if not secret_key.strip():
            raise governance_error("invalid_secret_key", "secret_key cannot be empty", 400, {})
        
        # Deactivate old secret_key credentials
        old_sk = ObservabilityCredential.query.filter_by(
            service_id="langfuse", secret_name="secret_key", is_active=True
        ).first()
        if old_sk:
            old_sk.is_active = False
        
        # Create new secret_key credential
        record = encrypt_secret(secret_key)
        cred = ObservabilityCredential(
            credential_id=f"obs_cred_{uuid4().hex}",
            service_id="langfuse",
            secret_name="secret_key",
            encrypted_secret=record.encrypted_secret,
            encrypted_dek=record.encrypted_dek,
            secret_nonce=record.secret_nonce,
            dek_nonce=record.dek_nonce,
            dek_algorithm=record.dek_algorithm,
            secret_fingerprint=record.secret_fingerprint,
            is_active=True,
            rotated_at=utc_now(),
        )
        db.session.add(cred)
        result["secret_key_fingerprint"] = record.secret_fingerprint
    
    # Mark credential as configured if both keys present
    if result:
        config.credential_configured = True
        config.updated_at = utc_now()
    
    db.session.commit()
    result["credential_written"] = True
    result["rotated_at"] = utc_now().isoformat()
    
    _audit("observability_credential_written", "observability", "langfuse", actor, "Credential rotated", result)
    
    return result


def get_observability_credential_for_runtime(secret_name: str = "secret_key") -> str | None:
    """Decrypt and return Langfuse credential for runtime use."""
    cred = ObservabilityCredential.query.filter_by(
        service_id="langfuse",
        secret_name=secret_name,
        is_active=True
    ).first()
    
    if not cred:
        return None
    
    try:
        decrypted = decrypt_secret(
            encrypted_secret=cred.encrypted_secret,
            encrypted_dek=cred.encrypted_dek,
            secret_nonce=cred.secret_nonce,
            dek_nonce=cred.dek_nonce,
        )
        return decrypted.get(secret_name) if isinstance(decrypted, dict) else str(decrypted)
    except Exception:
        return None


def test_observability_connection(actor: str = "system") -> dict:
    """Test Langfuse connection health."""
    config = get_observability_config()
    
    if not config["credential_configured"]:
        raise governance_error("credential_required", "Langfuse credential required before testing", 400, {})
    
    if not config["is_enabled"]:
        raise governance_error("not_enabled", "Langfuse is not enabled", 400, {})
    
    # Test connection
    try:
        from backend.app.observability.langfuse_adapter import LangfuseAdapter
        
        public_key = get_observability_credential_for_runtime("public_key")
        secret_key = get_observability_credential_for_runtime("secret_key")
        
        adapter = LangfuseAdapter(
            enabled=True,
            public_key=public_key,
            secret_key=secret_key,
            host=config["base_url"],
            environment=config["environment"],
        )
        
        # Simple health check: create and immediately end a test span
        trace = adapter.start_trace(name="admin_health_check", metadata={"test": True})
        adapter.end_trace(trace["trace_id"])
        adapter.flush()
        
        status = "healthy"
        message = "Successfully connected to Langfuse"
        
    except Exception as e:
        status = "unhealthy"
        message = f"Connection failed: {str(e)}"
    
    config_obj = ObservabilityConfig.query.filter_by(service_id="langfuse").first()
    if config_obj:
        config_obj.health_status = status
        config_obj.last_tested_at = utc_now()
        db.session.commit()
    
    _audit("observability_health_check", "observability", "langfuse", actor, message, {})
    
    return {
        "health_status": status,
        "message": message,
        "tested_at": utc_now().isoformat(),
        "details": {
            "base_url": config["base_url"],
            "auth": "configured" if config["credential_configured"] else "missing",
        }
    }
```

---

## Administration Tool Frontend Integration

### Route: `/manage/observability-settings`

Add to `route_registration_manage_sections.py`:

```python
@app.route("/manage/observability-settings")
def manage_observability_settings():
    """Observability services configuration (Langfuse, etc.)."""
    return render_template("manage/observability_settings.html")
```

### Template: `templates/manage/observability_settings.html`

```html
{% extends "manage/base.html" %}

{% block title %}Observability Settings{% endblock %}

{% block content %}
<section class="manage-section" data-page="observability-settings">
    <div class="manage-section-header">
        <div>
            <p class="manage-eyebrow">Operations</p>
            <h1>Observability Configuration</h1>
            <p class="manage-lead">Configure <strong>Langfuse</strong> for AI/runtime tracing and diagnostics. 
                All secrets are encrypted and never displayed in plaintext.</p>
        </div>
        <div class="manage-actions-row">
            <button type="button" class="btn" id="manage-obs-refresh">Reload settings</button>
        </div>
    </div>

    <p id="manage-obs-banner" class="form-error" style="display:none;" role="status" aria-live="polite"></p>
    <p id="manage-obs-success" class="manage-state manage-state--ok" style="display:none;" role="status" aria-live="polite"></p>

    <section class="panel">
        <header class="panel-header"><h2>Langfuse Observability</h2></header>

        <!-- Status Block -->
        <div style="margin-bottom: 1.5rem;">
            <div id="manage-obs-status-row" style="display: none;">
                <p id="manage-obs-status-headline" class="manage-lead" style="margin: 0 0 0.5rem 0;"></p>
                <p id="manage-obs-status-detail" class="muted" style="margin: 0;"></p>
            </div>
        </div>

        <!-- Configuration Form -->
        <fieldset style="border: 1px solid #ddd; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
            <legend style="font-weight: 500;">Public Configuration</legend>

            <label class="form-label"><input type="checkbox" id="manage-obs-enabled" /> Enable Langfuse observability</label>

            <label class="form-label">Base URL
                <input type="url" id="manage-obs-base-url" class="form-input" value="https://cloud.langfuse.com" />
            </label>

            <label class="form-label">Environment
                <select id="manage-obs-environment" class="form-input">
                    <option value="development">development</option>
                    <option value="staging">staging</option>
                    <option value="production">production</option>
                </select>
            </label>

            <label class="form-label">Release version
                <input type="text" id="manage-obs-release" class="form-input" value="unknown" />
            </label>

            <label class="form-label">Sample rate (0.0–1.0)
                <input type="number" id="manage-obs-sample-rate" class="form-input" min="0" max="1" step="0.1" value="1.0" />
            </label>

            <fieldset style="margin-top: 1rem; padding: 0.75rem; background: #f9f9f9; border-radius: 3px;">
                <legend style="font-size: 0.9rem; font-weight: 500; margin-bottom: 0.5rem;">Capture toggles</legend>
                <label class="form-label"><input type="checkbox" id="manage-obs-capture-prompts" checked /> Capture prompts</label>
                <label class="form-label"><input type="checkbox" id="manage-obs-capture-outputs" checked /> Capture outputs</label>
                <label class="form-label"><input type="checkbox" id="manage-obs-capture-retrieval" /> Capture retrieval queries</label>
            </fieldset>

            <label class="form-label" style="margin-top: 1rem;">Redaction mode
                <select id="manage-obs-redaction-mode" class="form-input">
                    <option value="strict">strict (default: maximum privacy)</option>
                    <option value="relaxed">relaxed</option>
                    <option value="none">none (test-only)</option>
                </select>
            </label>

            <div class="manage-actions-row" style="margin-top: 1.5rem;">
                <button type="button" class="btn btn-primary" id="manage-obs-save-config">Save configuration</button>
            </div>
        </fieldset>

        <!-- Credentials Block -->
        <fieldset style="border: 1px solid #ddd; padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem;">
            <legend style="font-weight: 500;">Credentials (Write-Only)</legend>

            <p class="muted" style="margin-top: 0; margin-bottom: 1rem;">
                Enter credentials once. After saving, only fingerprints are displayed. Credentials are encrypted at rest.
            </p>

            <label class="form-label">Langfuse Public Key (pk_...)
                <input type="password" id="manage-obs-public-key" class="form-input" autocomplete="new-password" />
            </label>

            <label class="form-label">Langfuse Secret Key (sk_...)
                <input type="password" id="manage-obs-secret-key" class="form-input" autocomplete="new-password" />
            </label>

            <p id="manage-obs-credential-status" class="muted" style="margin-top: 0.75rem; min-height: 1.25rem;"></p>

            <div class="manage-actions-row">
                <button type="button" class="btn btn-primary" id="manage-obs-save-credential">Update credentials</button>
                <button type="button" class="btn" id="manage-obs-test-connection">Test connection</button>
            </div>
        </fieldset>

        <!-- Danger Zone -->
        <fieldset style="border: 2px solid #cc0000; padding: 1rem; border-radius: 4px;">
            <legend style="font-weight: 500; color: #cc0000;">Danger Zone</legend>

            <p class="muted" style="margin-top: 0;">Disables Langfuse observability and clears configuration.</p>

            <div class="manage-actions-row">
                <button type="button" class="btn btn-danger" id="manage-obs-disable">Disable Langfuse</button>
            </div>
        </fieldset>

        <!-- Technical Details -->
        <details style="margin-top: 1.5rem;">
            <summary class="muted">Technical audit: full config JSON</summary>
            <pre id="manage-obs-config-json" class="manage-psc-json muted"></pre>
        </details>
    </section>
</section>
{% endblock %}

{% block extra_scripts %}
<script src="{{ url_for('static', filename='manage_observability_settings.js') }}"></script>
{% endblock %}
```

### JavaScript: `static/manage_observability_settings.js`

```javascript
(function() {
    const BASE_URL = '//_proxy';

    // State
    let currentConfig = null;

    // Elements
    const refreshBtn = document.getElementById('manage-obs-refresh');
    const saveConfigBtn = document.getElementById('manage-obs-save-config');
    const saveCredentialBtn = document.getElementById('manage-obs-save-credential');
    const testConnBtn = document.getElementById('manage-obs-test-connection');
    const disableBtn = document.getElementById('manage-obs-disable');
    const banner = document.getElementById('manage-obs-banner');
    const success = document.getElementById('manage-obs-success');
    const configJson = document.getElementById('manage-obs-config-json');

    // Inputs
    const enabledInput = document.getElementById('manage-obs-enabled');
    const baseUrlInput = document.getElementById('manage-obs-base-url');
    const environmentInput = document.getElementById('manage-obs-environment');
    const releaseInput = document.getElementById('manage-obs-release');
    const sampleRateInput = document.getElementById('manage-obs-sample-rate');
    const capturePromptsInput = document.getElementById('manage-obs-capture-prompts');
    const captureOutputsInput = document.getElementById('manage-obs-capture-outputs');
    const captureRetrievalInput = document.getElementById('manage-obs-capture-retrieval');
    const redactionModeInput = document.getElementById('manage-obs-redaction-mode');
    const publicKeyInput = document.getElementById('manage-obs-public-key');
    const secretKeyInput = document.getElementById('manage-obs-secret-key');
    const credentialStatus = document.getElementById('manage-obs-credential-status');

    // Initialize
    refreshBtn.addEventListener('click', loadConfig);
    saveConfigBtn.addEventListener('click', saveConfig);
    saveCredentialBtn.addEventListener('click', saveCredential);
    testConnBtn.addEventListener('click', testConnection);
    disableBtn.addEventListener('click', disableObservability);

    // Load config
    async function loadConfig() {
        try {
            banner.style.display = 'none';
            success.style.display = 'none';

            const resp = await fetch(`${BASE_URL}/api/v1/admin/observability/status`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

            currentConfig = await resp.json();
            renderConfig();
            updateStatus();
            updateTechnicalJson();

            showSuccess('Configuration loaded');
        } catch (err) {
            showError('Failed to load config: ' + err.message);
        }
    }

    // Render config
    function renderConfig() {
        if (!currentConfig) return;

        enabledInput.checked = currentConfig.is_enabled || false;
        baseUrlInput.value = currentConfig.base_url || 'https://cloud.langfuse.com';
        environmentInput.value = currentConfig.environment || 'development';
        releaseInput.value = currentConfig.release || 'unknown';
        sampleRateInput.value = currentConfig.sample_rate ?? 1.0;
        capturePromptsInput.checked = currentConfig.capture_prompts !== false;
        captureOutputsInput.checked = currentConfig.capture_outputs !== false;
        captureRetrievalInput.checked = currentConfig.capture_retrieval === true;
        redactionModeInput.value = currentConfig.redaction_mode || 'strict';

        // Credential status
        if (currentConfig.credential_configured) {
            credentialStatus.innerHTML = `✓ <strong>Configured</strong> (fingerprint: ${currentConfig.credential_fingerprint || 'unknown'})`;
            credentialStatus.style.color = '#060';
        } else {
            credentialStatus.innerHTML = '✗ <strong>Not configured</strong> — enter credentials to enable';
            credentialStatus.style.color = '#c00';
        }

        // Clear password fields (never pre-fill secrets)
        publicKeyInput.value = '';
        secretKeyInput.value = '';
    }

    // Update status
    function updateStatus() {
        const statusRow = document.getElementById('manage-obs-status-row');
        const headline = document.getElementById('manage-obs-status-headline');
        const detail = document.getElementById('manage-obs-status-detail');

        if (!currentConfig) {
            statusRow.style.display = 'none';
            return;
        }

        statusRow.style.display = 'block';
        
        const status = currentConfig.is_enabled ? '✓ Enabled' : '✗ Disabled';
        const credStatus = currentConfig.credential_configured ? 'configured' : 'not configured';
        
        headline.textContent = status;
        detail.textContent = `Health: ${currentConfig.health_status} | Credentials: ${credStatus}`;
    }

    // Update technical JSON
    function updateTechnicalJson() {
        configJson.textContent = JSON.stringify(currentConfig, null, 2);
    }

    // Save config
    async function saveConfig() {
        try {
            banner.style.display = 'none';
            success.style.display = 'none';

            const payload = {
                is_enabled: enabledInput.checked,
                base_url: baseUrlInput.value,
                environment: environmentInput.value,
                release: releaseInput.value,
                sample_rate: parseFloat(sampleRateInput.value),
                capture_prompts: capturePromptsInput.checked,
                capture_outputs: captureOutputsInput.checked,
                capture_retrieval: captureRetrievalInput.checked,
                redaction_mode: redactionModeInput.value,
            };

            const resp = await fetch(`${BASE_URL}/api/v1/admin/observability/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.error_message || `HTTP ${resp.status}`);
            }

            showSuccess('Configuration saved successfully');
            await loadConfig();
        } catch (err) {
            showError('Failed to save config: ' + err.message);
        }
    }

    // Save credential
    async function saveCredential() {
        try {
            banner.style.display = 'none';
            success.style.display = 'none';

            const pk = publicKeyInput.value.trim();
            const sk = secretKeyInput.value.trim();

            if (!pk && !sk) {
                showError('At least one credential (public_key or secret_key) is required');
                return;
            }

            const payload = {};
            if (pk) payload.public_key = pk;
            if (sk) payload.secret_key = sk;

            const resp = await fetch(`${BASE_URL}/api/v1/admin/observability/credential`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.error_message || `HTTP ${resp.status}`);
            }

            const result = await resp.json();
            showSuccess('Credentials saved successfully. Fingerprints: ' + 
                        (result.public_key_fingerprint ? 'pk ' : '') + 
                        (result.secret_key_fingerprint ? 'sk' : ''));

            await loadConfig();
        } catch (err) {
            showError('Failed to save credential: ' + err.message);
        }
    }

    // Test connection
    async function testConnection() {
        try {
            banner.style.display = 'none';
            success.style.display = 'none';

            testConnBtn.disabled = true;
            testConnBtn.textContent = 'Testing...';

            const resp = await fetch(`${BASE_URL}/api/v1/admin/observability/test-connection`, {
                method: 'POST',
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.error_message || `HTTP ${resp.status}`);
            }

            const result = await resp.json();
            showSuccess(`Connection test: ${result.health_status} — ${result.message}`);
            await loadConfig();
        } catch (err) {
            showError('Connection test failed: ' + err.message);
        } finally {
            testConnBtn.disabled = false;
            testConnBtn.textContent = 'Test connection';
        }
    }

    // Disable Langfuse
    async function disableObservability() {
        if (!confirm('Disable Langfuse observability? This will clear all configuration.')) {
            return;
        }

        try {
            banner.style.display = 'none';
            success.style.display = 'none';

            const resp = await fetch(`${BASE_URL}/api/v1/admin/observability/disable`, {
                method: 'DELETE',
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.error_message || `HTTP ${resp.status}`);
            }

            showSuccess('Langfuse observability disabled');
            await loadConfig();
        } catch (err) {
            showError('Failed to disable: ' + err.message);
        }
    }

    // Helpers
    function showError(msg) {
        banner.textContent = msg;
        banner.style.display = 'block';
    }

    function showSuccess(msg) {
        success.textContent = msg;
        success.style.display = 'block';
    }

    // Load on init
    loadConfig();
})();
```

---

## Integration Points

### 1. Backend Startup: Initialize Langfuse Adapter

Update `backend/app/factory_app.py`:

```python
def _initialize_observability(app):
    """Initialize Langfuse observability on startup."""
    from backend.app.observability.langfuse_adapter import LangfuseAdapter
    from backend.app.services.observability_governance_service import get_observability_config, get_observability_credential_for_runtime
    
    config = get_observability_config()
    
    if not config.get("is_enabled"):
        # Disabled: no-op adapter
        app.langfuse_adapter = LangfuseAdapter(enabled=False)
        return
    
    # Enabled: fetch credentials and initialize
    try:
        public_key = get_observability_credential_for_runtime("public_key")
        secret_key = get_observability_credential_for_runtime("secret_key")
        
        if not secret_key:
            print("[WARN] Langfuse enabled but secret_key not configured; falling back to no-op")
            app.langfuse_adapter = LangfuseAdapter(enabled=False)
            return
        
        app.langfuse_adapter = LangfuseAdapter(
            enabled=True,
            public_key=public_key,
            secret_key=secret_key,
            host=config["base_url"],
            environment=config["environment"],
            release=config["release"],
            sample_rate=config.get("sample_rate", 1.0),
            capture_prompts=config.get("capture_prompts", True),
            capture_outputs=config.get("capture_outputs", True),
            capture_retrieval=config.get("capture_retrieval", False),
            redaction_mode=config.get("redaction_mode", "strict"),
        )
        print("[INFO] Langfuse observability initialized")
    except Exception as e:
        print(f"[WARN] Failed to initialize Langfuse: {e}; using no-op adapter")
        app.langfuse_adapter = LangfuseAdapter(enabled=False)

# In create_app():
_initialize_observability(app)

# Register shutdown handler
@app.teardown_appcontext
def shutdown_observability(exc=None):
    if hasattr(app, 'langfuse_adapter'):
        app.langfuse_adapter.shutdown()
```

### 2. Propagation to World-Engine

World-Engine calls backend API to get current Langfuse config:

```python
# world-engine/app/config.py
def load_langfuse_from_backend() -> dict:
    """Fetch Langfuse config from backend admin API."""
    backend_url = os.getenv("BACKEND_API_URL")
    if not backend_url:
        return {}
    
    try:
        response = requests.get(
            f"{backend_url}/api/v1/admin/observability/status",
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    
    return {}
```

### 3. Release-Readiness: Check Langfuse Status

Update `backend/app/services/release_readiness_service.py`:

```python
def check_observability_readiness() -> dict:
    """Check if Langfuse is configured and ready."""
    from backend.app.services.observability_governance_service import get_observability_config
    
    config = get_observability_config()
    
    return {
        "service": "langfuse_observability",
        "enabled": config.get("is_enabled", False),
        "credential_configured": config.get("credential_configured", False),
        "health_status": config.get("health_status", "unknown"),
        "message": (
            "Langfuse is configured and ready"
            if config.get("is_enabled") and config.get("credential_configured")
            else ("Langfuse is disabled (optional)" if not config.get("is_enabled") else "Langfuse enabled but not fully configured")
        )
    }
```

---

## Tests

### Backend Tests: `backend/tests/test_observability/test_admin_config.py`

```python
def test_get_observability_config_defaults(client, admin_jwt):
    """GET /api/v1/admin/observability/status returns defaults when not configured."""
    resp = client.get(
        "/api/v1/admin/observability/status",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_enabled"] is False
    assert data["credential_configured"] is False
    assert data["health_status"] == "unknown"


def test_update_observability_config(client, admin_jwt):
    """POST /api/v1/admin/observability/update saves configuration."""
    payload = {
        "is_enabled": False,
        "base_url": "https://cloud.langfuse.com",
        "environment": "staging",
        "sample_rate": 0.5,
    }
    resp = client.post(
        "/api/v1/admin/observability/update",
        json=payload,
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    assert resp.status_code == 200
    
    # Verify saved
    resp2 = client.get(
        "/api/v1/admin/observability/status",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    data = resp2.get_json()
    assert data["environment"] == "staging"
    assert data["sample_rate"] == 0.5


def test_write_credential_returns_fingerprint_only(client, admin_jwt):
    """POST /api/v1/admin/observability/credential returns fingerprint, never plaintext key."""
    payload = {
        "public_key": "pk_test_abc123",
        "secret_key": "sk_test_xyz789",
    }
    resp = client.post(
        "/api/v1/admin/observability/credential",
        json=payload,
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    
    # Response has fingerprints, not plaintext
    assert "public_key_fingerprint" in data
    assert "secret_key_fingerprint" in data
    assert "public_key" not in data
    assert "secret_key" not in data
    assert data["public_key_fingerprint"].startswith("pk_")
    assert data["secret_key_fingerprint"].startswith("sk_")


def test_credential_never_in_status(client, admin_jwt):
    """GET /api/v1/admin/observability/status never includes plaintext credentials."""
    # Write credential
    client.post(
        "/api/v1/admin/observability/credential",
        json={"secret_key": "sk_secret123"},
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    
    # Get status - should have fingerprint but not plaintext
    resp = client.get(
        "/api/v1/admin/observability/status",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    data = resp.get_json()
    assert "credential_fingerprint" in data
    assert "sk_secret123" not in str(data)


def test_credential_rotation(client, admin_jwt):
    """Writing new credential rotates old one."""
    # Write first credential
    client.post(
        "/api/v1/admin/observability/credential",
        json={"secret_key": "sk_first"},
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    
    # Get first fingerprint
    resp1 = client.get(
        "/api/v1/admin/observability/status",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    fp1 = resp1.get_json()["credential_fingerprint"]
    
    # Write second credential
    client.post(
        "/api/v1/admin/observability/credential",
        json={"secret_key": "sk_second"},
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    
    # Get second fingerprint - should be different
    resp2 = client.get(
        "/api/v1/admin/observability/status",
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    fp2 = resp2.get_json()["credential_fingerprint"]
    assert fp1 != fp2


def test_validate_base_url(client, admin_jwt):
    """base_url validation rejects invalid URLs."""
    payload = {"base_url": "not-a-url"}
    resp = client.post(
        "/api/v1/admin/observability/update",
        json=payload,
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    assert resp.status_code == 400
    assert "invalid_url" in resp.get_json().get("error_code", "")


def test_validate_sample_rate(client, admin_jwt):
    """sample_rate validation ensures 0.0–1.0."""
    resp = client.post(
        "/api/v1/admin/observability/update",
        json={"sample_rate": 1.5},
        headers={"Authorization": f"Bearer {admin_jwt}"}
    )
    assert resp.status_code == 400
```

---

## Restart vs. Live-Reload Behavior

| Setting | Type | Restart Required? | Reason |
|---------|------|-------------------|--------|
| `is_enabled` | boolean | ✅ Yes | Controls adapter initialization |
| `base_url` | string | ❌ No | Can be reconfigured on adapter |
| `public_key` | secret | ❌ No | Can be re-fetched and rotated |
| `secret_key` | secret | ❌ No | Can be re-fetched and rotated |
| `environment` | string | ❌ No | Metadata only |
| `release` | string | ❌ No | Metadata only |
| `sample_rate` | float | ❌ No | Can be updated on adapter |
| `capture_prompts` | boolean | ❌ No | Adapter respects at trace time |
| `capture_outputs` | boolean | ❌ No | Adapter respects at trace time |
| `capture_retrieval` | boolean | ❌ No | Adapter respects at trace time |
| `redaction_mode` | string | ❌ No | Adapter respects at sanitization time |

**Note**: `is_enabled` requires restart because it determines whether the adapter is initialized. However, the adapter can be reconfigured at runtime for all other settings through a refresh mechanism.

---

## Secret Masking Strategy

**Never display**:
- Plaintext public_key
- Plaintext secret_key
- Raw encrypted bytes

**Always display**:
- Whether credential is configured (boolean)
- Credential fingerprint (first 2 + last 2 chars visible, middle masked)
- Health status
- Last tested timestamp

**Example**:
```
Credential Status: ✓ Configured
  Public Key:  pk_xxxxxxxxxxxxxxxxx8f9a
  Secret Key:  sk_xxxxxxxxxxxxxxxd3e2
  Last Test:   2026-04-24 15:30:45 UTC (healthy)
```

---

## Summary: 10 Implementation Checklist

- [ ] Create `ObservabilityConfig` database model
- [ ] Create `ObservabilityCredential` database model  
- [ ] Create `observability_governance_service.py` with functions for config, credential, and health check
- [ ] Create `observability_governance_routes.py` with 5 API endpoints
- [ ] Add `/manage/observability-settings` route and template
- [ ] Create `manage_observability_settings.js` with form logic
- [ ] Integrate Langfuse adapter initialization in `factory_app.py`
- [ ] Update release-readiness to include Langfuse status
- [ ] Create comprehensive tests for admin config, credentials, validation
- [ ] Update documentation with Administration Tool operator guide

---

## Files Touched

**Database Models**:
- `backend/app/models/governance_core.py` — Add ObservabilityConfig, ObservabilityCredential

**Backend Services**:
- `backend/app/services/observability_governance_service.py` — NEW (credential management)
- `backend/app/api/v1/observability_governance_routes.py` — NEW (API endpoints)
- `backend/app/factory_app.py` — Update to initialize Langfuse

**Administration Tool**:
- `administration-tool/route_registration_manage_sections.py` — Add observability route
- `administration-tool/templates/manage/observability_settings.html` — NEW (UI)
- `administration-tool/static/manage_observability_settings.js` — NEW (JavaScript)

**Tests**:
- `backend/tests/test_observability/test_admin_config.py` — NEW (comprehensive tests)

**Documentation**:
- `docs/ADMINISTRATION_TOOL.md` — Update with Langfuse section

---

## Next Steps

1. **Create database models** (ObservabilityConfig, ObservabilityCredential)
2. **Implement service layer** (observability_governance_service.py)
3. **Implement API routes** (observability_governance_routes.py)
4. **Create Administration Tool UI** (template + JS)
5. **Integrate with backend startup** (factory_app.py)
6. **Write comprehensive tests**
7. **Update documentation**
8. **Manual testing** with real Langfuse credentials

This implementation ensures:
- ✅ **Consistency** with existing AI provider model
- ✅ **Security** via encryption and write-only masked fields
- ✅ **Auditability** via fingerprints (never exposing secrets)
- ✅ **Operability** via Administration Tool UI
- ✅ **Flexibility** for live reconfiguration (except `is_enabled`)
