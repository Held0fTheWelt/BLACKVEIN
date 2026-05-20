# MVP_Live_Runtime_Completion — MVP 5 — Interactive Text-Adventure Frontend and Final E2E

**Status**: READY FOR IMPLEMENTATION
**Date**: 2026-04-30
**Architecture**: Modular Block Rendering (BlockRenderer + TypewriterEngine + BlocksOrchestrator)
**Data Integration**: HTTP Initial Load + WebSocket Narrator Streaming
**Configuration**: Global Typewriter Delivery Config via Admin Tool

---

## Mission

Implement the **staged interactive text-adventure / dramatic chat frontend** with modular block rendering, deterministic typewriter delivery, skip/reveal/accessibility controls, and final E2E proof for Annette and Alain God of Carnage solo play.

The frontend must:
- Consume `visible_scene_output.blocks.v1` from HTTP and WebSocket
- Render one DOM block per scene block (no single blob)
- Support deterministic typewriter delivery with virtual clock (for testing)
- Provide skip/reveal controls without runtime regeneration
- Support accessibility mode (disable animation, show all immediately)
- Reject legacy blob output (mark degraded, fail final E2E)
- Produce final Annette/Alain E2E transcript evidence

---

## Scope

### In Scope

- **Modular Frontend Architecture**:
  - `BlockRenderer` — Pure DOM rendering (no state)
  - `TypewriterEngine` — Virtual clock + character-by-character delivery
  - `BlocksOrchestrator` — State management + orchestration
  - `PlayControls` — UI event handlers (Skip/Reveal/Accessibility)

- **Data Integration**:
  - HTTP POST `/api/v1/sessions/{id}/turns` → `{visible_scene_output: {blocks: [...]}, diagnostics: {...}}`
  - WebSocket narrator streaming (extend `play_narrative_stream.js` to send blocks)
  - Merge initial blocks + streaming blocks into single render queue

- **Typewriter Delivery**:
  - `TypewriterDeliveryConfig` with `characters_per_second`, `pause_before_ms`, `pause_after_ms`, `skippable`
  - Virtual clock for deterministic tests (advance time with `clock.advanceBy(ms)`)
  - Production uses `requestAnimationFrame` (smooth, non-blocking)
  - Test mode uses virtual timer for reproducible behavior

- **Controls & Accessibility**:
  - Skip Current Block — complete current animation, move to next
  - Reveal All — show all queued blocks immediately
  - Accessibility Mode — disable typewriter, show all text immediately, preserve content order
  - Input-UI blocking: disabled while narrator streams, enabled when ruhepunkt signal arrives

- **Configuration**:
  - Global Typewriter Config stored in `backend/app/models/backend/site_setting.py` (key: `frontend_typewriter_config`)
  - Admin Tool UI in `administration-tool/static/manage_runtime_settings.js` to edit settings
  - API endpoint: `GET/PATCH /api/v1/admin/frontend-config/typewriter`
  - Settings applied per-session at load time

- **Testing**:
  - JS Unit Tests: `BlockRenderer`, `TypewriterEngine`, `BlocksOrchestrator`, `PlayControls`
  - Browser E2E Tests: Final Annette and Alain runs with transcript + trace + Narrative Gov cross-check
  - Final Report: `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` with evidence

### Out of Scope

- Changing LDSS behavior (except to fix contract mismatches discovered by frontend tests)
- Changing diagnostics semantics (except to consume MVP 4 fields)
- Adding new story content
- Per-module or per-session typewriter config (global only, for MVP5; per-module in future MVP)
- Diagnostic panels in player-facing UI (diagnostics are operator-only, via separate admin mode later)

---

## Base Contract

A real `live_dramatic_scene_simulator` runs in the live play path and renders a **staged interactive text-adventure / dramatic chat experience**.

The player chooses Annette or Alain. The selected character is human-controlled. The other canonical God of Carnage characters are free NPC dramatic actors. NPCs speak, act, pursue their own line, interact with other NPCs, and interact with the environment through canonical, typical, or `similar_allowed` affordances. NPCs may use admitted objects with or against other actors when valid and non-coercive. The Narrator is the player's inner perception/orientation voice, not a dialogue summarizer.

Diagnostics, Narrative Gov, and Langfuse or deterministic trace export prove the live runtime path. `docker-up.py`, `tests/run_tests.py`, GitHub workflows, and TOML/tooling configs remain fully functional. Partial foundation is not acceptable.

### Global Prohibitions

- Do not reintroduce `visitor` as a story actor, runtime participant, prompt role, responder, lobby seat, frontend role, or fallback alias.
- Do not convert `god_of_carnage_solo` into a content module.
- Do not place canonical God of Carnage story truth in a runtime profile or runtime module.
- Do not allow AI output to speak, act, emote, decide, or physically move for the selected human actor.
- Do not accept legacy blob output as canonical final output.
- Do not accept mock-only Langfuse or hand-written trace JSON as final proof.
- Do not accept field presence as behavior.
- Do not close the MVP if `docker-up.py`, `tests/run_tests.py`, GitHub workflows, or TOML/tooling are broken.
- Do not collapse blocks into a single final blob.
- Do not make CSS-only typewriter animation the only behavior; it must be deterministic in tests.
- Do not regenerate runtime output when skipping/revealing animation.
- Do not implement later MVPs except for explicit scaffolds and handoff contracts named in this guide.

---

## Architecture: Modular Frontend

### Module Breakdown

```
frontend/static/
├── play_block_renderer.js          [NEW] — BlockRenderer class
├── play_typewriter_engine.js       [NEW] — TypewriterEngine + VirtualClock classes
├── play_controls.js                [NEW] — PlayControls class (Skip/Reveal/Accessibility)
├── play_blocks_orchestrator.js     [NEW] — BlocksOrchestrator class (State + Orchestration)
├── play_narrative_stream.js        [EXTEND] — Add block payloads to WebSocket messages
├── play_shell.js                   [REPLACE] — Initialize modules, wire events
├── style.css                       [EXTEND] — Block styles + accessibility
└── (remove old entry-based rendering)
```

### Module Responsibilities

#### BlockRenderer
**File**: `frontend/static/play_block_renderer.js`

**Responsibility**: Pure DOM rendering (no state, no orchestration)

**Key Methods**:
- `render(block)` — Create `<div data-block-id="..." data-block-type="...">` and append to DOM
- `getBlockElement(block_id)` — Retrieve DOM element for a block ID

**Tests**: Unit tests in `frontend/tests/test_block_renderer.js`

#### TypewriterEngine
**File**: `frontend/static/play_typewriter_engine.js`

**Responsibility**: Virtual clock + character-by-character delivery

**Key Classes**:
- `VirtualClock(test_mode)` — Advance virtual time in tests, use `performance.now()` in production
- `TypewriterEngine(test_mode)` — Queue blocks, advance visible characters, handle skip/reveal

**Key Methods**:
- `startDelivery(block)` — Queue block for typing
- `skipBlock(block_id)` — Complete current block, move to next
- `revealAll()` — Show all queued blocks immediately
- `_renderBlock()` — Update DOM element with visible characters

**Tests**: Unit tests in `frontend/tests/test_typewriter_engine.js`

#### BlocksOrchestrator
**File**: `frontend/static/play_blocks_orchestrator.js`

**Responsibility**: State management + event coordination

**Key Properties**:
- `blocks: []` — All blocks ever rendered
- `currentBlockIndex: number` — Which block is being typed
- `accessibility_mode: boolean` — Typewriter enabled/disabled

**Key Methods**:
- `loadTurn(http_response)` — Initial HTTP load (sets blocks, renders all, starts typewriter)
- `appendNarratorBlock(block)` — WebSocket streaming (appends block, renders, queues for typewriter)
- `skipCurrentBlock()` — Complete current, move to next
- `revealAll()` — Show all blocks immediately
- `setAccessibilityMode(enabled)` — Toggle typewriter

**Tests**: Unit tests in `frontend/tests/test_blocks_orchestrator.js`

#### PlayControls
**File**: `frontend/static/play_controls.js`

**Responsibility**: UI event handlers

**Key Methods**:
- `attachEventListeners()` — Wire Skip/Reveal/Accessibility buttons

**Tests**: Unit tests in `frontend/tests/test_play_controls.js`

---

## Data Integration

### HTTP: Initial Turn Load

```
Frontend POST /api/v1/sessions/{session_id}/turns
  ↓
Backend (proxy) POST → World-Engine
  ↓
Response:
{
  "visible_scene_output": {
    "contract": "visible_scene_output.blocks.v1",
    "blocks": [
      {
        "id": "turn-4-block-1",
        "block_type": "narrator",
        "text": "You notice the pause.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, ...}
      },
      {
        "id": "turn-4-block-2",
        "block_type": "actor_line",
        "actor_id": "veronique_houllie",
        "text": "This is not a legal question.",
        "delivery": {...}
      }
    ]
  },
  "diagnostics": {
    "frontend_render_contract": {
      "version": "dramatic_chat_blocks.v1",
      "scene_block_count": 2,
      "legacy_blob_used": false
    },
    ...
  }
}

BlocksOrchestrator.loadTurn(response):
  1. this.blocks = [block1, block2]
  2. BlockRenderer.render(block1)  → <div data-block-id="...">
  3. BlockRenderer.render(block2)  → <div data-block-id="...">
  4. TypewriterEngine.startDelivery(block1)  → Begin typing block1
```

### WebSocket: Narrator Streaming

```
Narrator starts speaking (while block1 still typing):

WebSocket message (via extended play_narrative_stream.js):
{
  "type": "narrator_block",
  "block": {
    "id": "turn-4-block-3",
    "block_type": "actor_action",
    "text": "Alain pauses.",
    "delivery": {...}
  }
}

BlocksOrchestrator.appendNarratorBlock(block3):
  1. this.blocks.push(block3)  → [block1, block2, block3]
  2. BlockRenderer.render(block3)  → <div> appended to DOM
  3. TypewriterEngine.startDelivery(block3)  → Queue for typewriter
```

### Controls: Skip/Reveal During Typing

```
Player clicks "Skip Current" (while block1 typing):

PlayControls event handler:
  → BlocksOrchestrator.skipCurrentBlock()
    1. Get current block: this.blocks[this.currentBlockIndex]
    2. TypewriterEngine.skipBlock(block_id)  → Complete block1
    3. this.currentBlockIndex++  → Move to block2
```

---

## Configuration: Typewriter Delivery

### Storage Layer
**Model**: `backend/app/models/backend/site_setting.py`

```python
class SiteSetting(db.Model):
    key = db.Column(db.String(128), primary_key=True)
    value = db.Column(db.Text())

# Example:
setting = SiteSetting.query.get('frontend_typewriter_config')
# setting.value = '{"characters_per_second": 44, "pause_before_ms": 150, ...}'
```

### API Layer
**Endpoint**: `backend/app/api/v1/admin_settings_routes.py` (create or extend)

```python
@admin_bp.route('/frontend-config/typewriter', methods=['GET', 'PATCH'])
def typewriter_config():
    """Get or update typewriter delivery configuration."""
    if request.method == 'GET':
        setting = SiteSetting.query.get('frontend_typewriter_config')
        if setting:
            return jsonify(json.loads(setting.value))
        # Return defaults
        return jsonify({
            "characters_per_second": 44,
            "pause_before_ms": 150,
            "pause_after_ms": 650,
            "skippable": True
        })

    if request.method == 'PATCH':
        data = request.get_json()
        setting = SiteSetting.query.get('frontend_typewriter_config')
        if not setting:
            setting = SiteSetting(key='frontend_typewriter_config')
            db.session.add(setting)
        setting.value = json.dumps(data)
        db.session.commit()
        return jsonify({"saved": True})
```

### Admin Tool UI
**File**: `administration-tool/static/manage_runtime_settings.js` (extend)

```javascript
async function loadTypewriterConfig() {
  const response = await fetch('/api/v1/admin/frontend-config/typewriter');
  const config = await response.json();

  document.getElementById('tw-chars-per-sec').value = config.characters_per_second;
  document.getElementById('tw-pause-before').value = config.pause_before_ms;
  document.getElementById('tw-pause-after').value = config.pause_after_ms;
  document.getElementById('tw-skippable').checked = config.skippable;
}

async function saveTypewriterConfig() {
  const payload = {
    characters_per_second: parseInt(document.getElementById('tw-chars-per-sec').value),
    pause_before_ms: parseInt(document.getElementById('tw-pause-before').value),
    pause_after_ms: parseInt(document.getElementById('tw-pause-after').value),
    skippable: document.getElementById('tw-skippable').checked
  };

  const response = await fetch('/api/v1/admin/frontend-config/typewriter', {
    method: 'PATCH',
    body: JSON.stringify(payload)
  });

  if (response.ok) {
    alert('Typewriter config saved');
    // Reload frontend to pick up new config
  }
}
```

---

## Final Target Dependency

MVP 5 proves the final target end-to-end. The final pass requires:

1. ✅ Structured scene blocks (no single blob renderer)
2. ✅ No legacy fallback in final output (mark degraded if used, fail E2E)
3. ✅ No `visitor` actor or references
4. ✅ Valid Annette and Alain runs with full transcripts
5. ✅ Real trace/export evidence (Langfuse or deterministic export)
6. ✅ Narrative Gov confirmation (health panels functional)
7. ✅ Operational gates all passing (docker-up, tests/run_tests, GitHub workflows, TOML)

---

## Inputs from Previous MVP

| Input | Source MVP | Required Fields | Evidence Path |
|---|---|---|---|
| DiagnosticsEnvelope | MVP 4 | frontend_render_contract, quality, trace_id, ldss_status, narrator_agent_status | `tests/reports/MVP4_HANDOFF_DIAGNOSTICS_AND_TRACE.md` |
| Narrative Runtime Agent streaming | MVP 3 via MVP 4 | narrator blocks (real-time), ruhepunkt signals, streaming metadata | WebSocket stream (play_narrative_stream.js) |
| Input-blocking signal | MVP 3 via MVP 4 | narrator.streaming (true/false), can_accept_input (true/false) | story runtime manager event stream |
| Trace/export evidence | MVP 4 | real generated trace/export paths and matching IDs, narrator agent spans | `tests/reports/langfuse/*.json` |
| NarrativeGovSummary | MVP 4 | operator surface statuses, narrator agent health | admin route test artifact |
| SceneTurnEnvelope.v2 | MVP 3 via MVP 4 | non-empty visible scene blocks | live turn artifact |
| TypewriterDeliveryConfig | Admin Tool (MVP5) | characters_per_second, pause_before_ms, pause_after_ms, skippable | SiteSetting table, GET endpoint |

---

## This MVP Produces

| Output | Consumed By | Required Fields | Evidence Path |
|---|---|---|---|
| FrontendRenderContract | final | block_contract, DOM_invariant, delivery_config, legacy_fallback_policy | frontend tests |
| FrontendBlockRenderState | final | block_id, reveal_state, timing_state, accessibility_state | JS unit tests |
| BlockRenderer Module | final | render(block), getBlockElement(block_id) | `frontend/static/play_block_renderer.js` |
| TypewriterEngine Module | final | startDelivery(), skipBlock(), revealAll(), VirtualClock | `frontend/static/play_typewriter_engine.js` |
| BlocksOrchestrator Module | final | loadTurn(), appendNarratorBlock(), skipCurrentBlock(), revealAll(), setAccessibilityMode() | `frontend/static/play_blocks_orchestrator.js` |
| E2EAcceptanceEvidence | final | Annette_run, Alain_run, transcript, screenshots, trace_links, operational_evidence | `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` |
| Final transcript artifact | final | NPC_response, NPC_to_NPC_dialogue, environment_interaction, narrator_validity, no_legacy_blob | `tests/reports/goc_final_e2e_transcript.json` |

---

## Consumed By Next MVP

MVP 5 is the final guide. Consumed by final acceptance only.

MVP 5 → final handoff:

```text
staged frontend (modular, no legacy)
final E2E evidence (Annette + Alain transcripts)
operational evidence (docker-up, tests, workflows all green)
Narrative Gov cross-check (health panels functional)
trace/export cross-check (real Langfuse or deterministic export)
```

---

## Services Touched

| Service | File/Location | Change |
|---------|---------------|--------|
| **frontend** | `frontend/static/play_block_renderer.js` | [NEW] BlockRenderer class |
| **frontend** | `frontend/static/play_typewriter_engine.js` | [NEW] TypewriterEngine + VirtualClock classes |
| **frontend** | `frontend/static/play_controls.js` | [NEW] PlayControls class |
| **frontend** | `frontend/static/play_blocks_orchestrator.js` | [NEW] BlocksOrchestrator class |
| **frontend** | `frontend/static/play_narrative_stream.js` | [EXTEND] Add block payloads to WebSocket |
| **frontend** | `frontend/static/play_shell.js` | [REPLACE] Wire modules, initialize orchestrator |
| **frontend** | `frontend/static/style.css` | [EXTEND] Block styles + accessibility |
| **frontend** | `frontend/templates/session_shell.html` | [VERIFY] Confirm `<div id="turn-transcript">`, form IDs |
| **backend** | `backend/app/api/v1/admin_settings_routes.py` | [CREATE/EXTEND] `GET/PATCH /api/v1/admin/frontend-config/typewriter` |
| **backend** | `backend/app/models/backend/site_setting.py` | [ALREADY EXISTS] Use for typewriter config storage |
| **administration-tool** | `administration-tool/static/manage_runtime_settings.js` | [EXTEND] Add typewriter config UI section |
| **administration-tool** | `administration-tool/templates/manage_runtime_settings.html` | [VERIFY/EXTEND] Add form fields for typewriter config |
| **world-engine** | `world-engine/app/api/http.py` | [VERIFY] Confirm blocks in response |
| **tests** | `frontend/tests/test_block_renderer.js` | [NEW] JS unit tests |
| **tests** | `frontend/tests/test_typewriter_engine.js` | [NEW] JS unit tests |
| **tests** | `frontend/tests/test_blocks_orchestrator.js` | [NEW] JS unit tests |
| **tests** | `frontend/tests/test_play_controls.js` | [NEW] JS unit tests |
| **tests** | `tests/e2e/test_final_goc_annette_alain_e2e.py` | [NEW] Browser E2E tests |
| **tests** | `tests/run_tests.py` | [EXTEND] Add `--mvp5` flag, include frontend/browser suites |
| **tests** | `.github/workflows/tests.yml` | [EXTEND] Add JS test job + browser E2E job |
| **tests** | `frontend/pyproject.toml` | [EXTEND] Add test config, browser test config |
| **reports** | `tests/reports/MVP_Live_Runtime_Completion/MVP5_SOURCE_LOCATOR.md` | [NEW] Source mapping artifact |
| **reports** | `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` | [NEW] Final acceptance evidence |

---

## Source Locator Matrix (COMPLETE)

| Area | Expected Path | Actual Path | Symbol / Anchor | Status |
|---|---|---|---|---|
| **Frontend Route** | Play shell route handler | `frontend/app/routes_play.py` | `session_view()`, `session_execute()` at line 986+ | ✅ FOUND |
| **Frontend Template** | Session shell HTML | `frontend/templates/session_shell.html` | `<div id="turn-transcript">`, `<form id="play-execute-form">` | ✅ FOUND |
| **Frontend Static - Renderer** | Block-to-DOM mapper | `frontend/static/play_block_renderer.js` | `BlockRenderer.render(block)` | 🆕 CREATE |
| **Frontend Static - Typewriter** | Virtual clock + delivery | `frontend/static/play_typewriter_engine.js` | `TypewriterEngine`, `VirtualClock` | 🆕 CREATE |
| **Frontend Static - Orchestrator** | State + orchestration | `frontend/static/play_blocks_orchestrator.js` | `BlocksOrchestrator` | 🆕 CREATE |
| **Frontend Static - Controls** | Skip/Reveal/Accessibility | `frontend/static/play_controls.js` | `PlayControls` | 🆕 CREATE |
| **Frontend Static - WebSocket** | Narrator stream (extend) | `frontend/static/play_narrative_stream.js` | Add block payloads | ⏳ EXTEND |
| **Frontend Static - Entrypoint** | Module initialization | `frontend/static/play_shell.js` | Initialize all modules | ⏳ REPLACE |
| **Frontend Static - CSS** | Block + accessibility styles | `frontend/static/style.css` | `.scene-block`, `.block-typewriter`, `.accessibility-mode` | ⏳ EXTEND |
| **Backend API** | Settings endpoint | `backend/app/api/v1/admin_settings_routes.py` | `GET/PATCH /api/v1/admin/frontend-config/typewriter` | ⏳ CREATE/EXTEND |
| **Backend Model** | Settings storage | `backend/app/models/backend/site_setting.py` | `SiteSetting(key, value)` | ✅ FOUND |
| **Backend Service** | Game service | `backend/app/services/game/game_service.py` | `GameServiceError`, `_parse_create_run_v1()` | ✅ FOUND |
| **World-Engine API** | HTTP handler | `world-engine/app/api/http.py` | `CreateRunRequest`, `TicketRequest`, `router` | ✅ FOUND |
| **Admin Tool UI** | Runtime settings | `administration-tool/static/manage_runtime_settings.js` | Extend with typewriter config section | ⏳ EXTEND |
| **Admin Tool Template** | Settings form | `administration-tool/templates/manage_runtime_settings.html` | Form fields for typewriter config | ⏳ EXTEND/VERIFY |
| **JS Unit Tests** | Block renderer tests | `frontend/tests/test_block_renderer.js` | Unit tests | 🆕 CREATE |
| **JS Unit Tests** | Typewriter tests | `frontend/tests/test_typewriter_engine.js` | Unit tests | 🆕 CREATE |
| **JS Unit Tests** | Orchestrator tests | `frontend/tests/test_blocks_orchestrator.js` | Unit tests | 🆕 CREATE |
| **Browser E2E Tests** | Final Annette/Alain | `tests/e2e/test_final_goc_annette_alain_e2e.py` | `test_final_annette_e2e_evidence`, `test_final_alain_e2e_evidence` | 🆕 CREATE |
| **Test Runner** | MVP5 registration | `tests/run_tests.py` | `--mvp5` flag, frontend/browser suites | ⏳ EXTEND |
| **GitHub Workflows** | CI/CD | `.github/workflows/tests.yml` | JS + browser E2E jobs | ⏳ EXTEND |
| **TOML/Tooling** | Frontend test config | `frontend/pyproject.toml` | testpaths, pytest.ini, markers | ⏳ EXTEND |
| **Reports** | Source locator | `tests/reports/MVP_Live_Runtime_Completion/MVP5_SOURCE_LOCATOR.md` | This matrix | ✅ CREATED |
| **Reports** | Operational evidence | `tests/reports/MVP_Live_Runtime_Completion/MVP5_OPERATIONAL_EVIDENCE.md` | docker-up, tests, workflows results | ⏳ CREATE |
| **Reports** | Final E2E evidence | `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` | Annette/Alain transcripts, trace links | ⏳ CREATE |

---

## Patch Map

| Patch ID | Area | Files / Symbols | Required Change | Tests |
|---|---|---|---|---|
| MVP5-P01 | Frontend block renderer | `frontend/static/play_block_renderer.js` [NEW] | Create BlockRenderer class, render(block) method | `test_block_renderer_creates_div_with_data_attributes`, `test_block_renderer_appends_to_dom` |
| MVP5-P02 | Typewriter engine | `frontend/static/play_typewriter_engine.js` [NEW] | Create TypewriterEngine + VirtualClock, startDelivery/skipBlock/revealAll methods | `test_typewriter_virtual_clock_advances_in_test_mode`, `test_typewriter_renders_chars_progressively`, `test_skip_current_completes_block` |
| MVP5-P03 | Orchestrator | `frontend/static/play_blocks_orchestrator.js` [NEW] | Create BlocksOrchestrator, loadTurn/appendNarratorBlock/skipCurrentBlock/revealAll/setAccessibilityMode methods | `test_orchestrator_loads_initial_blocks`, `test_orchestrator_appends_narrator_block`, `test_orchestrator_skip_increments_index`, `test_orchestrator_accessibility_disables_typewriter` |
| MVP5-P04 | Controls | `frontend/static/play_controls.js` [NEW] | Create PlayControls, attachEventListeners method | `test_controls_skip_button_calls_orchestrator`, `test_controls_reveal_button_calls_orchestrator`, `test_controls_accessibility_checkbox_toggles_mode` |
| MVP5-P05 | WebSocket streaming | `frontend/static/play_narrative_stream.js` [EXTEND] | Add block payload support to narrator stream, emit narrator-block-received events | `test_narrative_stream_emits_narrator_block_event_with_block_payload` |
| MVP5-P06 | Entry point | `frontend/static/play_shell.js` [REPLACE] | Initialize BlockRenderer, TypewriterEngine, BlocksOrchestrator, PlayControls; wire HTTP/WebSocket events | `test_play_shell_initializes_modules`, `test_play_shell_wires_http_load_event`, `test_play_shell_wires_websocket_narrator_event` |
| MVP5-P07 | Styling | `frontend/static/style.css` [EXTEND] | Add `.scene-block`, `.block-typewriter`, `.accessibility-mode` CSS; preserve content order in a11y mode | `test_css_scene_blocks_visible`, `test_css_accessibility_mode_preserves_order` |
| MVP5-P08 | Typewriter config API | `backend/app/api/v1/admin_settings_routes.py` [CREATE] | Create endpoint `GET/PATCH /api/v1/admin/frontend-config/typewriter` | `test_get_typewriter_config_returns_defaults`, `test_patch_typewriter_config_persists_to_db` |
| MVP5-P09 | Admin Tool UI | `administration-tool/static/manage_runtime_settings.js` [EXTEND] | Add typewriter config section (input fields, save button) | `test_admin_loads_typewriter_config`, `test_admin_saves_typewriter_config` |
| MVP5-P10 | Test runner | `tests/run_tests.py` [EXTEND] | Add `--mvp5` flag, include `frontend/tests/*.js` and `tests/e2e/test_final_*.py` | `test_run_tests_mvp5_runs_all_frontend_tests` |
| MVP5-P11 | GitHub workflows | `.github/workflows/tests.yml` [EXTEND] | Add JS test job + browser E2E job | Workflow file validates on commit |
| MVP5-P12 | TOML tooling | `frontend/pyproject.toml` [EXTEND] | Add testpaths, markers, pytest.ini for frontend tests | `test_toml_includes_frontend_testpaths` |
| MVP5-P13 | Final E2E | `tests/e2e/test_final_goc_annette_alain_e2e.py` [NEW] | Create Annette + Alain browser tests with transcript capture, trace link verification, Narrative Gov check | `test_final_annette_e2e_evidence`, `test_final_alain_e2e_evidence` |

---

## Data Contracts

### FrontendRenderContract

```json
{
  "contract": "frontend_render_contract.v1",
  "input_contract": "visible_scene_output.blocks.v1",
  "dom_contract": "dramatic_chat_blocks.v1",
  "one_dom_element_per_block": true,
  "legacy_blob_final_allowed": false,
  "required_controls": ["skip_current", "reveal_all", "accessibility_mode"],
  "diagnostics_required": true,
  "delivery_config_source": "admin_tool_site_setting"
}
```

### FrontendBlockRenderState

```json
{
  "contract": "frontend_block_render_state.v1",
  "block_id": "turn-4-block-2",
  "block_type": "actor_line",
  "actor_id": "veronique_houllie",
  "target_actor_id": "alain_reille",
  "total_characters": 52,
  "visible_characters": 17,
  "status": "rendering",
  "delivery_mode": "typewriter",
  "skippable": true,
  "accessibility_mode": false
}
```

### TypewriterDeliveryConfig

```json
{
  "contract": "typewriter_delivery_config.v1",
  "mode": "typewriter",
  "characters_per_second": 44,
  "pause_before_ms": 150,
  "pause_after_ms": 650,
  "skippable": true,
  "render_test_mode": true,
  "clock": "virtual",
  "advance_time_api": "renderer.clock.advanceBy(ms)"
}
```

### LegacyFallbackPolicy

```json
{
  "contract": "legacy_fallback_policy.v1",
  "legacy_blob_may_be_adapted_for_debug": false,
  "legacy_blob_marks_degraded": true,
  "legacy_blob_final_e2e_allowed": false,
  "degradation_signal": "legacy_visible_output_adapter_used"
}
```

### E2EAcceptanceEvidence

```json
{
  "contract": "e2e_acceptance_evidence.v1",
  "annette_run_required": true,
  "alain_run_required": true,
  "npc_to_npc_dialogue_required": true,
  "environment_interaction_required": true,
  "narrator_inner_voice_required": true,
  "trace_or_export_required": true,
  "narrative_gov_cross_check_required": true,
  "operational_gate_required": true,
  "no_legacy_blob_required": true,
  "no_visitor_required": true
}
```

---

## Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| render input must match schema | frontend schema/renderer guard | `invalid_delivery_schema` | `test_invalid_delivery_schema_rejected` | `frontend_render_contract.version` |
| final output cannot be one blob | DOM tests and final E2E | `frontend_single_blob_final_output` | `test_frontend_does_not_collapse_to_single_blob` | `dom.one_element_per_block` |
| legacy fallback is degraded | renderer diagnostics consumer | `frontend_legacy_blob_fallback_not_final` | `test_frontend_legacy_blob_fallback_is_marked_degraded` | `quality.degradation_signals` |
| legacy fallback cannot pass final E2E | final E2E gate | `frontend_legacy_fallback_not_final` | `test_frontend_legacy_fallback_not_final` | `frontend_render_contract.legacy_blob_used` |
| typewriter must be testable | renderer virtual clock | `typewriter_not_deterministic` | `test_typewriter_uses_virtual_clock_in_test_mode` | `render_test_mode` |
| skip current animation does not call runtime | renderer controls | `skip_caused_runtime_regeneration` | `test_skip_current_animation` | `runtime_call_count` |
| reveal all does not call runtime | renderer controls | `reveal_all_caused_runtime_regeneration` | `test_reveal_all_without_regeneration` | `runtime_call_count` |
| accessibility disables animation | renderer config/reduced motion | `accessibility_typewriter_not_disabled` | `test_accessibility_mode_disables_typewriter` | `accessibility_mode` |
| final Annette E2E evidence required | browser E2E final report | `final_annette_e2e_missing` | `test_final_annette_e2e_evidence` | `e2e.annette_run` |
| final Alain E2E evidence required | browser E2E final report | `final_alain_e2e_missing` | `test_final_alain_e2e_evidence` | `e2e.alain_run` |
| no legacy blob in final output | final E2E assertion | `final_output_has_legacy_blob` | `test_final_output_no_legacy_blob` | `visible_scene_output.legacy_blob_used` |
| no visitor in final output | final E2E assertion | `final_output_has_visitor` | `test_final_output_no_visitor` | `npc_actor_ids` (should not contain "visitor") |

### Wave-Hardening Validation Rules

| Rule | Where Enforced | Error Code | Test Name | Diagnostic Field |
|---|---|---|---|---|
| Source Locator Matrix contains no unresolved placeholders | implementation report preflight | `source_locator_unresolved` | `test_source_locator_matrix_has_no_placeholders_before_patch` | `source_locator.status` |
| operational evidence lists exact MVP-specific suites/files/markers | operational report validator | `operational_suite_evidence_missing` | `test_operational_report_lists_mvp_specific_suites` | `operational_gate.mvp_specific_suites` |
| fixed MVP operational evidence artifact exists | operational report validator | `operational_evidence_artifact_missing` | `test_operational_evidence_artifact_exists_for_mvp` | `operational_gate.artifact_path` |
| browser runner and artifact locator table is complete | implementation report preflight | `browser_artifact_locator_missing` | `test_browser_artifact_locator_complete` | `browser_artifact_locator.status` |

---

## Examples

### Frontend render input (HTTP response)

```json
{
  "visible_scene_output": {
    "contract": "visible_scene_output.blocks.v1",
    "blocks": [
      {
        "id": "turn-4-block-1",
        "block_type": "narrator",
        "speaker_label": "You notice",
        "text": "You notice the pause before Alain answers.",
        "delivery": {"mode": "typewriter", "characters_per_second": 44, "pause_before_ms": 150, "pause_after_ms": 650, "skippable": true}
      },
      {
        "id": "turn-4-block-2",
        "block_type": "actor_line",
        "speaker_label": "Véronique",
        "actor_id": "veronique_houllie",
        "target_actor_id": "alain_reille",
        "text": "You keep turning this into a legal question.",
        "delivery": {...}
      }
    ]
  },
  "diagnostics": {
    "frontend_render_contract": {"version": "dramatic_chat_blocks.v1", "scene_block_count": 2, "render_mode": "typewriter", "typewriter_enabled": true, "legacy_blob_used": false}
  }
}
```

### Rendered transcript DOM

```html
<div id="turn-transcript">
  <div data-block-id="turn-4-block-1" data-block-type="narrator">You notice the pause before Alain answers.</div>
  <div data-block-id="turn-4-block-2" data-block-type="actor_line" data-actor-id="veronique_houllie" data-target-actor-id="alain_reille">You keep turning this into a legal question.</div>
</div>
```

Forbidden final DOM (collapsed blob):
```html
<div id="visible-output">You notice the pause... You keep turning...</div>
```

### Typewriter delivery config (in Admin Tool UI)

```json
{
  "characters_per_second": 44,
  "pause_before_ms": 150,
  "pause_after_ms": 650,
  "skippable": true
}
```

Admin Form:
```html
<div class="admin-section">
  <h3>Typewriter Delivery</h3>
  <label>Characters per second: <input id="tw-chars-per-sec" type="number" value="44" /></label>
  <label>Pause before (ms): <input id="tw-pause-before" type="number" value="150" /></label>
  <label>Pause after (ms): <input id="tw-pause-after" type="number" value="650" /></label>
  <label><input id="tw-skippable" type="checkbox" checked /> Skippable</label>
  <button onclick="saveTypewriterConfig()">Save Typewriter Config</button>
</div>
```

### Skip current animation

```javascript
// Player clicks "Skip Current" button
orchestrator.skipCurrentBlock();
// Expected: Block 1 completes typing, Block 2 begins
```

### Reveal all

```javascript
// Player clicks "Reveal All" button
orchestrator.revealAll();
// Expected: All queued blocks show full text immediately
```

### Accessibility mode

```javascript
// User enables accessibility mode
orchestrator.setAccessibilityMode(true);
// Expected: Typewriter disabled, all text visible immediately, no animation
```

---

## Required Tests

- `test_block_renderer_creates_div_with_data_attributes`
- `test_block_renderer_appends_to_dom`
- `test_typewriter_virtual_clock_advances_in_test_mode`
- `test_typewriter_renders_chars_progressively`
- `test_skip_current_completes_block`
- `test_reveal_all_shows_all_blocks`
- `test_orchestrator_loads_initial_blocks`
- `test_orchestrator_appends_narrator_block`
- `test_orchestrator_skip_increments_index`
- `test_orchestrator_accessibility_disables_typewriter`
- `test_controls_skip_button_calls_orchestrator`
- `test_controls_reveal_button_calls_orchestrator`
- `test_controls_accessibility_checkbox_toggles_mode`
- `test_narrative_stream_emits_narrator_block_event_with_block_payload`
- `test_play_shell_initializes_modules`
- `test_play_shell_wires_http_load_event`
- `test_play_shell_wires_websocket_narrator_event`
- `test_final_annette_e2e_evidence`
- `test_final_alain_e2e_evidence`
- `test_final_e2e_transcript_contains_trace_and_narrative_gov_links`
- `test_final_output_no_legacy_blob`
- `test_final_output_no_visitor`
- All mandatory operational checks from this guide

---

## Required ADRs

Required for this MVP:

- ADR-014 Interactive Text-Adventure Frontend
- ADR-016 Operational Test and Startup Gates

---

## Mandatory Operational Gate

**Required commands**:

```bash
python docker-up.py              # Start all services
python tests/run_tests.py --mvp5 # Run all MVP5 tests (JS + E2E)
python tests/run_tests.py --all  # Full test suite
```

**Required checks**:

- `test_docker_up_script_exists_or_equivalent_documented`
- `test_docker_up_reports_failed_service`
- `test_run_test_lists_required_suites`
- `test_run_test_includes_current_mvp_tests`
- `test_run_test_fails_on_failed_suite`
- `test_github_workflows_include_current_mvp_tests`
- `test_github_workflows_do_not_silently_skip_e2e`
- `test_toml_testpaths_include_current_mvp_tests`
- `test_toml_pythonpath_supports_services`

---

## MVP-Specific Suite Evidence

The operational report must list the exact test files, markers, or suites added for this MVP:

```text
MVP-specific test coverage:
- unit test files: frontend/tests/test_block_renderer.js, test_typewriter_engine.js, test_blocks_orchestrator.js, test_play_controls.js
- integration test files: frontend/tests/test_play_shell_integration.js
- e2e/browser test files: tests/e2e/test_final_goc_annette_alain_e2e.py
- pytest markers: @pytest.mark.mvp5, @pytest.mark.frontend, @pytest.mark.e2e
- tests/run_tests.py suite entries: --mvp5, --frontend, --browser-e2e
- GitHub workflow jobs: js-unit-tests, browser-e2e-tests
- TOML testpaths/markers: frontend/pyproject.toml includes frontend/tests/*, tests/e2e/test_final_*.py
```

---

## Required Operational Evidence Artifact

Write the final operational evidence for this MVP to:

```text
tests/reports/MVP_Live_Runtime_Completion/MVP5_OPERATIONAL_EVIDENCE.md
```

Include:

- exact `docker-up.py` command and result
- exact `tests/run_tests.py --mvp5` command and result
- unit/integration/e2e/browser suite names
- concrete test files added or modified
- pytest markers or runner suite names
- GitHub workflow files and job names
- TOML/tooling files checked
- skipped suites, if any, and why
- failure output for any failed command
- final PASS/FAIL verdict

---

## Stop Condition

Stop only when **all** conditions are met:

1. ✅ BlockRenderer renders one DOM element per scene block (no collapsed blob)
2. ✅ TypewriterEngine uses virtual clock (deterministic in tests, `advanceBy()` works)
3. ✅ BlocksOrchestrator merges HTTP initial blocks + WebSocket narrator blocks
4. ✅ Skip/Reveal controls work without runtime regeneration calls
5. ✅ Accessibility mode disables typewriter, shows all text immediately
6. ✅ Typewriter config editable in Admin Tool (global, persisted in SiteSetting, API endpoint works)
7. ✅ All JS unit tests pass (`test_block_renderer.js`, `test_typewriter_engine.js`, `test_blocks_orchestrator.js`, `test_play_controls.js`)
8. ✅ Final Annette E2E run completes with:
   - NPC to NPC dialogue present
   - Environment interaction present
   - Narrator inner voice valid
   - No legacy blob
   - No `visitor` actor
   - Trace/export evidence collected
   - Narrative Gov cross-check functional
9. ✅ Final Alain E2E run completes (same as Annette)
10. ✅ Operational gate: docker-up.py works, tests/run_tests.py passes, GitHub workflows pass, TOML valid
11. ✅ Source Locator Matrix has zero unresolved placeholders
12. ✅ Operational Evidence artifact complete

---

## Implementation Entry Point

**Start with Source Locator Matrix** (already completed: `tests/reports/MVP_Live_Runtime_Completion/MVP5_SOURCE_LOCATOR.md`)

**Then implement Patch Map in order (MVP5-P01 through MVP5-P13)**:

1. BlockRenderer (P01) — Pure DOM, no state
2. TypewriterEngine (P02) — Virtual clock + typing
3. BlocksOrchestrator (P03) — State + orchestration
4. PlayControls (P04) — UI event handlers
5. NarratorStream extend (P05) — Block payloads
6. play_shell.js rewrite (P06) — Module initialization
7. CSS (P07) — Block styles
8. Admin API (P08) — Typewriter config endpoint
9. Admin UI (P09) — Typewriter config form
10. Test runner (P10) — --mvp5 flag
11. GitHub workflows (P11) — CI/CD jobs
12. TOML (P12) — Test config
13. Final E2E (P13) — Annette/Alain browser tests

**Verification sequence**:
- Unit tests pass → Integration tests pass → E2E tests pass → Operational gates pass

---

## Reference Documents

- `tests/reports/MVP_Live_Runtime_Completion/MVP5_SOURCE_LOCATOR.md` — Source mapping (COMPLETE)
- `tests/reports/MVP_Live_Runtime_Completion/MVP5_IMPLEMENTATION_PLAN.md` — Detailed module specs
- `tests/reports/MVP_Live_Runtime_Completion/MVP5_OPERATIONAL_EVIDENCE.md` — Final evidence (to be filled)
- `tests/reports/GOC_FINAL_E2E_ACCEPTANCE.md` — Final E2E evidence (to be filled)
- `tests/reports/goc_final_e2e_transcript.json` — Final transcript artifact (to be filled)

---

## Global Prohibitions (Enforced)

- ❌ Do not collapse blocks into a single blob
- ❌ Do not use CSS-only typewriter (must be deterministic, testable)
- ❌ Do not regenerate runtime output when skipping/revealing
- ❌ Do not accept legacy fallback as final E2E
- ❌ Do not reintroduce `visitor` anywhere (actor, tests, UI, fallback)
- ❌ Do not break docker-up.py, tests/run_tests.py, GitHub workflows, TOML
- ❌ Do not implement later MVPs (only explicit scaffolds)

---

**MVP 5 is FINAL. After this, only operational acceptance remains.**
