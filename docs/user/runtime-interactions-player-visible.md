# Runtime interactions (player-visible)

What players typically **do** in live play: interactions supported by the **play service** and frontend. This is **not** a developer API reference.

> Note: `docs/features/RUNTIME_COMMANDS.md` begins with a **historical / non-canonical** section for an external CLI workflow. For in-product play, rely on this page and your deployment’s UI.

## Natural language

The primary interaction mode is **typing what your character does or says** in the play UI. The system interprets input using the **current scene**, **roles**, and **module** configuration.

## Common interaction patterns

Depending on module and UI version, you may see patterns such as:

- **Say / emote / act** — express dialogue or bodily action in fiction.
- **Inspect / look** — ask for more detail about people, objects, or the environment when the story supports it.
- **Move / go** — change location when transitions are authored for the scene.
- **Choose** — explicit choices or buttons when the UI presents decision points.

Exact verbs and affordances are **deployment- and module-specific**; follow on-screen prompts first.

## Multiplayer sessions

Some deployments support **multiple participants** in a session:

- Take turns according to UI cues.
- Avoid overlapping actions that confuse scene focus if the UI warns you.

## What players should not expect

- Direct access to **admin** or **internal diagnostics** screens.
- Raw **model transcripts** or **unvalidated** proposal text as committed canon—players see **rendered** outcomes after runtime processing.

## Operators and developers

- Feature overview (broader than GoC): `docs/features/README.md` (Game & Runtime section).
- Architecture: [System map](../start-here/system-map-services-and-data-stores.md), [Runtime authority and state flow](../technical/runtime/runtime-authority-and-state-flow.md).

## Related

- [God of Carnage player guide](god-of-carnage-player-guide.md)
- [Glossary](../reference/glossary.md)
