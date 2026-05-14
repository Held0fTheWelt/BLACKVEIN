---
name: rag_context_usefulness_judge
group: rag_content_usefulness
score_type: categorical
categories:
  - strong_use
  - some_use
  - unused
  - misused
severity:
  positive: [strong_use]
  weak: [some_use, unused]
  failure: [misused]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - RAG retrieval scope
  - context pack assembly / token budget
  - prompt injection of retrieved context
  - content module fact coverage
---

# rag_context_usefulness_judge

## Purpose

Bewertet, ob bereitgestellter RAG-Kontext sinnvoll genutzt wurde. Erkennt,
ob Kontext hilfreich eingebunden, ignoriert oder falsch/verzerrt verwendet
wurde.

## Prompt

You are evaluating whether the generated output meaningfully uses the
provided World of Shadows / God of Carnage context.

Evaluate only context use and faithfulness. Do not judge backend
implementation quality. Do not reward the mere presence of retrieved
context; judge whether the output uses it well.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the generated output uses the provided context in a useful,
faithful, and relevant way.

Pay attention to:
- whether the output reflects the provided scene, role, phase, premise,
  constraints, or character context
- whether the output uses relevant context rather than ignoring it
- whether it invents unsupported facts that conflict with the context
- whether it preserves the intended God of Carnage / World of Shadows
  setup
- whether the selected player role and scene premise align with the
  context
- whether the output is generic despite receiving specific context
- whether the context is overused mechanically or copied without dramatic
  integration

Rubric:

strong_use:
The output clearly and naturally uses relevant provided context. It
reflects the scene premise, role setup, constraints, and dramatic
situation while remaining faithful and playable.

some_use:
The output uses some relevant context, but only partially. It may be
broadly aligned but misses important details, role specifics, or scene
constraints.

unused:
The output appears generic or disconnected from the provided context. It
could have been generated without the retrieved material.

misused:
The output contradicts, distorts, or invents facts against the provided
context. It may use the wrong role, wrong scene premise, wrong
relationship, or unsupported story facts.

## Score reasoning prompt

Explain briefly why this category best matches the context use. Mention
whether the output uses, partially uses, ignores, or contradicts the
provided context.

## Category selection prompt

Choose exactly one category: strong_use, some_use, unused, or misused.
Select misused if the output contradicts or distorts the provided context.
Select unused if the output is generic or disconnected from the context.
