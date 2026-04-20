# Candidate E Wave E1 Report

## Delivered

- Candidate D remains default.
- Candidate E remains opt-in via explicit strategy selection.
- runtime metadata now emits execution-lane and depth semantics.
- compare-runs and observifyfy surfaces can distinguish D from E.

## Real split

- D lane: `balanced_review_first`
- E lane: `candidate_e_narrow_deep`
- D planning_horizon: `1`
- E planning_horizon: `3`
- D handoff_depth: `standard`
- E handoff_depth: `deep_structured`
