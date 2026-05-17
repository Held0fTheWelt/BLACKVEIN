---
name: language_consistency_judge
group: language_style_cleanliness
score_type: categorical
categories:
  - consistent
  - minor_drift
  - mixed_language
  - wrong_language
severity:
  positive: [consistent]
  weak: [minor_drift, mixed_language]
  failure: [wrong_language]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - session_output_language enforcement
  - session_input_language / internal-normalization leakage
  - output-language enforcement on narrator/NPC blocks
  - scaffold / system-language leakage suppression
---

# language_consistency_judge

## Purpose

Bewertet, ob die Sprache des Outputs konsistent zur erwarteten Spielsitzung
bleibt. Erkennt Sprachwechsel, Mischsprache oder falsche Ausgabesprache.

## Prompt

You are evaluating language consistency in player-facing visible output.

This is a qualitative review signal only. Do not judge backend
implementation quality.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the visible output follows the expected session language.

For German sessions:
- German visible prose is expected.
- Names such as Véronique, Alain, Annette, Michel are allowed.
- A brief foreign-language quote may be acceptable only if clearly
  intentional.
- English stage direction such as “gently nods” is not acceptable.
- French dialogue should not appear unless specifically justified by the
  scene.

Pay attention to:
- English narrator or stage-direction leaks
- French dialogue drift in a German session
- mixed German/English/French inside one card
- internal prompt language leaking into visible text
- whether the output language matches metadata if available
- whether internal English normalization or semantic grounding labels leaked
  into player-visible prose

Rubric:

consistent:
The visible output consistently follows the expected session language.
Names are allowed.

minor_drift:
There is a small foreign-language fragment or stylistic drift, but the
output remains mostly in the expected language.

mixed_language:
The output noticeably mixes languages in a way that harms readability or
immersion.

wrong_language:
The output is mostly in the wrong language or contains clear
prompt/scaffold-language leakage.

## Score reasoning prompt

Explain briefly why this category best matches language consistency.
Mention the expected language and any visible drift or language leakage.

## Category selection prompt

Choose exactly one category: consistent, minor_drift, mixed_language, or
wrong_language. Select wrong_language when the output is mostly not in the
expected session language.
