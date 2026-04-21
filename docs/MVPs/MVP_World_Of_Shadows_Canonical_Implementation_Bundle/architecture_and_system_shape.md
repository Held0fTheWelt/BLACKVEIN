# Architecture and System Shape

## Authority Model

- Authored source is created and reviewed in authoring/governance surfaces.
- Published artifacts are the activation boundary for runtime.
- Runtime truth is owned by execution services, then projected to user/operator surfaces.

Canonical source authority for the slice is the YAML module tree under `content/modules/god_of_carnage/`. Builtins and writers-room artifacts are secondary and must not silently override YAML truth.

## Core Service Roles

- `world-engine`: authoritative runtime lifecycle and turn execution
- `backend`: publish/governance APIs, session integration, support services
- `frontend`: player-visible shell and interaction surfaces
- `administration-tool`: operator and diagnostics surfaces
- `ai_stack` and shared runtime modules: bounded proposal support, retrieval, orchestration

## Turn Seam Contract

The MVP turn path must keep the following semantic seams explicit:

1. Proposal seam (candidate dramatic output only)
2. Validation seam (policy/rule outcome)
3. Commit seam (only place where dramatic truth is committed)
4. Visible render seam (player-visible projection aligned with committed truth)

No player-visible factual claim may bypass committed result boundaries.

## Stage Continuity Contract

1. Authored source preparation
2. Review and validation gates
3. Publish and activation
4. Runtime session birth and execution
5. Player-visible interaction loop
6. Operator diagnosis and corrective governance

This chain is mandatory for drift control. Missing stage visibility is treated as a governance defect.

## Data and Contract Surfaces

- Content authority and module activation contracts
- Session/runtime state contracts
- API and MCP integration surfaces
- Auditability, evidence, and governance references

## Target Runtime Direction (Preserved Intent)

- Layered runtime evolution remains a valid target direction
- Current MVP implementation must stay honest about what is live versus target-only
- Architecture records must preserve boundaries between proven behavior and future extension

## Runtime Node Shape (Current Baseline)

The runtime baseline includes a staged graph path across interpretation, retrieval, scene assessment, dramatic parameter selection, model invocation, proposal normalization, validation, commit, visible rendering, and packaging/diagnostics. Future changes must extend this shape without creating parallel truth surfaces.
