# MVP 1 Capability Evidence Report

```json
{
  "contract": "capability_evidence_report.v1",
  "content_module_id": "god_of_carnage",
  "runtime_profile_id": "god_of_carnage_solo",
  "generated": "2026-04-24",
  "mvp": "1",
  "capabilities": [
    {
      "capability": "runtime_profile_resolution",
      "status": "implemented",
      "source_anchors": [
        "world-engine/app/runtime/profiles.py:resolve_runtime_profile",
        "world-engine/app/runtime/profiles.py:RuntimeProfile",
        "world-engine/app/api/http.py:create_run"
      ],
      "tests": [
        "test_runtime_profile_resolver_success",
        "test_create_run_missing_runtime_profile_returns_contract_error",
        "test_unknown_runtime_profile_rejected"
      ]
    },
    {
      "capability": "role_selection",
      "status": "implemented",
      "source_anchors": [
        "world-engine/app/runtime/profiles.py:validate_selected_player_role",
        "world-engine/app/runtime/manager.py:_bootstrap_instance",
        "backend/app/api/v1/game_routes.py:game_create_run"
      ],
      "tests": [
        "test_valid_annette_start",
        "test_valid_alain_start",
        "test_session_creation_without_selected_player_role_fails",
        "test_session_creation_invalid_role_fails",
        "test_role_slug_must_resolve_to_canonical_actor"
      ]
    },
    {
      "capability": "visitor_removal",
      "status": "implemented",
      "source_anchors": [
        "story_runtime_core/goc_solo_builtin_roles_rooms.py:goc_solo_role_templates",
        "world-engine/app/runtime/profiles.py:validate_selected_player_role",
        "world-engine/app/runtime/profiles.py:build_actor_ownership"
      ],
      "tests": [
        "test_visitor_absent_from_prompts_responders_lobby",
        "test_visitor_rejected_as_selected_player_role",
        "test_visitor_rejected_from_build_actor_ownership",
        "test_visitor_not_in_npc_actor_ids"
      ]
    },
    {
      "capability": "canonical_content_authority",
      "status": "implemented",
      "source_anchors": [
        "content/modules/god_of_carnage/module.yaml",
        "world-engine/app/runtime/profiles.py:assert_profile_contains_no_story_truth",
        "story_runtime_core/goc_solo_builtin_template.py:build_god_of_carnage_solo"
      ],
      "tests": [
        "test_goc_solo_not_loadable_as_content_module",
        "test_profile_contains_no_story_truth",
        "test_runtime_module_contains_no_story_truth",
        "test_profile_story_truth_fields_are_forbidden"
      ]
    },
    {
      "capability": "actor_ownership_handoff",
      "status": "implemented",
      "source_anchors": [
        "world-engine/app/runtime/profiles.py:build_actor_ownership",
        "world-engine/app/api/http.py:create_run"
      ],
      "tests": [
        "test_valid_annette_start",
        "test_valid_alain_start"
      ]
    },
    {
      "capability": "live_dramatic_scene_simulator",
      "status": "missing",
      "source_anchors": [],
      "tests": [],
      "notes": "LDSS is out of scope for MVP1. Will be implemented in MVP3."
    },
    {
      "capability": "narrative_gov_dashboard",
      "status": "missing",
      "source_anchors": [],
      "tests": [],
      "notes": "Narrative Gov admin surface is out of scope for MVP1. Will be implemented in MVP4."
    },
    {
      "capability": "langfuse_trace_export",
      "status": "missing",
      "source_anchors": [],
      "tests": [],
      "notes": "Langfuse real-trace export is out of scope for MVP1. Will be implemented in MVP4."
    },
    {
      "capability": "frontend_staged_rendering",
      "status": "missing",
      "source_anchors": [],
      "tests": [],
      "notes": "Staged frontend rendering is out of scope for MVP1. Will be implemented in MVP5."
    }
  ]
}
```

## Summary

| Capability | Status |
|---|---|
| Runtime profile resolution | implemented |
| Role selection (annette/alain) | implemented |
| Visitor removal | implemented |
| Canonical content authority | implemented |
| Actor ownership handoff | implemented |
| Live dramatic scene simulator | missing (MVP3) |
| Narrative Gov dashboard | missing (MVP4) |
| Langfuse trace export | missing (MVP4) |
| Frontend staged rendering | missing (MVP5) |

Implemented capabilities have concrete source anchors. Missing capabilities are honestly reported as `missing` — not as static success.
