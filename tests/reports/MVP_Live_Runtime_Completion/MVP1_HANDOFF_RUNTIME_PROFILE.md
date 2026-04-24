# MVP 1 Handoff — Runtime Profile and Role Ownership

**For**: MVP 2 (Runtime State, Actor Lanes, Content Boundary)
**Source**: MVP 1 (Experience Identity and Session Start)
**Date**: 2026-04-24

## Normalized Runtime Profile

```json
{
  "contract": "runtime_profile.v1",
  "runtime_profile_id": "god_of_carnage_solo",
  "content_module_id": "god_of_carnage",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "requires_selected_player_role": true,
  "selectable_player_roles": [
    {"role_slug": "annette", "canonical_actor_id": "annette", "display_name": "Annette"},
    {"role_slug": "alain", "canonical_actor_id": "alain", "display_name": "Alain"}
  ],
  "forbidden_story_truth_fields": ["characters", "roles", "rooms", "props", "beats", "scenes", "relationships", "endings"],
  "profile_version": "goc-solo.v1"
}
```

**Source**: `world-engine/app/runtime/profiles.py:resolve_runtime_profile`

## Selected Role Contract

The `selected_player_role` field is required when `runtime_profile_id=god_of_carnage_solo` is sent.

| Field | Value |
|---|---|
| `selected_player_role` | `"annette"` or `"alain"` |
| Validation | `validate_selected_player_role()` in `profiles.py` |
| Error if missing | `selected_player_role_required` |
| Error if invalid | `invalid_selected_player_role` |
| Error if visitor | `invalid_visitor_runtime_reference` |

## Role Slug to Canonical Actor Mapping

```json
{
  "contract": "role_slug_actor_id_map.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "role_slug_actor_id_map": {
    "annette": "annette",
    "alain": "alain"
  },
  "source": "canonical_content.characters",
  "resolved_from_content": true,
  "content_source": "content/modules/god_of_carnage/characters.yaml"
}
```

**Note**: The content module `characters.yaml` uses IDs `annette`, `alain`, `veronique`, `michel` (without `_reille`/`_houllie` suffixes). The `canonical_actor_id` in the runtime profile maps to these exact content IDs.

**Source**: `content/modules/god_of_carnage/characters.yaml`

## Human Actor Ownership (Annette selected)

```json
{
  "contract": "create_run_response.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "selected_player_role": "annette",
  "human_actor_id": "annette",
  "npc_actor_ids": ["alain", "veronique", "michel"],
  "actor_lanes": {
    "annette": "human",
    "alain": "npc",
    "veronique": "npc",
    "michel": "npc"
  },
  "visitor_present": false
}
```

## Human Actor Ownership (Alain selected)

```json
{
  "contract": "create_run_response.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "runtime_module_id": "solo_story_runtime",
  "runtime_mode": "solo_story",
  "selected_player_role": "alain",
  "human_actor_id": "alain",
  "npc_actor_ids": ["annette", "veronique", "michel"],
  "actor_lanes": {
    "alain": "human",
    "annette": "npc",
    "veronique": "npc",
    "michel": "npc"
  },
  "visitor_present": false
}
```

## Visitor Removal Proof

- `visitor` is no longer a role in `story_runtime_core/goc_solo_builtin_roles_rooms.py`
- `validate_selected_player_role("visitor", profile)` raises `invalid_visitor_runtime_reference`
- `build_actor_ownership("visitor", profile)` raises `invalid_visitor_runtime_reference`
- Test proof: `test_visitor_absent_from_prompts_responders_lobby` in `world-engine/tests/test_mvp1_experience_identity.py` (PASS)
- Test proof: `test_visitor_rejected_as_selected_player_role` (PASS)
- Test proof: `test_visitor_rejected_from_build_actor_ownership` (PASS)
- Test proof: `test_visitor_not_in_npc_actor_ids` (PASS)

## Canonical Content Proof

- `god_of_carnage_solo` does NOT appear under `content/modules/` — it is runtime-profile only
- `god_of_carnage` IS the canonical content module at `content/modules/god_of_carnage/`
- Test proof: `test_goc_solo_not_loadable_as_content_module` (PASS)
- Test proof: `test_profile_contains_no_story_truth` (PASS)
- Test proof: `test_runtime_module_contains_no_story_truth` (PASS)

## god_of_carnage_solo is Runtime Profile Only

- Template ID `god_of_carnage_solo` is registered in `story_runtime_core/goc_solo_builtin_template.py` as an `ExperienceTemplate` (runtime configuration), not a content module
- It does not own characters, scenes, relationships, or any story truth fields
- The runtime profile resolver at `world-engine/app/runtime/profiles.py:resolve_runtime_profile` treats it as profile-only and binds it to `content_module_id="god_of_carnage"`

## Implementation Source Anchors

| Capability | Source File | Symbol |
|---|---|---|
| Runtime profile resolver | `world-engine/app/runtime/profiles.py` | `resolve_runtime_profile()` |
| Role validation | `world-engine/app/runtime/profiles.py` | `validate_selected_player_role()` |
| Actor ownership | `world-engine/app/runtime/profiles.py` | `build_actor_ownership()` |
| Story truth guard | `world-engine/app/runtime/profiles.py` | `assert_profile_contains_no_story_truth()` |
| HTTP profile integration | `world-engine/app/api/http.py` | `create_run()` handler |
| Template role configuration | `story_runtime_core/goc_solo_builtin_roles_rooms.py` | `goc_solo_role_templates()` |
| Preferred role in bootstrap | `world-engine/app/runtime/manager.py` | `_bootstrap_instance()` |
| Backend profile forwarding | `backend/app/services/game_service.py` | `create_run()` |
| Backend route forwarding | `backend/app/api/v1/game_routes.py` | `game_create_run()`, `game_player_session_create()` |

## What MVP 2 Can Assume

1. `runtime_profile_id=god_of_carnage_solo` is always bound to `content_module_id=god_of_carnage`
2. `selected_player_role` is always `"annette"` or `"alain"` — never `"visitor"` or any other value
3. `human_actor_id` is the canonical actor ID of the selected role (same as role_slug for GoC content)
4. `npc_actor_ids` contains all other three canonical GoC actors (no visitor)
5. `actor_lanes` is a dict of actor_id → "human"|"npc"
6. `visitor_present=False` is always guaranteed
7. The `annette` and `alain` roles in the ExperienceTemplate are both `HUMAN+can_join`, starting in `hallway`
8. The runtime profile resolver validates before any instance is created
9. Profile contains no story truth (characters, scenes, etc.)
