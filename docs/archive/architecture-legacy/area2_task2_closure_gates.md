# Area 2 Task 2 Closure Gates — Registry/Routing Convergence

This document lists the closure gates for Area 2 Task 2 (registry/routing convergence).
The canonical routing authority implementation is `area2_routing_authority` in
`backend/app/runtime/area2_routing_authority.py`.

## Gate Table

| Gate | Description |
|------|-------------|
| G-T2-01 | Primary authority sources per canonical surface are non-empty and non-competing. |
| G-T2-02 | Named startup profiles and operational/bootstrap classification are deterministic. |
| G-T2-03 | Healthy staged runtime and bounded HTTP paths route without hitting no_eligible_adapter. |
| G-T2-04 | Degraded vs misconfigured vs test-isolated vs true no-eligible discipline are distinct. |
| G-T2-05 | Compact operator truth on bounded HTTP plus legibility derivation. |
| G-T2-06 | Inventory surfaces satisfied by bootstrap specs and Writers' Room spec builder. |
| G-T2-07 | Bootstrap-off test isolation and legacy expectations remain intact. |
| G-T2-08 | Task 2 docs and architecture cross-references list every G-T2 id and reference area2_routing_authority. |

## Authority Reference

All routing policy is governed by `area2_routing_authority` (`AREA2_AUTHORITY_REGISTRY`).
See `backend/app/runtime/area2_routing_authority.py`.
