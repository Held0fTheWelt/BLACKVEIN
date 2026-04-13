# Revised MVP Specification

## Goal

Build a first production-meaningful foundation MVP that:

1. compiles authored narrative source into immutable runtime packages
2. executes turns through a scene packet contract and engine validation
3. recovers gracefully from runtime validation failure in live play
4. extends research into structured, review-bound revision generation
5. exposes runtime, package, policy, revision, evaluation, and runtime-health control in the administration-tool
6. supports preview build, preview evaluation, promotion, history, and rollback
7. supports conflict-aware multi-operator revision review
8. makes runtime validation behavior explicit and configurable

## Product statement

The MVP creates a governed narrative pipeline:

**Authored source -> Draft workspace -> Compiled preview package -> Preview evaluation -> Manual promotion -> Active runtime package**

In parallel, it creates a governed improvement loop:

**Runtime observations + research -> Findings -> Revision candidates -> Conflict check -> Draft patch apply -> Preview rebuild -> Preview evaluation -> Approval -> Promotion**

And it creates a governed live-play recovery loop:

**Turn generation -> Validation -> Corrective retry with feedback -> Safe fallback -> Runtime health telemetry**

## Must-have outcomes

### Runtime foundation
- Compiled narrative package per module
- Active package pointer plus immutable package history
- Scene packet builder
- Policy resolver that produces effective policy
- Structured turn output contract aligned to runtime needs
- Output validator with explicit strategy selection
- Corrective retry path that passes actionable validation feedback back into generation
- Scene fallback content available for every playable scene
- Internal world-engine package reload/load-preview endpoints
- Preview session isolation from active runtime state

### Governance foundation
- Backend package registry and history log
- Revision candidate store
- Revision conflict detection
- Revision review state machine
- Draft preview apply path
- Preview package registry
- Evaluation run store
- Notification trigger and event pipeline
- Runtime health event persistence for retry/fallback spikes

### Administration-tool foundation
- Overview surface
- Runtime surface
- Runtime health surface
- Packages and history surface
- Policy preview surface
- Findings surface
- Revisions surface with conflict display
- Evaluations surface
- notifications and alerts for failed evaluations, urgent review items, and live fallback spikes

### Research suite foundation
- Package-aware analysis
- Structured revision candidate output
- Draft patch bundle generation
- Target localization down to content unit
- Expected impact metadata for evaluation routing
- Ability to propose fallback-content improvements and policy/fallback refinements when live runtime health indicates repeated degradation

## Out of scope
- full graphical authoring studio
- unrestricted prompt editing in admin
- autonomous direct publishing from research
- multi-judge evaluator fleets
- mandatory multi-module dependency graph
- fully adaptive player-personalization as first-class live feature

## Service responsibilities

### world-engine
- load approved packages
- load preview package for preview execution only
- build scene packets
- resolve effective policy
- validate model output
- generate corrective feedback when validation fails
- retry once or more within configured bounds
- produce safe fallback output when retries still fail
- commit only validated effects
- emit runtime health events

### backend
- persist packages, previews, revisions, evaluations, conflicts, workflow state, and runtime health metrics
- orchestrate preview build/promotion/rollback
- own package history log
- own revision workflow and notification orchestration
- expose admin APIs

### administration-tool
- present governance state and operator actions
- present runtime-health visibility and fallback diagnostics
- no authoritative mutation without backend approval APIs

### ai_stack
- compile narrative packages
- run preview evaluation and coverage tracking
- support research-to-revision workflows
- support delta-aware analysis for fallback-heavy scenes

### writers-room
- own draft workspace source edits
- accept structured patch bundles
- remain the authored-source boundary

## Live-play continuity requirement

The runtime must never leave the player with:
- a raw validation error
- an unhandled exception surface
- a permanently hung turn because the model output was rejected

At minimum, every turn must end in one of these outcomes:
- first-pass valid output
- corrected output after feedback-driven retry
- safe fallback output with zero illegal effects

## Preview isolation requirement

Preview sessions must be isolated from active runtime sessions.
A preview load may never replace or mutate the active package for live users.

Allowed implementation modes:
- dedicated preview process/container
- dedicated in-memory preview package loader and session namespace
- dedicated preview resolver keyed by preview session token

## Future dramatic-quality seams that must remain possible

The MVP must not block later introduction of:
- character emotional state continuity
- contradiction detection against canonical runtime state
- proactive narrative steering
- branch simulation against preview packages
- player affect detection and adaptive assistance
