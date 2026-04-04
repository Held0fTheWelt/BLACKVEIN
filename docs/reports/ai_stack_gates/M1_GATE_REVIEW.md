# Milestone 1 — Gate Review

**Date:** 2026-04-04  
**Status:** **PASS**  
**Recommendation:** **Proceed**

## Scope

- Single canonical authored content model (scene/trigger/ending-oriented `ContentModule`).
- Deterministic compiler producing runtime projection, retrieval corpus seed, and review/export seed.
- Publishing integration attaching compilation metadata when a canonical module resolves.
- God of Carnage as compiler proof case.

## Files changed (M1 scope)

| Area | Path |
|------|------|
| Architecture | `docs/architecture/canonical_authored_content_model.md` (new) |
| Compiler | `backend/app/content/compiler/__init__.py`, `compiler.py`, `models.py` |
| Services | `backend/app/services/game_content_service.py` |
| Tests | `backend/tests/content/test_content_compiler.py` (new) |
| Tests | `backend/tests/test_game_content_service.py` |

## Design decisions

- **Canonical source:** Authored narrative modules under the existing `ContentModule` / scene-phase model remain the source of truth.
- **Compiler outputs:** `CompiledModulePackage` exposes `runtime_projection`, `retrieval_corpus_seed`, `review_export_seed` as structured Pydantic models for deterministic JSON serialization.
- **Publishing:** Seeded/published payloads include `canonical_compilation` when compilation succeeds for the resolved module.

## Deterministic mapping (summary)

- Scene graph and metadata are projected into a runtime-facing bundle (start scene, scenes, trigger hints, beat hints where modeled).
- Retrieval and review seeds are first-class artifacts for later RAG/admin workflows (not fully wired in M1).

## Tests run

```text
cd backend
python -m pytest tests/content/test_content_compiler.py tests/test_game_content_service.py -q --tb=short
```

**Result:** Pass.

## Acceptance criteria

| Criterion | Status |
|-----------|--------|
| One canonical authored format designated | **Pass** |
| Compiler / projection layer exists | **Pass** |
| Publishing reflects compilation-aware payloads | **Pass** |
| God of Carnage compiles through the path | **Pass** |
| Automated tests prove reproducible compilation | **Pass** |

## Gate review — required extras

### Canonical authored source of truth?

- **On-disk YAML/module graph** loaded into `ContentModule` (scene/trigger/ending-oriented), as documented in `canonical_authored_content_model.md`.

### Runtime projection(s) generated?

- **`runtime_projection`** — engine-oriented structure including `start_scene_id`, scene entries, and narrative hints suitable for World-Engine-hosted execution.

### Compatibility for older structures?

- Experience templates and legacy JSON remain **downstream**; mapping from template id to canonical module is **heuristic** where needed (called out as risk).

### Intentionally not in v1 compiler?

- Full retrieval ingestion pipeline, admin UI over review export, and automated corpus deployment.

## Known limitations

- Heuristic template → module mapping for some publishing flows.

## Risks

- Mis-mapping template ids could attach wrong compilation metadata until mapping is tightened.

## Recommendation

**Proceed** to M2.
