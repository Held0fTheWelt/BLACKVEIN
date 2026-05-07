# ADR-0036: Player Session Output Language (Launch-Time Selection)

Normative contract for **which natural language the runtime must use for player-visible generation** in a session, independent of template, role, or incidental French proper nouns in canonical content.

## Status

Accepted

## Implementation Status

**Core runtime implemented; frontend UI and AI stack turn-prompt injection still pending.**

**Implemented (as of 2026-05-07):**
- `world-engine/app/story_runtime/manager.py`: `create_session()` accepts `session_output_language: str = "de"` parameter; stored on `StorySession.session_output_language`.
- `world-engine/app/api/http.py`: `CreateStorySessionRequest` accepts `session_output_language` parameter.
- `world-engine/app/story_runtime/manager.py` (`_build_opening_prompt`): language directive prepended to opening prompt for `de` and `en`.
- Tests: `world-engine/tests/test_mvp1_experience_identity.py` asserts `session_output_language` round-trips and opening prompt contains "German" directive.
- Backend: `game_routes.py` validates `session_output_language` with `invalid_output_language` / `unsupported_language` error codes; persists in `GameSaveSlot.metadata["session_output_language"]`; passes to `create_story_session()`.

**Also implemented (as of 2026-05-07):**
- `frontend/templates/session_start.html`: select box (`session_output_language`, Deutsch / English, default de) added after Play-as selector.
- `frontend/app/routes_play.py`: `play_create()` reads and forwards `session_output_language` for both runtime_profile and template paths.
- `frontend/tests/test_mvp1_play_launcher.py`: 3 tests assert de/en forwarding and default=de.
- Langfuse `user_id` propagation: `backend/app/observability/langfuse_adapter.py` `start_trace()` accepts `user_id` and uses `propagate_attributes(user_id=...)` (SDK v4.x). `game_routes.py` passes `str(user.id)` on turn traces. `world-engine/app/observability/langfuse_adapter.py` `session_scope()` accepts and propagates `user_id`. `world-engine/app/api/http.py` `CreateStorySessionRequest` accepts `user_id`, forwarded to `session_scope()`. Wrong `adapter.client.update_user()` call removed.

**Not yet implemented:**
- `ai_stack/langgraph_runtime_executor.py`: language directive injection into turn prompts (only opening prompt currently).
- See ADR-0036 Follow-ups section for full list.

## Date

2026-05-07

## Acceptance Date

2026-05-07

## Acceptance Evidence

- Grill-me session completed (2026-05-07) — full design tree walked, all branches resolved
- Integration approach confirmed: per-session language selection, User-attribute in Langfuse, parameter to `create_story_session()`
- Backend persistence via `GameSaveSlot.metadata["session_output_language"]` confirmed
- Default language (`de`) established
- Error codes defined: `invalid_output_language`, `unsupported_language`

## Intellectual property rights

Repository authorship and licensing: see project **LICENSE**; contact maintainers for clarification.

## Privacy and confidentiality

This ADR contains no personal data. Implementers must follow repository privacy policies; do not log raw prompts containing secrets.

## Related ADRs

- [ADR-0033](adr-0033-live-runtime-commit-semantics.md) — commit truth and observability surfaces (language must be attributable on spans and session state).
- [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) — player shell renders committed blocks; language choice affects **text generation**, not block typing mechanics.
- [ADR-0035](adr-0035-story-opening-economy-and-warmup.md) — opening composition; opening beats must respect the selected output language once implemented.

## Context

1. **Observed failure mode:** Generated narrative sometimes **drifts into French** (e.g. when prompts, module metadata, character names, or Paris-setting cues stack with model defaults), even when the player expects **German or English**. That is a product defect: language is part of the **experience contract**, not an emergent side effect of setting.

2. **Missing control surface:** Today the play launcher exposes **template** and **Play As** (role). There is no first-class **output language** choice, so the stack cannot consistently steer the model or validate “wrong language” drift.

3. **Scope for v1:** The product needs **German** and **English** as the first supported **player-visible output languages** for generation. Additional locales are out of scope for this ADR but must remain **extensible** (registry or enum, not hard-coded `if` trees scattered across services).

## Decision

### D1 — Canonical notion: `session_output_language`

- Introduce a session-scoped, normative field **`session_output_language`** (working name; implementation may use `output_language` in API JSON if aliased in OpenAPI).
- **Allowed values (v1):** `de` and `en` (BCP 47 primary language tags; region subtags optional later).
- **Semantics:** All **player-visible** model-generated prose for that session (narrator, NPC lines, stage directions where generated) SHALL be produced in this language unless a future **module-declared exception** is accepted in a separate ADR (not in v1).

### D2 — Launch-time selection (UX)

- At **game start** (same step as template selection and **Play As**), the player SHALL choose **`session_output_language`** explicitly.
- **Default value (v1):** `de` (German-first product). If player does not choose, backend defaults to `de`.
- Browser locale MAY inform the UI default (suggested pre-selection), but does not override explicit backend default of `de`.
- The launcher MUST persist the chosen/resolved language tag on the session so it is not lost on resume.

#### D2a — Frontend implementation contract

The language selector is part of the existing play launcher form (`frontend/templates/session_start.html`) and its server-side handler (`frontend/app/routes_play.py`).

**UI widget:** One select box with two options (`de`, `en`) — closed choice, no free-text entry:

```html
<label for="session_output_language">Sprache / Language</label>
<select id="session_output_language" name="session_output_language">
  <option value="de" selected>Deutsch</option>
  <option value="en">English</option>
</select>
```

- The select box enforces a closed choice; the user cannot submit an arbitrary string.
- `de` is pre-selected (German-first product default).
- Shown for **all** templates that reach the `POST /api/v1/game/player-sessions` endpoint (not only `god_of_carnage_solo`); it is a session-level, not template-level, choice.
- Widget position: immediately after the **Play as** role selector and before the submit button.

**Server-side handler** (`routes_play.py`, function `play_create`):

- Read `session_output_language` from `request.form` (or query param if the launcher uses AJAX).
- Fall back to `"de"` if absent or empty.
- Include in the `json_data` dict for **both** the `runtime_profile_id` path and the `template_id` path:
  ```python
  session_output_language = (request.form.get("session_output_language") or "de").strip()
  json_data["session_output_language"] = session_output_language
  ```
- Do **not** duplicate backend validation in the frontend — the backend is the authority. If the backend returns `unsupported_language` or `invalid_output_language`, surface the backend error message via `flash()` and redirect, same as other validation errors.

**Idempotent resume:** Language is fixed at session creation and stored server-side; the resume path (`GET /api/v1/game/player-sessions/<id>`) does not re-submit `session_output_language`. Frontend tests need not assert language on resume.

### D3 — Propagation (runtime contract)

The chosen language MUST flow through the canonical play path so all generation seams see it:

1. **Frontend** — submit `session_output_language` with `POST /api/v1/game/player-sessions` payload (same request as `runtime_profile_id`, `selected_player_role`).

2. **Backend** — validate allowed values (`de` or `en`; reject with `invalid_output_language` or `unsupported_language` error code); store on **`GameSaveSlot.metadata[“session_output_language”]`**; forward to World-Engine `create_story_session()` call as parameter.

3. **World-Engine** — receive `session_output_language` parameter; store on **`StorySession.session_output_language`** (session-level attribute, not runtime_projection). World-Engine passes language to all downstream consumers (`_build_opening_prompt`, turn prompts, LDSS, graph packaging) from this single source.

4. **Observability (Langfuse)** — attach `user_id` (backend user ID as string) to all Langfuse traces via `propagate_attributes(user_id=...)` (Langfuse SDK v4.x API). Langfuse automatically groups traces in the Users view. `session_output_language` appears in trace metadata; the language is visible per-trace without a separate “User object” API call.

5. **AI stack / LangGraph** — inject a **hard instruction block** (system or structured context) of the form: “Write all player-visible narrative in **{language}**,” plus negative guidance (“Do not switch to French unless quoting in-world French text marked as such”).

### D4 — Relationship to canonical module content

- **Character names, place names, and in-world documents** may remain French or mixed where the module is faithful to source material; the ADR governs **narrative language**, not renaming **Véronique** to **Veronika**.
- If a beat requires **quoted** French (e.g. a letter read aloud), the module or director policy may emit it as **quoted** content; the surrounding frame stays in `session_output_language`.

### D5 — Observability and QA

- **Langfuse / trace attributes:** `user_id` is set on all Langfuse traces via `propagate_attributes(user_id=str(user.id))` (Langfuse SDK v4.x; **not** `update_user()`). This causes Langfuse to show the user in the Users view and enables filtering by player. `session_output_language` is attached as trace metadata in addition.
- **Tests:** Contract tests SHALL assert that both `de` and `en` values reach World-Engine `StorySession` and appear in prompt assembly (golden or snapshot tests acceptable); optional LLM-as-judge **not** required for CI.

### D5a — Error Codes

Backend validation of `session_output_language` uses two structured error codes:

- **`invalid_output_language`** — Request contains malformed value (null, empty string, non-string type). HTTP 400.
- **`unsupported_language`** — Request contains valid string but not in allowed set (`de`, `en`). HTTP 400. Response body includes allowed values.

Both errors are returned in the standard game API error response format (see `backend/app/api/errors.py`).

### D6 — Non-goals (this ADR)

- Full **UI i18n** (menus, errors) — orthogonal; only **generated story text**.
- Automatic **translation** of existing committed transcript when the user changes language mid-session — not in v1; language is fixed at session create unless a future ADR defines migration.
- **Per-block** language tags — v1 is session-wide unless superseded.

## Consequences

### Positive

- Reproducible language behavior; easier QA and player trust.
- Clear seam for prompts and validation; reduces “model picked French” incidents.

### Negative / risks

- Models may still code-mix; mitigated by prompt discipline and optional lightweight post-checks later.
- German-first copy in YAML prompts may need alignment so English sessions do not receive contradictory static German instructions.

### Follow-ups

- OpenAPI schema: add `session_output_language` field to `game_player_session` request/response.
- Launcher UI + routes_play.py: implement per D2a with select widget semantics (frontend not yet implemented as of 2026-05-07).
- ADR-0035 opening prompt alignment: opening beats must respect `session_output_language`; static German copy in YAML prompts must not contradict an English session.
- Graph prompt injection: `ai_stack/langgraph_runtime_executor.py` — mirror language directive into all turn prompts, not only the opening prompt (currently only `_build_opening_prompt()` injects it).
- Langfuse `update_user` verification: confirm `session_output_language` appears on User objects in Langfuse dashboard after live session create.

## Diagrams

### Session create flow (end-to-end)

```mermaid
flowchart LR
  subgraph fe [Frontend — session_start.html]
    TS["Template\n(select)"]
    RS["Play as\n(select)"]
    LS["Sprache / Language\n(select: Deutsch | English,\ndefault: de)"]
    FORM["POST /api/v1/game/player-sessions\nsession_output_language = de | en"]
  end
  subgraph backend [Backend]
    VAL["Validate\n(invalid_output_language\nunsupported_language)"]
    SLOT["GameSaveSlot.metadata\n[session_output_language]"]
    LF["Langfuse User\nattribute"]
    CSS["create_story_session()"]
  end
  subgraph we [World-Engine]
    REQ["CreateStorySessionRequest\n.session_output_language"]
    SS["StorySession\n.session_output_language"]
    OP["_build_opening_prompt()\nlang directive prepended"]
  end
  subgraph ai [AI stack — pending]
    TURN["Turn prompts\n(not yet injected)"]
  end

  TS --> FORM
  RS --> FORM
  LS --> FORM
  FORM --> VAL
  VAL --> SLOT
  VAL --> CSS
  VAL --> LF
  CSS --> REQ --> SS --> OP --> TURN
```

### Backend validation (API contract)

The select box in the UI enforces a closed choice — only `de` or `en` can be submitted by the play launcher. Validation guards exist for direct API callers (Postman, integrations, future mobile clients).

```mermaid
flowchart TD
  SRC{caller} -->|Play launcher\nselect box| OK2["always valid\nde or en"]
  SRC -->|direct API call| IN["session_output_language\nin request body"]
  IN --> CHK{type check}
  CHK -->|non-string / null| E1["400 invalid_output_language"]
  CHK -->|string| CHK2{value in\nallowed set?}
  CHK2 -->|no e.g. fr| E2["400 unsupported_language\n+ allowed: [de, en]"]
  CHK2 -->|yes / omitted| OK["proceed\ndefault = de"]
  OK2 --> OK
```

## Testing

- **Contract:** Assert `session_output_language` round-trips Frontend → Backend → World-Engine projection for `de` and `en`.
- **Prompt assembly:** Unit or golden tests that prompt text contains the selected language directive.
- **Manual:** Start two sessions (`de` vs `en`) with the same template; compare opening narration language (subjective checklist until automated judge exists).
- **Failure mode triggering ADR review:** Sustained player-visible text predominantly not in `session_output_language` across golden runs.

## References and Affected Services

### Frontend
- `frontend/templates/session_start.html` — add `<select name="session_output_language">` widget (de/en, default de) after the Play-as role selector, before the submit button; visible for all templates
- `frontend/app/routes_play.py` — in `play_create()`: read `session_output_language` from `request.form`, fall back to `"de"`, inject into `json_data` for both the `runtime_profile_id` path and the `template_id` path; surface backend `unsupported_language` / `invalid_output_language` errors via `flash()` same as other form errors
- `frontend/tests/test_mvp1_play_launcher.py` — assert `session_output_language` is forwarded to backend in POST payload; assert default `"de"` when field omitted

### Backend
- `backend/app/api/v1/game_routes.py` — extend `POST /api/v1/game/player-sessions` to accept `session_output_language` parameter
- `backend/app/services/game_service.py` — pass language to `create_story_session()` call
- `backend/app/models/game_save_slot.py` — persist in `GameSaveSlot.metadata["session_output_language"]`
- `backend/app/api/errors.py` — add error codes `invalid_output_language`, `unsupported_language`

### World-Engine
- `world-engine/app/runtime/session_manager.py` — add `session_output_language` field to `StorySession`
- `world-engine/app/api/http.py` — accept `session_output_language` parameter in `CreateStorySessionRequest`
- `world-engine/app/story_runtime/manager.py` — pass language to `_build_opening_prompt()` and downstream consumers

### AI Stack
- `ai_stack/langgraph_runtime_executor.py` — inject language directive into prompt context
- `ai_stack/diagnostics_envelope.py` — mirror `session_output_language` in diagnostics for observability

### Observability
- Langfuse trace integration — set User-level attribute `session_output_language` on all traces
