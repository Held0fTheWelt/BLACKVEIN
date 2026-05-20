# Delagecy Removed Entry Semantic Audit

Date: 2026-05-20  
Scope: individual recheck of the 69 registry entries that were marked `removed` in `active_surface_report_after_wave_next_4.md`  
Primary evidence: Delagecy reports and registry, plus targeted source/test inspection

## Applied Rules

- Compatibility with earlier repo/product versions is not active compatibility and must be removed.
- Compatibility for active alternative usage, such as provider, adapter, or supported wire-form variation, may be retained only as canonicalized active behavior.
- If behavior remains active and only the name/wording was wrong, the entry is `canonicalized_active_behavior`, not `removed`.
- New legacy findings are registered and reported before removal. Ambiguous breakage risk is discussed before removal.
- Removal means implementation, tests, docs, generated/config text, and UI/API residue are removed together where that surface exists.

## Result

The 69 `removed` entries were reclassified individually:

| Final status | Count | Meaning |
| --- | ---: | --- |
| `removed` | 26 | Earlier-version compatibility, obsolete acceptance, old input aliases, old reason/output labels, or generated text residue were actually removed. |
| `canonicalized_active_behavior` | 43 | Behavior remains current; old legacy wording/name was canonicalized and the registry no longer counts it as true removal. |

Additional stale approved rows found during the same audit were corrected:

| IDs | Final status | Reason |
| --- | --- | --- |
| `DLG-555`, `DLG-1046`-`DLG-1047`, `DLG-1049`-`DLG-1052` | `canonicalized_active_behavior` | Active `npc_initiatives` and MCP permission metadata remained current; only stale internal names were canonicalized. |
| `DLG-557`, `DLG-899`, `DLG-1084` | `removed` | Old `initiatives` compatibility fallback and ADR claims of backward compatibility were removed. |

An adjacent W5 player-view residue was removed while preserving the current fallback behavior:

| Surface | Removed old terms | Current surface |
| --- | --- | --- |
| W5 player-view diagnostics and backend shell payload | `legacy_current_room`, `current_room_legacy_value`, `fallback_current_room_id` | `fallback_current_room`, `current_room_fallback_value` |

## Individual Decisions

| ID | Final status | Semantic decision | Evidence/action |
| --- | --- | --- | --- |
| `DLG-034` | `removed` | Old normal-turn false default was earlier-version compatibility. | `AdapterRequest.request_role_structured_output` now defaults to role-structured output. |
| `DLG-035` | `removed` | Mock adapter no longer returns the old unstructured normal-turn branch. | Normal-turn mock payload is AIRoleContract-shaped. |
| `DLG-036` | `removed` | Adapter response documentation no longer advertises old mock data. | Tests expect interpreter/director/responder keys. |
| `DLG-037` | `removed` | Old fallback branch was removed, not renamed. | Passing `request_role_structured_output=False` no longer re-enables old payload. |
| `DLG-038` | `canonicalized_active_behavior` | `role_aware_decision=None` is still active for recovery/error/no-role records. | Logging keeps role fields `None` for current no-role payloads. |
| `DLG-041` | `canonicalized_active_behavior` | LangGraph routing remains an active non-authoritative alternative surface. | Operator truth calls it non-authoritative for Task 2A HTTP paths. |
| `DLG-048` | `canonicalized_active_behavior` | Translation/adapter support layers remain current when bounded. | Routing authority describes non-competing support layers. |
| `DLG-049` | `canonicalized_active_behavior` | Inventory report classifiers remain active. | Wording changed to adapter-instance classifiers. |
| `DLG-050` | `canonicalized_active_behavior` | Story runtime core routing policy remains active for LangGraph. | Component id canonicalized to `story_runtime_core_routing_policy_choose`. |
| `DLG-051` | `canonicalized_active_behavior` | `RoutingPolicy.choose()` remains active outside canonical Task 2A HTTP routing. | Registry classifies it as adapter layer with no canonical Task 2A surface. |
| `DLG-230` | `removed` | Test no longer expects false flag to return old payload. | Test asserts false flag still returns role contract. |
| `DLG-231` | `removed` | Old payload assertion was removed. | Test now verifies role-structured keys. |
| `DLG-232` | `removed` | Test wording no longer treats old format as acceptable. | Role payload recognition is canonical. |
| `DLG-233` | `removed` | Old top-level payload keys are rejected. | Test asserts absent old keys. |
| `DLG-234` | `removed` | `detected_triggers` old top-level normal-turn payload is not accepted. | Test asserts key absence. |
| `DLG-235` | `removed` | `proposed_deltas` old top-level normal-turn payload is not accepted. | Test asserts key absence. |
| `DLG-236` | `canonicalized_active_behavior` | Decision logging without role payload remains current. | Test name/wording now says unstructured parsing, not legacy. |
| `DLG-237` | `canonicalized_active_behavior` | `role_aware_decision=None` remains current for no-role records. | Test comment canonicalized. |
| `DLG-238` | `canonicalized_active_behavior` | Empty interpreter diagnostics are current for no-role records. | Assertion remains with canonical wording. |
| `DLG-239` | `canonicalized_active_behavior` | Empty director diagnostics are current for no-role records. | Assertion remains with canonical wording. |
| `DLG-240` | `canonicalized_active_behavior` | Empty responder diagnostics are current for no-role records. | Assertion remains with canonical wording. |
| `DLG-241` | `canonicalized_active_behavior` | ParsedAIDecision-only logging still works for current no-role paths. | Test wording no longer claims legacy. |
| `DLG-242` | `canonicalized_active_behavior` | No-role path remains current. | Comment canonicalized. |
| `DLG-243` | `canonicalized_active_behavior` | No-role logs still have no role fields. | Comment canonicalized. |
| `DLG-250` | `canonicalized_active_behavior` | Full-deepcopy comparison is a current reference oracle. | Test uses reference terminology. |
| `DLG-251` | `canonicalized_active_behavior` | Reference helper remains active for parity testing. | Helper renamed to `_reference_preview_with_full_deepcopy`. |
| `DLG-252` | `canonicalized_active_behavior` | Guard outcome parity remains active. | Assertion compares result to reference. |
| `DLG-253` | `canonicalized_active_behavior` | Accepted-delta parity remains active. | Assertion compares result to reference. |
| `DLG-254` | `canonicalized_active_behavior` | Rejected-delta parity remains active. | Assertion compares result to reference. |
| `DLG-255` | `canonicalized_active_behavior` | Accepted target-path parity remains active. | Assertion compares result to reference. |
| `DLG-256` | `canonicalized_active_behavior` | Rejected target-path parity remains active. | Assertion compares result to reference. |
| `DLG-463` | `canonicalized_active_behavior` | `narrative_response` is still an active alternate/current runtime output field. | LangChain bridge now documents it as alternate caller surface. |
| `DLG-527` | `canonicalized_active_behavior` | MCP permission derivation remains active metadata. | Internal descriptor field is now `permission_scope`. |
| `DLG-528` | `canonicalized_active_behavior` | Permission derivation helper remains active. | Helper is now `_derive_permission_scope`. |
| `DLG-529` | `canonicalized_active_behavior` | Descriptor construction still derives permission metadata. | Constructor uses `permission_scope`. |
| `DLG-560` | `removed` | Old `pressure_shift` input alias was previous contract residue. | Planner now reads only `social_pressure_shift`. |
| `DLG-561` | `canonicalized_active_behavior` | Social pressure signal logic remains active. | Variable naming changed from old `legacy_shift` concept. |
| `DLG-562` | `removed` | Old `legacy_social_pressure_shift` reason code was removed. | Reason code is now `social_pressure_shift`. |
| `DLG-563` | `canonicalized_active_behavior` | Social pressure branch remains current. | Branch uses canonical `pressure_shift` local derived from `social_pressure_shift`. |
| `DLG-564` | `canonicalized_active_behavior` | Social pressure value emission remains current. | Emitted value is canonical `social_pressure_shift`. |
| `DLG-598` | `canonicalized_active_behavior` | MCP permission helper tests remain active. | Imports use `_derive_permission_scope`. |
| `DLG-599` | `canonicalized_active_behavior` | MCP permission helper test section remains active. | Test wording canonicalized. |
| `DLG-600` | `canonicalized_active_behavior` | Read permission derivation remains active. | Test calls `_derive_permission_scope`. |
| `DLG-601` | `canonicalized_active_behavior` | Preview permission derivation remains active. | Test calls `_derive_permission_scope`. |
| `DLG-602` | `canonicalized_active_behavior` | Write permission derivation remains active. | Test calls `_derive_permission_scope`. |
| `DLG-604` | `canonicalized_active_behavior` | Narrative runtime test still covers current `npc_initiatives`. | Test reads `npc_initiatives` with `initiative_rows`. |
| `DLG-605` | `canonicalized_active_behavior` | Actor-id extraction remains active test behavior. | Variable naming canonicalized. |
| `DLG-606` | `canonicalized_active_behavior` | Initiative row loop remains current. | Loop uses canonical rows. |
| `DLG-607` | `canonicalized_active_behavior` | Remaining initiative count remains active. | Count uses canonical rows. |
| `DLG-608` | `canonicalized_active_behavior` | Initiative actor set remains active. | Set uses canonical rows. |
| `DLG-609` | `removed` | Test module no longer advertises old compatibility adapters. | Docstring says input adapters. |
| `DLG-610` | `canonicalized_active_behavior` | NPC contract test row fixture remains active. | Variable naming canonicalized. |
| `DLG-611` | `removed` | Old `initiatives` acceptance was removed. | Test now verifies `normalize_npc_agency_plan({"initiatives": ...}) is None`. |
| `DLG-612` | `removed` | Old alias actor-id acceptance assertion was removed. | Test no longer maps old alias rows to normalized rows. |
| `DLG-613` | `removed` | Old `initiative_type` alias acceptance assertion was removed. | Contract uses `intent`; old alias is not consumed. |
| `DLG-614` | `removed` | Old alias resolved-state acceptance assertion was removed. | Old alias acceptance test replaced by rejection test. |
| `DLG-1015` | `canonicalized_active_behavior` | Current `npc_initiatives` read remains active. | Variable name is now `initiative_rows`. |
| `DLG-1016` | `canonicalized_active_behavior` | Empty canonical row handling remains active. | Logic uses canonical row variable. |
| `DLG-1017` | `removed` | Old `initiatives` input fallback was removed. | Contract no longer reads `raw_plan.get("initiatives")`. |
| `DLG-1018` | `canonicalized_active_behavior` | Raw row actor derivation remains active. | Uses canonical row variable. |
| `DLG-1019` | `canonicalized_active_behavior` | NPC initiative loop remains active. | Loop iterates canonical row source. |
| `DLG-1096` | `removed` | Generated recommendation text no longer claims compatibility-only routing. | Snapshot text uses non-authoritative routing wording. |
| `DLG-1097` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |
| `DLG-1098` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |
| `DLG-1099` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |
| `DLG-1100` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |
| `DLG-1101` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |
| `DLG-1102` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |
| `DLG-1103` | `removed` | Generated recommendation text residue removed. | Snapshot text canonicalized. |

## Verification

- `PYTHONPATH="'fy'-suites" python3 -m pytest "'fy'-suites/delagecy/tools/tests" -q`
- `PYTHONPATH=backend python3 -m pytest backend/tests/runtime/test_ai_adapter.py -q`
- `PYTHONPATH=. python3 -m pytest ai_stack/tests/test_npc_agency_contracts.py ai_stack/tests/test_narrative_runtime_agent.py ai_stack/tests/test_actor_lane_hydration.py ai_stack/tests/test_npc_agency_planner.py ai_stack/tests/test_social_pressure_engine.py -q`
- `PYTHONPATH=. python3 -m pytest tools/mcp_server/tests/test_mcp_runtime_safe_session_surface.py tools/mcp_server/tests/test_tools_registry_aliases.py -q`
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python3 -m pytest world-engine/tests/test_mvp3_narrative_agent_orchestration.py -q`
- `PYTHONPATH=/mnt/d/WorldOfShadows/world-engine:/mnt/d/WorldOfShadows python3 -m pytest world-engine/tests/test_story_runtime_w5_player_view.py -q`
- `PYTHONPATH=backend python3 -m pytest backend/tests/test_w5_player_shell_payload.py -q`

