# Canonical Authored Content Model

Status: Canonical for Milestone 1.

## Decision

The canonical authored source model is the existing scene/trigger/ending content
module format under `content/modules/<module_id>/` loaded into `ContentModule`.

This model is authoritative for authored narrative intent.

## Source contract

- Primary source files:
  - `module.yaml`
  - `scenes.yaml`
  - `triggers.yaml`
  - `endings.yaml`
  - `characters.yaml`
  - `relationships.yaml`
  - `transitions.yaml`
- Backend loader contract:
  - `backend/app/content/module_loader.py`
  - `backend/app/content/module_models.py`

## Compiler outputs

Canonical authored content is compiled into three projections:

1. `runtime_projection` for World-Engine story runtime loading.
2. `retrieval_corpus_seed` for future RAG ingestion.
3. `review_export_seed` for policy/review/publishing surfaces.

## Compatibility

- Existing God of Carnage authored content remains valid.
- Published experience payloads can embed canonical compilation metadata.
- Experience templates remain consumable by existing clients.
