# Acceptance and Validation

## Acceptance Areas

- Authority and source precedence correctness
- Runtime continuity and slice behavior quality
- Player-visible clarity and supportability
- Operator diagnostics and governance controls
- Integration contract coherence (API/MCP/control plane)

## Validation Expectations

- Each acceptance area must map to explicit checks or evidence references.
- Claims of closure must identify what is directly validated versus preserved as historical evidence.
- Any unresolved item must be tracked as open obligation, not hidden in narrative.

## Verification Inputs

- `mvp_source_inventory.md`
- `source_to_destination_mapping_table.md`
- active bundle docs (`README.md` + core sections)
- navigation update record

## Mandatory Verification Rules

- Verification fails if any source file lacks mapping-table coverage.
- Verification fails if any merged or omitted source lacks explicit justification.
- Verification fails if canonical navigation still routes to retired `MVP/` paths.
- Verification fails if implementation guidance loses dependencies, sequencing, or acceptance constraints.
