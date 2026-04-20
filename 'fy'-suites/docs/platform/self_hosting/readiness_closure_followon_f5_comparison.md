# F5 Readiness/Closure Comparison

- before_wave: `F4`
- after_wave: `F5`
- readiness_status: `implementation_ready` -> `implementation_ready`
- closure_status: `bounded_partial_closure` -> `bounded_review_ready`
- obligation_count: `20` -> `8`
- required_test_count: `2` -> `2`
- required_doc_count: `27` -> `9`
- residue_count: `6` -> `0`
- warning_count: `0` -> `4`

## Residue moved to warning

- `residue:testify:warnings` -> `warning:testify:proof-items`
- `residue:despaghettify:packetized-hotspots` -> `warning:despaghettify:packetized-hotspots`
- `residue:dockerify:warnings` -> `warning:dockerify:warnings`
- `residue:readiness:optional-evidence-missing` -> `warning:readiness:optional-evidence-missing`

## Residue removed

- `residue:readiness:bounded-closure-only`
- `residue:coda:closure-not-complete`

