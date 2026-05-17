# Canonical Authored Content Model

Status: Canonical authored-content reference.

## Decision

The canonical authored source model is the structured content-module format
under `content/modules/<module_id>/` loaded into `ContentModule`.

This model is authoritative for authored narrative intent.

**Migrated Decision:** See canonical ADR: [ADR-0025: Canonical Authored Content Model](../ADR/adr-0025-canonical-authored-content-model.md)

## Source contract

- Primary source surfaces:
  - `module.yaml`
  - `canonical_path/`
  - `locations/`
  - `objects/`
  - `characters/`
  - `knowledge/`
  - `direction/`
  - module policy files such as `phase_beat_policy.yaml`,
    `memory_policy.yaml`, `information_disclosure_policy.yaml`, and
    `narrative_aspect_policy.yaml`
- Runtime indexes such as `scene_graph.yaml` may reference canonical ids, but
  they must not duplicate room, object, character, or path descriptions.
- Backend loader contract:
  - `backend/app/content/module_loader.py`
  - `backend/app/content/module_models.py`

## Compiler outputs

Canonical authored content is compiled into three projections:

1. `runtime_projection` for World-Engine story runtime loading.
2. `retrieval_corpus_seed` for future RAG ingestion.
3. `review_export_seed` for policy/review/publishing surfaces.

## Compatibility

- Existing God of Carnage authored content remains valid when it follows the
  current modular authority surfaces.
- Published experience payloads can embed canonical compilation metadata.
- Experience templates remain consumable by existing clients.
