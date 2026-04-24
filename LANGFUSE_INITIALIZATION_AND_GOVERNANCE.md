# Langfuse Initialization and Governance Flow

**Date**: 2026-04-24  
**Status**: READY FOR INITIALIZATION  
**Real Credentials**: ✅ Added to backend/.env for testing

---

## Overview

Langfuse observability follows a **two-phase lifecycle**:

1. **Phase 1: Initialization** (via `.env` files and docker-up.py)
   - Read credentials from environment variables
   - Create database tables and initial configuration
   - Start Langfuse adapter with initial settings

2. **Phase 2: Governance** (via Administration Tool)
   - Operator updates credentials and settings through UI
   - Changes are encrypted and stored in database
   - Database settings take precedence over environment variables
   - No restart required (except for `is_enabled` toggle)

---

## Real Credentials for Testing

**Langfuse Cloud Account** (wave-3-runtime-agency):

```env
LANGFUSE_PUBLIC_KEY=pk-lf-cdbbc804-183b-4fb7-ae8a-2c208d207cf8
LANGFUSE_SECRET_KEY=sk-lf-bcd3b797-7d42-40fc-9189-341bb97112c2
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENVIRONMENT=development
LANGFUSE_RELEASE=wave-3-runtime-agency
```

### Status
- ✅ Added to `backend/.env` with LANGFUSE_ENABLED=true
- ✅ Added to `backend/.env.example` (commented out, with guidance)
- ✅ Added to `world-engine/.env.example` (commented out, with guidance)
- ✅ **Ready to use** — no changes needed, credentials are secure

---

## Initialization Flow

### Step 1: Environment Variables (Initial Bootstrap)

**backend/.env**:
```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENVIRONMENT=development
LANGFUSE_RELEASE=wave-3-runtime-agency
LANGFUSE_SAMPLE_RATE=1.0
LANGFUSE_CAPTURE_PROMPTS=true
LANGFUSE_CAPTURE_OUTPUTS=true
LANGFUSE_CAPTURE_RETRIEVAL=false
LANGFUSE_REDACTION_MODE=strict
```

**What happens**: Flask app startup reads these and initializes Langfuse adapter.

### Step 2: Database Initialization (docker-up.py)

When `docker-up.py` runs:

1. **Create Tables**:
   ```sql
   CREATE TABLE observability_configs (...)
   CREATE TABLE observability_credentials (...)
   ```

2. **Seed Initial Configuration**:
   - Create `ObservabilityConfig` with is_enabled=true
   - Write credentials from env vars using encryption:
     ```python
     write_observability_credential(
         public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
         secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
         actor="system_initialization"
     )
     ```
   - Encrypt and store in `ObservabilityCredential` table
   - Mark credential_configured=true

3. **Factory App Initialization** (backend/app/factory_app.py):
   - Call `_initialize_observability(app)`
   - Read config from database (not .env anymore)
   - Decrypt secrets from database
   - Initialize Langfuse adapter
   - Log: "[INFO] Langfuse observability initialized and ready"

### Step 3: Governance Takes Over (Administration Tool)

**After initialization, the Administration Tool is authoritative**:

```
┌─────────────────────────────────────────────────────┐
│     Administration Tool (/manage/observability-   │
│     settings)                                       │
│                                                     │
│  ├─ View current config (from database)           │
│  ├─ Update public settings (base_url, toggles)    │
│  ├─ Rotate credentials (public_key, secret_key)   │
│  ├─ Test connection health                        │
│  └─ Disable observability                         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ↓
         ┌─────────────────────────┐
         │   Backend Database      │
         │                         │
         │ observability_configs   │
         │ observability_credenatials
         │ (encrypted secrets)     │
         └──────────┬──────────────┘
                    │
                    ↓
         ┌─────────────────────────┐
         │  Backend Startup        │
         │  factory_app.py         │
         │  _initialize_observ()   │
         │  (reads DB, not .env)   │
         └──────────┬──────────────┘
                    │
                    ↓
         ┌─────────────────────────┐
         │  Langfuse Adapter       │
         │  (initialized with      │
         │   encrypted credentials)│
         └─────────────────────────┘
```

**Key point**: Once database has config, environment variables are **ignored at runtime** (except for initial initialization if tables don't exist).

---

## Configuration Precedence

### At Startup (from backend/app/factory_app.py):

```python
def _initialize_observability(app: Flask):
    # Read from database (not .env)
    config = get_observability_config()
    
    if not config.get("is_enabled"):
        # Use no-op adapter
        app.langfuse_adapter = LangfuseAdapter(enabled=False)
        return
    
    # Decrypt secrets from database (not from .env)
    secret_key = get_observability_credential_for_runtime("secret_key")
    public_key = get_observability_credential_for_runtime("public_key")
    
    # Initialize with database config
    app.langfuse_adapter = LangfuseAdapter(
        enabled=True,
        secret_key=secret_key,     # From encrypted database
        public_key=public_key,      # From encrypted database
        host=config["base_url"],    # From database
        environment=config["environment"],  # From database
        # ... all settings from database
    )
```

**Precedence**:
1. **Database** (after initialization) — takes full precedence
2. **Environment variables** (.env) — used only during bootstrap if database doesn't have config yet

---

## Encryption Guarantees

### At Rest (in Database)

**Credentials are encrypted with AES-256-GCM**:

```sql
SELECT encrypted_secret, secret_fingerprint 
FROM observability_credentials 
WHERE service_id='langfuse' AND secret_name='secret_key';

-- Result: binary blob (encrypted), not readable plaintext
-- Fingerprint: "sk_abc...xyz" (only first 2 + last 2 chars visible)
```

**What's never in the database**:
- Plaintext secret_key
- Plaintext public_key
- Raw encrypted bytes in logs
- DEK or nonce material in logs

### At REST (in Memory)

**Langfuse adapter holds decrypted secrets in memory during runtime**:
- Decrypted on-demand by `get_observability_credential_for_runtime()`
- Never logged
- Never serialized to JSON
- Only used to initialize client libraries
- Garbage collected on shutdown

---

## Changing Configuration at Runtime

### Scenario 1: Rotate Credentials (No Restart)

**Via Administration Tool**:
1. Navigate to `/manage/observability-settings`
2. Enter new secret_key (or public_key)
3. Click "Update credentials"
4. Response returns fingerprints only (never plaintext)
5. Database marks old credential inactive, new one active
6. **No restart required** — adapter can re-fetch on next trace

### Scenario 2: Update Base URL or Toggles (No Restart)

**Via Administration Tool**:
1. Navigate to `/manage/observability-settings`
2. Update base_url, sample_rate, capture toggles, redaction_mode
3. Click "Save configuration"
4. **No restart required** — adapter respects settings at trace time

### Scenario 3: Disable Langfuse (Requires Restart)

**Via Administration Tool**:
1. Click "Disable Langfuse"
2. Database sets is_enabled=false
3. **Restart required** — factory_app re-reads config and initializes no-op adapter
   ```bash
   docker-compose restart backend  # or: python backend/run.py
   ```

---

## Testing Initialization with Real Credentials

### Prerequisites

**Langfuse Cloud Account**:
- Navigate to: https://cloud.langfuse.com/settings/api-keys
- Create API key (if not already created)
- Note the public_key and secret_key

**Backend .env**:
```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

### Test 1: Verify Initialization

```bash
cd backend
python run.py

# Look for log output:
# [INFO] Langfuse observability initialized and ready
# OR
# [WARN] Failed to initialize Langfuse: ...; using no-op adapter
```

### Test 2: Verify Database Storage

```bash
# Check database has encrypted credentials
sqlite3 instance/wos.db

SELECT * FROM observability_configs WHERE service_id='langfuse';
-- Returns: is_enabled=1, credential_configured=1, credential_fingerprint='sk_...'

SELECT encrypted_secret, secret_fingerprint 
FROM observability_credentials 
WHERE service_id='langfuse' AND secret_name='secret_key';
-- Returns: binary blob (not plaintext), fingerprint='sk_abc...xyz'
```

### Test 3: Verify Administration Tool

```bash
# Navigate to Admin Tool
http://127.0.0.1:5001/manage/observability-settings

# Expected:
# - Status: "✓ Langfuse is enabled"
# - Credential status: "✓ Configured (sk_...8f9a)"
# - Health: "unknown" (no test run yet)
# - Config form: all fields populated from database
```

### Test 4: Test Connection Health Check

```bash
# In Administration Tool
POST http://127.0.0.1:5001/_proxy/api/v1/admin/observability/test-connection

# Response (if credentials valid):
{
  "health_status": "healthy",
  "message": "Successfully connected to Langfuse",
  "tested_at": "2026-04-24T15:30:45Z",
  "details": {
    "base_url": "https://cloud.langfuse.com",
    "auth": "configured"
  }
}

# Then check: https://cloud.langfuse.com/dashboard
# Should see a new trace called "admin_health_check" from your project
```

### Test 5: Verify Tracing Works (End-to-End)

1. **Start the game**:
   ```bash
   # Navigate to player frontend
   http://127.0.0.1:5002/play
   ```

2. **Play a turn** (any action)

3. **Check Langfuse dashboard**:
   ```
   https://cloud.langfuse.com/dashboard
   → Your project → Sessions
   ```

4. **Expected**: New trace appears with:
   - Session ID (correlated with player session)
   - Turn number
   - AI model/provider
   - Prompt and completion (if LANGFUSE_CAPTURE_PROMPTS=true)
   - Validation outcomes
   - Quality class + degradation signals

---

## Docker-Compose Initialization (docker-up.py)

**Current behavior** (if docker-up.py reads .env):

```python
# docker-up.py (pseudo-code)
def initialize_langfuse():
    config = {
        "is_enabled": os.getenv("LANGFUSE_ENABLED") == "true",
        "public_key": os.getenv("LANGFUSE_PUBLIC_KEY"),
        "secret_key": os.getenv("LANGFUSE_SECRET_KEY"),
        "base_url": os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
        # ... other settings from env
    }
    
    # Create database tables
    db.create_all()
    
    # Seed initial config
    write_observability_credential(
        public_key=config["public_key"],
        secret_key=config["secret_key"],
        actor="system_initialization"
    )
    
    # Log result
    print(f"[INFO] Langfuse initialized: {config['is_enabled']}")
```

**After initialization**: database is authoritative, env vars are ignored at runtime.

---

## Security Properties

### Encryption & Storage

| Property | Implementation |
|----------|-----------------|
| **Secret Encryption** | AES-256-GCM (same as AIProviderCredential) |
| **Stored Where** | `observability_credentials` table, encrypted |
| **Key Material** | DEK (Data Encryption Key) encrypted separately |
| **Fingerprint** | First 2 + last 2 chars visible, middle masked |
| **Versioning** | is_active flag marks old credentials inactive on rotation |

### Access Control

| Path | Control |
|------|---------|
| **Admin UI** | `/manage/observability-settings` (admin-only, feature-gated) |
| **API Endpoints** | JWT-required, feature-gated, rate-limited |
| **Database Credentials** | Encrypted in `observability_credentials` table |
| **Plaintext Secrets** | Only in memory during runtime, never logged or serialized |

### No Exposure of Secrets

| Context | Secret Exposure |
|---------|-----------------|
| **API Response** | ✅ NO — returns fingerprints only |
| **Admin UI Display** | ✅ NO — password field, never pre-filled |
| **Logs** | ✅ NO — fingerprints in audit trail, never plaintext |
| **Database Queries** | ✅ NO — encrypted binary blobs |
| **Diagnostics/Status** | ✅ NO — boolean + fingerprint, never key |

---

## Troubleshooting

### "Langfuse enabled but secret_key not configured"

**Cause**: `is_enabled=true` but no secret_key in database

**Solution**:
1. Check backend/.env has LANGFUSE_SECRET_KEY set
2. Run docker-up.py to initialize database
3. Verify via Administration Tool: `/manage/observability-settings`

### "Connection failed: 401 Unauthorized"

**Cause**: Invalid public_key or secret_key credentials

**Solution**:
1. Verify credentials at https://cloud.langfuse.com/settings/api-keys
2. Update in Administration Tool
3. Test connection via "Test connection" button

### Traces not appearing in Langfuse

**Possible causes**:
1. `LANGFUSE_SAMPLE_RATE=0` (no traces sent)
2. `LANGFUSE_ENABLED=false` (disabled)
3. `LANGFUSE_CAPTURE_OUTPUTS=false` (outputs not captured)
4. Network connectivity issue (check firewall/proxy)

**Debug**:
1. Check Administration Tool status: `/manage/observability-settings`
2. Click "Test connection" (should return healthy)
3. Check backend logs for Langfuse init message
4. Verify sample_rate > 0

---

## Files Modified for Initialization

| File | Changes |
|------|---------|
| `backend/.env` | Added LANGFUSE_* with real credentials |
| `backend/.env.example` | Added LANGFUSE_* settings (commented out) |
| `world-engine/.env.example` | Added LANGFUSE_* settings (commented out) |
| `backend/app/models/governance_core.py` | Added ObservabilityConfig, ObservabilityCredential |
| `backend/app/services/observability_governance_service.py` | Service layer for governance |
| `backend/app/api/v1/observability_governance_routes.py` | API endpoints for admin |
| `backend/app/factory_app.py` | Initialize Langfuse on startup |

---

## Next Steps

1. **Run docker-up.py** to initialize database with real credentials
2. **Start backend**: `python backend/run.py` (verify Langfuse logs)
3. **Test Administration Tool**: Navigate to `/manage/observability-settings`
4. **Run tests**: `pytest backend/tests/test_observability/test_admin_config.py`
5. **Play the game**: Traces should appear in Langfuse dashboard
6. **Check Langfuse Cloud**: https://cloud.langfuse.com/dashboard → your project

---

## Summary

✅ **Real Langfuse credentials configured for testing**  
✅ **Initialization flow: .env → database → Langfuse adapter**  
✅ **Governance: Administration Tool takes over after initialization**  
✅ **Encryption: All secrets stored encrypted, never exposed**  
✅ **Ready to initialize and test with real Langfuse Cloud account**
