# Source inventory

This inventory focuses on the **load-bearing artifacts directly read in content** during the post-repair re-audit, plus a few broader structural lanes that were inventoried and classified.

| Artifact | Classification(s) | Role | Current post-repair reading |
| --- | --- | --- | --- |
| README.md | canonical authority, experience-bearing material, architecture authority | Root package entrypoint and authority-lane summary. | Strongly improved; correctly routes to the active recomposed route. |
| docs/README.md | canonical authority, fragmented but important | Docs root entrypoint. | Partly stale; still names the older parent spine and older repair bundle as primary. |
| docs/start-here/README.md | experience-bearing material, canonical authority | Plain-language orientation and route chooser. | Aligned with the active route and properly subordinate to canon. |
| docs/MVPs/README.md | canonical authority | MVP route map and authority table. | Strong and aligned; clearly identifies the active recomposed route. |
| docs/MVPs/world_of_shadows_canonical_mvp/README.md | canonical authority, duplicate / near-duplicate, fragmented but important | Detailed canonical companion family entrypoint. | Mostly aligned but still uses wording that partly competes with the active route and still points to the older repair bundle. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/README.md | canonical authority | Active first-pass canonical reading spine. | Strong and currently the clearest package center. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/00_reading_order_and_authority_model.md | canonical authority, architecture authority | Explicit lane separation and anti-loss rule. | Strong; does the main anti-fragmentation work. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/02_authority_and_stage_continuity.md | canonical authority, architecture authority | Service ownership and stage chain. | Strong; aligns with code and technical docs. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/03_target_layers_and_world_model.md | canonical authority, historical but still truth-bearing | Carry-forward of broader WoS target layers. | Strong as enduring-target preservation; not overclaimed as live proof. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/04_surface_families_and_ui_ux.md | canonical authority, experience-bearing material | Player/operator/authoring/support surface model. | Strong and honest; still depends on broader proof follow-up. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/05_control_plane_ai_stack_and_governed_revision.md | canonical authority, architecture authority | Governed AI/control-plane ecosystem. | Strongly recomposed; bounded and subordinate to commit authority. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/06_implementation_and_proof_posture.md | canonical authority, proof/test evidence | Current proof ladder and carried-forward evidence posture. | Improved and mostly honest; still not normalized with every docs index surface. |
| docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/07_open_tensions_and_follow_up_obligations.md | canonical authority, proof/test evidence | Explicit named tensions. | Strong and honesty-preserving. |
| docs/MVPs/MVP_VSL_And_GoC_Contracts/* | canonical authority, architecture authority, experience-bearing material | Normative GoC contract lane. | Strong; still the primary normative home for GoC behavior. |
| content/modules/god_of_carnage/module.yaml | canonical authority, experience-bearing material | Authored-source anchor for the active slice. | Strong and correctly central. |
| docs/CANONICAL_TURN_CONTRACT_GOC.md / docs/VERTICAL_SLICE_CONTRACT_GOC.md / docs/GATE_SCORING_POLICY_GOC.md | duplicate / near-duplicate, fragmented but important | Root-level compatibility mirrors for GoC contracts. | Now properly bounded as mirrors; still physically duplicative by design. |
| docs/technical/runtime/runtime-authority-and-state-flow.md | architecture authority | Technical authority and state-flow explanation. | Aligned with active canon. |
| docs/technical/content/writers-room-and-publishing-flow.md | architecture authority, experience-bearing material | Authoring/review/publish continuity. | Aligned and still load-bearing. |
| docs/user/runtime-interactions-player-visible.md | experience-bearing material | Player-visible runtime/support expectations. | Aligned with the repaired shell posture. |
| docs/user/god-of-carnage-player-guide.md | experience-bearing material | Player-facing GoC expectations. | Aligned and helpfully bounded. |
| frontend/templates/session_shell.html | implementation evidence, experience-bearing material | Player shell UI and support-surface disclosure. | Materially improved; support obligations are now explicit. |
| frontend/app/routes.py | implementation evidence | Player shell observation, recovery, and support-surface status logic. | Aligned with the active UI/UX truth posture. |
| frontend/tests/test_routes_extended.py | proof/test evidence | Player-route regression corpus. | Valuable, but fresh replay was blocked here due missing Flask. |
| administration-tool/templates/manage/inspector_workbench.html | implementation evidence, experience-bearing material | Operator inspection surface. | Aligned; clearly operator-facing and read-only. |
| backend/app/api/v1/writers_room_routes.py | implementation evidence | Authoring/review API surface. | Aligned with canonical writers-room governance posture. |
| backend/app/api/v1/ai_stack_governance_routes.py | implementation evidence | Admin/governance diagnostic API surface. | Aligned and bounded. |
| world-engine/app/runtime/manager.py | implementation evidence | Published-template sync and run lifecycle manager. | Strong; supports publish/feed → runtime activation continuity. |
| world-engine/app/story_runtime/manager.py | implementation evidence | Authoritative turn execution and shell readout context. | Strong and load-bearing. |
| world-engine/tests/test_backend_content_feed.py | proof/test evidence | Backend feed / remote template path tests. | Freshly rerun: passed. |
| world-engine/tests/test_story_runtime_shell_readout.py | proof/test evidence | Shell readout / social-emotional projection tests. | Freshly rerun: passed. |
| world-engine/tests/test_runtime_manager.py | proof/test evidence | Runtime manager behavior tests. | Freshly rerun: passed. |
| ai_stack/tests/test_mcp_canonical_surface.py | proof/test evidence | Bounded AI-stack/MCP surface proof. | Freshly rerun: passed. |
| docs/audit/world_of_shadows_canonical_mvp_repair_implementation_2026-04-21/* | proof/test evidence, fragmented but important | Current repair-implementation evidence bundle. | Important and newer, but not yet consistently routed as the active evidence lane. |
| docs/audit/README.md | fragmented but important, duplicate / near-duplicate | Audit lane entrypoint. | Still stale; routes to the older repair bundle. |
| mvp/docs/* | historical but still truth-bearing, fragmented but important | Broader WoS target lineage and anti-loss corpus. | Still truth-bearing and necessary for carry-forward of broader families. |
| repo/README.md and repo/MIRROR_LANE_NOTICE.md | duplicate / near-duplicate, fragmented but important | Embedded packaged mirror lane. | Much better bounded; still a physical duplication lane. |
| 'fy'-suites/ | likely ballast, implementation evidence | Governed implementation tooling family, not product canon. | Correctly outside WoS product canon, though still visually noisy in repo structure. |
