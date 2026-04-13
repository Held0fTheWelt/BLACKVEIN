# God of Carnage vertical slice — stakeholder brief

**Slide-deck / one-pager source.** Technical contracts exist separately; this is **decision-grade** narrative for stakeholders.

---

## Positioning

**God of Carnage (GoC)** is the **first MVP vertical slice** of World of Shadows: a **guided interactive drama** with **truth-aligned turns**—not open-ended roleplay or a generic chatbot.

## Player value

- Scene-grounded interpretation of **natural language** input.
- Dramatic pacing and visibility classes **bound** to authored YAML and frozen vocabulary.
- Visible outcomes reflect **validated** state changes, not raw model improvisation.

## Engineering reality (honest status)

- **Implemented:** LangGraph-based turn graph for GoC, RAG hooks, validation/commit seams — see `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §3 for the code-facing anchor table.
- **Governance:** extensive **contracts** and **quality gates** protect slice semantics.
- **Structural normalization:** Task 4 **control closure** is **complete**, but **physical GoC namespace movement / renamespace** remains **NO-GO** until `docs/audit/TASK_4_GOC_DEPENDENCY_SUFFICIENCY_RECORD.md` lifts the dependency gate (`docs/audit/TASK_4_FINAL_CLEANUP_CLOSURE_REPORT.md`). **Do not** claim renamespace completion in external comms.

## Dependencies and risks

- **Cross-stack coupling:** `backend/`, `world-engine/`, `ai_stack/`, `content/modules/god_of_carnage/`, schemas, tests, MCP tooling — coordinated changes only (`docs/audit/TASK_1B_CROSS_STACK_COHESION_BASELINE.md`).
- **Duplicate-truth risk:** parallel narrative assets under `writers-room/` vs canonical YAML — product must declare **which is authoritative** for customer-facing story edits.

## Roadmap relationship

- `docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_VSL.md` and related roadmap files describe **targets**; stakeholder decks must label **aspirational** vs **delivered** to avoid over-claiming.

## Suggested slides

1. Title — God of Carnage slice
2. Experience promise (3 bullets)
3. Architecture thumbnail (frontend → backend → play service)
4. “How AI helps” (propose → validate → commit)
5. Status — shipped elements vs gated structural work
6. Risks & mitigations (dependency gate, contracts, tests)
7. Next milestone / ask

## Related (internal)

- [God of Carnage as an experience](../start-here/god-of-carnage-as-an-experience.md)
- [Executive summary](executive-summary-world-of-shadows.md)
- [Normative contracts index](../dev/contracts/normative-contracts-index.md)
