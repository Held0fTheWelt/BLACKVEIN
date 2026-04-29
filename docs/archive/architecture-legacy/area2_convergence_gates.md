# Area 2 Convergence Gates — Routing/Registry Operational Truth

This document lists the convergence gate identifiers for Area 2 routing and registry
operational truth. The canonical authority implementation is `area2_routing_authority`
in `backend/app/runtime/area2_routing_authority.py`.

## Gate Table

| Gate | Description |
|------|-------------|
| G-CONV-01 | One explicit Task 2A policy; LangGraph not canonical for HTTP paths. |
| G-CONV-02 | Bootstrap populates specs; canonical runtime tuples route. |
| G-CONV-03 | Operational states are mutually exclusive and reachable. |
| G-CONV-04 | Distinguish setup gap vs true no-eligible vs executor mismatch. |
| G-CONV-05 | Bounded HTTP paths expose Writers' Room and Improvement specs. |
| G-CONV-06 | TestingConfig leaves registry empty when bootstrap off; factory unchanged. |
| G-CONV-07 | Routing registry bootstrap disabled mode verified isolated. |
| G-CONV-08 | Architecture docs enumerate G-CONV acceptance ids and name area2_routing_authority. |

## Task 2 Cross-Reference

The following Task 2 gate identifiers (G-T2-01 … G-T2-08) are cross-referenced from convergence
to provide documentation continuity:
G-T2-01, G-T2-02, G-T2-03, G-T2-04, G-T2-05, G-T2-06, G-T2-07, G-T2-08.

See [`area2_task2_closure_gates.md`](area2_task2_closure_gates.md) for the Task 2 gate table.

## Authority Reference

`area2_routing_authority` is the single importable authority map for routing policy.
