# Task 4 — GoC Namespace Pre/Post Map

## Scope

- This file defines target namespace categories and pre/post mapping for Task 4.
- In this pass, blocker gate is not lifted, so **post-state is control-normalized with no physical path relocation**.

## Conflict-priority classification rule

When a surface appears classifiable into multiple categories, apply:

1. runtime-consumed canonical GoC content
2. authoring-side GoC content
3. GoC-specific template material
4. generic schema/model material
5. fixture/demo/builtin/published-support material
6. residue/obsolete transitional material

Lower-priority selection requires explicit written justification.

## Pre/Post category map

| Surface | Pre classification | Post classification | Physical move | Note |
|---|---|---|---|---|
| `content/modules/god_of_carnage/*` | runtime-consumed canonical GoC content | runtime-consumed canonical GoC content | no | canonical module remains authoritative |
| `writers-room/app/models/implementations/god_of_carnage/*` | authoring-side GoC content | authoring-side GoC content | no | authoring surface remains distinct from runtime canon |
| `writers-room/app/models/markdown/_registry/prompt_registry.yaml` (`implementation.god_of_carnage.*`) | authoring registry surface | authoring registry surface | no | no renamespace while blocker is active |
| `world-engine/app/content/builtins.py` (GoC template seed) | fixture/demo/builtin-support | fixture/demo/builtin-support | no | remains secondary to canonical module |
| `backend/app/content/builtins.py` | fixture/demo/builtin-support | fixture/demo/builtin-support | no | same role as world-engine builtin surface |
| `schemas/content_module.schema.json` | generic schema/model material | generic schema/model material | no | schema remains generic, non-GoC namespace owner |
| `docs/goc_evidence_templates/*` | fixture/published-support material | fixture/published-support material | no | evidence-template support remains explicit |
| `outgoing/*g9b*` and `docs/g9_evaluator_b_external_package/*` | published-support / mirror package surfaces | published-support / mirror package surfaces | no | mirror policy retained; stale mirrors handled via residue process |

## Future-module coexistence constraints

- No GoC-special logic may be introduced in loader/discovery namespaces for module categorization.
- Namespace categories must remain module-agnostic (`<module_id>` driven) across backend loader, MCP tools, and RAG lane logic.
- Any future module must fit the same category model without new special-case path families.

## Outcome

- Structural legibility is normalized at category/governance level.
- Physical namespace relocation is deferred by hard blocker until dependency classes are fully closed.

