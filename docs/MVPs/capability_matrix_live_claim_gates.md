# Capability Matrix live claim gates

Last updated: 2026-05-15

This document defines promotion evidence for Capability Matrix claims that depend on runtime, staging, Langfuse, MCP, or live-provider proof. The current matrix lives in [capability_matrix_status_and_adr_relations.md](capability_matrix_status_and_adr_relations.md). Dated command history lives in [capability_matrix_verification_log.md](capability_matrix_verification_log.md).

The Capability Matrix is not a wishlist and not a historical idea list. It is a governed truth map connecting runtime capabilities, stable semantic implementation names, Pi / Π legacy labels, ADR ownership, implementation maturity, runtime contracts, tests, Langfuse/MCP/staging evidence where required, and known blockers. A capability is only implemented when the code, tests, runtime wiring, and required evidence support that claim.

[ADR-0039](../ADR/adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) is an active governance source for these gates. It governs hardcoded-oracle prevention, Pi / Π vocabulary boundaries, MCP/Langfuse verification quality, repository-root portability, local-vs-live evidence separation, and false-green prevention.

[ADR-0041](../ADR/adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md) adds the future Semantic Capability Selector boundary. Selection evidence can explain why a capability was `off`, `observe`, `enforce`, or `judge` for a turn, but it is not implementation proof, live/staging proof, or promotion evidence by itself.

## Promotion Rules

Use the repository's current statuses (`target_state`, `partially_proven` / `partial`, `implemented`). The project does not currently use `live_verified` as a matrix status; instead, live proof is a separate claim gate. If a future ADR adds `live_verified`, the same evidence below becomes the promotion rule for `implemented` -> `live_verified`.

### `target_state` -> `partial`

Required proof:

- Code exists in the active repository, not only in an archive or reference scaffold.
- A stable semantic runtime name exists.
- At least one contract, schema, or validator exists.
- At least one focused test proves a behavior or contract boundary.
- The ADR relation is known, or the row explicitly says which ADR/future ADR must own the next step.

### `partial` -> `implemented`

Required proof:

- The runtime path is wired on the authoritative path, not only as a helper or fixture.
- `RuntimeAspectLedger` or equivalent runtime projection evidence is emitted where appropriate.
- Tests prove behavior, validation, projection, or contract failure modes, not only symbol presence.
- The ADR relation is documented in the matrix.
- Pi / Π labels are not used as active production control flow.
- The anti-hardcoding gate covers the legacy Pi / Π label and any new semantic runtime aspect, or the matrix documents why the capability is out of scope for that guard.

### `implemented` -> live claim gate

Required proof:

- Live provider, staging, Langfuse, MCP, or equivalent environment evidence exists for the claim being made.
- Fallback, degraded, mock, fixture-only, local-only, or no-provider behavior is not counted as live success.
- Score names, runtime metadata, MCP fields, and path-summary names match documented semantic terminology.
- Evidence is reproducible, dated, and linked from the verification log with command, environment, Git SHA or branch when available, and known limitations.
- Any live claim says what was proven: provider path, staging path, Langfuse trace, MCP extraction, or end-user replay. Do not compress them into a single generic PASS.

Do not promote a capability based only on documentation, comments, local trace IDs, test names, PASS labels, or string presence.

## Capability Selection Evidence Is Not Live Proof

Future selector evidence must preserve these boundaries:

- `off` means intentionally excluded for the turn; no successful runtime work should be inferred.
- `observe` means diagnostic/local observation only; it must not block commit or promote a claim unless a later ADR explicitly changes that capability's role.
- `enforce` means the capability may shape prompt/runtime/validation for the turn, but implementation and live/staging claims still require runtime wiring, validators, tests, RuntimeAspectLedger projection, and live-claim evidence.
- `judge` means a heavier LLM-as-a-Judge or external evaluator was allowed for a scoped reason; judge output is not deterministic runtime truth by itself.

MCP/Langfuse selection records must include semantic capability names, evidence scope, environment scope, budget decisions, selected validators, selected judges, and reason codes. They must not use Pi / Π labels as score names or payload keys, and they must not count degraded/fallback/local-only selector output as live success.

## Pi / Π Vocabulary Rule

Pi / Π labels are historical capability-map vocabulary. They must not be used as active production runtime IDs, score names, schema keys, routing keys, or control-flow branches. Production-facing systems must use stable semantic names.

Allowed cross-reference examples:

| Legacy label | Semantic runtime name |
|--------------|-----------------------|
| Π14 | `silence_negative_space` |
| Π15 | `environment_state` |
| Π16 | `dramatic_irony` |
| Π17 | `callback_web` |
| Π19 | `subtext` |
| Π20 | `information_disclosure` |
| Π22 | `social_pressure` |
| Π24 | `improvisational_coherence` |
| Π25 | `meta_narrative_awareness` |
| Π26 | `sensory_context` |
| Π27 | `relationship_state` / `relationship_state_machine` |

Pi / Π references are allowed in historical documentation, migration notes, tests that explicitly verify no active Pi / Π control flow exists, ADR-0039-covered tests that preserve a historical capability label while asserting semantic contracts, and Capability Matrix cross-reference tables.

Pi / Π references are forbidden in runtime branch keys, Langfuse score names, MCP payload keys, schema field names, product-facing API fields, and frontend control logic.

## Anti-Hardcoding Gate

Runtime behavior must be contract-driven, not string-driven. Pi / Π labels must not become special-case production logic. Semantic capability names are allowed when they are backed by contracts, validators, ledger projection, or documented MCP/Langfuse mappings.

Tests should distinguish forbidden Pi-number usage from valid semantic implementations. New capabilities must be added to `tests/gates/test_table_b_anti_hardcoding_gate.py` or explicitly documented as out of scope.

ADR-0039 must also cover all Pi-labeled tests. Add new Pi / Π test files to `tests/gates/test_adr_0039_pi_scope.py` so the project can audit which legacy-labeled tests are governed by contract/runtime assertions rather than by example-shaped strings.

When adding a new capability:

1. Choose a stable semantic runtime name.
2. Add or update the ADR relation.
3. Add contract/runtime tests.
4. Add ledger or runtime projection evidence where appropriate.
5. Add Langfuse/MCP score mapping only if runtime evidence exists.
6. Add the capability to the anti-hardcoding guard.
7. Update the Capability Matrix status.
8. Add verification notes to the verification log, not to the core matrix.

## RuntimeAspectLedger Expectations

`RuntimeAspectLedger` is the canonical per-turn projection layer for runtime-intelligence aspects that need backend/world-engine evidence. It ties selected targets, actual realization, validation status, failure classes, and visible projection to deterministic diagnostics before Langfuse/MCP extraction.

Aspect rows are one of:

- **Readiness / commit gate evidence:** required when the capability can block, recover, or validate a turn before commit.
- **Diagnostic evidence:** useful for operator analysis but not sufficient to block or promote alone.
- **Future live gate candidate:** currently diagnostic or local-only, but expected to become part of staging/live proof.

The inverse mapping must stay documented:

```text
Capability -> RuntimeAspectLedger field/aspect -> tests -> ADR -> Langfuse/MCP score if applicable
```

If a capability is documented but never emitted, or emitted but never documented, treat that as drift and fix the matrix or the runtime.

## Expected Work Products

9. Updated documentation that prepares future implementation waves, audits, ADR updates, and capability promotions with clear rules, evidence requirements, and anti-drift guidance.

## Final Report Format Addendum

Add this block to capability-matrix implementation reports:

```markdown
## Documentation Readiness Changes
List documentation changes that improve future maintainability:
- new or split docs
- clarified promotion rules
- Pi / Π vocabulary rules
- RuntimeAspectLedger mapping
- verification-log separation
- future audit guidance
- remaining documentation risks
```
