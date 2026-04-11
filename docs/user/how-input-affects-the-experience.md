# How input affects the experience

Players usually interact by **typing** in the play UI. The system interprets your text using the **current scene**, **roles**, and **module** configuration, then updates what you see after **runtime processing**.

## Natural language first

You do **not** need to memorize commands. Describe what your character **does** or **says** in plain language. The play service may still recognize explicit command-style phrases when the module defines them.

## What you see is already processed

You receive **rendered** outcomes—dialogue, scene changes, and UI updates—after the backend and play service apply **validation and commit** rules. You should **not** expect to see raw, unreviewed model drafts as canonical story text.

## Patterns you might notice

Depending on the module and UI version, you may use patterns such as speaking, acting, inspecting, moving, or choosing from presented options. Follow **on-screen prompts** first; exact verbs differ by deployment.

## Multiplayer

When multiple people share a session, take turns as the UI indicates so the scene stays coherent.

## Related

- [Runtime interactions (player-visible)](runtime-interactions-player-visible.md)
- [How AI fits the platform](../start-here/how-ai-fits-the-platform.md) (conceptual)
- [Glossary](../start-here/glossary.md)
