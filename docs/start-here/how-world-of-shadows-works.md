# How World of Shadows works

This page is the **plain-language** bridge between “what it is” and “how do I use or run it.” For definitions, see the [glossary](glossary.md). For containers and ports, see [System map: services and data stores](system-map-services-and-data-stores.md).

## The story in one pass

1. **Authors** maintain narrative modules as structured files (chiefly YAML) under `content/modules/`. The **backend** loads and **compiles** those modules into projections the rest of the stack can consume.
2. **Players** use the **frontend** in a browser. They sign in through the backend, open play, and connect to the **play service** (world-engine) for live sessions.
3. The **play service** owns **live session state** and **turn execution**. When a turn uses AI assistance, models **propose** text and structure; **runtime rules** decide what becomes **committed** story state.
4. **Operators** use the separate **administration tool** for governance, diagnostics, and configuration—always through the backend APIs, not by reaching into player-only flows.
5. **Retrieval (RAG)** and **orchestration** (LangGraph/LangChain in `ai_stack/`) support turns and review workflows, but they do **not** replace runtime authority.

## Where “truth” lives

| Kind of truth | Primary owner |
|---------------|---------------|
| Platform accounts, forum, news, wiki | Backend + database |
| Authored module source | `content/modules/` (files) |
| Compiled module projections | Backend content pipeline |
| Live play session + committed turn history | Play service (world-engine) |
| AI proposals before validation | Ephemeral / diagnostic until committed |

## AI in one sentence

AI **assists** turns; **you** (through runtime contracts) **decide** what counts as committed narrative. See [How AI fits the platform](how-ai-fits-the-platform.md) and, for engineers, [`docs/technical/ai/ai-stack-overview.md`](../technical/ai/ai-stack-overview.md).

## God of Carnage

The first vertical slice is **God of Carnage**—a scene-led dramatic module with explicit contracts binding content, runtime, and tests. Start with [God of Carnage as an experience](god-of-carnage-as-an-experience.md).

## Related

- [What is World of Shadows?](what-is-world-of-shadows.md)
- [User documentation root](../user/README.md)
- [Admin documentation root](../admin/README.md)
- [Developer documentation root](../dev/README.md)
