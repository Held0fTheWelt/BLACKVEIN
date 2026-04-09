# API Documentation

Complete API reference for all services in WorldOfShadows.

## Backend API

### [REST API Reference](./REFERENCE.md#backend-api)
Complete REST endpoint documentation for the Flask backend.

The Flask app also exposes **non-API technical pages** at **`/backend/*`** (architecture summary, API overview, operations pointers). These are for operators/developers only; canonical player UI remains in `frontend/`.

**Base URL:** `http://localhost:5000` (development) or `https://api.worldofshadows.com` (production)

**Key Endpoints:**
```
Authentication
  POST   /api/v1/auth/login            - User login
  POST   /api/v1/auth/logout           - User logout
  POST   /api/v1/auth/refresh          - Refresh access token

Users
  GET    /api/v1/users/<id>            - Get user profile
  PUT    /api/v1/users/<id>            - Update user profile
  DELETE /api/v1/users/<id>            - Delete user account

Forum
  GET    /api/v1/forum/categories      - List forum categories
  GET    /api/v1/forum/threads         - List threads
  POST   /api/v1/forum/threads         - Create thread
  GET    /api/v1/forum/posts           - List posts in thread
  POST   /api/v1/forum/posts           - Create post

See [REST API Reference](./REFERENCE.md#backend-api) for complete details.
```

### Authentication & Authorization
- **Type:** JWT (JSON Web Tokens)
- **Header:** `Authorization: Bearer <access_token>`
- **Tokens:** Access (short-lived) + Refresh (long-lived)
- **Revocation:** Via refresh_tokens database table
- **See:** [API reference](./REFERENCE.md), [Service boundaries](../technical/architecture/service-boundaries.md)

## World Engine API

### [World Engine Specification](./REFERENCE.md#world-engine-api)
FastAPI-based game runtime with HTTP and WebSocket endpoints.

**Base URL:** `http://localhost:5002` (development) or `https://engine.worldofshadows.com` (production)

**Key Endpoints:**
```
HTTP (REST)
  GET    /api/health                   - Service health
  GET    /api/templates                - Available game templates
  POST   /api/runs                     - Create game run
  GET    /api/runs/<run_id>            - Get run details
  POST   /api/tickets                  - Issue player ticket
  POST   /api/internal/join-context    - Add participant (internal)

WebSocket (Real-time)
  WS     /ws?ticket=<ticket>           - Player connection
  Messages: snapshot, join, leave, move, say, emote, etc.

See [World Engine API](./REFERENCE.md#world-engine-api) for complete details.
```

### Ticket Authentication
- **Type:** Signed JWT tickets
- **Contains:** player identity (account_id, character_id, role_id)
- **Validation:** Signature verification + expiration check
- **Creation:** Backend → World Engine → Browser
- **See:** [World Engine Security](../security/README.md)

## Administration Tool

### [Administration Endpoints](./REFERENCE.md#administration-tool)
Proxy endpoints for content management and user administration.

**Key Endpoints:**
```
Routes & Navigation
  GET    /manage/home                  - Dashboard
  GET    /manage/users                 - User management
  GET    /manage/forum                 - Forum moderation

Forum Management
  GET    /manage/forum/categories      - Manage categories
  POST   /manage/forum/categories      - Create category
  GET    /manage/forum/moderation      - Moderation queue

News & Wiki
  GET    /manage/news                  - News management
  GET    /manage/wiki                  - Wiki management
  POST   /manage/content                - Create content

See [Administration API](./REFERENCE.md#administration-tool) for complete details.
```

### Security
- **Type:** Session-based (cookies)
- **Sessions:** Stored in backend database
- **CSRF:** Token-based protection
- **Scope:** Managers and administrators only

## API Contracts & Examples

### Example: User Login
```javascript
// Request
POST /api/v1/auth/login HTTP/1.1
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password"
}

// Response (200 OK)
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "user": {
    "id": 123,
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

### Example: Create Game Run
```javascript
// Request
POST /api/runs HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "template_id": "god_of_carnage_solo",
  "account_id": "user_123",
  "display_name": "John Doe"
}

// Response (200 OK)
{
  "run": {
    "id": "run_abc123",
    "template_id": "god_of_carnage_solo",
    "created_at": "2026-03-26T18:00:00Z"
  }
}
```

### Example: WebSocket Connection
```javascript
// Connect with ticket
const ticket = "eyJhbGc...";
const ws = new WebSocket(`ws://localhost:5002/ws?ticket=${ticket}`);

// Listen for snapshots
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "snapshot") {
    console.log("Current state:", msg.data);
  }
};

// Send action
ws.send(JSON.stringify({
  "action": "move",
  "target_room_id": "kitchen"
}));
```

## Error Handling

All APIs return consistent error responses:

```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "detail": "Additional context"
}
```

**Common Status Codes:**
- `200` - Success
- `400` - Bad request (validation error)
- `401` - Unauthorized (missing or invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not found
- `500` - Server error

## Rate Limiting

- **Backend:** 100 requests per minute per IP
- **World Engine:** No rate limit (internal use only)
- **Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Postman Collections

Complete collections available in `postman/` directory.

## Integration Guides

- [Backend integration (archived note)](../archive/architecture-legacy/FrontendBackendRestructure.md) — historical; see [Service boundaries](../technical/architecture/service-boundaries.md)
- [Game Integration](../features/README.md#game-integration) - How to integrate world engine

## Related Documentation

- [Technical architecture](../technical/architecture/architecture-overview.md) — system design; [Architecture redirect](../architecture/README.md)
- [Security Guide](../security/README.md) - Authentication & authorization
- [Testing Guide](../testing/README.md) - API testing strategies

---

**API Issue?** Check the [Testing Guide](../testing/README.md) or create an issue.
