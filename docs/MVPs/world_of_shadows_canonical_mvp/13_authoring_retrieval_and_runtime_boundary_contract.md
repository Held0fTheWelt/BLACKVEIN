# Authoring, retrieval, and runtime boundary contract

## Why this document exists

The canonical MVP already carries both of these truths:

- writers' room / authoring intelligence is part of the intended World of Shadows system,
- and retrieval is a necessary governed support layer in the active slice.

What repeatedly causes confusion is the overlap zone between them.

This document keeps that overlap usable without letting it become a second truth boundary.

## The stage contract

### Stage 1 — Authoring and writers' room preparation
Owns:

- authored dramatic source material,
- revision proposals,
- structural critique,
- quality review,
- publish preparation,
- and human-governed module change decisions.

May propose:

- scene structure changes,
- authoring refinements,
- quality annotations,
- evaluation targets,
- and release candidates.

May not do:

- self-authorize live story truth,
- retroactively redefine committed runtime events,
- or silently bypass publish discipline.

### Stage 2 — Publish validation and release control
Owns:

- what authored package becomes the active released artifact,
- release identity,
- provenance bundle,
- and compatibility / fallback classification.

May do:

- validate module completeness and release suitability,
- bind artifact identity,
- classify whether a path is canonical, fallback, local-only, or compatibility-only.

May not do:

- let convenience fallback impersonate published canon,
- or allow artifact identity drift across activation and resume.

### Stage 3 — Runtime activation and birth
Owns:

- binding the published artifact into a live story-session birth,
- Turn 0 truth creation,
- session provenance continuity,
- and lawful handoff to the player route.

Must preserve:

- module identity,
- artifact / revision identity,
- activation path,
- applicable fallback classification,
- and audience / route classification.

### Stage 4 — Live runtime execution
Owns:

- interpretation,
- bounded proposal generation,
- validation,
- commit,
- state progression,
- and player-visible truth.

May consult retrieval and support systems.
May not yield truth authority to them.

### Stage 5 — Retrieval and semantic support
Owns:

- support retrieval,
- semantic lookup,
- reference bundling,
- and bounded assistive context for authoring or runtime.

May do:

- improve grounding,
- surface relevant authored material,
- assist planners and reviewers.

May not do:

- become the canonical authored source,
- create new live truth by convenience,
- or silently remap scene identity, module identity, or commit truth.

### Stage 6 — Operator and inspection surfaces
Owns:

- diagnosis,
- review,
- governance visibility,
- human-readable projection of subordinate system state,
- engine-near operational health views,
- and capability-gated observe / operate / author consoles.

May clarify.
May not outrank canonical contracts, live runtime truth, or commit records.

## Boundary table

| Concern | Authoring / writers' room | Retrieval | Runtime |
|---|---|---|---|
| Creates authored possibility space | Yes | No | No |
| Selects released canonical artifact | Human-governed publish path | No | No |
| Supplies contextual support | Sometimes | Yes | Sometimes consumes |
| Interprets live player input | No | No | Yes |
| Validates and commits live story truth | No | No | Yes |
| Diagnoses and reviews output quality | Yes, pre-release and post-review | Sometimes supportively | Sometimes through internal checks |
| May become a second truth boundary | No | No | Only runtime is the live truth boundary |

## Path-role classification for the overlap zone

The repaired package now classifies the most confusing path families directly:

| Path family | Primary role | May define canon? |
|---|---|---|
| `content/modules/god_of_carnage/` | Canonical authored source | Yes |
| published experience identity / release surfaces | Release-binding and provenance classification | Yes |
| world-engine committed session state and narrative commits | Live runtime truth | Yes |
| player shell observations and transcript framing | Player-facing projection of committed truth | No, unless derived from committed runtime truth |
| `writers-room/` and writers' room review artifacts | Authoring support and review | No |
| `docs/audit/`, `validation/`, `evidence/raw_test_outputs/` | Audit and evidence | No |
| `runtime_data/`, backend compatibility sessions, cached observations | Runtime/environment payload or residue | No |

This is the rule that prevents the support tree from being mistaken for content truth and prevents runtime/environment payload from obscuring normative source truth.

## Provenance bundle that should remain legible

The audited material repeatedly implies a provenance bundle that must stay stable across publish, birth, and resume.
At minimum that bundle should make these things legible:

- module / experience identity,
- released artifact or revision identity,
- whether the path is canonical published, fallback, local-only, or compatibility-only,
- session identity in the live truth host,
- route / audience classification,
- and any explicit degraded-safe state.

This package does not overclaim that every field is uniformly exposed everywhere today.
It does claim that this is the right canonical contract to preserve.

## Session-surface transport rule

The supplied archive family makes one more boundary law necessary:

- the **committed story path** is the canonical ordinary-player truth surface,
- **live-room snapshot paths** may exist, but they do not automatically become the same contract,
- and **operator bundles / inspector projections** are never ordinary-player truth.

If more than one session-facing surface is player-visible, then future work must make all of these explicit:

- which surface is canonical,
- which surface is advisory, live-presence, or operator-only,
- how the surfaces converge or diverge,
- how audience classification is exposed,
- and which tests prove that no secondary surface silently outranks commit truth.

This rule does not forbid multiple surfaces.
It forbids ungoverned ambiguity between them.

## Overlap rule

Overlap between writers' room and retrieval is acceptable only when it stays subordinate to the stage contract above.

That means:

- writers' room may use retrieval support,
- retrieval may support authoring and runtime,
- but neither may silently replace authored canon, publish identity, commit truth, or route classification.

## Refactor safety rule

A future refactor should be rejected or rewritten if it causes any of these:

- retrieval starts behaving like canonical authored source material,
- operator projections begin functioning as truth authority,
- a writers' room workflow mutates live runtime truth without publish and activation discipline,
- published-path identity becomes optional on the hardened ordinary-player path,
- or a secondary session-facing surface silently displaces the committed player path.

## Why this helps the MVP stay focused

This boundary contract does not broaden the MVP.
It prevents an already-existing multi-surface MVP from being simplified into the wrong shape.
