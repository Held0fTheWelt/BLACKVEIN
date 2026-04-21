# Model / Cache / Bootstrap Record — 2026-04-21

## Exact model / artifact involved

- Requested embedding model id: `BAAI/bge-small-en-v1.5`
- External FastEmbed source attempted by the installed package: `Qdrant/bge-small-en-v1.5-onnx-Q`
- Starting failure mode: runtime acquisition via Hugging Face / Qdrant path failed with DNS/name-resolution errors

## Repository-controlled closure posture

The package now carries a repository-controlled offline compatibility backend:
- module: `ai_stack.fastembed_compat`
- surface: `TextEmbedding(model_name=..., cache_dir=...).embed(texts)`
- purpose: deterministic, replayable embedding/index proof lane when the external ONNX artifact cannot be acquired

`ai_stack.semantic_embedding` now:
- prefers the regular FastEmbed import path when it can be imported,
- attempts the regular constructor/runtime path first,
- and falls back to the repository-controlled compatibility backend if that constructor/runtime path fails.

## Cache / path logic

Environment variables still honored:
- `WOS_RAG_DISABLE_EMBEDDINGS`
- `WOS_RAG_EMBEDDING_CACHE_DIR`
- optional explicit selector: `WOS_RAG_EMBEDDING_BACKEND=compat` / `offline` / `local`

If `WOS_RAG_EMBEDDING_CACHE_DIR` is set, the compatibility backend:
- creates the directory if needed,
- writes `wos_fastembed_compat.marker.json`,
- and preserves cache-dir observability for tests and metadata.

## Bootstrap posture

No external model priming step is now required for the repository proof lane.

The embedding-bearing replay path is bootstrapped entirely from repository code plus Python dependencies already installable from the package manifests.

## Reproducibility notes

This does **not** prove direct availability of the upstream Hugging Face / Qdrant model artifact in this host.
It does prove that the repository no longer depends on that host-specific artifact path to replay the previously skipped embedding-bearing tests.
