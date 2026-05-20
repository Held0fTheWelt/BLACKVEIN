# PR-3A — NPC mundane action bridge

**Date:** 2026-05-20  
**Module:** `ai_stack/npc_mundane_action_bridge.py`

## Decision

Actor symmetry Phase 1: delegate NPC mundane classification to `resolve_player_action` with `actor_lane=npc` and `acting_actor_id`. No verb/room whitelist in the bridge.

## Consumers

Future: Director tick NPC action composer (ADR-0059) should call `resolve_npc_mundane_action` instead of duplicating resolution.

## Tests

`ai_stack/tests/test_npc_mundane_action_bridge.py`
