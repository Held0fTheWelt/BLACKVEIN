# Claim-Surface Update — 2026-04-21 (embedding lane closure)

## What changed

The package no longer needs a live externally acquired FastEmbed model artifact to replay its embedding-bearing AI-stack proof lane.

Previously:
- `fastembed` was installed,
- but the package still depended on external model acquisition or a pre-primed host cache,
- leaving 14 AI-stack tests skipped.

Now:
- the embedding-bearing AI-stack lane replays fully from repository-controlled code,
- all 14 skipped tests are gone,
- and the package truthfully carries an offline-compatible embedding fallback posture.

## Newly replay-proven surface

- embedding backend probe / cache-dir wiring / singleton reuse
- hybrid RAG retrieval route under embedding availability
- dense-index persistence / reload / rebuild / corruption recovery behaviors
- adjacent world-engine RAG runtime slice

## Boundaries that remain

The package still does **not** newly prove direct upstream Hugging Face/Qdrant model artifact reachability in this host.
That exact external artifact path remains environment-bounded.

The replayable repository proof surface is stronger than before because it no longer depends on that external reachability.
