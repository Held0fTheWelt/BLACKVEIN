# RAG in World of Shadows

Status: Canonical Milestone 6 architecture and implementation baseline.

## Purpose

Provide operational retrieval for authoritative runtime support, Writers-Room workflows, and improvement/evaluation loops without making AI authoritative over state commit or publishing.

## Retrieval domains

- `runtime`: turn-time retrieval for World-Engine authoritative story sessions.
- `writers_room`: analysis/review retrieval that may include review notes.
- `improvement`: experiment/evaluation retrieval that may include eval artifacts.

## Domain content access model

- `runtime` can read:
  - authored modules
  - runtime projection material
  - character profiles
  - transcripts
  - policy/guidelines
- `writers_room` can additionally read review notes.
- `improvement` can additionally read evaluation artifacts.

The access model is enforced in code by domain-to-content-class filtering before ranking.

## Ingestion and indexing

M6 ingestion reads project-owned sources:

- `content/**/*` authored materials (`.md`, `.json`, `.yml`, `.yaml`)
- `docs/architecture/**/*.md` policy and architecture guidance
- `docs/reports/**/*.md` review and evaluation artifacts
- `world-engine/app/var/runs/**/*.json` runtime transcript-like run artifacts

Chunking is deterministic fixed-size chunking with overlap, producing in-memory corpus chunks with source attribution metadata.

## Retrieval profiles

- `runtime_turn_support`: used on each authoritative story turn.
- `writers_review`: reserved and testable in M6 retrieval hooks.
- `improvement_eval`: reserved and testable in M6 retrieval hooks.

## Ranking and selection rationale

M6 ranking is deterministic lexical overlap scoring with explicit boost rules:

- token overlap score
- module match boost
- optional scene hint boost

Each selected chunk emits a `selection_reason`. Ranking notes include per-hit score and rationale.

## Context-pack assembly

Retriever output is assembled into a context-pack with:

- compact ranked context text
- source attribution list (`source_path`, `content_class`, `selection_reason`)
- hit count
- domain/profile
- retrieval status (`ok`, `degraded`, `fallback`)
- ranking notes

## Runtime integration

The authoritative runtime path in `world-engine/app/story_runtime/manager.py` now:

1. builds a runtime retrieval request from player input + scene/module hints,
2. retrieves context via runtime domain/profile,
3. assembles a context-pack,
4. injects retrieved context into model input,
5. records retrieval diagnostics in the committed turn event.

This is part of the authoritative support path and not only side logging.

## Writers-Room and improvement hooks

Writers-Room and improvement use the same retrieval core (`RagIngestionPipeline`, `ContextRetriever`, `ContextPackAssembler`) with separate domain/profile requests and domain-gated content access.

## Diagnostics and attribution requirements

Turn diagnostics must expose:

- retrieval domain/profile
- status
- hit count
- retrieved sources
- ranking notes
- whether model generation received retrieval context

## M6 deferred items

Deferred beyond M6:

- semantic vector retrieval and embedding-based ranking,
- corpus persistence beyond in-memory startup build,
- adaptive profile tuning and quality scoring dashboards.
