# Post-Hydration Validation Record — 2026-04-21

## Collection proof

- `python -m pytest backend/tests --collect-only -q -o addopts=` → **3681 tests collected in 11.67s**
- `python -m pytest frontend/tests --collect-only -q` → **104 tests collected in 0.06s**
- `python -m pytest administration-tool/tests --collect-only -q` → **1108 tests collected in 0.47s**
- `python -m pytest world-engine/tests --collect-only -q` → **908 tests collected in 3.06s**
- `python -m pytest ai_stack/tests --collect-only -q` → **222 tests collected in 1.62s**

## Fresh suite / slice replays

- `python -m pytest frontend/tests -q` → **104 passed**
- `python -m pytest ai_stack/tests -q` → **208 passed, 14 skipped**
- `python -m pytest tests/smoke/test_backend_startup.py -q` → **29 passed**
- `python -m pytest tests/smoke/test_admin_startup.py -q` → **35 passed**
- `python -m pytest tests/smoke/test_engine_startup.py -q` → **50 passed**
- `python -m pytest backend/tests/test_app_init.py -q -o addopts=` → **4 passed**
- `python -m pytest backend/tests/test_bootstrap_staged_runtime_integration.py -q -o addopts=` → **1 passed**
- `python -m pytest backend/tests/test_backend_playservice_integration.py -q -o addopts=` → **3 passed**
- `python -m pytest backend/tests/test_e2e_god_of_carnage_full_lifecycle.py -q -o addopts=` → **6 passed**
- `python -m pytest backend/tests/writers_room/test_writers_room_g7_operating_contract.py -q -o addopts=` → **6 passed**
- `python -m pytest backend/tests/writers_room/test_writers_room_model_routing.py -q -o addopts=` → **24 passed**
- `python -m pytest backend/tests/writers_room/test_writers_room_routes.py -q -o addopts=` → **17 passed**
- `python -m pytest backend/tests/test_game_routes.py -q -o addopts=` → **29 passed**
- `python -m pytest administration-tool/tests/test_app_factory.py -q` → **17 passed**
- `python -m pytest administration-tool/tests/test_manage_routes.py -q` → **94 passed**
- `python -m pytest administration-tool/tests/test_proxy.py -q` → **5 passed**
- `python -m pytest administration-tool/tests/test_security_headers.py -q` → **135 passed**
- `python -m pytest world-engine/tests/test_story_runtime_rag_runtime.py -q` → **8 passed**
- `python -m pytest world-engine/tests/test_story_runtime_api.py -q` → **2 passed**
- `python -m pytest world-engine/tests/test_api.py -q` → **4 passed**

## Validation interpretation

The blocker family that had been recorded as missing runtime libraries is no longer blocking these surfaces.
The newly remaining partial area is embedding model acquisition for the fastembed-backed path. That is not evidence of missing `langchain` / `langgraph` / `flask` / `sqlalchemy` packages.
