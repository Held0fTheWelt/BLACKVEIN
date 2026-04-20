# Development Setup: Local World-Engine + Remote Backend

Guide for testing the World-Engine with the PythonAnywhere remote backend.

## Prerequisites

- Python 3.8+
- Git
- Virtual environment (`venv`)
- Access to PythonAnywhere backend at `https://held0fthewelt.pythonanywhere.com`

## Architecture

```
┌─────────────────────────────────────┐
│   Local World-Engine               │
│   (Development Machine)            │
│   - Game logic                      │
│   - Character management           │
│   - Story generation               │
│   - Local testing                  │
└──────────────────┬──────────────────┘
                   │
                   │ HTTPS API Calls
                   ▼
┌─────────────────────────────────────┐
│   PythonAnywhere Backend            │
│   (Remote: held0fthewelt.pa.com)   │
│   - User authentication             │
│   - Data persistence                │
│   - Email verification              │
│   - Game saves storage              │
└─────────────────────────────────────┘
```

## Setup Steps

### 1. Clone the World-Engine

```bash
cd ~/projects
git clone <world-engine-repo>
cd world-engine
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in the world-engine root:

```env
# Backend Configuration
BACKEND_URL=https://held0fthewelt.pythonanywhere.com
BACKEND_API_BASE=/api/v1

# Game Server
GAME_SERVER_HOST=127.0.0.1
GAME_SERVER_PORT=5001

# Authentication (optional for testing)
DEBUG=1
LOG_LEVEL=DEBUG
```

### 3. Update Game Routes (if needed)

If the world-engine makes API calls, ensure it uses the remote backend:

```python
import os

BACKEND_URL = os.getenv("BACKEND_URL", "https://held0fthewelt.pythonanywhere.com")

# Example: Fetch user data
def get_user_data(user_id, token):
    url = f"{BACKEND_URL}/api/v1/users/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    return response.json()
```

### 4. Start World-Engine Locally

```bash
# Terminal 1: Activate environment
cd ~/projects/world-engine
source venv/bin/activate

# Run the world-engine
python run.py
# Output: Server running on http://127.0.0.1:5001
```

### 5. Test Connectivity

#### Health Check

```bash
curl https://held0fthewelt.pythonanywhere.com/api/v1/health
# Response: {"status": "ok"}
```

#### Authentication Flow

```bash
# 1. Register user on remote backend
curl -X POST https://held0fthewelt.pythonanywhere.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'

# 2. Login to get JWT token
curl -X POST https://held0fthewelt.pythonanywhere.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "SecurePassword123!"
  }'
# Response: {"access_token": "eyJ0eXAi..."}

# 3. Use token in world-engine requests
TOKEN="eyJ0eXAi..."
curl http://127.0.0.1:5001/game/start \
  -H "Authorization: Bearer $TOKEN"
```

## Integration Points

### User Authentication

World-Engine should validate tokens with the remote backend:

```python
from flask import request
from functools import wraps
import requests

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return {"error": "Missing authorization header"}, 401

        token = auth_header.split(" ")[1]

        # Validate with remote backend
        response = requests.post(
            f"{BACKEND_URL}/api/v1/auth/validate",
            headers={"Authorization": f"Bearer {token}"}
        )

        if response.status_code != 200:
            return {"error": "Invalid token"}, 401

        return f(*args, **kwargs)
    return decorated
```

### Game Saves

Store game saves on the remote backend:

```python
def save_game(user_id, game_data, token):
    """Save game state to remote backend"""
    url = f"{BACKEND_URL}/api/v1/game/saves"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "user_id": user_id,
        "data": game_data,
        "timestamp": datetime.now().isoformat()
    }

    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def load_game(user_id, save_id, token):
    """Load game state from remote backend"""
    url = f"{BACKEND_URL}/api/v1/game/saves/{save_id}"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)
    return response.json()
```

## Testing Scenarios

### Scenario 1: Basic Authentication

```bash
# 1. Create account on web UI
# Visit: https://held0fthewelt.pythonanywhere.com/register

# 2. Login and get token
TOKEN=$(curl -X POST https://held0fthewelt.pythonanywhere.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"SecurePassword123!"}' \
  | jq -r '.access_token')

# 3. Test world-engine with token
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5001/game/profile
```

### Scenario 2: Game Save/Load

```bash
# Save game
curl -X POST http://127.0.0.1:5001/game/save \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "character_name": "Shadow Walker",
    "level": 42,
    "inventory": ["sword", "shield"]
  }'

# Load game
curl http://127.0.0.1:5001/game/load \
  -H "Authorization: Bearer $TOKEN"
```

### Scenario 3: Multi-User Testing

```bash
# Register multiple users
for i in {1..5}; do
  curl -X POST https://held0fthewelt.pythonanywhere.com/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{
      \"username\": \"player$i\",
      \"email\": \"player$i@example.com\",
      \"password\": \"SecurePassword123!\"
    }"
done

# Run simultaneous game sessions
parallel -j 5 'TOKEN=$(curl -s -X POST https://held0fthewelt.pythonanywhere.com/api/v1/auth/login -H "Content-Type: application/json" -d "{\"username\":\"player{}\",\"password\":\"SecurePassword123!\"}" | jq -r .access_token); curl http://127.0.0.1:5001/game/start -H "Authorization: Bearer $TOKEN"' ::: {1..5}
```

## Debugging

### Enable Verbose Logging

```python
# In world-engine code
import logging
logging.basicConfig(level=logging.DEBUG)

# Example: Log API calls
logger = logging.getLogger(__name__)
logger.debug(f"Calling backend: {url}")
logger.debug(f"Response: {response.json()}")
```

### Monitor Backend Logs

```bash
# SSH into PythonAnywhere and check logs
# (or check Error log in PythonAnywhere dashboard)
tail -f /var/log/pythonanywhere.com/held0fthewelt.pythonanywhere.com.error.log
```

### Network Debugging

```bash
# Use Postman or Insomnia to test API endpoints
# Or use curl with verbose mode
curl -v https://held0fthewelt.pythonanywhere.com/api/v1/health

# Check SSL/TLS
openssl s_client -connect held0fthewelt.pythonanywhere.com:443
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `Connection refused` | Check if world-engine is running on port 5001 |
| `SSL certificate error` | Update `requests` or use `REQUESTS_CA_BUNDLE` env var |
| `401 Unauthorized` | Verify JWT token hasn't expired (24h lifetime) |
| `CORS errors` | Backend has CORS configured; check `CORS_ORIGINS` in `.env` |
| `Timeout` | PythonAnywhere may be slow; increase timeout to 30s |

## Performance Testing

### Load Test World-Engine

```bash
# Using Apache Bench (ab)
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5001/game/profile

# Using wrk (better for concurrent testing)
wrk -t4 -c100 -d30s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:5001/game/profile
```

### Measure Backend Response Times

```python
import requests
import time

token = "your_token_here"

for i in range(10):
    start = time.time()
    response = requests.get(
        "https://held0fthewelt.pythonanywhere.com/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    elapsed = time.time() - start
    print(f"Request {i+1}: {elapsed*1000:.2f}ms - Status {response.status_code}")
```

## Production Checklist

Before deploying world-engine to production:

- [ ] Replace `localhost` URLs with production world-engine domain
- [ ] Update `BACKEND_URL` to production backend (or keep PythonAnywhere)
- [ ] Set `DEBUG=0` in environment
- [ ] Configure proper CORS origins on backend
- [ ] Set up HTTPS for world-engine
- [ ] Test authentication flow end-to-end
- [ ] Load test with realistic concurrent users
- [ ] Monitor error logs during deployment
- [ ] Set up health checks / monitoring
- [ ] Document API contract changes

## Additional Resources

- [PythonAnywhere Docs](https://help.pythonanywhere.com/)
- [Flask CORS Configuration](https://flask-cors.readthedocs.io/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [REST API Testing Tools](https://www.postman.com/)

---

**Last Updated**: 2026-03-23
**Maintainer**: Development Team
