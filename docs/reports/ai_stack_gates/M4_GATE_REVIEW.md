# Milestone 4 — Gate Review

**Date:** 2026-04-04  
**Status:** **PASS**  
**Recommendation:** **Proceed**

## Scope

- Real provider-capable adapters (OpenAI chat, Ollama) plus deterministic mock.
- Model registry and routing policy (LLM vs SLM, timeouts, structured-output flags, cost/latency class).
- Startup registration via World-Engine `StoryRuntimeManager` (registry + adapter instances).
- Observability of model choice and generation attempt outcome on each turn.

## Files changed (M4 scope)

| Area | Path |
|------|------|
| Core | `story_runtime_core/model_registry.py` |
| Core | `story_runtime_core/adapters.py` (includes `build_default_model_adapters`) |
| Core | `story_runtime_core/tests/test_model_registry.py`, `test_adapters.py` |
| Host | `world-engine/app/story_runtime/manager.py` (routing + adapter invoke + diagnostics) |

## Design decisions

- **Registry** (`ModelSpec`) declares model id, provider, `llm_or_slm`, timeout, structured-output support, cost/latency/use-case tuples.
- **RoutingPolicy** routes auxiliary/classification-style tasks toward **SLM** entries first; narrative-style tasks toward **LLM**, with a recorded **fallback_model** hint (SLM).
- **Adapters** keyed by provider (`mock`, `openai`, `ollama`) are constructed at manager init (`build_default_model_adapters`).
- **Per-turn observability:** `model_route` includes `registered_adapter_providers`, `generation` (`attempted`, `success`, `error` from adapter metadata when calls fail, e.g. missing API key).

## Tests run

```text
cd <repo-root>
python -m pytest story_runtime_core/tests/test_model_registry.py story_runtime_core/tests/test_adapters.py -q --tb=short

cd world-engine
python -m pytest tests/test_story_runtime_api.py -q --tb=short
```

**Result:** Pass.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| Real adapters in addition to mocks | **Pass** |
| Registry + routing explicit | **Pass** |
| Startup registration (non-test-only) | **Pass** (`StoryRuntimeManager` lifespan) |
| Model selection visible in diagnostics | **Pass** |
| Tests for resolution / routing / fallback metadata | **Pass** |

## Gate review — required extras

### Which providers were added and why?

- **OpenAI** (`gpt-4o-mini`) — first hosted **LLM** path for narrative-class routing when credentials exist.
- **Ollama** (`llama3.2`) — local / provider-agnostic **SLM** path for auxiliary routing when a local server is available.
- **Mock** — deterministic tests and safe default behavior without network.

### First real LLM path?

- `OpenAIChatAdapter` calling `https://api.openai.com/v1/chat/completions` when `OPENAI_API_KEY` is set.

### First real SLM path?

- `OllamaAdapter` calling `{OLLAMA_BASE_URL}/api/generate` (default `http://127.0.0.1:11434`).

### Escalation / degradation?

- Routing selects LLM vs SLM by **task_type** derived from interpreted input; **fallback_model** is recorded on LLM decisions. Automatic re-invocation on failure is **not** implemented yet (deferred).

### Intentionally deferred?

- Retry/backoff, budget caps, streaming, structured-output enforcement, LangChain abstraction.

## Known limitations

- Without API keys or local Ollama, generation attempts may fail while routing metadata still records the intended model.

## Risks

- Provider endpoints and credentials are environment-dependent.

## Recommendation

**Proceed** to M5.
