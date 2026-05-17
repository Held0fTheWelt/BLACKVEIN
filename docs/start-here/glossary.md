# Glossary (start here)

Short orientation for **non-developers**. For the **full, maintained** term list (normative where marked), see **[`docs/reference/glossary.md`](../reference/glossary.md)**.

| Term | Plain meaning |
|------|----------------|
| **Better Tomorrow** | The product title for the narrative game and community platform. |
| **World of Shadows** | Subtitle and world/platform context for Better Tomorrow; also historical shorthand in older engineering docs. |
| **Play service / world-engine** | The service that runs **live story sessions** and owns committed play state for those sessions. |
| **Backend** | The API and database service for accounts, forum, content compilation, admin features, and integration with the play service. |
| **Frontend** | The player-facing website. |
| **Administration tool** | The separate admin web app for operators. |
| **Module** | A packaged story configuration (files under `content/modules/<id>/`). |
| **God of Carnage (GoC)** | The first full vertical slice module and its contracts. |
| **Turn** | One cycle of player input, processing, and updated session state in live play. |
| **Proposal vs commit** | AI may **propose** content; only **validated, committed** results become authoritative narrative state. |
| **Runtime aspect ledger** | The backend/world-engine evidence record that explains whether important runtime contracts passed. |
| **EnvironmentState** | The committed room/object/actor-location state for a live story session; narration may describe it, but only committed/admitted actions change it. |
| **Callback web** | A bounded continuity index that links later committed turns back to earlier committed turns using structured evidence; it helps diagnostics and context, but it is not canon itself. |
| **Subtext interpretation** | A bounded diagnostic surface for what a player move appears to do and what scene-pressure function it may carry; it shapes planning but does not create story truth. |
| **Dramatic irony** | A bounded runtime contract for private-plan asymmetry: the model may show approved subtext, behavior, or misread reactions, but must not reveal hidden NPC intent directly. |
| **Information disclosure** | The runtime’s bounded reveal-control system: it decides which mystery/clue units may surface now and records if the model stayed inside that budget. |
| **RAG** | Retrieval over project documents to **inform** generation—does not override runtime authority. |

When you implement behavior, use the [normative contracts index](../dev/contracts/normative-contracts-index.md) and [`docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md`](../MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md) instead of this short table alone.
