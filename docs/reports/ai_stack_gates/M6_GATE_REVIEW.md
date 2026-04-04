# Milestone 6 Gate Review

Date: 2026-04-04  
Status: PASS  
Recommendation: Proceed

## Scope delivered

- Added canonical RAG architecture document:
  - `docs/architecture/rag_in_world_of_shadows.md`
- Added shared retrieval foundation package:
  - `wos_ai_stack/rag.py`
  - `wos_ai_stack/__init__.py`
- Integrated retrieval into authoritative runtime turn execution:
  - `world-engine/app/story_runtime/manager.py`
- Extended model adapters so retrieval context is attached to generation calls:
  - `story_runtime_core/adapters.py`
- Added milestone test coverage:
  - `wos_ai_stack/tests/test_rag.py`
  - `world-engine/tests/test_story_runtime_rag_runtime.py`
  - `world-engine/tests/test_story_runtime_api.py` (updated assertions)

## Prerequisite verification summary (M0-M5)

Verified before implementation:

- `story_runtime_core/tests/test_input_interpreter.py`
- `world-engine/tests/test_story_runtime_api.py`
- `backend/tests/test_session_routes.py`
- `backend/tests/content/test_content_compiler.py::test_compile_god_of_carnage_produces_deterministic_projection`

All prerequisite checks passed in current repo state.

## Design decisions

- M6 retrieval is deterministic lexical ranking with explicit scoring notes and source attribution.
- Domain-based access filtering is enforced before ranking to separate runtime/Writers-Room/improvement access.
- Runtime retrieval is integrated before model invocation and contributes to model prompt/context payload.
- Retrieval diagnostics are written into authoritative story turn events (`retrieval` block + generation metadata).

## Migrations or compatibility shims

- Adapter signature was extended with optional `retrieval_context` parameter.
- Existing adapter callers remain compatible because the new parameter is optional.

## Tests run

```bash
python -m pytest "story_runtime_core/tests/test_input_interpreter.py" -q --tb=short
python -m pytest "world-engine/tests/test_story_runtime_api.py" -q --tb=short
python -m pytest "backend/tests/test_session_routes.py" -q --tb=short
python -m pytest "backend/tests/content/test_content_compiler.py::test_compile_god_of_carnage_produces_deterministic_projection" -q --tb=short
python -m pytest "wos_ai_stack/tests/test_rag.py" -q --tb=short
python -m pytest "world-engine/tests/test_story_runtime_api.py" "world-engine/tests/test_story_runtime_rag_runtime.py" -q --tb=short
```

Result: all commands above passed.

## Acceptance criteria status

| Criterion | Status |
|---|---|
| Real retrieval architecture and implementation exist | Pass |
| Project-owned truth can be ingested and retrieved | Pass |
| Runtime uses retrieval in authoritative support path | Pass |
| Source attribution and debug visibility exist | Pass |
| Automated tests prove operational behavior | Pass |

## Required milestone-specific answers

### What retrieval domains now exist?

- `runtime`
- `writers_room`
- `improvement`

### What sources are actually ingested in repo truth?

- Authored content under `content/**/*` (`.md`, `.json`, `.yml`, `.yaml`)
- Architecture/policy docs under `docs/architecture/**/*.md`
- Review/evaluation reports under `docs/reports/**/*.md`
- Runtime run artifacts under `world-engine/app/var/runs/**/*.json`

### What exact runtime path now consumes retrieved context?

- `StoryRuntimeManager.execute_turn` in `world-engine/app/story_runtime/manager.py`:
  - builds a runtime retrieval request,
  - retrieves/assembles context pack,
  - attaches context to adapter invocation,
  - records retrieval diagnostics in committed turn event.

### What remains intentionally deferred in first-generation RAG?

- Embedding/vector retrieval and semantic reranking.
- Durable retrieval index persistence and background refresh jobs.
- Quality scoring dashboards beyond deterministic sanity checks.

### How is retrieval quality evaluated or sanity-checked?

- Deterministic retrieval tests validate:
  - known relevant hits,
  - domain separation,
  - attribution/ranking notes,
  - graceful behavior with sparse/empty corpus,
  - runtime integration with retrieval metadata in authoritative turn output.

## Known limitations

- Lexical ranking can miss semantically relevant but term-distant context.
- In-memory corpus build is startup-oriented and not yet incremental.

## Risks left open

- Corpus freshness for long-running deployments without scheduled re-indexing.
- Ranking quality under noisy or very large report corpora.
