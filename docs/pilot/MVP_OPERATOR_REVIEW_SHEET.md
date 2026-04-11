# MVP operator review sheet (WOS_VSL pilot)

Use this for **Experiment 2 — Operator failure classification** and diagnosability metrics ([ROADMAP_MVP_WOS_VSL.md](../ROADMAP_MVP_WOS_VSL.md) §10.2–10.3).

## Session metadata

| Field | Value |
|-------|--------|
| Reviewer | |
| Date | |
| Backend `session_id` | |
| `trace_id` (if known) | |
| World-engine `world_engine_story_session_id` (if exposed) | |
| Module id | `god_of_carnage` (or current MVP module) |

## Outcome summary

| Question | Answer |
|----------|--------|
| Session start succeeded? | Y / N |
| Turn success (operator view)? | Y / N / partial |
| Severe continuity break observed? | Y / N |
| Classifiable without engineering deep-dive? | Y / N (roadmap target ≥80% weak runs) |

## Failure class (pick one primary)

- Runtime legality failure  
- Continuity failure  
- Retrieval / context failure  
- Character inconsistency  
- Pacing / dramatic weakness  
- UX friction  
- Content gap  
- MCP suite confusion / control-plane ambiguity  

## Evidence pointers

1. Administration-tool diagnosis page (aggregated health).  
2. Backend session snapshot: `GET /api/v1/sessions/{session_id}` (Bearer MCP token).  
3. Diagnostics: `GET /api/v1/sessions/{session_id}/diagnostics`.  
4. MCP resources: `wos://session/{session_id}/diagnostics`, `/state`, `/logs` (see [docs/mcp/MVP_SUITE_MAP.md](../mcp/MVP_SUITE_MAP.md)).  
5. Audit log / bridge: look for `failure_class` e.g. `world_engine_unreachable` on weak runs.

## MCP suite misrouting (Experiment 5)

| Field | Value |
|-------|--------|
| Suite attached | |
| Intended suite per [MVP_SUITE_MAP.md](../mcp/MVP_SUITE_MAP.md) | |
| Misrouted? | Y / N |

## Notes

Free text for replay steps, screenshots, or follow-ups.
