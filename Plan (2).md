## 1. Executive Summary

This feature needs to be split into three layers, because they are not the same problem.

**Adjustable delivery form** is about how the runtime packages and presents a turn: how much narration appears, how much is shown as dialogue, how much explanation is included, how repetitive the prose is allowed to be, and how visible actions are. This is mostly a **rendering and output-packaging concern**, plus some generation steering.

**Adjustable NPC/Narrator behavior** is about how characters behave inside the turn: how terse they are, how often they initiate, how much they speak to each other, how dominant the narrator is, and whether the runtime tends to explain or dramatize. This is partly a **generation policy concern** and partly a **runtime orchestration concern**.

A true **live dramatic scene simulator** is more than either of those. It means the runtime is no longer just summarizing one player action into one recap block. It must support ongoing scene motion, microbeats, short action pulses, NPC↔NPC exchange, continuity between turns, and player re-entry into a scene that is already moving. That requires **structural runtime changes**, not only a prompt preset.

The clean architecture for this repository is:

* add a governed **story runtime experience** section to resolved runtime config,
* expose it in the Administration Tool as first-class operator controls,
* propagate it through backend → world-engine → runtime graph → output packaging,
* create an explicit intermediate mode called **`dramatic_turn`**,
* and only expose **`live_dramatic_scene_simulator`** as “active” once the runtime and packaging contract truly honor it.

That gives a safe path:

* first: truthful delivery controls,
* second: truthful dramatic-turn behavior,
* third: real live-scene simulation,
* all bootstrapped through repository defaults and `docker-up.py`.

---

## 2. Current-State Diagnosis

The current runtime behaves too much like a recap system because the inspected live path is still structurally centered on **single-turn narrative packaging**, not on scene pulses.

The most important signs are these:

* The canonical live session path runs through `world-engine/app/story_runtime/manager.py` into the `ai_stack` turn executor, which produces one committed turn result and one visible output bundle.
* The output contract in `world-engine/app/narrative/runtime_output_models.py` is still centered on fields like `narrative_response`, not on first-class action pulses or beat packets.
* In `ai_stack/goc_turn_seams.py` and the minimal turn path, the visible output bundle is still dominated by `gm_narration`, while `spoken_lines` are present structurally but often underused in practice.
* `frontend/app/routes_play.py` still projects the runtime view around `narration_text`, then separately surfaces `spoken_lines`. That means the player-facing shell is biased toward recap-first delivery.
* The repository already contains beat- and template-oriented material, but it is not yet cleanly fused into the active canonical live path. In other words, the repository already knows about dramatic structure, but the active runtime path still packages like a narrated turn report.
* Current governance surfaces focus strongly on provider/model/retrieval/validation/runtime profile, but not yet on scene-experience semantics. So even if dramatic behavior is attempted inside prompts, it is not yet governed as runtime truth.
* There is still visible truth drift between some docs/tests/UI expectations and the active runtime seams. That makes it easy for a mode to exist in operator language before it truly exists in the live path.

So the problem is not just “writing style.” The current system is structurally optimized for:

* one player turn,
* one orchestration pass,
* one packaged visible output,
* recap-heavy narration,
* limited persistent scene motion.

That is why characters can feel too quiet or too summarized even when the prose quality is good.

---

## 3. Target Experience Model

The repository should define three explicit experience modes.

### `turn_based_narrative_recap`

**Player experience**
The player gives input, and the runtime returns a compact but literarily strong recap of what happened, with selective quoted speech.

**Runtime behavior expectations**

* One main dramatic unit per player turn.
* Limited or no scene motion beyond directly responding to the player action.
* NPC↔NPC exchange is rare and brief.
* Continuity matters, but the turn is packaged as a summary.

**Packaging expectations**

* Narration-first.
* `gm_narration` can remain primary.
* `spoken_lines` are optional and sparse.
* Action is often described rather than staged line by line.

**Narrator/NPC expectations**

* Narrator is strong and interpretive.
* NPCs are believable but not highly initiative-driven.
* Good for clarity, fast play, and broad readability.

---

### `dramatic_turn`

This should be the intermediate production mode and the first meaningful runtime upgrade.

**Player experience**
The player still interacts turn-by-turn, but each runtime response feels more like a played scene than a recap. Dialogue appears more often, action beats are shorter, and the narrator is less dominant.

**Runtime behavior expectations**

* One dominant dramatic pulse per player turn.
* Optional secondary reaction pulse.
* Higher chance of direct spoken lines.
* NPC initiative can rise, but the scene does not free-run for long.
* Continuity survives from prior turn state and prior dramatic pressure.

**Packaging expectations**

* Dialogue-first or mixed dialogue/action packaging.
* Short narration bridges.
* Spoken lines become a primary output surface, not a decorative one.
* Responder attribution and small action beats are explicit.

**Narrator/NPC expectations**

* Narrator becomes more selective.
* NPCs speak more directly and more often.
* Characters can interrupt, react, and push tension without the runtime falling into full autonomous scene simulation.

---

### `live_dramatic_scene_simulator`

This is the true advanced mode.

**Player experience**
The player enters an already-moving dramatic scene. The response can contain multiple micro-events: actions, interruptions, exchanges, pressure shifts, and short scene pulses. The player is not just receiving a recap of what their action caused; they are stepping into live dramatic motion.

**Runtime behavior expectations**

* The runtime may emit multiple microbeats per response.
* NPC↔NPC exchange is allowed and can be substantive.
* Scene motion can continue briefly even without direct player instruction, if governed settings allow it.
* The runtime must preserve beat progression and continuity pressure across turns.
* The player can insert into an ongoing dramatic lane rather than resetting the scene every turn.

**Packaging expectations**

* Output must support multiple pulses or event segments.
* Spoken lines and action pulses are primary.
* Narration becomes connective tissue, not the main payload.
* The response contract needs explicit scene-motion metadata.

**Narrator/NPC expectations**

* Narrator becomes light-touch.
* NPCs act and speak with initiative.
* Inter-character dynamics can produce movement even before the player speaks again.
* The scene should feel continuous, not re-staged every turn.

---

## 4. Proposed Governed Settings Model

These settings should not be scattered across hidden prompt text. They should live as a governed runtime configuration section, ideally under a dedicated scope such as `story_runtime` or `scene_delivery`, then be included in `build_resolved_runtime_config()` in `backend/app/services/governance_runtime_service.py`.

I recommend this shape:

### Core mode fields

* `experience_mode`

  * `turn_based_narrative_recap`
  * `dramatic_turn`
  * `live_dramatic_scene_simulator`

* `delivery_profile`

  * preset-oriented profile name
  * examples:

    * `classic_recap`
    * `lean_dramatic`
    * `cinematic_live`
    * `npc_forward`
    * `operator_custom`

### Delivery controls

* `prose_density`

  * controls amount of prose per response
  * low / medium / high or bounded numeric scale

* `explanation_level`

  * how much the runtime explains motives, context, and subtext
  * low / medium / high

* `narrator_presence`

  * how often the narrator frames and interprets
  * low / medium / high

* `dialogue_priority`

  * how strongly the runtime prefers direct speech over narrated paraphrase
  * low / medium / high

* `action_visibility`

  * how explicitly actions, gestures, and motion are surfaced
  * low / medium / high

* `repetition_guard`

  * intensity of anti-redundancy behavior
  * low / medium / high

* `motif_handling`

  * how recurring motifs are treated
  * `strict_suppression`
  * `controlled_reuse`
  * `thematic_reinforcement`

### Character-behavior controls

* `npc_verbosity`

  * terse / balanced / expressive

* `npc_initiative`

  * passive / reactive / assertive

* `inter_npc_exchange_intensity`

  * off / light / medium / strong

### Scene-motion controls

* `pulse_length`

  * short / medium / long
  * defines how much can happen inside one microbeat

* `max_scene_pulses_per_response`

  * integer, likely 1–3 in normal operation

* `allow_scene_progress_without_player_action`

  * boolean
  * whether the runtime may continue scene motion briefly on its own

* `beat_progression_speed`

  * slow / normal / fast
  * governs how quickly pressure or scene state advances

### Strong recommendation on shape

Use **preset + advanced override** rather than only raw fields.

That means:

* `delivery_profile` defines a coherent operator-facing bundle,
* advanced controls allow bounded override,
* resolved runtime config must expose both:

  * selected profile
  * final effective values

### Validation rules

The config layer must reject misleading combinations. For example:

* `live_dramatic_scene_simulator` cannot be valid with `max_scene_pulses_per_response=1` and `inter_npc_exchange_intensity=off` unless explicitly marked as degraded.
* `turn_based_narrative_recap` should ignore or cap some live-only fields.
* `allow_scene_progress_without_player_action=true` should be gated to `dramatic_turn` or `live_dramatic_scene_simulator`.
* `operator_custom` should only be considered valid if all required effective values resolve.

This validation should live beside other governed runtime validation in the backend and be surfaced in resolved runtime truth.

---

## 5. Administration Tool Plan

### Where the controls should appear

The cleanest fit is to extend the existing runtime governance surfaces instead of inventing a disconnected UI.

Primary locations:

* `administration-tool/templates/manage/runtime_settings.html`
* `administration-tool/templates/manage/operational_governance.html`
* `administration-tool/templates/manage/world_engine_control_center.html`

### Recommended grouping

In `runtime_settings.html`, add a new bounded section:

**Story Runtime Experience**

* Experience Mode
* Delivery Profile
* Delivery Controls
* Character Behavior Controls
* Scene Motion Controls

Suggested group layout:

1. **Mode**

   * Experience Mode
   * Delivery Profile

2. **Delivery**

   * Prose Density
   * Explanation Level
   * Narrator Presence
   * Dialogue Priority
   * Action Visibility
   * Repetition Guard
   * Motif Handling

3. **Character Dynamics**

   * NPC Verbosity
   * NPC Initiative
   * Inter-NPC Exchange Intensity

4. **Scene Motion**

   * Pulse Length
   * Max Scene Pulses Per Response
   * Allow Scene Progress Without Player Action
   * Beat Progression Speed

### Operator labeling

Use operator language, not model-language.

Good labels:

* “Experience Mode”
* “Delivery Profile”
* “Narrator Presence”
* “Dialogue Priority”
* “NPC Initiative”
* “Scene Continuation”
* “Scene Pulse Count”
* “Beat Progression Speed”

Avoid misleading labels like:

* “Live Mode” if the runtime still behaves like recap packaging
* “Cinematic” if it is only longer prose
* “Dynamic Characters” if NPC initiative is not truly honored

### Defaults

Fresh bootstrap default should be:

* `experience_mode = turn_based_narrative_recap`
* `delivery_profile = classic_recap`
* moderate prose density
* medium explanation
* medium narrator presence
* low-to-medium dialogue priority
* balanced NPC verbosity
* reactive NPC initiative
* inter-NPC exchange light or off
* `max_scene_pulses_per_response = 1`
* `allow_scene_progress_without_player_action = false`

Safe first alternative profile:

* `dramatic_turn`
* `lean_dramatic`

Do **not** make live simulator the bootstrap default.

### Active truth surfaces

The admin must show both **desired** and **observed** state.

Add to operational governance and world-engine control center:

* configured `experience_mode`
* observed `experience_mode` honored by play-service
* resolved `delivery_profile`
* config version
* contract version for output packaging
* whether runtime is in degraded compatibility mode
* whether live-scene features are active, capped, or unavailable

### Session inspection truth

In admin session inspection, show:

* active experience config on session start
* effective overrides
* pulses emitted in last response
* spoken-line count vs narration-block count
* scene continuation active/inactive
* responder attribution
* beat progression movement
* reason when mode is downgraded or capped

This avoids the classic problem where the UI claims a mode exists but the actual session still runs like narrated recap.

---

## 6. Runtime Integration Plan

### Where settings enter the path

The flow should be:

Administration Tool
→ backend runtime settings/governance update API
→ resolved runtime config snapshot
→ internal runtime-config endpoint
→ world-engine runtime config client
→ story runtime manager / graph executor / packaging seams
→ diagnostics + player-facing output

### Likely backend seams

Primary files:

* `backend/app/services/governance_runtime_service.py`
* `backend/app/api/v1/operational_governance_routes.py`
* `backend/app/services/ai_engineer_suite_service.py`
* `backend/app/services/world_engine_control_center_service.py`

What should happen there:

* add a first-class governed section for story runtime experience
* include it in resolved runtime config
* version it
* validate it
* persist it in snapshots
* expose it in admin truth endpoints
* include it in “desired vs observed” control-center surfaces

### Likely world-engine seams

Primary files:

* `world-engine/app/runtime/runtime_config_client.py`
* `world-engine/app/story_runtime/live_governance.py`
* `world-engine/app/story_runtime/governed_runtime.py`
* `world-engine/app/story_runtime/manager.py`
* `world-engine/app/narrative/runtime_output_models.py`
* `world-engine/app/story_runtime_shell_readout.py`

What should happen there:

* runtime config client must fetch and hold effective story runtime experience settings
* the governed runtime layer must expose them as active runtime truth
* `StoryRuntimeManager` must pass them into turn execution and packaging
* output models must be extended so live-scene packaging becomes first-class rather than improvised inside narration
* shell readout and diagnostics must reveal the actually active behavior branch

### Likely `ai_stack` seams

Primary files:

* `ai_stack/langgraph_runtime_executor.py`
* `ai_stack/langgraph_runtime_state.py`
* `ai_stack/goc_turn_seams.py`
* any packaging/output assembly seam around visible output bundle

What should change there:

* consume active experience settings as execution policy
* branch between recap-oriented packaging and dramatic/live packaging
* create explicit pulse-aware packaging in live modes
* enforce repetition suppression and motif policy at packaging level as well as generation level
* elevate `spoken_lines`, action beats, and responder attribution into core output handling

### What is delivery-only vs structural

**Delivery-only / low-risk**

* prose density
* explanation level
* narrator presence
* repetition guard
* motif handling
* dialogue priority when it only affects packaging preference

**Behavioral but still moderate-risk**

* NPC verbosity
* NPC initiative
* inter-NPC exchange intensity

**Structural runtime change**

* pulse length
* max scene pulses per response
* allow scene progress without player action
* beat progression speed
* true live-scene continuation
* multiple micro-events in a single response
* player entering a scene that already has momentum

### Packaging changes required

The visible output bundle should evolve from a narration-heavy structure to an experience-aware one.

At minimum, the runtime needs to support:

* `narration_blocks`
* `spoken_lines`
* `action_pulses`
* `responder_trace`
* `scene_motion_summary`
* `beat_progression`
* `continuation_state`

Recap mode can still collapse these into a narration-dominant display.
Dramatic and live modes should not.

---

## 7. Live Dramatic Scene Simulator Architecture

A real live dramatic scene simulator inside this repository should still honor the turn-driven transport layer, but inside one player turn it should be allowed to execute **multiple microbeats** before returning.

### Core concept

One player input does not always map to one narrated summary.
Instead it maps to:

1. interpretation of player insertion,
2. scene-state update,
3. one or more scene pulses,
4. packaging of the resulting dramatic motion.

### Scene pulse model

A **scene pulse** is a small dramatic unit containing:

* active responder(s),
* a short action beat,
* one or more spoken lines,
* optional narration bridge,
* continuity update,
* beat progression signal.

A pulse is not a full turn recap. It is a dramatic event packet.

### Microbeats / beat progression

The system should maintain a lightweight beat state even if it does not revive an older legacy beat lane wholesale.

That means each scene tracks:

* current pressure or tension state,
* current active dramatic thread,
* who currently has initiative,
* whether the scene is escalating, holding, or releasing,
* what changed in the last pulse.

This can initially be layered onto the existing `narrative_threads` and continuity surfaces in `StoryRuntimeManager`, instead of forcing an immediate full engine rewrite.

### Scene continuation

To avoid recap restaging, the runtime must carry forward:

* who just spoke,
* who currently has attention/focus,
* unresolved emotional or tactical pressure,
* whether the scene is in interruption, escalation, retreat, or confrontation,
* what the scene is expecting next.

This continuation state must feed the next turn executor.
Without that, every turn will be reintroduced like a narrated reset.

### NPC↔NPC exchange

In live simulator mode, the runtime must be allowed to emit NPC↔NPC exchange without waiting for the next player prompt, within bounded limits.

That means:

* one player provocation can trigger an NPC reaction and a second NPC counter-reaction,
* bounded by `max_scene_pulses_per_response`,
* bounded by continuation safety and verbosity budgets.

This is one of the main differences between `dramatic_turn` and `live_dramatic_scene_simulator`.

### Player re-entry into an already-moving scene

The runtime must treat the player as re-entering a scene state that already has momentum.

So when the next player turn arrives, the runtime should not ask:

* “what happened this turn?”

It should ask:

* “what is the current dramatic state, who has initiative, what pulse is in progress, and how does the player’s input alter that motion?”

That is the correct mental model for live dramatic continuity.

### Reduction of prose recap

In live simulator mode:

* narration should bridge and orient,
* dialogue should carry the dramatic weight,
* action beats should surface physical and emotional movement,
* recap should be minimal and mostly reserved for clarity repair.

### Use of spoken lines and short action beats

Spoken lines should become first-class output, not optional decoration.
Short action beats should sit between lines where needed, rather than being absorbed into one long narrator paragraph.

### Multiple micro-events per response

Yes, in real live mode, multiple micro-events are needed.

Recommended bounded behavior:

* `dramatic_turn`: usually 1 pulse, occasionally 2
* `live_dramatic_scene_simulator`: 1–3 pulses
* anything above that should require explicit operator policy and likely stay off by default

This keeps the system game-suitable instead of becoming a wall of text.

---

## 8. Docker-Up.py Bootstrap Plan

The goal is: fresh repository boot, run `docker-up.py`, and the feature works with repository-contained defaults.

### Required defaults

The repository needs default governed story runtime settings baked into bootstrap:

* default profile
* default experience mode
* default advanced values
* default config version
* default validation rules

These defaults should be created automatically by the backend governance bootstrap path, not by manual admin interaction.

### Where defaults should live

Primary home:

* backend governance bootstrap logic in `backend/app/services/governance_runtime_service.py`

Optionally mirrored in:

* a repository seed/default config module
* or a migration/bootstrap seed path if one already exists for system settings

### Required config propagation

The world-engine already has a runtime config client that expects backend runtime-config fetch settings. For this feature to be truly governed on fresh Docker startup, that path must be fully wired by default.

That means the repository bootstrap needs the play-service to have working defaults for:

* backend runtime config URL
* internal runtime config token

From the inspected compose/bootstrap seams, this is a likely current gap that should be closed explicitly in compose/env defaults rather than relying on local manual setup.

### Required compose/env changes

At minimum, ensure Docker defaults include a coherent set of runtime-config fetch secrets/URLs for:

* backend internal config endpoint
* play-service runtime config client
* any reload path or observed-state surface if used

These should be handled the same way the repository already handles shared service secrets:

* included in compose defaults for local/dev bootstrap
* optionally overridden by env
* never requiring a manual pre-run edit just to make governed runtime config work

### `docker-up.py` behavior

`docker-up.py` should not need custom operator steps. It should:

* build containers,
* start services,
* let backend bootstrap default governed story runtime settings,
* let play-service fetch the resolved config,
* expose the default mode truthfully in admin UI,
* allow immediate operator adjustment after startup.

### Acceptance proof for bootstrap

A clean bootstrap is successful only if:

* no manual DB edit is required,
* no manual admin click is required to make story runtime settings exist,
* backend exposes resolved config including story runtime experience,
* play-service observes and reports the same effective values,
* the default player flow runs in recap mode out of the box,
* switching to `dramatic_turn` or `live_dramatic_scene_simulator` after startup changes actual runtime behavior.

---

## 9. Implementation Waves

### Wave 1 — Truthful config surfacing

Low-risk.

* Add governed story runtime experience settings in backend config model/snapshot generation.
* Expose them in admin runtime settings and operational governance.
* Expose desired/effective values in world-engine control center.
* Keep runtime behavior unchanged for now, but clearly mark mode support level.
* Do not yet label live simulator as fully active.

Primary seams:

* backend governance services/routes
* admin templates/JS
* control-center service

### Wave 2 — Delivery and packaging controls

Still relatively safe.

* Implement delivery-form controls in output packaging.
* Make prose density, explanation level, narrator presence, repetition guard, motif handling, and dialogue priority materially affect visible output.
* Improve use of `spoken_lines` and reduce recap redundancy.
* Keep one-pulse model underneath if needed.

Primary seams:

* `ai_stack/goc_turn_seams.py`
* output assembly code
* `frontend/app/routes_play.py`
* player-facing shell projection

### Wave 3 — `dramatic_turn` runtime behavior

This should be the first real runtime upgrade.

* Add initiative-aware responder behavior.
* Allow one dominant dramatic pulse with optional short follow-up.
* Increase direct speech and action beat packaging.
* Carry forward stronger continuation state between turns.
* Expose pulse metadata in diagnostics.

Primary seams:

* `StoryRuntimeManager`
* runtime state/executor
* output models
* session diagnostics

### Wave 4 — live simulator foundation

Deeper runtime work.

* Introduce bounded microbeat/pulse execution.
* Add explicit continuation state and beat progression state.
* Permit bounded NPC↔NPC exchange.
* Support multiple micro-events per response.
* Prevent recap-style restaging at turn boundaries.

Primary seams:

* `StoryRuntimeManager`
* executor/state
* structured output models
* packaging contract
* continuity storage

### Wave 5 — governance hardening and observed-state truth

Critical before declaring live simulator done.

* Add degraded-mode reporting.
* Add observed-state reporting from play-service.
* Add config-version and contract-version visibility.
* Ensure admin “active mode” only reflects runtime-honored mode.

### Wave 6 — Docker/bootstrap integration

* Add default config seeds.
* Add compose/env defaults for runtime-config fetch path.
* Ensure backend and play-service agree on internal config secrets/URLs.
* Verify first boot works without operator intervention.

### Wave 7 — E2E validation and release gate

* Full tests
* mode-difference evidence
* bootstrap proof
* operator truth proof

---

## 10. Tests and Evidence

### Admin UI config tests

Needed in administration-tool tests:

* story runtime experience section renders
* supported values match backend enums
* saving preset and advanced values works
* invalid combinations are rejected visibly
* desired/effective state is displayed distinctly

### Runtime config truth tests

Needed in backend tests:

* resolved runtime config includes story runtime experience section
* config version increments or snapshots correctly
* validation rejects impossible combinations
* defaults bootstrap automatically
* world-engine control center surfaces desired values

### Live mode propagation tests

Needed across backend + world-engine:

* changing experience mode in admin updates resolved runtime config
* play-service fetches new config
* session diagnostics show the new mode as active
* no stale mode mismatch remains between backend and play-service

### Packaging/rendering mode-difference tests

Needed in world-engine / ai_stack / frontend:

* recap mode yields narration-dominant packaging
* dramatic_turn yields more spoken lines and shorter narration
* live mode yields multiple pulses when configured
* repetition guard and motif handling alter packaging behavior measurably
* player shell projection renders each mode truthfully

### Beat/pulse behavior tests

Needed in world-engine:

* pulse count obeys cap
* scene continuation survives across turns
* NPC initiative increases response motion when configured
* inter-NPC exchange activates only when allowed
* beat progression speed changes continuity advancement
* scene progress without player action is bounded and visible

### Session truth and diagnostics tests

Needed in world-engine:

* diagnostics contain active experience settings
* diagnostics contain pulse execution summary
* diagnostics expose downgrade/degraded reason when applicable
* observed packaging contract version is visible

### Docker bootstrap tests

Needed at integration/E2E layer:

* fresh environment + `docker-up.py` creates usable default story runtime settings
* backend resolved config is available without manual setup
* play-service consumes it without manual env edits
* default gameplay path runs immediately
* post-start admin mode change alters subsequent runtime output
* no hidden preconfiguration is required

### Strong acceptance evidence

To prove recap mode and live simulator mode are genuinely different, the evidence should include:

* same scene/setup
* same or similar player input
* captured outputs under all three modes
* measurable differences in spoken-line count, narration density, pulse count, responder motion, and continuity advancement

---

## 11. Risks / Decision Gates

### What can be done as pure delivery control

Safe early work:

* prose density
* explanation level
* narrator presence
* repetition guard
* motif handling
* dialogue priority as packaging preference

These can materially improve the game feel even before live simulation exists.

### What requires deeper runtime change

Not safe to fake as a prompt preset:

* multiple scene pulses
* bounded scene motion without player action
* strong NPC↔NPC exchange
* persistent initiative state
* beat progression speed
* player entering a moving scene

These require actual runtime and output-contract work.

### What may need architecture decisions

These need explicit decisions before implementation:

* whether beat state lives inside `StoryRuntimeManager` or a dedicated continuity/beat component
* whether live simulator uses the existing turn graph with experience-aware branching, or whether it needs dedicated live-scene nodes
* whether the player shell should display pulse-segmented output directly, or whether frontend should first keep a flattened projection

### What would be misleading if exposed too early

Do not expose as fully active until honored:

* “Live dramatic scene simulator”
* “NPC initiative”
* “Inter-NPC exchange intensity”
* “Scene progress without player action”

If these appear in admin before the runtime truly uses them, the UI becomes dishonest.

### Key technical risk

The biggest risk is adding controls faster than the canonical live runtime path can honor them.
That would reproduce the repository’s existing drift problem in a new area.

The safest rule is:

* no setting is marked active unless observed runtime diagnostics confirm it.

---

## 12. Final Recommendation

### Best minimal viable governed setup

Implement a new governed **Story Runtime Experience** section with:

* `experience_mode`
* `delivery_profile`
* delivery controls
* bounded character-behavior controls

Ship it first with two truthful modes:

* `turn_based_narrative_recap`
* `dramatic_turn`

Treat `dramatic_turn` as the first real improvement path.
It gives immediate value without pretending full live simulation already exists.

### Best medium-term live simulator design

Build `live_dramatic_scene_simulator` as a bounded multi-pulse scene system layered onto the current canonical live path:

* pulse-aware execution
* stronger continuation state
* initiative-aware responder logic
* explicit NPC↔NPC exchange
* spoken-line and action-beat-first packaging
* narrator as bridge, not payload
* bounded autonomous scene continuation

Do not build it as a style preset.
Build it as a runtime behavior mode with its own packaging contract and diagnostics truth.

### Cleanest path to `docker-up.py` compatibility

Use repository-contained bootstrap defaults:

* backend seeds default story runtime settings automatically
* resolved runtime config includes them automatically
* compose/env defaults wire backend ↔ play-service runtime-config fetch path automatically
* play-service reports observed mode truth automatically
* admin UI reads and displays both configured and observed values automatically

That gives the clean rollout sequence:

1. governed config model and truthful admin surfaces
2. delivery-form improvements
3. `dramatic_turn` runtime branch
4. live-scene pulse architecture
5. bootstrap hardening
6. E2E proof through `docker-up.py`

That is the lowest-risk path that stays honest, repository-grounded, and actually moves the system from recap-heavy delivery toward a real governed live dramatic scene simulator.
