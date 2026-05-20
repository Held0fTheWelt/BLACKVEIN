# ADR-0040: Quality Lab MCP Runtime Diagnostics and Judge-Guided Improvement

## Status

Accepted

## Date

2026-05-14

## Implementation status

| Phase | Status | Evidence |
|-------|--------|----------|
| **1 — Evaluator catalog and judgment interpretation** | Implemented | `ai_stack/quality_lab/evaluator_catalog.py`, `judgment_interpreter.py`, `schemas.py`; MCP tool `wos.quality_lab.review_judgments`; tests in `ai_stack/tests/test_quality_lab_judgment_interpreter.py`, `ai_stack/tests/test_quality_lab_evaluator_catalog.py`, and `tools/mcp_server/tests/test_quality_lab_tools.py`. |
| **2 — Trace and metadata analysis** | Implemented | `ai_stack/quality_lab/trace_interpreter.py`; MCP tool `wos.quality_lab.review_trace`; tests in `ai_stack/tests/test_quality_lab_trace_interpreter.py` and `tools/mcp_server/tests/test_quality_lab_tools.py`. |
| **3 — MCP exchange analysis** | Implemented | `ai_stack/mcp/mcp_exchange_interpreter.py`; MCP tool `wos.quality_lab.review_mcp_exchange`; tests in `ai_stack/tests/test_quality_lab_mcp_exchange_interpreter.py` and `tools/mcp_server/tests/test_quality_lab_tools.py`. |
| **4 — Problem clustering and investigation** | Implemented | `ai_stack/quality_lab/pattern_interpreter.py`; MCP tools `wos.quality_lab.find_patterns` and `wos.quality_lab.suggest_investigation`; tests in `ai_stack/tests/test_quality_lab_pattern_and_planning.py` and `tools/mcp_server/tests/test_quality_lab_tools.py`. |
| **5 — Repair, judge-set, and content planning** | Implemented | `ai_stack/quality_lab/planning_interpreter.py`; MCP tools `wos.quality_lab.plan_repair_wave`, `wos.quality_lab.refine_judge_set`, and `wos.quality_lab.plan_content_revision`; tests in `ai_stack/tests/test_quality_lab_pattern_and_planning.py` and `tools/mcp_server/tests/test_quality_lab_tools.py`. |

All implemented surfaces are read-only and registered in
`ai_stack/mcp/mcp_canonical_surface.py` with `McpToolClass.read_only`,
`McpSuite.wos_runtime_read`, and `AUTH_QUALITY_LAB_ANALYSIS`.

## Related ADRs

- [ADR-0033](adr-0033-live-runtime-commit-semantics.md) — live runtime commit semantics; remains authoritative for runtime truth. Quality Lab must never override deterministic runtime gates defined there.
- [ADR-0009](adr-0009-evaluation-is-a-promotion-gate.md) — evaluation evidence must not be "string-matched theatre." Quality Lab interprets, never decides promotion.
- [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) — gate tests must not hardcode oracles. Quality Lab test files (`ai_stack/tests/test_quality_lab_*.py`) must derive expected judge names, categories, and severity buckets from the canonical evaluator catalog and `docs/llm-as-a-judge/` directory, never from copy-pasted literal lists.
- [Capability Matrix live claim gates](../MVPs/capability_matrix_live_claim_gates.md) — Quality Lab may provide diagnostic evidence, but it does not own Capability Matrix truth or promote live claims without the required runtime, staging, Langfuse, MCP, and ADR evidence.

## Context

World of Shadows / Better Tomorrow now uses multiple layers of runtime
evidence: Langfuse observability, deterministic runtime gates, LLM-as-a-Judge
evaluators, MCP analyses, and content-pipeline documents to assess the
quality of interactive story turns.

The current MCP/Langfuse tooling can already inspect traces and scores, but
the analysis surface is still too narrow. It often focuses on individual
judge scores or raw Langfuse evidence, while the actual quality problems
can originate from many different areas:

- Runtime graph behavior
- ADR-0033 live runtime commit semantics
- Beat selection and beat realization
- Dramatic capability selection and realization
- Narrator authority
- NPC authority boundaries
- Actor-lane ownership
- Visible block origin/provenance
- Recovery and playability of blocked or ambiguous actions
- RAG/content usefulness
- Content module gaps
- Prompt/context injection defects
- Langfuse evaluator configuration
- Missing or weak runtime metadata
- MCP request/response quality
- Stale assumptions in MCP tools or docs
- Judge prompt/category maintenance needs

The project now contains a human-maintained LLM-as-a-Judge definition
document under:

```text
docs/llm-as-a-judge/
```

This document must become the canonical source for evaluator definitions and
must be used to concretize MCP analyses before further judge maintenance or
prompt rewriting is performed.

The new diagnostic layer must not treat LLM-as-a-Judge results as runtime
truth. Deterministic runtime gates remain authoritative for runtime contract
status.

## Decision

Introduce a new read-only MCP Quality Lab / Quality Intelligence diagnostics
layer.

The new toolset shall analyze:

- MCP requests
- MCP responses
- Langfuse traces
- Langfuse generation observations
- Deterministic runtime scores
- LLM-as-a-Judge scores
- Evaluator definitions from `docs/llm-as-a-judge`
- Runtime metadata coverage
- Actor-lane and origin evidence
- Beat and capability realization evidence
- Recovery/playability evidence
- RAG/content evidence
- Content pipeline gaps
- Prompt/context injection risks
- Runtime architecture risks
- MCP analysis quality
- Langfuse configuration coverage
- Judge definition coverage
- Targeted claude-context investigation queries

The toolset shall produce evidence-backed quality findings, problem
clusters, improvement candidates, investigation plans, content-revision
candidates, prompt-maintenance suggestions, and repair-wave proposals.

The toolset is analysis-only. It must not mutate runtime state, Langfuse
evaluators, prompts, content files, source code, or deterministic runtime
gates.

Quality Lab is also not the owner of the Capability Matrix. It can inspect and
summarize runtime metadata, judge evidence, Langfuse traces, MCP exchanges, and
problem patterns, but Capability Matrix status changes must still follow the
semantic-name, ADR, anti-hardcoding, verification-log, and live-claim rules in
the matrix documentation. Quality Lab outputs must use production semantic names
for scores and runtime metadata; historical Pi / Π labels may appear only as
explanatory cross-references.

## Canonical Sources

### Evaluator Definitions

The canonical evaluator definition source is the directory:

```text
docs/llm-as-a-judge/
  README.md                              # index + canonical declaration
  <evaluator_name>.md                    # one file per evaluator
  LLM-as-a-Judge Definition Table - Judges.csv   # legacy export, frozen
```

Each per-evaluator file has YAML frontmatter and a fixed body structure:

```yaml
---
name: <evaluator_name>
group: <evaluator_group>
score_type: categorical
categories: [<cat>, ...]                  # exact order shown to Langfuse
severity:
  positive: [<cat>, ...]
  weak: [<cat>, ...]
  failure: [<cat>, ...]
  neutral: [<cat>, ...]                   # often empty
  insufficient_evidence: [<cat>, ...]     # only "newer" 6-tier judges
suggested_repair_areas:
  - <area>
---
```

Body sections (markdown headings):

- `## Purpose` — short qualitative description (mixed language permitted;
  primary purpose may be German because it was authored that way).
- `## Prompt` — exact prompt text fed to the judge model (English).
- `## Score reasoning prompt` — short rationale prompt.
- `## Category selection prompt` — single-line category-pick prompt.

This source defines:

- Evaluator names
- Evaluator group
- Evaluator purpose
- Prompt text
- Score type
- Categories (order-preserving)
- Severity buckets (positive/weak/failure/neutral/insufficient_evidence)
- Suggested repair areas
- Score reasoning prompt
- Category selection prompt
- Intended qualitative use

MCP analysis code must not rely on stale hardcoded judge lists when they
disagree with `docs/llm-as-a-judge/`. The CSV remains in the directory as a
frozen historical export; the per-evaluator `.md` files are authoritative
going forward.

### Runtime Trace Assumptions

The repository currently uses three canonical trace names, all proven by
code:

- `world-engine.session.create` — opening generation root span
  (world-engine path)
- `backend.turn.execute` — interactive-turn **backend root span**
  (`backend/app/api/v1/session_routes.py`, `backend/app/api/v1/game_routes.py`)
- `world-engine.turn.execute` — interactive-turn **world-engine child span**
  on the same distributed Langfuse trace as `backend.turn.execute`
  (`world-engine/app/api/http.py`)

`backend.turn.execute` and `world-engine.turn.execute` are a **paired
distributed trace**, not alternatives. The Quality Lab must treat them as
two observations on the same Langfuse trace; when only one side is present
on a turn that should have both, that is itself a degradation signal, not a
naming-drift error.

This pairing is already encoded in:

- `ai_stack/langfuse/langfuse_evaluator_catalog.py` —
  `WORLD_ENGINE_TURN_TRACE_NAME` and `BACKEND_TURN_ROOT_TRACE_NAME`;
  `LANGFUSE_TURN_GENERATION_FILTER_BUNDLE.alternate_backend_root_trace_name`.
- `tools/mcp_server/tools_registry_handlers_langfuse_verify.py` —
  documents the pairing in the `distributed_trace_note` field.
- `tools/mcp_server/tests/test_langfuse_verify_tools.py` —
  default `trace_names == ("backend.turn.execute",
  "world-engine.turn.execute")`.
- `backend/tests/test_observability/test_langfuse_live_c640_gate.py` —
  asserts both observations exist on the live trace with matching
  player-input SHA.

The expected generation observation is:

- Observation Type: `GENERATION`
- Observation Name: `story.model.generation`
- Environment: `live`

If code evolves to use different trace names, observation names, or
environment semantics, the tool must report the exact evidence (file path,
line, and current value) before changing its assumptions. The Quality Lab
catalog must derive the canonical trace-name set from
`ai_stack/langfuse/langfuse_evaluator_catalog.py`, not from a literal list.

### MCP wire-form name rewrite

Tool names in this ADR use the canonical dotted form
(`wos.quality_lab.review_trace`). The MCP registry rewrites `.` → `_` on
the wire for Cursor compatibility
(`tools/mcp_server/tools_registry.py::cursor_safe_name`); both forms are
accepted by `tools/call`. Quality Lab tools inherit this behavior — no
extra handling needed.

## Scope

The Quality Lab must cover more than JudgeOps.

It must inspect and reason across the following dimensions.

### 1. MCP Request Quality

The tool must evaluate whether an MCP request is useful and specific enough.

It should detect:

- Missing `trace_id`, `session_id`, `turn_id`, `actor`, or context
- Wrong trace-name assumptions
- Overly broad or vague requests
- Overly narrow requests
- Missing focus area
- Requests that confuse deterministic gates with qualitative judges
- Requests that ask the wrong tool
- Requests that do not provide enough evidence for a meaningful answer

### 2. MCP Response Quality

The tool must evaluate whether an MCP response is actually useful.

It should detect:

- Raw score dumping without interpretation
- Missing distinction between deterministic gates and LLM judges
- Missing category-aware interpretation
- Missing repair direction
- Missing uncertainty labeling
- Unsupported claims
- False runtime conclusions
- Stale assumptions
- Failure to use `docs/llm-as-a-judge`
- Failure to ask useful follow-up questions

### 3. Langfuse Trace Quality

The tool must evaluate whether a trace is suitable for quality analysis.

It should detect:

- Missing `story.model.generation`
- Missing input
- Missing output
- Missing metadata
- Missing usage
- Missing deterministic scores
- Missing LLM judge scores
- Scores attached at the wrong level
- Degraded/fallback/mock traces being treated as healthy
- Trace naming drift
- Observation naming drift
- Missing evaluator coverage

### 4. Judge Coverage and Interpretation

The tool must evaluate judge coverage and category meaning.

It should detect:

- Which judges should have run
- Which judges are missing
- Which judges returned `not_applicable`
- Which judges returned `insufficient_evidence`
- Which categories are positive, weak, failure, neutral, or coverage-related
- Which evaluators overlap
- Which evaluator names are duplicated
- Which categories MCP cannot interpret
- Which judge definitions need maintenance

Judge failures are qualitative findings, not runtime gate failures.

### 5. Runtime Metadata Coverage

The tool must evaluate whether the metadata is sufficient to audit the
turn.

It should inspect whether evidence exists for:

- Runtime aspect ledger
- Path summary
- Degradation chain
- Selected human actor
- Actor lane validation
- Selected beat
- Beat phase / beat intent
- Selected capabilities
- Capability constraints
- Visible blocks
- Visible origin metadata
- Narrator/NPC/player provenance
- Recovery/outcome state
- RAG evidence
- Content module provenance
- Deterministic score evidence

Missing metadata should be reported as an auditability or observability
issue unless it also causes a deterministic runtime gate failure.

### 6. Beat and Capability Realization

The tool must detect when runtime-selected dramatic structures fail to
appear in visible output.

It should detect:

- Selected beat not realized
- Beat realized only as generic prose
- Beat does not advance the scene
- Capability selected but not visible
- Capability contradicted by output
- Capability realization too weak or generic
- Relationship pressure missing despite beat/capability expectations
- Scene function not reflected in output
- No concrete turn delta

### 7. Authority and Origin Problems

The tool must detect authority and provenance issues.

It should detect:

- Narrator displaced by NPCs
- NPCs narrating world state
- NPCs controlling or explaining the selected player actor
- Player actor ownership violations
- Visible block origin mismatch
- Technical/fallback text leaking into player-facing output
- Origin metadata missing or contradictory
- Actor-lane deterministic gate overlap

### 8. Recovery and Playability Problems

The tool must detect whether blocked, impossible, ambiguous, or partial
outcomes remain playable.

It should detect:

- Flat refusals
- Dead-end outcomes
- Unsupported success
- Ignored blocked/ambiguous action
- No concrete next step
- Player agency loss
- Recovery not grounded in fiction
- Recoverable failure not made dramatic or usable

### 9. RAG and Content Problems

The tool must detect whether RAG and content support the runtime.

It should detect:

- RAG not used when needed
- RAG used but irrelevant
- Content module not linked to runtime
- Missing content provenance
- Hardcoded content bindings
- Missing scene pressure
- Missing relationship pressure
- Missing NPC reaction options
- Missing beat affordances
- Missing room/object affordances
- Missing recovery affordances
- Content gaps blocking quality improvement

### 10. Prompt and Context Injection Problems

The tool must detect whether runtime evidence is merely present or actually
used.

It should detect:

- Selected beat present in metadata but not injected as actionable
  instruction
- Capabilities present but not operationalized
- Relationship pressure present but not used
- Origin rules too weak
- Narrator/NPC/player constraints conflicting
- RAG context attached but not used
- Prompt contains generic dramatic instructions without concrete obligations
- Prompt fails to bind runtime evidence to visible output

### 11. Claude-Context Investigation Support

The tool may use claude-context if available.

Claude-context must only be used for targeted, evidence-derived queries.

If claude-context is unavailable, the tool must return suggested
claude-context queries instead of failing.

Example query generation:

For `beat_realization_judge = weak_realization`:

- `selected_beat generation prompt story.model.generation`
- `beat realization runtime graph visible output`
- `beat algorithm selected beat metadata`

For `visible_origin_consistency_judge = contradictory`:

- `visible block origin assignment narrator npc player`
- `visible_blocks origin metadata story.model.generation`
- `actor lane visible block provenance`

For `runtime_aspect_integrity_judge = incomplete`:

- `runtime_aspect_ledger metadata path_summary runtime diagnostics`
- `story.model.generation metadata construction`
- `runtime aspect evidence propagation`

For `relationship_pressure_judge = missing_or_wrong`:

- `relationship pressure prompt content module beat`
- `NPC relationship state scene pressure`
- `god_of_carnage relationship pressure content`

## Non-Goals

The Quality Lab must not:

- Replace ADR-0033
- Replace deterministic runtime gates
- Treat judge failures as runtime truth
- Mutate runtime sessions
- Mutate Langfuse evaluators
- Rewrite prompts automatically
- Rewrite content automatically
- Edit source code automatically
- Weaken actor-lane gates
- Weaken fallback/mock/live separation
- Mark degraded/fallback traces as healthy
- Invent trace names
- Hide uncertainty
- Collapse all judge failures into generic story quality

## Deterministic Gates Remain Authoritative

The following remain deterministic/runtime gate territory:

- ADR-0033 live runtime commit semantics
- `actor_lane_safety_pass`
- `fallback_absent`
- `non_mock_generation_pass`
- `visible_output_present`
- `usage_present`
- `rag_context_attached`
- `live_runtime_contract_pass`
- `live_opening_contract_pass`
- `runtime_session_ready`
- `can_execute`
- `opening_generation_status`

LLM-as-a-Judge outputs may inform:

- qualitative QA
- operator reports
- MCP repair hints
- regression triage
- prompt maintenance
- content revision planning
- runtime investigation

They must not decide runtime truth.

## Implemented Architecture

### Inherit from existing surface (do not greenfield)

Quality Lab **inherits and extends** existing infrastructure rather than
re-bootstrapping it:

| Existing surface | Reused by Quality Lab |
|------------------|-----------------------|
| `ai_stack/langfuse/langfuse_evaluator_catalog.py` — `WOS_CATEGORICAL_JUDGES_ORDER`, `get_categorical_evaluator_spec()`, `OPENING_JUDGE_LANGFUSE_OBSERVATION_FILTERS`, `TURN_JUDGE_LANGFUSE_OBSERVATION_FILTERS`, filter bundles | Source of canonical judge names, trace-name constants, and Langfuse filter templates |
| `tools/mcp_server/tools_registry_handlers_evaluators.py` — `wos.evaluators.catalog`, `wos.evaluators.get` (pure catalog reads) | Quality Lab does not duplicate; instead `wos.quality_lab.review_judgments` calls into the same catalog |
| `tools/mcp_server/tools_registry_handlers_langfuse_verify.py` — `fetch_langfuse_trace`, `fetch_langfuse_trace_scores`, `build_opening_quality_context`, `_build_llm_judge_interpretation`, `_judge_score_coverage_gaps`, `_evaluator_column_metadata`, `normalized_wos_evidence` | Quality Lab composes: `review_trace` consumes `fetch_langfuse_trace` output and shared extraction helpers; `review_judgments` consumes `fetch_langfuse_trace_scores` output and adds semantic interpretation |
| `docs/llm-as-a-judge/` (per-judge `.md` directory + index) | Canonical evaluator definitions; CSV is legacy |

### Compose-and-extend, do not replace

The existing read-only tools remain. Quality Lab tools sit **above** them
and add: MCP exchange analysis, problem clustering across multiple
traces/judges, investigation planning, repair-wave proposals, judge-set
maintenance, content-revision planning, and structured user-decision
prompts. Where a new tool overlaps an existing one (`review_trace` ⊃
`fetch_langfuse_trace`), the new tool accepts the existing tool's output
or uses the same extraction helpers rather than duplicating Langfuse access.

### Package layout

The implementation introduces this package:

```text
ai_stack/quality_lab/
```

Implemented modules:

- `ai_stack/quality_lab/__init__.py`
- `ai_stack/quality_lab/schemas.py`
- `ai_stack/quality_lab/evaluator_catalog.py` — loads per-evaluator markdown frontmatter and severity buckets from `docs/llm-as-a-judge/`
- `ai_stack/quality_lab/judgment_interpreter.py`
- `ai_stack/quality_lab/trace_interpreter.py`
- `ai_stack/mcp/mcp_exchange_interpreter.py`
- `ai_stack/quality_lab/pattern_interpreter.py`
- `ai_stack/quality_lab/planning_interpreter.py`

MCP handlers live in:

- `tools/mcp_server/tools_registry_handlers_quality_lab.py`

Register tools through the existing MCP registry and canonical surface:

- `tools/mcp_server/tools_registry.py`
- `tools/mcp_server/tools_registry_handlers.py`
- `tools/mcp_server/tools_registry_metadata.py`
- `ai_stack/mcp/mcp_canonical_surface.py`

### Canonical-surface registration

Every `wos.quality_lab.*` tool must appear in
`CANONICAL_MCP_TOOL_DESCRIPTORS` with:

- `tool_class = read_only`
- `authority_source = "quality_lab_analysis"` (or per-tool specialization)
- `narrative_mutation_risk = "none"`
- `mcp_suite = wos-runtime-read`

The `wos-runtime-read` suite is the correct home because Quality Lab
**reads** runtime/observability evidence and **never mutates** runtime
state. A dedicated `wos-quality-lab` suite is not introduced; it would
fragment the suite map without benefit.

The new tools must be read-only.

## MCP Tool Surface

### `wos.quality_lab.review_mcp_exchange`

Analyzes an MCP request/response pair.

Input:

```json
{
  "request": {},
  "response": {},
  "focus": [
    "judges",
    "runtime",
    "trace",
    "metadata",
    "content",
    "rag",
    "prompt",
    "mcp_quality"
  ]
}
```

Output includes:

```json
{
  "mcp_request_quality": {},
  "mcp_response_quality": {},
  "missing_context": [],
  "wrong_assumptions": [],
  "recommended_followup_queries": [],
  "improvement_candidates": []
}
```

### `wos.quality_lab.review_trace`

Analyzes a trace or trace-like payload.

Input:

```json
{
  "trace_id": "optional string",
  "trace_name": "optional string",
  "scores": {},
  "input": "optional",
  "output": "optional",
  "metadata": {},
  "include_claude_context": false,
  "focus": [
    "judges",
    "runtime",
    "metadata",
    "beat",
    "capabilities",
    "authority",
    "origin",
    "rag",
    "content"
  ]
}
```

Output includes:

```json
{
  "trace_quality": {},
  "deterministic_runtime_status": {},
  "qualitative_judge_status": {},
  "metadata_coverage": {},
  "problem_clusters": [],
  "improvement_candidates": [],
  "claude_context_queries": [],
  "next_user_decision": {}
}
```

### `wos.quality_lab.review_judgments`

Interprets judge scores using `docs/llm-as-a-judge`.

Input:

```json
{
  "scores": {},
  "input": "optional",
  "output": "optional",
  "metadata": {}
}
```

Output includes:

```json
{
  "judge_interpretations": [],
  "qualitative_issue_clusters": [],
  "repair_area_summary": {},
  "missing_judges": [],
  "coverage_gaps": [],
  "improvement_candidates": []
}
```

### `wos.quality_lab.find_patterns`

Finds recurring quality problems across traces or judge results.

Input:

```json
{
  "trace_summaries": [],
  "judge_results": [],
  "cluster_by": [
    "judge",
    "category",
    "runtime_area",
    "actor",
    "beat",
    "content_module",
    "trace_name"
  ],
  "include_claude_context": false
}
```

Output includes:

```json
{
  "recurring_patterns": [],
  "top_improvement_targets": [],
  "likely_root_causes": [],
  "recommended_repair_waves": [],
  "claude_context_queries": []
}
```

### `wos.quality_lab.suggest_investigation`

Converts a problem cluster into targeted investigation steps.

Input:

```json
{
  "problem_cluster": {},
  "available_context": {},
  "include_claude_context": true
}
```

Output includes:

```json
{
  "hypotheses": [],
  "investigation_steps": [],
  "claude_context_queries": [],
  "mcp_followup_tools": [],
  "evidence_needed": [],
  "user_decision": {}
}
```

### `wos.quality_lab.plan_repair_wave`

Turns improvement candidates into a safe repair plan.

Input:

```json
{
  "improvement_candidates": [],
  "constraints": {
    "no_runtime_gate_weakening": true,
    "no_hardcoded_content": true,
    "modular_only": true
  }
}
```

Output includes:

```json
{
  "repair_waves": [],
  "risks": [],
  "acceptance_criteria": [],
  "tests_to_add": [],
  "do_not_change": []
}
```

### `wos.quality_lab.refine_judge_set`

Analyzes whether judges require maintenance.

Input:

```json
{
  "judge_names": [],
  "observed_failures": [],
  "examples": [],
  "mode": "analysis_only"
}
```

Output includes:

```json
{
  "judge_maintenance_findings": [],
  "prompt_delta_proposals": [],
  "category_delta_proposals": [],
  "new_judge_candidates": [],
  "merge_or_remove_candidates": [],
  "requires_user_review": true
}
```

### `wos.quality_lab.plan_content_revision`

Connects quality findings to possible content gaps.

Input:

```json
{
  "content_module": "optional string",
  "quality_findings": [],
  "scene_or_context": "optional",
  "include_claude_context": false
}
```

Output includes:

```json
{
  "content_gap_hypotheses": [],
  "content_revision_tasks": [],
  "content_questions_for_user": [],
  "claude_context_queries": []
}
```

## Core Schemas

### `QualityFinding`

```json
{
  "finding_id": "string",
  "source": "deterministic_gate | llm_judge | mcp_analysis | langfuse_trace | metadata | rag | content | prompt | claude_context | user_note",
  "source_ref": "string | null",
  "evaluator_name": "string | null",
  "category": "string | null",
  "severity": "info | low | medium | high | critical",
  "confidence": "low | medium | high",
  "affected_area": "string",
  "evidence": [],
  "interpretation": "string",
  "suggested_repair_area": "string | null",
  "deterministic_gate_related": false,
  "runtime_gate_failure": false,
  "qualitative_only": true,
  "needs_more_evidence": false
}
```

### `ProblemCluster`

```json
{
  "cluster_id": "string",
  "title": "string",
  "affected_areas": [],
  "affected_judges": [],
  "affected_traces": [],
  "repeated_categories": [],
  "evidence": [],
  "likely_causes": [],
  "confidence": "low | medium | high",
  "severity": "info | low | medium | high | critical",
  "frequency": "integer | null",
  "next_best_investigation": "string"
}
```

### `ImprovementCandidate`

```json
{
  "candidate_id": "string",
  "title": "string",
  "priority": "low | medium | high | urgent",
  "severity": "info | low | medium | high | critical",
  "confidence": "low | medium | high",
  "affected_judges": [],
  "affected_runtime_areas": [],
  "affected_content_areas": [],
  "evidence": [],
  "suspected_causes": [],
  "recommended_actions": [],
  "claude_context_queries": [],
  "prompt_revision_relevance": "none | low | medium | high",
  "runtime_revision_relevance": "none | low | medium | high",
  "content_revision_relevance": "none | low | medium | high",
  "mcp_analysis_revision_relevance": "none | low | medium | high",
  "langfuse_config_relevance": "none | low | medium | high",
  "judge_definition_relevance": "none | low | medium | high",
  "requires_user_decision": true,
  "decision_options": []
}
```

### `UserDecisionPrompt`

The `next_user_decision` / `decision_options` / `requires_user_decision`
fields define a **structured human-AI co-decision contract**. Quality Lab
is read-only and stateless; it cannot resolve open questions on its own.
Instead, it surfaces concrete choices for the operator (or for a coding AI
acting on the operator's behalf — Claude Code, Codex, Cursor) so the human
makes the call and the AI tool can act on the answer.

```json
{
  "requires_user_decision": true,
  "context_summary": "string — one-paragraph problem statement quoting evidence",
  "question": "string — the actual question being asked, single sentence",
  "decision_options": [
    {
      "id": "string — stable token, e.g. \"compose_with_existing_handler\"",
      "label": "string — short human label, 3-8 words",
      "description": "string — what choosing this option means in practice",
      "ai_action": "string — what an AI tool should do if the user picks this",
      "tradeoff": "string — what is given up by choosing this",
      "recommended": false
    }
  ],
  "evidence_refs": [
    { "type": "file | trace | score | judge | adr", "ref": "string" }
  ]
}
```

Contract rules:

- The tool itself does not pick an option. `recommended: true` is allowed
  on at most one option and reflects evidence-weighted preference; it is
  not a decision.
- `ai_action` must be specific enough that another coding AI can execute
  it without re-asking the user (e.g. `"Add ai_stack/quality_lab/evaluator_catalog.py
  that re-exports get_categorical_evaluator_spec()"`).
- `evidence_refs` must point to real artifacts (file paths, trace IDs,
  ADR ids). No invented references.
- Consumers (operators, coding AIs) read this surface and resolve via the
  normal MCP/repository workflow. The Quality Lab does not call back.

### `McpExchangeQuality`

```json
{
  "request_specificity": "low | medium | high",
  "context_completeness": "low | medium | high",
  "tool_choice_quality": "poor | acceptable | good",
  "assumption_risk": "low | medium | high",
  "response_evidence_quality": "low | medium | high",
  "response_actionability": "low | medium | high",
  "deterministic_vs_qualitative_separation": "poor | acceptable | good",
  "missing_followups": [],
  "recommended_next_request": "string"
}
```

## Evaluator Groups

The Quality Lab must recognize evaluator groups.

At minimum:

- Runtime aspect integrity
- Authority and origin
- Dramatic runtime realization
- Recovery and playability
- Player action resolution
- RAG/content usefulness
- Language/style/cleanliness
- Actor-lane/narrative boundary
- Opening quality
- Turn relevance

Known new evaluators include:

- `runtime_aspect_integrity_judge`
- `narrator_authority_judge`
- `npc_authority_violation_judge`
- `dramatic_capability_realization_judge`
- `beat_realization_judge`
- `visible_origin_consistency_judge`
- `recoverable_outcome_quality_judge`
- `relationship_pressure_judge`
- `player_turn_playability_judge`, if present

Existing older evaluators must remain supported, but older hardcoded lists
must not define the full evaluator universe.

## Category Severity Interpretation

For every evaluator from `docs/llm-as-a-judge`, the Quality Lab must define:

- `evaluator_group`
- `positive_categories`
- `weak_categories`
- `failure_categories`
- `neutral_categories`
- `insufficient_evidence_categories`
- `suggested_repair_areas`

Examples:

- `beat_realization_judge = weak_realization`
  - qualitative issue
  - group: Dramatic runtime realization
  - likely repair areas: beat algorithm, prompt injection, runtime beat
    metadata, content beat affordances

- `visible_origin_consistency_judge = contradictory`
  - qualitative issue with possible deterministic overlap
  - group: Authority and origin
  - likely repair areas: visible block origin assignment, actor-lane
    boundary, narrator/NPC/player provenance

- `runtime_aspect_integrity_judge = incomplete`
  - qualitative auditability issue
  - group: Runtime aspect integrity
  - likely repair areas: metadata propagation, runtime aspect ledger, path
    summary, diagnostics

- `recoverable_outcome_quality_judge = failed_recovery`
  - qualitative playability issue
  - group: Recovery and playability
  - likely repair areas: blocked action handling, outcome routing, recovery
    affordances, content support

- `relationship_pressure_judge = missing_or_wrong`
  - qualitative dramatic pressure issue
  - group: Dramatic runtime realization
  - likely repair areas: relationship state, NPC reaction model, beat
    pressure, content module

## Output Requirements

All Quality Lab tools must distinguish:

- deterministic runtime failure
- qualitative judge concern
- missing evidence
- missing expected judge score
- `not_applicable` judge result
- `insufficient_evidence` judge result
- coverage gap
- configuration gap
- analysis gap

Missing judge scores are evaluator coverage gaps unless there is
deterministic evidence of a runtime failure.

LLM judge failures are qualitative findings unless correlated with
deterministic runtime gate failures.

## Documentation Requirements

Document the Quality Lab tools.

At minimum, update relevant MCP/observability documentation to explain:

- What Quality Lab analyzes
- What it does not decide
- How it uses `docs/llm-as-a-judge`
- How it separates runtime truth from qualitative judgment
- How claude-context is used
- How content revision candidates are produced
- Why it is read-only
- Why `backend.turn.execute` must not be assumed

Possible docs to update:

- `docs/mcp/07_M0_observability.md`
- `docs/mcp/05_M0_tool_inventory_v0.md`
- `docs/MVPs/MVP_MCP/README.md`
- `docs/MVPs/MVP_MCP_Operations_Cockpit_WoS/README.md`
- `docs/technical/operations/observability-and-governance.md`

Do not duplicate the full judge table into every doc. Reference
`docs/llm-as-a-judge` as canonical.

## Testing Requirements

Add tests for:

- evaluator catalog loading
- category severity mapping
- deterministic vs qualitative separation
- trace-name set validation **including** the `backend.turn.execute` +
  `world-engine.turn.execute` distributed-trace pairing — the test must
  derive the expected names from
  `ai_stack/langfuse/langfuse_evaluator_catalog.py`, never from a literal list
- `docs/llm-as-a-judge/` ↔ code **drift detection** (mandatory): a test
  asserts that the set of evaluator names in
  `WOS_CATEGORICAL_JUDGES_ORDER` matches the set of per-evaluator `.md`
  files in `docs/llm-as-a-judge/` exactly (no extras either side), and
  that each file's frontmatter `categories` matches what the code
  expects via `get_categorical_evaluator_spec()`. Drift in either
  direction fails CI.
- MCP exchange analysis
- judgment review semantic interpretation
- missing judge score handling
- missing metadata handling
- weak beat + weak relationship pressure clustering
- contradictory origin clustering
- incomplete runtime aspect clustering
- failed recovery clustering
- claude-context query generation
- repair wave planning
- read-only behavior
- invalid judge name handling
- `decision_options` schema conformance — every emitted `decision_options`
  array satisfies `UserDecisionPrompt`; `ai_action` is non-empty and
  `evidence_refs` resolve

Tests must obey **ADR-0039**: derive expected judge names, categories, and
severity buckets from the canonical catalog / `docs/llm-as-a-judge/`
directory. Hardcoded literal lists in test bodies are forbidden ("no
example-shaped bypass").

Implemented test files:

- `ai_stack/tests/test_quality_lab_evaluator_catalog.py`
- `ai_stack/tests/test_quality_lab_judgment_interpreter.py`
- `ai_stack/tests/test_quality_lab_trace_interpreter.py`
- `ai_stack/tests/test_quality_lab_mcp_exchange_interpreter.py`
- `ai_stack/tests/test_quality_lab_pattern_and_planning.py`
- `tools/mcp_server/tests/test_quality_lab_tools.py`

## Rollout Plan

### Phase 1: Evaluator Catalog and Judge Interpretation — Implemented

- Load or mirror `docs/llm-as-a-judge`
- Interpret categories semantically
- Separate qualitative judge concerns from deterministic gates
- Add `wos.quality_lab.review_judgments`

### Phase 2: Trace and Metadata Analysis — Implemented

- Add trace-like payload analysis
- Detect missing input/output/metadata
- Detect missing generation observation
- Detect score coverage gaps
- Add `wos.quality_lab.review_trace`

### Phase 3: MCP Exchange Analysis — Implemented

- Analyze MCP request/response quality
- Detect stale assumptions
- Detect weak analysis responses
- Add `wos.quality_lab.review_mcp_exchange`

### Phase 4: Problem Clustering and Investigation — Implemented

- Group recurring issues
- Generate claude-context queries
- Add `wos.quality_lab.find_patterns`
- Add `wos.quality_lab.suggest_investigation`

### Phase 5: Repair Planning and Maintenance — Implemented

- Add repair-wave planning
- Add judge-set maintenance proposals
- Add content-revision planning
- Add:
  - `wos.quality_lab.plan_repair_wave`
  - `wos.quality_lab.refine_judge_set`
  - `wos.quality_lab.plan_content_revision`

## Acceptance Criteria

The ADR is satisfied when:

- `docs/llm-as-a-judge` is treated as the canonical evaluator definition
  source.
- MCP Quality Lab tools are read-only.
- The tools can analyze MCP request/response quality.
- The tools can analyze a trace-like payload with scores, output, and
  metadata.
- The tools can interpret evaluator categories semantically.
- The tools can detect missing evidence and evaluator coverage gaps.
- The tools can cluster problems into runtime, prompt, content, RAG, MCP,
  Langfuse, and judge-definition areas.
- The tools can generate targeted claude-context queries.
- The tools can produce prioritized improvement candidates.
- The tools can ask focused user decision questions.
- The tools do not mutate runtime, Langfuse, prompts, content, or code.
- Existing deterministic runtime gates remain authoritative.
- Existing older judges remain supported.
- Newer judges are not ignored or collapsed into generic story-quality
  summaries.
- Trace-name handling derives from `ai_stack/langfuse/langfuse_evaluator_catalog.py`
  and treats `backend.turn.execute` / `world-engine.turn.execute` as a
  paired distributed turn trace, not as competing canonical names.

## Consequences

### Positive

- MCP analysis becomes more actionable.
- Judge results become semantically meaningful instead of raw category
  strings.
- Runtime, prompt, content, RAG, Langfuse, and MCP-analysis issues can be
  separated.
- claude-context can be used in a targeted and evidence-derived way.
- Content revision can be guided by actual quality findings.
- Judge maintenance becomes structured and reviewable.
- Deterministic runtime gates remain protected.

### Negative / Risks

- The Quality Lab can become too broad if not phased carefully.
- Category mappings must be maintained when evaluator definitions change.
- Human-maintained CSV/document definitions may drift from code if no
  validation exists.
- Overinterpretation risk exists if the tool treats weak evidence as proof.
- claude-context integration must remain targeted to avoid noisy searches.

### Mitigations

- Keep tools read-only.
- Require confidence and evidence fields.
- Report missing evidence explicitly.
- Add tests for deterministic/qualitative separation.
- Add tests that detect stale `backend.turn.execute` rejection assumptions.
- Keep `docs/llm-as-a-judge` canonical.
- Use phased implementation.
