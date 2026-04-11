# MVP WOS_VSL — subsystem ownership (Phase 0)

This table satisfies the Phase 0 exit criterion in [ROADMAP_MVP_WOS_VSL.md](ROADMAP_MVP_WOS_VSL.md) §4.3: named accountability per subsystem. Until people are assigned, **roles** are authoritative; replace assignee cells when staffing is fixed.

| Subsystem | Responsibility | Owner role | Named assignee |
|-----------|----------------|------------|----------------|
| `world-engine` | Authoritative runtime: session lifecycle, turn execution, committed narrative state | Runtime / Play Service Lead | *TBD* |
| `ai_stack` | Turn graph orchestration, retrieval governance, MCP descriptors, research scaffolding (proposals, not truth) | AI / Orchestration Lead | *TBD* |
| `backend` | API, integration, publishing governance, proxy to world-engine, auth | Backend / Platform Lead | *TBD* |
| `administration-tool` | Operator diagnostics, review surfaces, play-service control | Admin / Governance Lead | *TBD* |
| `writers-room` | Authored content path, draft manuscripts, module contracts | Content / Authoring Lead | *TBD* |
| `frontend` | Player-facing shell, session start, turn UX | Frontend / Player Experience Lead | *TBD* |
| MCP suite architecture | Bounded suites (`wos-admin`, `wos-author`, `wos-ai`, `wos-runtime-read`, `wos-runtime-control`), suite map, resources vs tools | Tooling / Control-Plane Lead | *TBD* |
| Pilot evaluation / reporting | Thresholds, surveys, operator classification, go/no-go evidence | Product / Research Ops Lead | *TBD* |

## MVP vertical slice record (repository)

| Field | Value |
|-------|--------|
| **MVP codename** | WOS_VSL (World of Shadows Vertical Slice) |
| **Canonical module id** | `god_of_carnage` |
| **Content posture** | Proving-ground slice; license-free replacement is explicitly post-MVP (see roadmap §4.4). |
| **Primary slice contract** | [VERTICAL_SLICE_CONTRACT_GOC.md](VERTICAL_SLICE_CONTRACT_GOC.md) |
| **External project tracker** | If your org uses Linear/Jira/etc., mirror this module id there; the repository record above is the technical source for `module_id` at runtime. |

## References

- [ROADMAP_MVP_WOS_VSL.md](ROADMAP_MVP_WOS_VSL.md)
- [docs/mcp/MVP_SUITE_MAP.md](mcp/MVP_SUITE_MAP.md) (suite ↔ tool mapping for pilot misrouting metrics)
- [docs/pilot/MVP_OPERATOR_REVIEW_SHEET.md](pilot/MVP_OPERATOR_REVIEW_SHEET.md)
- [docs/MVP_WOS_VSL_EXTERNAL_BLOCKERS.md](MVP_WOS_VSL_EXTERNAL_BLOCKERS.md)
- [docs/technical/integration/mvp_wos_vsl_mcp_surface.md](technical/integration/mvp_wos_vsl_mcp_surface.md)
