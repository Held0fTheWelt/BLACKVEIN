# Start here

Plain-language entry to World of Shadows documentation. Read **one** path below based on your role, then use the [documentation registry](../reference/documentation-registry.md) for owners and maintenance.

## Choose a path

| I am… | Read next |
|-------|-----------|
| New to the product | [What is World of Shadows?](what-is-world-of-shadows.md) → [How the system works](how-world-of-shadows-works.md) → [System map](system-map-services-and-data-stores.md) |
| A player or forum user | [User documentation root](../user/README.md) → [Getting started](../user/getting-started.md) |
| Deploying or operating the stack | [Admin documentation root](../admin/README.md) → [Setup and first run](../admin/setup-and-first-run.md) |
| Building or debugging the system | [Developer documentation root](../dev/README.md) → [Onboarding](../dev/onboarding.md) |
| Preparing slides or an executive brief | [Presentations](../presentations/executive-summary-world-of-shadows.md) |

## Short system story

World of Shadows is a **multi-service platform**: a **player** web app, an **admin** web app, a **backend** API with database, and a **play service** (world-engine) that owns **live narrative session** execution. **Artificial intelligence** assists turns through a **bounded pipeline** (retrieval, orchestration, validation, commit); **committed truth** is decided by runtime rules, not by the model alone. See [How AI fits the platform](how-ai-fits-the-platform.md).

## God of Carnage (first slice)

The **God of Carnage** module is the first **vertical slice**: scene-led drama with contracts that bind YAML content, runtime behavior, and tests. Start with [God of Carnage as an experience](god-of-carnage-as-an-experience.md).

## Terms

Use the [short glossary](glossary.md) for quick definitions; the [full glossary](../reference/glossary.md) is maintained for normative terms.

## What this layer is not

- **Not** internal program evidence: gate baselines, task closures, and audit matrices live under `docs/audit/` and `docs/archive/`; they support engineering governance, not end-user understanding.
- **Not** a substitute for normative contracts when you are implementing behavior: developers must use the [normative contracts index](../dev/contracts/normative-contracts-index.md) and [`docs/technical/`](../technical/README.md) for binding detail.
