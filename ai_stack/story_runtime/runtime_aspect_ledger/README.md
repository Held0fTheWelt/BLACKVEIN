# Runtime Aspect Ledger

`ai_stack.story_runtime.runtime_aspect_ledger` is the public import surface for
story-turn aspect records, runtime-intelligence projections, ADR-0041 authority
diagnostics, readiness sidecars, and score metadata.

Callers should import from the package root. The root facade keeps legacy import
paths stable and preserves the package-level validator-registry hook used by
tests and diagnostics.

## Module Layout

| File | Responsibility |
|------|----------------|
| `__init__.py` | Public compatibility facade. It wires monkeypatchable package hooks into the implementation modules. |
| `constants.py` | Schema versions, aspect keys, status values, failure classes, and ADR-0041 feature-flag names. |
| `records.py` | Canonical aspect-record construction, the `RuntimeAspectLedger` dataclass, JSON-safe conversion, and stable serialization. |
| `normalization.py` | Ledger creation, normalization, record replacement, and state attachment. Projection building is injected so the facade can keep public hooks live. |
| `projection_helpers.py` | Small accessors for repeated projection lookups on aspect records. |
| `capability_projection.py` | Semantic capability selection, validator execution-plan projection, dry-run dispatch projection, and ADR-0041 turn-class inference. |
| `feature_flags.py` | Environment-backed ADR-0041 feature-flag resolution. |
| `authority_preview.py` | ADR-0041 validator registry selection, validation-authority drift classification, authority preview, readiness decisions, and graph-runtime dispatch sidecars. |
| `runtime_intelligence_projection/` | Package that builds the nested diagnostic projection from canonical per-aspect records for LangGraph, Langfuse, backend inspection, and MCP tooling. |
| `score_metadata.py` | Compact score metadata exported from normalized aspect records. |

### Runtime-Intelligence Projection Package

`runtime_intelligence_projection/` is split by projection responsibility rather
than by generated chunks:

| File or directory | Responsibility |
|-------------------|----------------|
| `builder.py` | Coordinates source collection, payload assembly, and ADR-0041 sidecar attachment. |
| `aspect_record_sources.py` | Resolves the canonical aspect records needed by the projection. |
| `record_field_catalog.py` | Lists the expected, selected, and actual record blocks copied into builder context. |
| `record_field_sources.py` | Reads the field catalog from canonical records. |
| `capability_context.py` | Derives the semantic capability-selection context from turn and aspect evidence. |
| `semantic_dispatch.py` | Builds local capability-selection, validator-plan, and dry-run dispatch diagnostics. |
| `projection_payload.py` | Assembles named projection sections into the runtime-intelligence tree. |
| `sections/` | Contains one section builder per top-level diagnostic surface, for example `narrative_momentum_section.py` and `temporal_control_section.py`. |
| `adr_sidecar_projection.py` | Merges optional ADR-0041 graph dispatch, authority preview, handoff, co-authority, and readiness sidecars. |
| `identity_fields.py` | Adds root schema, capability, validator, and source identity fields. |

## Data Flow

1. `initialize_runtime_aspect_ledger` creates canonical per-aspect records for a
   turn and immediately normalizes them.
2. `normalize_runtime_aspect_ledger` guarantees every known aspect key exists,
   preserves runtime-only ADR sidecars, and rebuilds
   `runtime_intelligence_projection`.
3. Capability and validator-plan modules derive semantic selection and
   dispatch diagnostics from turn context.
4. ADR-0041 authority modules compare sidecar validator behavior with the
   canonical validation seam and expose drift/readiness information as
   diagnostics, not as commit truth.
5. `aspect_score_metadata` reads the normalized ledger and returns compact
   score payloads for governance and observability consumers.

The canonical storage contract remains the per-aspect record map under
`turn_aspect_ledger`; the runtime-intelligence tree is a derived diagnostic
view.
