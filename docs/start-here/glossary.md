# Glossary (start here)

Short orientation for **non-developers**. For the **full, maintained** term list (normative where marked), see **[`docs/reference/glossary.md`](../reference/glossary.md)**.

| Term | Plain meaning |
|------|----------------|
| **World of Shadows** | The narrative game and community platform (multi-service software). |
| **Play service / world-engine** | The service that runs **live story sessions** and owns committed play state for those sessions. |
| **Backend** | The API and database service for accounts, forum, content compilation, admin features, and integration with the play service. |
| **Frontend** | The player-facing website. |
| **Administration tool** | The separate admin web app for operators. |
| **Module** | A packaged story configuration (files under `content/modules/<id>/`). |
| **God of Carnage (GoC)** | The first full vertical slice module and its contracts. |
| **Turn** | One cycle of player input, processing, and updated session state in live play. |
| **Proposal vs commit** | AI may **propose** content; only **validated, committed** results become authoritative narrative state. |
| **RAG** | Retrieval over project documents to **inform** generation—does not override runtime authority. |

When you implement behavior, use the [normative contracts index](../dev/contracts/normative-contracts-index.md) and [`docs/CANONICAL_TURN_CONTRACT_GOC.md`](../CANONICAL_TURN_CONTRACT_GOC.md) instead of this short table alone.
