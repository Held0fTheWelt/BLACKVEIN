---
name: visible_card_cleanliness_judge
group: language_style_cleanliness
score_type: categorical
categories:
  - clean
  - minor_artifacts
  - messy
  - broken_cards
severity:
  positive: [clean]
  weak: [minor_artifacts, messy]
  failure: [broken_cards]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - visible block projection / folding
  - duplicate detection on adjacent cards
  - card formatting and label suppression
  - actor_line / actor_action deduplication
---

# visible_card_cleanliness_judge

## Purpose

Bewertet die Sauberkeit der sichtbaren Karten. Achtet auf doppelte Inhalte,
Name-only Cards, Label-Stottern, technische Artefakte oder falsch
zusammengeführte Action-/Speech-Texte.

## Prompt

You are evaluating the cleanliness of player-facing visible story cards.

This is a qualitative UI/content review signal only. Do not judge backend
implementation quality.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the visible card text is clean, readable, non-duplicative,
and free from internal artifacts.

Pay attention to:
- name-only cards such as “Veronique”
- speaker stutter such as “Veronique: Veronique ...”
- duplicated action in adjacent cards
- actor_line and actor_action repeating the same content
- internal labels such as narrator_intro:, role_anchor:, scene_setup:
- placeholder phrases such as “reacts immediately”
- broken quote formatting
- repeated speaker labels inside one card
- unnecessary blue/action card duplication when the action is already
  folded into a story card

Rubric:

clean:
The visible cards are readable, well formatted, and free from obvious
duplication or internal artifacts.

minor_artifacts:
There are small formatting issues, but they do not seriously harm
playability.

messy:
The output has noticeable duplicated cards, label stutter, awkward
formatting, or repeated action text.

broken_cards:
The card output is visibly broken, with name-only cards, repeated labels,
debug/internal text, or severe duplication.

## Score reasoning prompt

Explain briefly why this category best matches visible card cleanliness.
Mention duplicated cards, name stutter, internal labels, or formatting
artifacts if present.

## Category selection prompt

Choose exactly one category: clean, minor_artifacts, messy, or
broken_cards. Select broken_cards when visible card formatting seriously
harms playability.
