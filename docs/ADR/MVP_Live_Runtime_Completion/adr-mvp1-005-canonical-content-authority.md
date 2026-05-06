# ADR-MVP1-005: Canonical Content Authority

**Status**: Accepted
**MVP**: 1 — Experience Identity and Session Start (enforced; also required by MVP 2)
**Date**: 2026-04-25

## Context

The `god_of_carnage_solo` ExperienceTemplate in `story_runtime_core/` owned role descriptions, NPC voice strings, room layouts, props, actions, and beats — story truth that belongs exclusively to the canonical content module at `content/modules/god_of_carnage/`. This created two competing authorities: the runtime template and the content YAML. Changes to character identity, NPC voice, or scene props required updates in two places, with no guarantee of consistency.

FIX-006 of the MVP1 audit cycle identified that the role IDs (`annette`, `alain`, `veronique`, `michel`) in the runtime template must derive from canonical content, not be maintained independently.

## Decision

1. **`content/modules/god_of_carnage/`** is the sole canonical content authority for God of Carnage story truth: character identities, relationships, scenes, escalation axes, props, beats, endings, and NPC voice intent.

2. **`god_of_carnage_solo` ExperienceTemplate** (in `story_runtime_core/`) is runtime scaffolding only — it provides the game-engine participation model (lobby seats, room graph, action menus). It does not author story truth.

3. **Runtime profile** (`world-engine/app/runtime/profiles.py`) resolves canonical actor IDs from `content/modules/god_of_carnage/characters.yaml` at runtime via `_resolve_goc_content()`, not from hardcoded constants.

4. **Role IDs** in the ExperienceTemplate must be a subset of character IDs in `characters.yaml`. This is enforced by `test_goc_solo_runtime_projection_is_derived_from_canonical_content`.

5. **`god_of_carnage_solo` runtime module** cannot own characters, rooms, scenes, relationships, or endings as story truth. `assert_profile_contains_no_story_truth()` enforces this for profile dicts.

## Affected Services/Files

- `content/modules/god_of_carnage/characters.yaml` — canonical authority for character IDs
- `world-engine/app/runtime/profiles.py` — `_resolve_goc_content()` reads characters.yaml, produces content hash
- `story_runtime_core/goc_solo_builtin_roles_rooms.py` — role IDs must match characters.yaml IDs
- `world-engine/tests/test_mvp1_experience_identity.py` — `TestStoryTruthBoundary` and `TestContentResolvedRoleMapping`

## Consequences

- Any change to canonical character IDs in `characters.yaml` must be reflected in the ExperienceTemplate role IDs
- Test `test_goc_solo_runtime_projection_is_derived_from_canonical_content` will fail if they drift
- The runtime profile produces a `content_hash` (SHA-256 of `characters.yaml`) in `build_actor_ownership()`, enabling drift detection
- MVP 2 can trust that `human_actor_id` and `npc_actor_ids` in the handoff trace back to canonical content

## Diagrams

**YAML in `content/modules/god_of_carnage/`** is sole story authority; the **solo ExperienceTemplate** is scaffolding only; resolver pulls IDs from **`characters.yaml`**.

```mermaid
flowchart TB
  Y[characters.yaml + module YAML]
  TPL[god_of_carnage_solo template]
  Y -->|subset IDs enforced by tests| TPL
  Y --> PROF[Runtime profile resolver]
  PROF --> HASH[content_hash drift detection]
```

## Alternatives Considered

- Keep role descriptions in the template: rejected — creates dual authority and drift risk
- Sync from canonical content at template build time (code generation): deferred as over-engineering for one module
- Validate at CI time only: rejected — runtime resolution is more robust than a separate CI check

## Validation Evidence

- `test_goc_solo_runtime_projection_is_derived_from_canonical_content` — PASS
- `test_profile_contains_no_story_truth` — PASS
- `test_runtime_module_contains_no_story_truth` — PASS
- `test_role_slug_map_uses_content_resolved_actor_ids` — PASS
- `test_build_actor_ownership_includes_content_hash` — PASS

## Related Findings

- FIX-006 (story truth boundary enforcement)
- FIX-007 (content-resolved role mapping)
- ADR-MVP1-001 (experience identity)
- ADR-MVP1-002 (runtime profile resolver)

## Tests Proving the Decision

- `test_goc_solo_runtime_projection_is_derived_from_canonical_content` in `world-engine/tests/test_mvp1_experience_identity.py`
- `test_role_slug_map_uses_content_resolved_actor_ids` in `world-engine/tests/test_mvp1_experience_identity.py`

## Operational Gate Impact

`tests/reports/MVP_Live_Runtime_Completion/MVP1_CAPABILITY_EVIDENCE.md` marks `canonical_content_authority` as `implemented` with concrete source anchors. The `mvp1-tests.yml` workflow job `mvp1-tooling-gate` verifies this ADR file exists before closing.
