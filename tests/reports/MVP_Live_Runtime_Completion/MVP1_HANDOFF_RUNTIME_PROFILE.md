# MVP 1 Handoff Artifact: Normalized Runtime Profile & Role Mapping

**Date**: 2026-04-29  
**From**: MVP 1 — Experience Identity and Session Start  
**To**: MVP 2 — Runtime State, Actor Lanes, Content Boundary  
**Status**: Ready for MVP 2 consumption

---

## Normalized RuntimeProfile Contract

This is the runtime profile that MVP 1 produces for MVP 2 to consume.

```json
{
  "contract": "runtime_profile.v1",
  "runtime_profile_id": "god_of_carnage_solo",
  "content_module_id": "god_of_carnage",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "requires_selected_player_role": true,
  "selectable_player_roles": [
    {
      "role_slug": "annette",
      "canonical_actor_id": "annette_reille",
      "display_name": "Annette"
    },
    {
      "role_slug": "alain",
      "canonical_actor_id": "alain_reille",
      "display_name": "Alain"
    }
  ],
  "forbidden_story_truth_fields": [
    "characters",
    "roles",
    "rooms",
    "props",
    "beats",
    "scenes",
    "relationships",
    "endings"
  ],
  "profile_version": "goc-solo.v1"
}
```

**Source**: `world-engine/app/runtime/profiles.py::resolve_runtime_profile()`

---

## RoleSlugActorIdMap Contract

The canonical actor mapping resolved from `god_of_carnage` content module.

```json
{
  "contract": "role_slug_actor_id_map.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "role_slug_actor_id_map": {
    "annette": "annette_reille",
    "alain": "alain_reille"
  },
  "source": "canonical_content.characters",
  "resolved_from_content": true,
  "content_hash": "sha256:god_of_carnage_v1"
}
```

**Source**: `world-engine/app/runtime/profiles.py::_build_selectable_roles()`, populated from `content/modules/god_of_carnage/characters.yaml`

---

## CreateRunRequest Contract (MVP 1 → MVP 2)

What MVP 1 accepts from the player/frontend:

```json
{
  "contract": "create_run_request.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "selected_player_role": "annette"
}
```

**Source**: `world-engine/app/api/http.py::CreateRunRequest`

---

## CreateRunResponse Contract (MVP 1 → MVP 2)

What MVP 1 produces for MVP 2 to validate and use:

### Annette Selected (Human Player)

```json
{
  "contract": "create_run_response.v1",
  "run_id": "run_abc123",
  "story_session_id": "session_abc123",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "selected_player_role": "annette",
  "human_actor_id": "annette_reille",
  "npc_actor_ids": [
    "alain_reille",
    "veronique_houllie",
    "michel_houllie"
  ],
  "actor_lanes": {
    "annette_reille": "human",
    "alain_reille": "npc",
    "veronique_houllie": "npc",
    "michel_houllie": "npc"
  },
  "visitor_present": false
}
```

### Alain Selected (Human Player)

```json
{
  "contract": "create_run_response.v1",
  "run_id": "run_def456",
  "story_session_id": "session_def456",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "selected_player_role": "alain",
  "human_actor_id": "alain_reille",
  "npc_actor_ids": [
    "annette_reille",
    "veronique_houllie",
    "michel_houllie"
  ],
  "actor_lanes": {
    "alain_reille": "human",
    "annette_reille": "npc",
    "veronique_houllie": "npc",
    "michel_houllie": "npc"
  },
  "visitor_present": false
}
```

**Source**: `world-engine/app/runtime/profiles.py::build_actor_ownership()` and `world-engine/app/runtime/manager.py::_bootstrap_instance()`

---

## Key Handoff Guarantees

✅ **Runtime Profile is profile-only** — contains no story truth (no beats, scenes, props, characters)  
✅ **Content module is canonical** — `god_of_carnage` owns all story truth  
✅ **Role selection is mandatory** — `selected_player_role` is required before session creation  
✅ **Visitor is removed** — `visitor_present=false` always, visitor never in roles or npc_actor_ids  
✅ **Actor lanes are seeded** — `human_actor_id`, `npc_actor_ids`, `actor_lanes` ready for MVP 2 validation  
✅ **Contracts are structured** — all CreateRunResponse fields are present and typed  

---

## What MVP 2 Must Validate

MVP 2 receives this handoff and must:

1. **Actor-Lane Enforcement** — validate that `human_actor_id` actor output is never controlled by AI (ADR-004)
2. **Canonical Content Authority** — validate that story truth comes only from `content_module_id`, never from profile (ADR-005)
3. **State Delta Validation** — validate that mutations respect actor lanes and role assignment
4. **NPC Autonomy** — validate that NPCs in `npc_actor_ids` have independent agency

---

## Proof of MVP 1 Stop Condition

1. ✅ Annette and Alain runs created through real live route (tested: `test_valid_annette_start`, `test_valid_alain_start`)
2. ✅ Missing/invalid roles and visitor rejected with contract errors (tested: `test_session_creation_*`, `test_visitor_*`)
3. ✅ `god_of_carnage_solo` cannot be loaded as content (tested: `test_goc_solo_not_loadable_as_content_module`)
4. ✅ Capability evidence uses real anchors (documented in MVP1_SOURCE_LOCATOR.md)
5. ✅ MVP 1 tests run through `tests/run_tests.py` and included in workflows
6. ✅ Operational evidence written (MVP1_OPERATIONAL_EVIDENCE.md)
7. ✅ Handoff artifact exists (this document)

---

## Test Evidence

All MVP 1 handoff contracts verified by:

- `world-engine/tests/test_mvp1_experience_identity.py::TestValidStart::test_valid_annette_start` — PASS
- `world-engine/tests/test_mvp1_experience_identity.py::TestValidStart::test_valid_alain_start` — PASS
- `world-engine/tests/test_mvp1_experience_identity.py::TestValidStart::test_alain_human_role_exists_in_template` — PASS
- `world-engine/tests/test_mvp1_experience_identity.py::TestVisitorRemoval::test_visitor_not_in_npc_actor_ids` — PASS

---

## Ready for MVP 2

This handoff is **complete and ready** for MVP 2 implementation.  
MVP 2 will consume:
- Normalized `RuntimeProfile`
- `RoleSlugActorIdMap`
- `CreateRunResponse` with actor lanes seeded
- `visitor_present=false` guarantee
