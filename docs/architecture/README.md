# Architecture Documentation

System design and technical architecture for WorldOfShadows.

## Core Architecture

### 🏗️ [Server Architecture](./ServerArchitecture.md)
High-level backend infrastructure, service decomposition, and deployment topology.

### 🌐 [Backend API Design](./BackendApi.md)
RESTful API structure, authentication, data models, and service patterns.

### 🎨 [Frontend Architecture](./FrontendArchitecture.md)
Client-side structure, component organization, state management, and user interface patterns.

### 🔄 [Frontend-Backend Integration](./FrontendBackendRestructure.md)
Data flow, API contracts, session management, and cross-service communication.

### 🌍 [Multilingual Support](./MultilingualArchitecture.md)
i18n implementation, translation systems, language negotiation, and content localization.

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Administration)                 │
│                   (Flask + Jinja2 Templates)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP REST API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Backend API                             │
│              (Flask + SQLAlchemy + Alembic)                  │
├─────────────────────────────────────────────────────────────┤
│ - User Management & Authentication                           │
│ - Forum & Community Features                                 │
│ - News & Wiki Management                                     │
│ - Data Persistence (SQLite)                                  │
└────────────┬──────────────────────────┬──────────────────────┘
             │                          │
    WebSocket │                         │ Internal API
             ▼                          ▼
    ┌──────────────────┐       ┌──────────────────┐
    │  World Engine    │       │  Administration  │
    │   (FastAPI)      │       │     Tool         │
    │                  │       │                  │
    │ - Game Runtime   │       │ - Content Mgmt   │
    │ - Player Seats   │       │ - User Admin     │
    │ - Narrative Flow │       │ - Moderation     │
    └──────────────────┘       └──────────────────┘
```

## Data Flow

### Authentication & Session
- User logs in via `/api/v1/auth/login`
- Backend generates JWT access token + refresh token
- Tokens stored in database (`refresh_tokens` table)
- Administration tool forwards requests with Bearer token

### Game Session (World Engine)
- Player joins run via WebSocket ticket authentication
- Ticket contains player identity (account_id, display_name, character_id)
- World Engine maintains runtime state in memory
- Actions broadcast to all players in run via WebSocket

## Database

- **Primary:** SQLite (`backend/instance/wos.db`)
- **Migrations:** Alembic-managed schema evolution
- **Current version:** Migration 039 (refresh tokens table)
- **See:** [Database Documentation](../database/README.md)

## Key Design Decisions

1. **Microservice approach:** Backend, Frontend, and World Engine as separate services
2. **Stateless frontend:** Administration tool is session-based proxy to Backend
3. **Real-time gaming:** World Engine uses WebSocket for low-latency game updates
4. **OAuth-ready:** Refresh token pattern enables token rotation and revocation
5. **Multilingual:** Locale detection via Accept-Language and session storage

## Security Architecture

- JWT-based authentication (short-lived access tokens)
- Refresh token rotation and revocation
- Session cookies with secure flags (HTTPS in production)
- CORS allowlisting for cross-origin requests
- Input validation at service boundaries
- **See:** [Security Documentation](../security/README.md)

## Related Documentation

- [Development Guide](../development/README.md) - How to work with this architecture
- [Testing Guide](../testing/README.md) - Testing strategy across services
- [API Documentation](../api/README.md) - Endpoint specifications

---

**Need clarification?** Ask in [Architecture Discussion](https://github.com/your-org/worldofshadows/discussions)
