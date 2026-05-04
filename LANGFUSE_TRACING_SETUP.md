# Langfuse Tracing Setup & Testing

## Current Status

✅ **Backend:** Session persistence is working - sessions are stored in database and retrieved across requests
✅ **Code:** Langfuse adapters are wired up in both backend and world-engine
✅ **Credentials:** Stored in backend database (not environment variables)
⏳ **Tracing:** Requires running backend + world-engine to verify

## How It Works

1. **Backend** stores Langfuse credentials in encrypted database tables
2. **World-Engine** fetches credentials from backend via internal API endpoint
3. **Tracing** happens during story turn execution (automatically)

## To Enable & Test Tracing

### 1. Verify .env has LANGFUSE_ENABLED=true
```bash
grep LANGFUSE_ENABLED .env
# Should show: LANGFUSE_ENABLED=true
```

### 2. Start Backend
```bash
cd backend
FLASK_APP=run:app python -m flask run --port 5000
```

### 3. Start World-Engine (in another terminal)
```bash
cd world-engine
python -m uvicorn app.main:app --port 8000
```

### 4. Run Integration Test
```bash
# In main directory
LANGFUSE_ENABLED=true python tests/test_langfuse_story_turn_trace.py
```

## What the Test Does

1. Verifies backend is running
2. Verifies world-engine is running  
3. Fetches Langfuse credentials from backend database
4. Creates a session via backend API
5. Executes a story turn via world-engine API
6. Verifies Langfuse connection

## Expected Behavior

When running, you should see:
```
================================================================================
LANGFUSE STORY TURN TRACE TEST
================================================================================
Backend URL: http://localhost:5000
World-Engine URL: http://localhost:8000
Langfuse Enabled: True
...
[1/6] Checking backend...
[OK] Backend is running
[2/6] Checking world-engine...
[OK] World-Engine is running
[3/6] Fetching Langfuse credentials...
[OK] Credentials available
[4/6] Creating session...
[OK] Session created: <session_id>
[5/6] Executing story turn...
[OK] Turn executed successfully
[6/6] Verifying Langfuse trace...
[OK] Langfuse connection verified

SUCCESS! Check Langfuse dashboard for traces
================================================================================
```

## Debugging

If credentials don't load:
- Check backend has `LANGFUSE_ENABLED=true` 
- Verify credentials exist in database:
  ```bash
  cd backend
  python -m flask shell
  >>> from app.models.governance_core import ObservabilityConfig
  >>> ObservabilityConfig.query.filter_by(service_id='langfuse').first()
  ```

If traces don't appear in Langfuse:
- Check world-engine adapter is initializing (look for logs in world-engine terminal)
- Verify `adapter.is_ready == True` after credentials are fetched
- Make sure story turn execution completes successfully
