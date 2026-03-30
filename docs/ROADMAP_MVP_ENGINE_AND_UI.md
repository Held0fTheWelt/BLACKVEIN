# Roadmap MVP — World of Shadows

## Purpose

This document describes the precise MVP roadmap for the first playable vertical slice of **World of Shadows**.
The MVP is intended to demonstrate that the **World Engine**, with a **dynamic but controlled AI story core**, can load a formal content module, advance it, validate it, visualize it, and make it diagnostically traceable.

The first reference content includes:

- **1 content module:** *God of Carnage*
- **1 playable run**
- **1 usable UI**
- **1 controlled AI story loop**
- **1 solid foundation for additional modules**

---

## Core Idea of the MVP

The MVP is **not a free story sandbox system**, but a **tightly guided, formally secured AI story vertical slice**.

The core logic is:

- **Content** defines the dramatic possibility space.
- **AI** generates interpretations, reaction impulses, and proposals.
- **Engine** validates, decides, and advances canonical states.
- **UI** makes story, state, decisions, and errors visible.

The AI core is conceived as **hybrid**:

- **SLMs** handle narrow, fast, strictly limited helper tasks.
- **LLMs** handle the actual narrative interpretation and conflict advancement.
- **The Engine** remains the authoritative instance in all cases.

---

## MVP Target Vision

At the end of W4, a system exists that:

1. can formally load the **God of Carnage** module,
2. can start a session,
3. can advance scenes and states,
4. can receive AI outputs in structured form,
5. can reject invalid AI proposals,
6. explicitly logs state changes,
7. makes the progression visible in a UI,
8. supports development, debugging, and demonstration.

Additionally, by then exists a first robust **hybrid AI execution logic** in which small models take on clearly delineated pre- and post-processing tasks without replacing the engine's canonical control or the larger story model's dramaturgical leadership role.

---

## What the MVP Is

The MVP includes:

- a formally defined content module format
- a complete reference module for **God of Carnage**
- a World Engine with:
  - Session State
  - Turn State
  - Event Log
  - State Deltas
  - Rule and validation layer
- an AI story loop with controlled outputs
- a hybrid AI execution with:
  - small specialized models for preprocessing, structuring, routing, and pre-checking
  - a larger story model for scene interpretation, conflict dynamics, and reaction impulses
- a UI for:
  - Session start
  - Scene display
  - Character status
  - Conflict development
  - Turn execution
  - Debug/diagnostic view
- Tests for contracts, content, runtime, AI integration, and end-to-end flows

---

## What **Not** Part of the MVP

These points are explicitly **not** part of the MVP:

- generic authoring tool for arbitrary story modules
- open multi-module ecosystem
- free lore invention by the AI
- autonomous AI with write rights to canon
- unlimited free character or scene generation
- real large multi-agent system as a mandatory component
- elaborate presentation/cinematic features before functional stability
- complex player choice economy outside the core loop
- broad content wave beyond *God of Carnage*
- scope expansions not directly required for MVP function
- sprawling model landscape with many interchangeable specialized models without clear roles
- replacement of the actual story core by pure SLM logic

---

## System Boundaries

### World Engine

The World Engine is responsible for:

- canonical states
- state transitions
- rule checking
- validation
- delta application
- session progress
- error handling
- logging
- reproducibility

The Engine is the **authoritative instance**.

### AI

The AI is responsible for:

- scene interpretation
- conflict interpretation
- trigger recognition
- reaction impulses
- proposals for permissible state changes
- dramatic conflict movement within defined boundaries

The AI is **not authoritative**.
It may only make **structured proposals**.

### Hybrid AI Layer

Within the AI layer, two classes of models apply:

#### SLMs

SLMs handle narrow, fast, and strictly limited tasks, e.g.:

- context compression
- trigger extraction
- pre-normalization of structured outputs
- cheap routing
- pre-checking for obvious contract violations
- debug/diagnostic summaries for UI and logs

SLMs are **helper models**, not story sovereigns.

#### LLMs

LLMs handle the actual story advancement, in particular:

- scene interpretation
- conflict movement
- reaction impulses
- ambivalence handling
- character-faithful advancement
- dramatic development within the contract

The LLM is the **primary generator of story proposals**, but also not authoritative.

### UI

The UI is responsible for:

- visibility
- operation
- diagnosis
- progression insight
- debug support

The UI makes no canon decisions.

### Content

The content module defines:

- characters
- relationships
- scenes
- transitions
- triggers
- escalation axes
- end states
- direction/interpretation spaces

Content provides the **formally permitted possibility space**.

---

## Principle: Authority and Control

The central tenet of the MVP is:

> **The AI may be creative, but never sovereign. The Engine remains sovereign, but never blind.**

From this follow these rules:

- AI never sets truth itself.
- AI may not create facts outside the contract.
- AI may only use defined action types.
- AI may only influence permitted state fields.
- SLMs may prepare, normalize, and pre-check, but may not make canonical decisions.
- LLMs may generate story proposals, but may not commit states.
- The Engine validates every AI output.
- Only the Engine commits canonical state changes.

---

## Target Structure of Deliverables

```text
docs/
  roadmap_mvp.md
  mvp_definition.md
  god_of_carnage_module_contract.md
  ai_story_contract.md
  session_runtime_contract.md

schemas/
  content_module.schema.json
  ai_story_output.schema.json
  session_state.schema.json
  state_delta.schema.json

content/
  modules/
    god_of_carnage/
      module.yaml
      characters.yaml
      relationships.yaml
      scenes.yaml
      transitions.yaml
      triggers.yaml
      endings.yaml
      direction/
        system_prompt.md
        scene_guidance.yaml
        character_voice.yaml

engine/
  content/
  session/
  story/

ai/
  adapters/
  prompts/
  validators/
  roles/
  slm/
    context_packer/
    trigger_extractor/
    delta_normalizer/
    guard_precheck/
    router/

ui/
  routes/
  templates/
  static/

tests/
  contracts/
  content/
  engine/
  ai/
  ui/
  e2e/
```

---

## Hybrid AI Target Vision for the MVP

The MVP's model architecture is intentionally small and controlled.

### Target Roles

#### 1. SLM `context_packer`

Input:

- Session state
- recent turns
- event log
- active relationship axes

Output:

- compact, prioritized story context for the next story call

#### 2. SLM `trigger_extractor`

Input:

- operator/player input
- current scene status
- optionally raw draft of story model output

Output:

- recognized triggers from the permitted trigger set

#### 3. SLM `delta_normalizer`

Input:

- raw structured story output

Output:

- normalized `proposed_state_deltas` in the permitted target format

#### 4. SLM `guard_precheck`

Input:

- structured AI output
- contract snapshot
- current scene/state metadata

Output:

- suspicion list for:
  - illegal references
  - forbidden fields
  - risky scene jumps
  - contradictory or incomplete responses

#### 5. SLM `router`

Input:

- task context
- session complexity
- response quality of last turn
- error/recovery status

Output:

- decision whether:
  - only pre/post-processing is needed,
  - a full LLM story call is needed,
  - a repair/fallback round should run

### Architecture Principle

> **SLMs do not lead the canon in World of Shadows, but prepare the canon flow, compress it, structure it, and secure it.**

---

# W0 — Sharpen Foundation and Lock MVP Contract

## Goal

To organize the existing state so that the next waves do not end up in architecture drift, special logic, or unclear responsibilities.

## Result of W0

At the end of W0, it is crystal clear:

- what the MVP exactly is
- what is not part of the MVP
- where Engine, AI, Content, and UI each begin and end
- what God of Carnage module format applies
- what AI outputs are permissible
- how Session, Turn, Delta, and Logging are structured
- what target folder structure applies
- what role SLMs and LLMs each play in the MVP
- which AI tasks may be handled cheaply and small, and which must remain in the story core

## Work Packages

### 1. Lock MVP Definition

Define:

- 1 story module: **God of Carnage**
- 1 playable run
- 1 UI for operation and diagnosis
- AI as dynamic core, but controlled
- hybrid AI architecture with tight SLM support and clearly bounded LLM story core

### 2. Define System Boundaries

Delineation between:

- World Engine
- AI
- UI
- Content
- SLM helper layer
- LLM story core

### 3. Define Content Contract

Define structure for:

- characters
- relationships
- scenes
- transitions
- triggers
- escalation axes
- end states
- intervention points

### 4. Define AI Contract

Establish:

- structured outputs
- permitted action types
- forbidden changes
- required fields
- validation rules
- permitted SLM roles
- handoff points between SLMs, LLM, and Engine

### 5. Define Session Contract

Define:

- Session State
- Turn State
- Event Log
- State Delta
- AI Decision Log
- optional SLM decision/routing metadata

### 6. Define Model Strategy and Task Assignment

Establish:

- which tasks are SLM-suitable
- which tasks only the story LLM may handle
- when a direct LLM call is triggered
- when routing/fallback/reduced context kicks in
- how many model roles the MVP can at most support

### 7. Define Error and Guard Classes

At minimum:

- schema invalid
- forbidden mutation
- unknown reference
- illegal scene jump
- unsupported trigger
- canon conflict
- partial AI output
- empty AI response
- timeout / backend failure
- SLM normalization failure
- SLM routing mismatch
- precheck warning overflow

### 8. Lock Repo/Folder Structure

No mixing of:

- Content
- Engine
- Runtime
- UI
- AI-specific logic
- SLM helper roles and story core logic

## Deliverables

- `docs/mvp_definition.md`
- `docs/god_of_carnage_module_contract.md`
- `docs/ai_story_contract.md`
- `docs/session_runtime_contract.md`
- first target folder structure
- `schemas/` skeleton
- test skeleton for contracts
- first model role definition for SLM/LLM task division

## Acceptance Criteria

- For all stakeholders, it is clear what will be built in W1–W4.
- No central area remains implicit.
- An AI output can be formally checked against a schema.
- The content module has a defined target structure.
- The authority of the Engine is explicitly documented.
- SLM usage is clearly limited and architecturally cleanly organized.
- It is clear which tasks may not be outsourced to SLMs.

## Gate for W1

W1 begins only when:

- Core terms are defined
- Contracts are documented
- First schemas exist
- Target structure is established
- Test skeleton is present
- SLM/LLM roles are cleanly separated from each other

---

# W1 — God of Carnage as Real Content Module

## Goal

Model *God of Carnage* not as a loose idea, but as a formal, machine-readable, testable module.

## Result of W1

The play exists as the first reference content module and can be loaded by the Engine.

## Work Packages

### 1. Build Module Structure

Define and create:

- `module.yaml/json`
- `characters`
- `relationships`
- `scenes`
- `transitions`
- `triggers`
- `endings`
- prompt/direction components

### 2. Model Characters

At minimum:

- Véronique
- Michel
- Annette
- Alain

With clear formal properties, roles, basic attitudes, and relevant tension attributes.

### 3. Define Relationship Axes

At minimum:

- spousal internal
- host vs. guests
- moral vs. pragmatic attitudes
- latent dominance/devaluation axes

### 4. Model Scene Structure

At minimum:

- polite opening
- moral negotiation
- coalition formation / shifts
- emotional derailment
- loss of control / escalation

### 5. Define Triggers

At minimum:

- contradiction
- exposure
- relativization
- apology / non-apology
- cynicism
- flight into subplots

### 6. Define Escalation Logic

At minimum:

- individual escalation
- relationship instability
- conversation breakdown
- coalition shift

### 7. Define End and Shift Conditions

At minimum:

- termination
- open implosion
- temporary calm
- toxic pseudo-solution

### 8. Build Content Validation

Check:

- references complete
- no dead transitions
- no invalid triggers
- ends reachable
- no special logic required

### 9. Define SLM-relevant Content Hints

Add, where appropriate:

- prioritizable conflict axes
- trigger-relevant markers
- structured short contexts for context packing
- clearly named fields relevant for delta normalization and guard precheck

## Deliverables

- complete `god_of_carnage` module
- module loader
- content validator
- content tests
- module documentation

## Acceptance Criteria

- The module is fully loadable.
- All characters, scenes, and triggers are structurally consistent.
- At least one complete story run is modeled as a valid graph.
- The module can be read by the Engine without special logic.
- The module provides clear structured signals for later SLM helper roles without forcing SLM-specific special logic into the content format.

## Gate for W2

W2 begins only when:

- the module loads stably
- references are valid
- at least one run is formally possible
- no hardcoded special handling is required
- the module provides enough clean structure for later context/trigger/delta helper roles to work with

---

# W2 — Draw Dynamic AI Story Core into the World Engine

## Goal

The Engine should not only store states, but should be able to truly advance a scene with advanced dynamic AI.

## Result of W2

A first AI-supported story loop runs with controlled dynamics.

## W2 Sub-waves

---

## W2.0 — Story Loop Skeleton

### Goal

Close the complete control path without creative dependency.

### Work Packages

- start session
- load module
- activate scene
- prepare state
- feed dummy/mock AI output
- validate output
- apply deltas
- write event log
- derive next situation
- define placeholder hooks for SLM preprocessing, routing, and post-normalization

### Acceptance

- A complete turn runs technically through.
- The control chain is testable.
- Error paths are visible.
- The pipeline is already cut such that SLM helper roles can be cleanly integrated later.

---

## W2.1 — Real AI Adapter with Structured Output

### Goal

A model delivers formally checkable story proposals.

### Work Packages

- connect AI adapter
- fixed prompt structure
- strictly structured JSON output
- parsing + schema check
- no uncontrolled truth-setting via free text
- integrate first SLM-supported pre/post-processing where it is clearly limited and cost-reducing

### Mandatory Components of AI Output

- `scene_interpretation`
- `detected_triggers`
- `proposed_state_deltas`
- `dialogue_impulses`
- `conflict_vector`
- optional `confidence` / `uncertainty`

### Acceptance

- Multiple turns are possible.
- Outputs remain formally validatable.
- Faulty responses are detected.
- The pipeline clearly distinguishes between SLM preparation, LLM story output, and Engine validation.

---

## W2.2 — Guard and Validation Layer

### Goal

The AI may not sneak in invalid changes.

### Work Packages

- whitelist permitted action types
- check character and scene references
- triggers only from permitted set
- no new facts
- no invalid state fields
- no illegal scene jumps
- end states only under valid conditions
- integrate guard precheck from the SLM layer as upstream risk marking, without replacing engine validation

### Acceptance

- Faulty AI outputs are rejected or partially adopted.
- The Engine remains stable.
- Rejections are logged.
- SLM pre-checks increase visibility and efficiency without ever bypassing engine guards.

---

## W2.3 — Memory and Context Logic

### Goal

Dynamics without context drift.

### Work Packages

- short-term turn context
- session history
- compressed progression summary
- relevant relationship axes
- modular lore/direction context supply
- build `context_packer` as a clearly bounded SLM helper role

### Acceptance

- Longer sessions remain coherent.
- Escalation patterns remain traceable.
- Context remains controllable.
- The context packer reduces ballast without destroying important conflict signals.

---

## W2.4 — Internal Role Logic

### Goal

Better quality through clean internal task distribution.

### Roles

- **Interpreter** — What is happening right now?
- **Director** — What conflict movement fits now?
- **Responder** — What concrete reaction follows from it?

### Complementary Helper Roles

- **Context Packer (SLM)** — Which parts of the progression are really relevant for the next turn?
- **Trigger Extractor (SLM)** — Which permitted triggers are likely active?
- **Delta Normalizer (SLM)** — How are story proposals cleanly transformed into permitted delta structures?
- **Router (SLM)** — Is a small round sufficient, is a full story call needed, or must recovery kick in?

### Acceptance

- Interpretation, conflict dynamics, and response are more cleanly separated.
- Diagnosis becomes clearer.
- Role logic remains MVP-compatible.
- SLM roles support but do not dominate the story core.

---

## W2.5 — Recovery and Stability Mode

### Goal

A run must not die from a bad AI response.

### Work Packages

- retry rules
- reduced context retry
- fallback mode
- safe no-op/safe turn strategy
- last valid state is preserved
- degraded but running session mode
- define SLM-based repair/normalization attempts before triggering more expensive story re-calls

### Acceptance

- Invalid AI outputs do not break the run.
- Recovery is traceable.
- The session remains debuggable.
- Small helper models can inexpensively repair or classify faulty responses without diluting the story core.

---

## Overall Deliverables of W2

- `story_loop`
- AI adapter
- AI output schemas
- validator
- session state model
- event/delta logging
- AI loop tests
- first SLM helper roles for:
  - context compression
  - trigger extraction
  - delta normalization
  - guard precheck or routing

## Overall Acceptance for W2

- A session can run from start through multiple turns.
- The AI dynamically generates different reactions within the rules.
- Invalid AI outputs do not break the run.
- State changes are traceable and stored.
- The Engine remains master of the canon.
- SLMs reduce costs and structure subtasks without replacing the dramatic core.

## Gate for W3

W3 begins only when:

- sessions run stably over multiple turns
- AI output is formally validated
- error cases are handled in a controlled manner
- deltas are explicitly stored
- engine authority is not undermined
- SLM helper roles remain clearly limited, testable, and interchangeable

---

# W3 — Playable UI with Diagnostic and Control Depth

## Goal

The MVP should become usable: not just via tests, but via a real interface.

## Result of W3

A first UI allows starting *God of Carnage*, making inputs, and visibly tracking dynamic development.

## Work Packages

### 1. Session Start View

- start new game
- select module
- load session

### 2. Scene View

- current scene
- situational description
- conversational state

### 3. Character Panel

- emotional state
- attitude
- escalation status
- relationship shifts

### 4. Conflict/Tension Panel

- dominant axes
- current escalation
- shift risks

### 5. Interaction Panel

- player/operator input
- next turn
- execute AI

### 6. Progression View

- turn history
- significant events
- state changes

### 7. Debug/Diagnostic Panel

- AI output raw/structured
- validation decisions
- adopted vs. rejected changes
- active triggers / rules
- SLM intermediate steps, routing decisions, and normalization results as far as useful for development
- clear visibility of which outputs came from the story LLM and which were prepared or repaired by helper roles

### 8. API Endpoints

At minimum:

- start session
- get session
- execute turn
- get logs
- get state

## Deliverables

- playable Jinja/web UI
- API endpoints
- UI smoke tests
- debug views

## Acceptance Criteria

- A user can start a run without code intervention.
- The progression is visible.
- The AI reactions are visible.
- State changes are traceable.
- Debug information actually helps with development and testing.
- The hybrid AI pipeline remains diagnostically traceable in the UI.

## Gate for W4

W4 begins only when:

- session start works without code intervention
- story progression is visible
- debug data is useful
- the UI can reliably serve the core loop
- SLM and LLM portions are cleanly distinguishable in debugging

---

# W4 — MVP Hardening, Quality, First Real Presentation Edition

## Goal

Turn the technically running prototype into a robust MVP that not only works somehow, but is presentable as the first real vertical slice.

## Result of W4

*God of Carnage* runs as a stable, traceable, dynamic AI MVP.

## Work Packages

### 1. System Tests / End-to-End Tests

- session start to end
- typical escalation paths
- error paths
- recovery behavior
- hybrid pipeline behavior under normal, degradation, and retry conditions

### 2. Balancing / Fine-tuning

- escalation not too flat
- escalation not chaotic
- coalition shifts traceable
- characters remain character-true
- correct load distribution between SLM helper layer and story LLM

### 3. AI Quality Improvement

- better prompt structure
- better context selection
- cleaner validation
- more stable responses
- better thresholds for when small helper models suffice and when the story LLM must take over

### 4. Harden Session Persistence

- save / load
- resumption
- reproducible diagnostics
- persistence of relevant hybrid metadata where useful for debugging and comparison

### 5. Improve UI Usability

- clearer story flow
- better visibility of direction/AI decisions
- better developer diagnostics
- meaningful reduction or switchability of technical hybrid details so debug transparency does not become UI confusion

### 6. Check MVP Delineation

- no scope creep
- only MVP-necessary additions
- no sprawling specialization into too many micro-models

### 7. Demo / Demo Script

- defined demonstration run
- defined test runs
- defined failure cases
- defined hybrid fallback cases that showcase system robustness

## Deliverables

- hardened MVP
- end-to-end test package
- demo documentation
- clear definition of "ready for next content wave"

## Acceptance Criteria

- Multiple sessions run stably.
- The AI feels dynamic but not arbitrary.
- The story run is traceable and debuggable.
- The MVP is internally presentable.
- The MVP is usable as a foundation for additional modules.
- The hybrid architecture of SLM helper layer and story LLM is robust enough to serve as a pattern for additional modules.

---

# Reproducibility and Diagnostics

For solid analysis and later development, every run must be diagnostically traceable.

## Mandatory Session Metadata

- `session_id`
- `module_id`
- `module_version`
- `contract_version`
- `prompt_version`
- `ai_backend`
- `ai_model`
- optional `seed`
- timestamps

## Extended Hybrid Metadata

Additionally, where appropriate:

- `routing_mode`
- `context_packer_version`
- `trigger_extractor_version`
- `delta_normalizer_version`
- `guard_precheck_version`
- `fallback_mode`
- `recovery_attempt_count`

## Mandatory Logs

- Event Log
- AI Decision Log
- Validation Log
- State Delta Log
- Recovery/Fallback Log
- optional SLM routing/pre-check/normalization log, as long as with reasonable effort and without log explosion

---

# Quality Principles

## 1. No Implicit Truth

Everything central must either:

- be defined in content,
- be described in the contract,
- or be explicitly stored in state.

## 2. No Special Logic for God of Carnage

The first module is reference module, not exception.

## 3. No Free AI Canon

AI may propose meaning but may not set new world order.

## 4. Validation Before Application

Every AI proposal is checked before it changes state.

## 5. Diagnosis is Mandatory, Not Bonus

An MVP without traceable diagnostics is insufficient for this project.

## 6. SLMs as Tools, Not Sovereigns

Small models serve preparation, compression, structuring, pre-checking, and efficiency.
They do not replace story leadership and make no canonical decisions.

## 7. Keep Hybrid Architecture Small

The MVP needs meaningful task division but not model explosion.
Few, clearly defined helper roles are better than many diffuse specialized models.

---

# The Wave Logic in One Sentence

- **W0 = Contract**
- **W1 = Content**
- **W2 = Dynamic AI Core**
- **W3 = Playability**
- **W4 = Hardening and MVP Maturity**

---

# What Concretely Exists at the End of W4

Then exist:

- a real **God of Carnage content module**
- a **World Engine** that advances story states with AI support
- a controlled **AI story loop**
- a **hybrid AI layer** of SLM helper roles and story LLM
- a **playable UI**
- visible **diagnostic and validation logic**
- reproducible **session and delta logs**
- a first presentable **AI story MVP**
- a robust basis for additional modules following the same pattern

---

# Critical Priority

The most critical wave is **W2**.

There it is decided whether the system:

- becomes just a nicely packaged state machine,
- or truly gains an advanced, controlled AI story core.

Therefore:

> **W2 is not implemented as one block, but in clear sub-waves with hard gates.**

Additionally:

> **The hybrid architecture must be cut in W2 such that SLMs reduce costs, latency, and structural problems without damaging dramatic quality or engine authority.**
