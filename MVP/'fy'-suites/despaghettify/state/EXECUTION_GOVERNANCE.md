# Repository-wide execution governance

## Purpose

This document defines binding governance for all state-changing workstreams in `WorldOfShadows`.
It complements existing functional and audit documentation; it does not replace it.

**Language:** Human-readable artefacts (`.md` / `.txt`), state-document prose, and pre→post comparison notes written under this model must be **strict English**, per the canonical policy in [`../../docs/dev/contributing.md#repository-language`](../../docs/dev/contributing.md#repository-language) (do not paraphrase from other entry points).

Authority order when sources disagree:
1. Repository reality (files, code, current behaviour)
2. Objective artefacts in the repository
3. Canonical state documents under `despaghettify/state/`
4. Historical narrative / chat context

## Scope

Governance applies to all real state-changing workstreams, in particular:
- Backend Runtime and Services
- AI Stack
- Administration Tool
- Documentation
- World Engine

## Binding model per workstream

Each workstream must have:
1. A canonical state document under `despaghettify/state/`.
2. A pre-artefact set under `despaghettify/state/artifacts/workstreams/<workstream>/pre/`.
3. A post-artefact set under `despaghettify/state/artifacts/workstreams/<workstream>/post/`.

At least one artefact must be human-readable (`.txt` / `.md`); a machine-readable artefact (`.json`) is preferred.

## Completion gate (non-negotiable)

A wave, task, or closure claim is only allowed when all of the following hold:
- The relevant state document was read before work started.
- Repository reality was inspected on a fresh tree.
- Pre-artefacts exist.
- Execution work was done against the current repository state.
- Post-artefacts exist.
- Post vs pre is compared and documented.
- The state document was updated from evidence.
- No unsupported closure claim remains.

## Contradiction stop rule

When repository reality contradicts existing state or audit narrative:
- Stop.
- Record the contradiction in the affected state document under "Contradictions / caveats".
- Re-scope and plan next steps from repository reality.
- Only then continue.

## Rollout artefacts for this governance installation

Repository-wide rollout evidence:
- Pre: `despaghettify/state/artifacts/repo_governance_rollout/pre/`
- Post: `despaghettify/state/artifacts/repo_governance_rollout/post/`

Workstreams are listed in `WORKSTREAM_INDEX.md`.
