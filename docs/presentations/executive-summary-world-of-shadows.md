# Executive summary — World of Shadows

**Slide-deck source (Markdown outline).** Export to slides/PDF per your template. Audience: **executives, partners, investors**—not engineers.

---

## Slide 1 — Title

- **World of Shadows** — multi-service narrative platform
- Tagline (optional): product line naming as approved (`Better Tomorrow` vs `World of Shadows` — align with leadership)

## Slide 2 — Problem / opportunity

- Interactive drama and community need **reliable** runtime authority, not “chatbot only” experiences.
- Goal: **scene-led** narrative with **governed AI** assistance.

## Slide 3 — What we ship (containers)

- **Player web app** → **Backend API** + **Play service** (authoritative sessions)
- **Admin web app** → **Backend API**
- **Database** + **canonical content modules** (`content/modules/`)

*Diagram:* C4 context from [System map](../start-here/system-map-services-and-data-stores.md).

## Slide 4 — MVP vertical slice

- **God of Carnage** — first dramatic slice; YAML-authored, contract-bound.
- **Honest scope:** roadmap docs describe **targets**; label **shipped vs planned** in verbal pitch.

## Slide 5 — AI without handing over truth

- Models **propose**; runtime **validates and commits**.
- Retrieval + orchestration support grounding; **policy** stays in platform code.

## Slide 6 — Risk posture (high level)

- Cross-stack coupling (backend, play service, AI stack, content) — requires disciplined seams.
- **Documentation and audit** program tracks dependency gates; **not all structural moves are complete** (see GoC brief).

## Slide 7 — Ask / next milestone

- Define your milestone (e.g. freeze exit, production pilot, partner demo).
- Link deeper reading: [Start here](../start-here/README.md) (internal), this summary (external-safe after redaction).

---

## Speaker notes

- Avoid internal **task IDs** and **gate** vocabulary unless audience is technical.
- If asked about **renames/moves** of GoC assets: cite **Task 4 NO-GO** on physical namespace movement until dependency record lifts — see [GoC stakeholder brief](goc-vertical-slice-stakeholder-brief.md).
