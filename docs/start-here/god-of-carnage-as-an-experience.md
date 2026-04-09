# God of Carnage as an experience

**God of Carnage (GoC)** is the first **MVP vertical slice** of World of Shadows: a **guided interactive drama**—scene-led, with **truth-aligned turns**—not a generic open-ended chat toy. Normative engineering detail lives in slice contracts; this page explains the **human-visible idea**.

## What the player experiences

- **Free language input** interpreted in the context of the **current scene** and module state.
- **Scene-grounded** responses: the system selects dramatic parameters (responders, scene function, pacing) consistent with authored YAML and slice vocabulary.
- **Visible output** that reflects **validated** outcomes: proposals from models pass through **validation** and **commit** seams before they become committed narrative state (developer detail: `docs/CANONICAL_TURN_CONTRACT_GOC.md`).

## Where the story comes from

- **Canonical source:** the module tree `content/modules/god_of_carnage/` (YAML: scenes, characters, triggers, transitions, endings, etc.).
- **Builtins / templates** in code may exist for bootstrapping demos but **must not silently override** YAML truth for this slice; see `docs/VERTICAL_SLICE_CONTRACT_GOC.md` §6.

## What “slice” means for scope

The vertical slice contract defines **in scope** and **out of scope** behavior (multi-module improvisation, unconstrained roleplay, etc.). For product and freeze language, see `docs/VERTICAL_SLICE_CONTRACT_GOC.md` and `docs/ROADMAP_MVP_VSL.md` as referenced there.

## Repository reality (honest status)

Engineering cleanup and **control** artifacts have progressed through audit Tasks 1–4, but **physical namespace movement** of GoC assets (renames/moves beyond current hard-couplings) remains **gated**; do **not** assume a completed “GoC renamespace” from documentation alone. See `docs/audit/TASK_4_FINAL_CLEANUP_CLOSURE_REPORT.md` and `docs/presentations/goc-vertical-slice-stakeholder-brief.md`.

## For different readers

- **Players:** [God of Carnage player guide](../user/god-of-carnage-player-guide.md)
- **Developers:** [Normative contracts index](../dev/contracts/normative-contracts-index.md), [AI stack and GoC seams](../dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md)
- **Stakeholders:** [GoC vertical slice stakeholder brief](../presentations/goc-vertical-slice-stakeholder-brief.md)
