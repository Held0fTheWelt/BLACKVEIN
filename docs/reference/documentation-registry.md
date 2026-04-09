# Documentation registry

Canonical map of **audience-first** documentation, plus **ownership placeholders** and **update expectations**. Historical audit matrices remain under `docs/audit/` and `docs/archive/` and are **not** duplicated row-by-row here.

## Baseline validation

See [baseline-validation-note.md](baseline-validation-note.md) for Task 1A–4 artifact presence and `docs/` Markdown counts (note: counts change after consolidations).

## Start here (all audiences)

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [start-here/README.md](../start-here/README.md) | Docs lead | When top-level navigation changes |
| [what-is-world-of-shadows.md](../start-here/what-is-world-of-shadows.md) | Product + docs | When product definition changes |
| [how-world-of-shadows-works.md](../start-here/how-world-of-shadows-works.md) | Product + engineering | When system story changes |
| [system-map-services-and-data-stores.md](../start-here/system-map-services-and-data-stores.md) | Engineering lead | When services/ports/Compose change |
| [god-of-carnage-as-an-experience.md](../start-here/god-of-carnage-as-an-experience.md) | Product + narrative lead | When slice scope or player story changes |
| [how-ai-fits-the-platform.md](../start-here/how-ai-fits-the-platform.md) | AI/runtime lead | When AI stack or authority boundaries change |
| [glossary.md](../start-here/glossary.md) (short) | Docs lead | When onboarding terms change |

## User

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [user/README.md](../user/README.md) | Product/docs | With user doc set |
| [getting-started.md](../user/getting-started.md) | Product/docs | When onboarding UX changes |
| [how-to-start-a-session.md](../user/how-to-start-a-session.md) | Product/docs | When play/session UX changes |
| [how-input-affects-the-experience.md](../user/how-input-affects-the-experience.md) | Gameplay product | When input/UX messaging changes |
| [faq.md](../user/faq.md) | Product/docs | When common questions shift |
| [god-of-carnage-player-guide.md](../user/god-of-carnage-player-guide.md) | Narrative + product | When GoC UX changes |
| [forum-player-guide.md](../user/forum-player-guide.md) | Community product | When forum UX changes |
| [runtime-interactions-player-visible.md](../user/runtime-interactions-player-visible.md) | Gameplay engineering | When player-visible commands change |

## Admin / operator

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [admin/README.md](../admin/README.md) | Ops lead | With admin doc set |
| [setup-and-first-run.md](../admin/setup-and-first-run.md) | Ops/SRE | When bootstrap topology changes |
| [services-and-health-checks.md](../admin/services-and-health-checks.md) | Ops/SRE | When health surfaces change |
| [publishing-and-module-activation.md](../admin/publishing-and-module-activation.md) | Platform/content + ops | When publishing pipeline changes |
| [diagnostics-and-auditing.md](../admin/diagnostics-and-auditing.md) | Ops + security | When audit/trace surfaces change |
| [deployment-guide.md](../admin/deployment-guide.md) | Ops/SRE | When deploy topology or env vars change |
| [operations-runbook.md](../admin/operations-runbook.md) | Ops | When run procedures change |
| [monitoring-logging-and-incident-response.md](../admin/monitoring-logging-and-incident-response.md) | Ops/SRE | When observability stack changes |
| [security-and-compliance-overview.md](../admin/security-and-compliance-overview.md) | Security owner | When threat model or controls change |
| [release-and-quality-gates-for-operators.md](../admin/release-and-quality-gates-for-operators.md) | Release manager | When release policy changes |

## Developer

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [dev/README.md](../dev/README.md) | Engineering lead | When dev entry paths change |
| [onboarding.md](../dev/onboarding.md) | Engineering lead | When contributor path changes |
| [contributing.md](../dev/contributing.md) | Engineering lead | When repo topology changes |
| [local-development-and-test-workflow.md](../dev/local-development-and-test-workflow.md) | Engineering lead | When local/Compose defaults change |
| [architecture/runtime-authority-and-session-lifecycle.md](../dev/architecture/runtime-authority-and-session-lifecycle.md) | Runtime lead | When seam entry points change |
| [architecture/ai-stack-rag-langgraph-and-goc-seams.md](../dev/architecture/ai-stack-rag-langgraph-and-goc-seams.md) | AI/runtime lead | When graph or RAG seams change |
| [architecture/content-modules-and-compiler-pipeline.md](../dev/architecture/content-modules-and-compiler-pipeline.md) | Platform/content lead | When compiler projections change |
| [contracts/normative-contracts-index.md](../dev/contracts/normative-contracts-index.md) | Tech lead | When contracts are added/deprecated |
| [api/openapi-and-api-explorer-strategy.md](../dev/api/openapi-and-api-explorer-strategy.md) | Backend lead | When API doc strategy changes |
| [testing/test-pyramid-and-suite-map.md](../dev/testing/test-pyramid-and-suite-map.md) | QA or engineering lead | When major suite layout changes |
| [tooling/mcp-server-developer-guide.md](../dev/tooling/mcp-server-developer-guide.md) | Tooling owner | When MCP tools or env change |

## Technical (system documentation)

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [technical/README.md](../technical/README.md) | Architecture council | When technical IA changes |
| [technical/architecture/architecture-overview.md](../technical/architecture/architecture-overview.md) | Architecture council | When platform shape changes |
| [technical/runtime/runtime-authority-and-state-flow.md](../technical/runtime/runtime-authority-and-state-flow.md) | Runtime lead | When authority or session flow changes |
| [technical/ai/ai-stack-overview.md](../technical/ai/ai-stack-overview.md) | AI/runtime lead | When stack integration changes |
| [technical/ai/RAG.md](../technical/ai/RAG.md) | AI/runtime lead | When retrieval behavior changes |
| [technical/integration/MCP.md](../technical/integration/MCP.md) | Tooling + runtime lead | When capability surface changes |
| [technical/integration/LangGraph.md](../technical/integration/LangGraph.md) | AI/runtime lead | When graph semantics change |
| [technical/integration/LangChain.md](../technical/integration/LangChain.md) | AI/runtime lead | When LC integration changes |
| [technical/content/writers-room-and-publishing-flow.md](../technical/content/writers-room-and-publishing-flow.md) | Platform/content lead | When review/publish flow changes |
| [technical/architecture/service-boundaries.md](../technical/architecture/service-boundaries.md) | Backend + frontend leads | When service ownership changes |
| [technical/reference/test-strategy-and-suite-layout.md](../technical/reference/test-strategy-and-suite-layout.md) | QA or engineering lead | When suite strategy changes |

## Presentations / stakeholders

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [executive-summary-world-of-shadows.md](../presentations/executive-summary-world-of-shadows.md) | Product leadership | Each release milestone |
| [goc-vertical-slice-stakeholder-brief.md](../presentations/goc-vertical-slice-stakeholder-brief.md) | Product + engineering | When slice status changes |

## Governance

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [governance/README.md](../governance/README.md) | Tech lead | When ADR set changes |
| [governance/adr-template.md](../governance/adr-template.md) | Tech lead | Rare |
| [governance/adr-0001-runtime-authority-in-world-engine.md](../governance/adr-0001-runtime-authority-in-world-engine.md) | Architecture council | When superseding the decision |

## Reference

| Document | Owner (placeholder) | Update cadence |
|----------|---------------------|----------------|
| [glossary.md](glossary.md) | Docs lead | When new normative terms appear |
| This registry | Docs lead | When new canonical docs are added |

## PR checklist (recommended)

- New normative term → update [glossary.md](glossary.md).
- New canonical audience doc → add a row here and link from [INDEX.md](../INDEX.md).
- Changed ports or Compose services → update [system map](../start-here/system-map-services-and-data-stores.md) and [deployment guide](../admin/deployment-guide.md).
