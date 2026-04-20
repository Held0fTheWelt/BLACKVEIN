# Readiness-and-Closure F2 Comparison

## Before (F1 after-state)

- readiness_status: `not_ready`
- closure_status: `bounded_partial_closure`
- blocker_count: `2`
- blocker_ids: `blocker:testify:proof-family-gaps, blocker:despaghettify:local-hotspots`

## After (F2 current state)

- readiness_status: `not_ready`
- closure_status: `bounded_partial_closure`
- blocker_count: `1`
- blocker_ids: `blocker:despaghettify:local-hotspots`
- obligation_count: `20`
- required_test_count: `2`
- required_doc_count: `27`
- affected_surface_count: `8`
- residue_count: `6`

## Movement

- blockers_removed: `blocker:testify:proof-family-gaps`
- blockers_still_open: `blocker:despaghettify:local-hotspots`
- newly_discovered_blockers: `none`
- obligation_delta: `10`
- required_test_delta: `0`
- required_doc_delta: `16`
- residue_delta: `1`

## Evidence notes

- Testify proof-family summary: Testify sees 0 blocker-class proof family gap(s), 1 warning-shaped proof item(s), and 1 linked claim(s).
- Despaghettify hotspot summary: Despaghettify sees 7 blocking hotspot(s) and 7 packetized non-blocking hotspot(s).

