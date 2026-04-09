# What is World of Shadows?

## What it is

**World of Shadows** is a narrative game and community platform delivered as **several cooperating services**. Players use a **public web application**; operators use a **separate admin application**. A **backend** service provides APIs, accounts, and persistence. A **play service** (the **world-engine**) runs **live story sessions**—scene flow, turns, and authoritative session state—according to authored content and strict runtime rules.

The repository README also introduces the product line as **Better Tomorrow (World of Shadows)**. This documentation primarily uses **World of Shadows** as the public name.

## What problem it solves

- **Separation of concerns:** Player experience, admin workflows, platform API, and runtime execution are isolated so teams can scale and secure each surface.
- **Authoritative play:** The play service is the **runtime authority** for story sessions; models propose content, but **validation and commit** follow platform contracts (see [How AI fits the platform](how-ai-fits-the-platform.md)).
- **Canonical content:** Authored stories live as **modules** under `content/modules/` (YAML and related assets), compiled for runtime, retrieval, and review projections.

## Major pieces (names you will see)

| Piece | Role |
|-------|------|
| `frontend/` | Player/public web UI |
| `administration-tool/` | Admin and management UI |
| `backend/` | API, auth, database, content pipeline |
| `world-engine/` | Play service: authoritative sessions and WebSocket gameplay |
| `ai_stack/` | Retrieval, LangGraph turn graph (GoC slice), LangChain adapters, capabilities |
| `story_runtime_core/` | Shared models, registry, interpretation contracts |
| `content/modules/` | Canonical authored modules (including **God of Carnage**) |
| `writers-room/` | Optional demo UI calling backend Writers Room APIs |
| `tools/mcp_server/` | MCP tooling for developers/operators (read-heavy in current phases) |

## Where to go next

- **How services connect:** [System map: services and data stores](system-map-services-and-data-stores.md)
- **First dramatic slice:** [God of Carnage as an experience](god-of-carnage-as-an-experience.md)
- **Plain-language system story:** [How World of Shadows works](how-world-of-shadows-works.md)
- **Definitions:** [Glossary](../reference/glossary.md)
