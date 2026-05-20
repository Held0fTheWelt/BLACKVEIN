# MVP5 Source Locator Matrix

**Status**: PREFLIGHT - Source Resolution Gate  
**Date**: 2026-04-30  
**Purpose**: Map all MVP5 implementation targets to concrete repository paths before patching begins.

---

## Source Locator Matrix

| Area | Expected Path | Actual Path | Symbol/Anchor | Status |
|---|---|---|---|---|
| **Backend route** | Backend game/play turn execution | `backend/app/api/v1/session_routes.py` | `execute_session_turn()` at line 481 | ✅ FOUND |
| **Backend service** | Backend game service logic | `backend/app/services/game_service.py` | `GameServiceError`, `_parse_create_run_v1()` | ✅ FOUND |
| **World-Engine API** | HTTP handler for story turn execution | `world-engine/app/api/http.py` | `CreateRunRequest`, `TicketRequest`, `router` APIRouter | ✅ FOUND |
| **World-Engine story manager** | Turn execution and LDSS invocation | `world-engine/app/story_runtime/manager/` | `_build_ldss_scene_envelope()`, `_finalize_committed_turn()` | ✅ FOUND |
| **Frontend route** | Play shell route handler | `frontend/app/routes_play.py` | `session_view()`, `session_execute()` at line 986+ | ✅ FOUND |
| **Frontend template (main)** | Session shell HTML template | `frontend/templates/session_shell.html` | `<div id="turn-transcript">`, `<form id="play-execute-form">` | ✅ FOUND |
| **Frontend static - OLD renderer** | Current play shell (to be replaced) | `frontend/static/play_shell.js` | `renderEntries()`, `applyRuntimePayload()` | ✅ EXISTS (will rewrite) |
| **Frontend static - NEW block renderer** | Block-to-DOM mapper (MVP5-P01) | `frontend/static/play_block_renderer.js` | `BlockRenderer.render(blocks)` | 🆕 CREATE |
| **Frontend static - typewriter engine** | Virtual clock + delivery (MVP5-P02) | `frontend/static/play_typewriter_engine.js` | `TypewriterEngine`, `VirtualClock` | 🆕 CREATE |
| **Frontend static - controls** | Skip/Reveal UI handlers (MVP5-P03) | `frontend/static/play_controls.js` | `SkipCurrentControl`, `RevealAllControl` | 🆕 CREATE |
| **Frontend static - WebSocket listener** | Real-time block reception (MVP5 D) | `frontend/static/play_ws_listener.js` | `NarratorStreamListener.onBlock()` | ⏳ EXTEND existing `play_narrative_stream.js` |
| **Frontend static - CSS** | Block rendering + accessibility styles | `frontend/static/style.css` | `.scene-block`, `.block-typewriter`, `.accessibility-mode` | ⏳ EXTEND |
| **Admin Tool - settings storage** | Frontend config persistence | `backend/app/models/site_setting.py` | `SiteSetting` model with key/value columns | ✅ FOUND |
| **Admin Tool - settings route** | Typewriter config endpoint | `backend/app/api/v1/admin_settings_routes.py` | `GET/POST /api/v1/admin/frontend-config` (create or extend) | ⏳ CREATE/EXTEND |
| **Admin Tool - UI** | Typewriter delivery config panel | `administration-tool/static/manage_runtime_settings.js` | `TypewriterConfigPanel`, render delivery settings | ⏳ EXTEND |
| **Admin Tool - template** | Runtime settings admin page | `administration-tool/templates/manage_runtime_settings.html` | Typewriter delivery section | ⏳ EXTEND or reference |
| **JS Unit Tests** | Block renderer, typewriter, controls unit tests | `frontend/tests/test_block_renderer.js` | Test suite for MVP5-P01 through P04 | 🆕 CREATE |
| **Browser/E2E Tests** | Final Annette/Alain E2E acceptance | `tests/e2e/test_final_goc_annette_alain_e2e.py` | `test_final_annette_e2e_evidence`, `test_final_alain_e2e_evidence` | 🆕 CREATE |
| **Reports** | MVP5 source locator artifact | `tests/reports/MVP_Live_Runtime_Completion/MVP5_SOURCE_LOCATOR.md` | This file | 📝 IN PROGRESS |
| **Reports** | MVP5 operational evidence | `tests/reports/MVP_Live_Runtime_Completion/MVP5_OPERATIONAL_EVIDENCE.md` | docker-up.py, run_tests.py results | ⏳ CREATE |
| **Reports** | Final E2E acceptance evidence | `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` | Annette run, Alain run, transcripts, trace links | ⏳ CREATE |
| **Test runner** | MVP5 test suite registration | `tests/run_tests.py` | `--mvp5` flag, frontend/e2e suite inclusion | ⏳ EXTEND |
| **GitHub Workflows** | CI/CD frontend + E2E tests | `.github/workflows/tests.yml` | Jobs for JS tests, browser tests, E2E gate | ⏳ EXTEND |
| **TOML/Tooling** | Frontend test config | `pyproject.toml`, `frontend/pyproject.toml` | `testpaths`, `pytest.ini` for JS/DOM tests | ⏳ EXTEND |
| **docker-up.py** | Startup entrypoint with service verification | `docker-up.py` | Service startup + health check (no new changes needed) | ✅ READY |

---

## Resolution Results

### ✅ RESOLVED-1: `world-engine/app/api/http.py`
**Found**: Yes, file exists at `world-engine/app/api/http.py`  
**Key Symbols**: `CreateRunRequest`, `TicketRequest`, FastAPI `router`  
**Impact**: Frontend consumes via Backend proxy (Backend → World-Engine)

### ✅ RESOLVED-2: `backend/app/services/game_service.py`
**Found**: Yes, file exists at `backend/app/services/game_service.py`  
**Key Symbols**: `GameServiceError`, `_parse_create_run_v1()`, payload validation  
**Impact**: Backend game service is authoritative; Frontend Delivery Config stored via `SiteSetting` model

### ✅ RESOLVED-3: Frontend test infrastructure
**Found**: `frontend/pyproject.toml` exists (pytest for Python)  
**Framework**: Python pytest-based (no separate JS test framework detected yet)  
**Impact**: JS unit tests likely run via pytest with node/JavaScript runner or Playwright for integration

### ✅ RESOLVED-4: Admin Tool backend settings storage
**Found**: `backend/app/models/site_setting.py` exists  
**Key Symbols**: `SiteSetting(db.Model)` with `key` (primary key) and `value` (text) columns  
**Impact**: Typewriter delivery config stored as JSON in `SiteSetting` table via Admin API

---

---

## Stop Gate Status

MVP5 code patching **can now begin** when:
- ✅ All "FOUND" rows have concrete paths + symbols
- ✅ All "EXTEND/CREATE" rows have target paths defined
- ✅ All pending rows resolved (FOUND or not_present with reason)

**Current Status**: ✅✅✅ **SOURCE LOCATOR MATRIX COMPLETE — GATE PASSED**

**All 4 pending resolutions found. Ready for implementation planning.**

---

## Next Step: Implementation Planning

With source matrix complete, ready for:
1. **grill-me interview** to clarify MVP5 integration points
2. **Module design** for modular block renderer architecture
3. **Test strategy** for JS/DOM + Browser/E2E
4. **Admin Tool delivery config** UI/API design
5. **Code implementation** (MVP5-P01 through MVP5-P07)
