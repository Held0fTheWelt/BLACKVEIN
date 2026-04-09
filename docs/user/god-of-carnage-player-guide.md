# God of Carnage — player guide

**God of Carnage** is a **scene-led dramatic experience**: you play through a structured narrative slice with **free-text input** interpreted in context. This guide sets expectations for **players**. Engineering contracts are linked for curiosity, not required reading.

## What to expect

- **Grounded scenes:** the system interprets what you type in light of the **current scene** and story state.
- **Truth-aligned turns:** visible story progress follows **validated** outcomes—there is a real distinction between “what the model suggested” and “what the game accepted” (see [How AI fits the platform](../start-here/how-ai-fits-the-platform.md) if you want the short technical version).
- **Bounded slice:** the MVP slice focuses on this module’s dramatic arc; do not expect open-world improvisation beyond the slice design.

## How to play (typical flow)

1. Sign in on the **player frontend**.
2. Open the **play** or **God of Carnage** entry point your deployment exposes.
3. Read scene context and prompts shown by the UI.
4. Type **natural language** actions or dialogue; use any **on-screen buttons** or quick actions the UI provides.
5. Continue turn by turn; if the experience offers **choices** or **clarifications**, follow UI cues.

## Tips

- **Stay in scene:** references and actions that fit the scene are more likely to produce coherent drama.
- **If stuck:** try shorter, clearer input; some deployments surface **operator hints** or diagnostics only to staff—not to players.
- **Mature themes:** God of Carnage is adult dramatic material; operator policy may gate access.

## What players do **not** need

- Internal **contracts**, **gates**, or **audit** documents under `docs/audit/`.
- **MCP** or **developer** tooling documentation.

## For operators and developers

- Slice definition: `docs/VERTICAL_SLICE_CONTRACT_GOC.md`
- Turn semantics: `docs/CANONICAL_TURN_CONTRACT_GOC.md`
- Experience overview: [God of Carnage as an experience](../start-here/god-of-carnage-as-an-experience.md)

## Related

- [Getting started](getting-started.md)
- [Glossary](../reference/glossary.md) — vertical slice, play service, proposal vs commit
