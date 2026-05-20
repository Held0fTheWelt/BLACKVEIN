# MVP4 Phase B Implementation Plan

**Status**: Local implementation verified for canonical phase-cost truth; live/staging provider proof still pending
**Related**: adr-0032, `MVP4_PHASE_A_IMPLEMENTATION_PLAN.md`, `MVP4_PHASE_C_IMPLEMENTATION_PLAN.md`  
**Primary Goal**: Every runtime phase reports truthful token/cost evidence. Real LLM calls must carry real usage. Deterministic/mock paths must explicitly declare zero-cost provenance.

---

## Phase B Principle: Cost Truth, Not Forced Cost

Phase B must not require every span to have `input_tokens > 0`, `output_tokens > 0`, or `cost_usd > 0.0`.

That would be wrong for deterministic/bootstrap paths such as the current GoC deterministic LDSS opening. For these paths, zero tokens and zero cost are valid only if the runtime says why.

**Correct rule:**

Every phase that contributes to a story turn must emit a cost attribution record with:

```json
{
  "phase": "ldss",
  "billing_mode": "deterministic | mock | provider_usage | estimated | unavailable",
  "token_source": "provider_usage | deterministic_no_model_call | mock_no_model_call | unavailable",
  "billable": false,
  "input_tokens": 0,
  "output_tokens": 0,
  "cost_usd": 0.0,
  "model": "ldss_deterministic",
  "provider": "world_engine"
}
```

For real provider calls, `billing_mode` must be `provider_usage`, token counts must come from the provider/adapter response, and `billable` must be `true`.

**Current local implementation snapshot (2026-05-16):**

- `ai_stack/telemetry/runtime_cost_attribution.py` is the shared canonical helper surface for phase-cost records and aggregation.
- World-engine GoC committed turns aggregate `graph_state["phase_costs"]` into `diagnostics_envelope.cost_summary`.
- Deterministic/mock paths are explicit zero-cost records.
- Provider-backed model generation records a semantic `model_generation` phase only from adapter-reported usage metadata.
- If a real provider response has no usage metadata, the phase is `billing_mode="unavailable"` / `token_source="unavailable"` rather than guessed from text length.
- Langfuse observations receive the same cost truth as metadata/export data; Langfuse is not the source of local cost truth.

---

## Contract Requirements

### Contract 1: Backend -> World-Engine Handoff

Phase A owns the actual handoff fields. Phase B adds trace/cost correlation only.

Required Phase B proof:

- The same request trace ID is visible in backend, world-engine HTTP, story manager diagnostics, and Langfuse/local trace evidence.
- Cost attribution records include `trace_id`, `story_session_id`, `turn_number`, `runtime_profile_id`, `content_module_id`, and `runtime_module_id` where available.

### Contract 2: Opening Truthfulness

Opening execution must be classified honestly.

Allowed:

- Deterministic LDSS bootstrap with `billing_mode="deterministic"` and zero tokens.
- Real graph/model opening with `billing_mode="provider_usage"` and provider token usage.

Not allowed:

- Marking deterministic output as provider/model output.
- Failing a valid deterministic opening only because its cost is zero.
- Omitting cost provenance for opening turns.

### Contract 3: Frontend Playability

No Phase B behavior change. Phase A owns `can_execute == story_window.entry_count > 0`.

### Contract 4: Diagnostics Truthfulness

Phase B primary scope.

Diagnostics must expose:

- `cost_summary.input_tokens`
- `cost_summary.output_tokens`
- `cost_summary.cost_usd`
- `cost_summary.cost_breakdown`
- `cost_summary.phase_costs`
- per-phase `billing_mode`, `token_source`, `billable`, `provider`, and `model`

Zero cost is valid only when `billing_mode` explains why.

### Contract 5: Narrative Streaming

Phase B should preserve trace correlation for narrator streaming state, but should not implement the SSE streaming contract itself. SSE behavior remains Phase C unless already implemented elsewhere.

---

## Current Code Reality

Do not rebuild the following infrastructure:

| Area | Existing path | Current role |
|---|---|---|
| Backend Langfuse adapter | `backend/app/observability/langfuse_adapter.py` | Backend/admin observability and DB-backed credentials |
| World-Engine Langfuse adapter | `world-engine/app/observability/langfuse_adapter.py` | Runtime tracing, backend credential fetch, active span ContextVar |
| Trace propagation | `backend/app/services/game/game_service.py`, `world-engine/app/middleware/trace_middleware.py` | `X-WoS-Trace-Id` and `X-Langfuse-Trace-Id` propagation |
| Root turn spans | `world-engine/app/api/http.py` | `world-engine.turn.execute` root span for story/session and turn routes |
| Phase spans | `world-engine/app/story_runtime/manager.py` | `story.phase.ldss`, `story.phase.narrator` |
| LDSS execution | `ai_stack/live_dramatic_scene_simulator.py` | deterministic LDSS output and LDSS span metadata scaffold |
| Narrator blocks | `ai_stack/story_runtime/narrative_runtime_agent.py` | narrator block spans and scaffold token metadata |
| Diagnostics envelope | `ai_stack/telemetry/diagnostics_envelope.py` | response redaction, cost summary field, trace evidence |

Important boundary:

`ai_stack` and `world-engine` must not import `backend.app.observability.langfuse_adapter`. World-Engine has its own runtime adapter. Shared helpers should live in `ai_stack` or another neutral shared module.

---

## Target Data Model

Use one canonical shape for phase cost records.

```python
PhaseCost = {
    "phase": str,
    "billing_mode": "provider_usage" | "deterministic" | "mock" | "estimated" | "unavailable",
    "token_source": "provider_usage" | "deterministic_no_model_call" | "mock_no_model_call" | "estimated" | "unavailable",
    "billable": bool,
    "input_tokens": int,
    "output_tokens": int,
    "cost_usd": float,
    "provider": str,
    "model": str,
    "currency": "USD",
    "pricing_source": str,
    "latency_ms": int | None,
}
```

Minimum invariants:

- `input_tokens` and `output_tokens` are integers >= 0.
- `cost_usd` is a float >= 0.0.
- If `billing_mode == "provider_usage"`, then `token_source == "provider_usage"` and provider/model must be non-empty.
- If `billing_mode in ("deterministic", "mock")`, then `billable == False` and zero tokens/cost are acceptable.
- If usage is unavailable for a real provider response, use `billing_mode="unavailable"` and add a degradation/diagnostic signal. Do not silently write zero-cost provider usage.

---

## Implementation Order

### Step 1: Add Shared Cost Attribution Helpers

Add a small shared helper module, preferably in `ai_stack`, for normalizing cost attribution.

Suggested file:

`ai_stack/telemetry/runtime_cost_attribution.py`

Responsibilities:

- `build_deterministic_phase_cost(...)`
- `build_mock_phase_cost(...)`
- `build_provider_usage_phase_cost(...)`
- `build_unavailable_phase_cost(...)`
- `calculate_token_cost(model, input_tokens, output_tokens, provider=None)`
- `aggregate_phase_costs(phase_costs)`

Keep pricing table small and explicit. Pricing changes over time, so the helper must return `pricing_source` and should default unknown models to `billing_mode="unavailable"` or `estimated`, not silently pretend pricing is exact.

Do not duplicate separate pricing tables in backend and world-engine.

### Step 2: Make LDSS Cost Truthful

File:

`ai_stack/live_dramatic_scene_simulator.py`

Current behavior:

- LDSS is deterministic in the current path.
- It writes scaffold metadata with `input_tokens: 0`, `output_tokens: 0`, `cost_usd: 0.0`, `model: "mock"`.

Required change:

- Replace `"model": "mock"` for deterministic LDSS with a truthful model/provenance value such as `"ldss_deterministic"`.
- Add `billing_mode="deterministic"`.
- Add `token_source="deterministic_no_model_call"`.
- Add `billable=False`.
- Return or expose this phase cost in the LDSS result or graph state so `StoryRuntimeManager` can aggregate it.

Expected LDSS phase cost:

```json
{
  "phase": "ldss",
  "billing_mode": "deterministic",
  "token_source": "deterministic_no_model_call",
  "billable": false,
  "input_tokens": 0,
  "output_tokens": 0,
  "cost_usd": 0.0,
  "provider": "world_engine",
  "model": "ldss_deterministic"
}
```

If a future LDSS path calls a real model, that path must use provider usage and `billing_mode="provider_usage"`.

### Step 3: Make Narrator Cost Truthful

File:

`ai_stack/story_runtime/narrative_runtime_agent.py`

Current behavior:

- Narrator spans exist.
- Span metadata still uses scaffold values: zero tokens, `model="mock"`, zero cost.

Required change:

- If narrator text is synthesized deterministically, mark it as deterministic or mock explicitly.
- If narrator text is generated through an LLM, extract provider usage from the adapter response and mark it as provider usage.
- Add `narration_length` or `text_length` as content metadata, but do not confuse text length with token usage.

Do not add pseudofunctions like `call_llm_for_narration(...)` unless the implementation actually introduces that abstraction. Wire into the existing narrator generation path.

### Step 4: Propagate Phase Costs Through Graph State

File:

`world-engine/app/story_runtime/manager.py`

Current behavior:

`_finalize_committed_turn()` already aggregates `graph_state.get("phase_costs", {})`.

Required change:

- Ensure LDSS and narrator execution populate `graph_state["phase_costs"]`.
- Keep aggregation in `_finalize_committed_turn()`, but aggregate the canonical phase cost records.
- Preserve detailed per-phase records in diagnostics, not only a flat `cost_breakdown`.

Recommended shape:

```python
graph_state["phase_costs"] = {
    "ldss": {...PhaseCost...},
    "narrator": {...PhaseCost...},
    "model_generation": {...PhaseCost...},
}
```

Aggregated diagnostics:

```json
{
  "cost_summary": {
    "input_tokens": 0,
    "output_tokens": 0,
    "cost_usd": 0.0,
    "cost_breakdown": {"ldss": 0.0, "narrator": 0.0},
    "phase_costs": {
      "ldss": {"billing_mode": "deterministic", "...": "..."},
      "narrator": {"billing_mode": "deterministic", "...": "..."},
      "model_generation": {"billing_mode": "provider_usage", "token_source": "provider_usage", "...": "..."}
    }
  }
}
```

Provider-backed `model_generation` is emitted only when the adapter metadata
contains provider usage such as `usage_details.input`, `usage_details.output`,
and `usage_details.total` (or equivalent prompt/completion totals). Missing
usage on a real provider path is represented as an explicit unavailable cost
record; text length must not be used as a token-count substitute.

### Step 5: Attach Cost Data To Langfuse Spans

Files:

- `world-engine/app/story_runtime/manager.py`
- `ai_stack/live_dramatic_scene_simulator.py`
- `ai_stack/story_runtime/narrative_runtime_agent.py`

Required change:

- LDSS span metadata includes the LDSS phase cost record.
- Narrator span metadata includes the narrator phase cost record.
- Root turn span output/metadata includes the aggregated `cost_summary` where safe.

For Langfuse v4 observations, prefer native usage fields when available for generation observations. For regular spans, include the canonical cost record in metadata.

World-engine's Langfuse adapter also exposes shared helper parity for local
evidence export: `resolve_parent_observation_for_nested_span`,
`record_wos_nested_span_observation`, and
`record_adr0041_langfuse_scores`. These helpers are best-effort export
surfaces and mark local evidence as `proof_level="local_only"` /
`live_or_staging_evidence=false`.

### Step 6: Tests

Tests must not assert that every phase has cost > 0.

Replace that with:

- Real provider paths must have provider usage tokens and non-mock provider/model.
- Deterministic paths must have explicit deterministic billing metadata and zero-cost truth.
- Diagnostics aggregation must equal the sum of phase records.
- `to_response("operator")` redacts cost details where required.
- `to_response("langfuse")` and service-account/admin contexts keep cost details.

Suggested tests:

```python
def test_mvp4_deterministic_ldss_reports_zero_cost_truthfully():
    cost = diagnostics["cost_summary"]["phase_costs"]["ldss"]
    assert cost["billing_mode"] == "deterministic"
    assert cost["token_source"] == "deterministic_no_model_call"
    assert cost["billable"] is False
    assert cost["input_tokens"] == 0
    assert cost["output_tokens"] == 0
    assert cost["cost_usd"] == 0.0
    assert cost["model"] == "ldss_deterministic"


def test_mvp4_cost_summary_matches_phase_cost_sum():
    summary = diagnostics["cost_summary"]
    phases = summary["phase_costs"].values()
    assert summary["input_tokens"] == sum(p["input_tokens"] for p in phases)
    assert summary["output_tokens"] == sum(p["output_tokens"] for p in phases)
    assert summary["cost_usd"] == pytest.approx(sum(p["cost_usd"] for p in phases))


def test_mvp4_provider_usage_phase_requires_real_usage():
    phase = diagnostics["cost_summary"]["phase_costs"]["narrator"]
    if phase["billing_mode"] == "provider_usage":
        assert phase["token_source"] == "provider_usage"
        assert phase["billable"] is True
        assert phase["input_tokens"] > 0
        assert phase["output_tokens"] > 0
        assert phase["provider"]
        assert phase["model"]
        assert phase["model"] != "mock"
```

---

## Out Of Scope For Phase B

Keep these out of Phase B unless they already exist and only need trace correlation:

- SSE narrative streaming implementation
- OTEL multi-select filtering/admin UI
- Token budget enforcement
- Cost-aware degradation policy
- Evaluation pipeline
- Session replay debugger
- Audit trail multi-select UI
- Offline trace export as final proof path

These can consume Phase B cost truth later, but they should not block Phase B.

Note: a backend pre-turn hard-stop guard now exists as a bounded operational
settings closure over Phase B cost truth. That guard belongs to the operational
governance/control-plane slice, not to Phase B's cost attribution source of
truth.

---

## Stop Gate

Phase B is complete when all of the following are true:

1. Every committed GoC turn has `diagnostics_envelope.cost_summary.phase_costs`.
2. Every phase cost has `billing_mode`, `token_source`, `billable`, `provider`, and `model`.
3. Deterministic/mock paths are allowed to have zero tokens/cost only with explicit deterministic/mock provenance.
4. Provider-backed paths use provider usage, not guessed counts.
5. Aggregated `input_tokens`, `output_tokens`, and `cost_usd` equal the sum of phase records.
6. Langfuse spans include the same phase cost truth that diagnostics exposes.
7. Operator responses redact cost details where required; Langfuse/service-account contexts retain them.
8. Phase A tests still pass.

---

## Practical Implementation Notes

- Do not read cost values back out of Langfuse spans as the source of truth. Spans are the export surface; `graph_state["phase_costs"]` and diagnostics should be the local runtime source of truth.
- Do not infer tokens from text length for final cost accounting. If a provider does not return usage, mark usage unavailable.
- Do not import backend observability modules from `ai_stack` or `world-engine`.
- Do not label deterministic LDSS as `mock` unless it is actually test-only mock behavior.
- Do not fail deterministic opening tests because cost is zero; fail them if cost provenance is missing or dishonest.
