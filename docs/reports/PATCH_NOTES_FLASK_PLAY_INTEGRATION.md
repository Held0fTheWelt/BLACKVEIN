# Flask ↔ Play Service Integration Patch

This patch adds a first real integration layer between the existing Flask backend and the standalone play service.

## Included work

- Backend-side play service config
- Backend-side ticket signing
- Backend-side launcher API routes
- Session/JWT aware game endpoints
- `/game-menu` launcher UI and browser client
- Play-service internal join-context endpoint
- Play-service account/character-aware participant identity
- WebSocket ticket claim validation
- Test coverage for the new integration layer

## Relevant test commands used

### Play service
```bash
cd world-engine
pytest tests/test_api.py tests/test_runtime_manager.py -q
python -m py_compile app/api/http.py app/api/ws.py app/runtime/manager.py app/runtime/models.py app/auth/tickets.py app/config.py
```

### Backend
```bash
cd backend
PYTHONPATH=. pytest tests/test_game_routes.py --no-cov -q
python -m py_compile app/__init__.py app/config.py app/api/v1/game_routes.py app/services/game_service.py app/web/routes.py
```
