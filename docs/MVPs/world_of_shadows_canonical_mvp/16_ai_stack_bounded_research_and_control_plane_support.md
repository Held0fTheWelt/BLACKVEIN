
# AI stack, bounded research, and control-plane support

## Why this document is needed

The audited World of Shadows source family repeatedly treats the AI stack as a real subsystem, not as unnamed model glue.

Across the roadmap documents, the repository surfaces, the AI-stack code, and the later validation corpus, the same architectural pattern keeps returning:

- the world-engine remains the sole live truth host,
- AI support layers are allowed to interpret, retrieve, plan, and propose,
- research and canon-improvement tooling are allowed to inspect and prepare changes,
- and MCP is allowed to expose controlled tooling and operator visibility,
- but none of those support layers may silently become a second truth boundary.

The earlier canonical document family already preserved parts of this.
This document makes the subsystem explicit enough that future consolidations cannot compress it away.

## Canonical stack reading

The intended stack is layered:

### World-engine
Owns live story truth, validation, commit, and canonical state progression.

### AI stack
Owns bounded support behavior such as:

- scene interpretation support,
- semantic move interpretation,
- social-state reading,
- scene-direction planning support,
- retrieval and RAG support,
- model invocation and routing,
- and governed fallback / degraded-support behavior.

### Research and canon-improvement tooling
Owns source analysis, evidence-linked findings, exploratory hypotheses, canon-improvement candidates, and review-safe bundles.

### MCP and control-plane tooling
Own limited tool access, operator diagnostics, preview-style support flows, and capability-gated control-plane visibility.

The design only works if these layers remain subordinate to runtime truth.

## LLM / SLM / orchestration role split

The source family is consistent on the intended role split:

- **SLMs** may do narrow, fast, bounded helper work such as extraction, pre-normalization, routing hints, summaries, or cheap pre-checks.
- **LLMs** may do the heavier scene interpretation, dramatic proposal generation, ambiguity handling, and socially legible narrative reasoning.
- **LangGraph-style orchestration** may coordinate multi-step bounded flows.
- **LangChain-style integration layers** may provide adapter and tool abstractions.
- **RAG** may supply governed contextual support.
- **MCP** may provide bounded tool and system access.

None of these components outrank engine validation and commit.

## Bounded research and canon-improvement loop

The research-and-canon-improvement material is not a side curiosity.
It preserves a governed loop that belongs to the broader WoS MVP:

1. ingest approved resources,
2. extract dramatic aspects,
3. explore alternate readings in a bounded way,
4. verify promising findings,
5. store structured research records with provenance,
6. inspect canonical material for weaknesses or underused opportunities,
7. generate canon-improvement proposals,
8. assemble review-safe bundles,
9. and prevent silent canon mutation.

This loop is allowed to improve the system.
It is not allowed to self-publish canon.

## Truth-separation rules for research outputs

The source set explicitly distinguishes between:

- source-derived observations,
- exploratory hypotheses,
- candidate claims,
- validated insights,
- approved research,
- canon-applicable proposals,
- and canon-adopted changes.

That distinction is canonically important.
Without it, research and improvement tooling would drift from governed support into ungoverned authorship.

## Exploration mode is allowed, but bounded

The research subsystem was never intended to be purely linear note extraction.
It was also never intended to be an unbounded self-learning crawler.

The canonical rule is:

- exploration is allowed for hypothesis generation, alternate readings, thematic links, staging implications, and dramatic opportunity discovery,
- but exploration outputs begin as non-canonical and must remain budgeted, reviewable, and evidence-linked.

Useful bounded controls include:

- maximum depth,
- maximum branch count,
- maximum low-evidence expansion,
- token and model-call budgets,
- and stop conditions for drift, redundancy, or weak support.

## MCP staged integration path

The MCP roadmap in the source family is staged, not all-at-once.

### Stage A — out-of-band operator and developer tooling
Read-only or preview-style tools for inspection, diagnostics, content lookup, and guard explanation.

### Stage B — guarded in-loop AI support
Read-only or preview support inside the AI path, with guard preview and bounded tool use, while validation remains law.

### Stage C — supervisor and subagent orchestration
Only after the bounded A/B foundation is stable, and still under hard budgets, policies, and traceability.

This staged reading matters because it preserves both ambition and control.

## Preview is not commit

The source family is unusually consistent on preview discipline:

- preview may compare, inspect, and estimate,
- preview may help authoring, evaluation, or operator diagnosis,
- preview may inform a later decision,
- but preview does not itself create canonical live story truth.

This applies both to package/revision preview and to guard-preview style tool calls.

## Non-goals that remain canonical

The following remain explicitly out of scope for the MVP:

- autonomous canon mutation,
- unrestricted self-learning from arbitrary external sources,
- unconstrained agent swarms,
- raw model outputs with direct write authority,
- or MCP/control-plane actions that bypass runtime governance.

## Honest status reading

The correct consolidated reading is:

- the AI stack is already a real implementation surface in the repository,
- research and canon-improvement are already real documented subsystem intent with partial implementation support,
- MCP and bounded control-plane tooling are real architectural surfaces with partial implementation and strong governance constraints,
- but the full staged productization and replay of all these support layers is not yet equally proven at the same level as the active GoC runtime slice.

## Final rule

A future consolidation is incomplete if it preserves world-engine authority and GoC runtime proof but erases the bounded AI-stack / research / MCP support architecture that the repository and roadmap corpus already carry.
