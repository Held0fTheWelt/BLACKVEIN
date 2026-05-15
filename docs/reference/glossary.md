# Glossary

Authoritative short definitions for documentation across World of Shadows. Prefer linking here instead of redefining terms in every page.

**Quick orientation (non-normative):** readers new to the product may start with [`docs/start-here/glossary.md`](../start-here/glossary.md); this file remains the **maintained** term list for engineering and contracts.

## Product and scope

**World of Shadows**  
Multi-service narrative game platform: player and admin web apps, platform API, authoritative play runtime, shared AI stack (retrieval, orchestration, tooling). The root README also uses the line **Better Tomorrow (World of Shadows)**; use **World of Shadows** as the primary public documentation name unless product leadership standardizes otherwise.

**God of Carnage (GoC)**  
The first MVP **vertical slice**: a guided interactive drama experience backed by the canonical module under `content/modules/god_of_carnage/`. Bound by `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` and related contracts.

**Vertical slice**  
A deliberately narrow product and engineering cut (here: GoC) that binds content, runtime behavior, and validation gates without claiming the full multi-module product.

## Services and runtime

**Backend**  
Flask service in `backend/`: HTTP API, authentication, persistence, content loading and compilation, policy, and integration with the play service. See `docker-compose.yml` service `backend`.

**Frontend**  
Player/public Flask app in `frontend/`: pages and flows for registration, play shell, community features, etc. Talks to the backend API and, for play, to the configured play service URL.

**Administration tool**  
Separate Flask admin UI in `administration-tool/`; uses backend APIs for management workflows. Isolated from player UI by design.

**Play service (world-engine)**  
FastAPI service in `world-engine/` that hosts **authoritative** story session execution (including WebSocket live behavior where enabled). In Docker Compose this service is named `play-service`. **Do not confuse** with the nested `backend/world-engine/` path, which is a different layout concern documented in audit baselines.

**Runtime authority**  
The play service owns live session lifecycle and committed narrative state progression; the backend owns governance, publishing, and platform policy. Canonical summary: `docs/technical/runtime/runtime-authority-and-state-flow.md` (archived original: `docs/archive/architecture-legacy/runtime_authority_decision.md`).

## Content and AI

**Canonical module**  
YAML-first authored content under `content/modules/<module_id>/` loaded into `ContentModule` and compiled to projections (runtime, retrieval, review). See `docs/architecture/canonical_authored_content_model.md`.

**Module ID**  
String identifier for a content module (for GoC, `god_of_carnage` is the slice binding).

**AI proposal vs commit**  
Model output is **non-authoritative** until validated and **committed** by runtime rules. The graph may produce proposals; committed state follows validation and commit seams (see `docs/MVPs/MVP_VSL_And_GoC_Contracts/CANONICAL_TURN_CONTRACT_GOC.md` for normative detail).

**Runtime aspect ledger**  
Backend/world-engine-owned per-turn evidence record for runtime intelligence contracts such as beat, capability, authority, voice consistency, information disclosure, dramatic irony, visible projection, validation, commit, and memory. It is diagnostics/authority evidence; the player shell may display provided data but must not infer correctness from prose.

**EnvironmentState / environmental story**
Durable, bounded story-session environment state for the GoC slice: current room, actor locations, prop states, visible rooms, salient objects, and recent environment events. It is initialized from canonical module content and mutates only through committed/admitted actions; narration and RAG do not create persistent environment truth.

**Callback web / Pi17**
Bounded, deterministic continuity index over committed story-session records. It links earlier and later committed turns through structured evidence such as continuity classes, narrative threads, scene anchors, and selected branch replay events. It may support prompts and diagnostics, but it is non-authoritative and cannot mutate canon or replace memory.

**Consequence cascade / Pi21**
Bounded, deterministic consequence graph over committed story-session truth. It turns committed continuity impacts, pressure state, resolved pressures, narrative threads, and realized branch selections into consequence atoms and edges. It may support prompt context and diagnostics through `consequence_cascade_feedback.v1`, but it does not mutate canon, adopt inactive branch previews, or validate consequences from generated prose.

**Subtext interpretation / Pi19**
Bounded surface-vs-intent diagnostic carried as `SemanticMoveRecord.subtext`. It records policy-backed surface mode, hidden-intent hypothesis, subtext function, sincerity band, evidence codes, and policy provenance. It may shape planning and observability but does not commit story truth or use generated prose as an oracle.

**Dramatic irony runtime aspect**
Bounded Π16 runtime contract for selected NPC private-plan asymmetry. The runtime may pass only surface-safe opportunity ids and allowed surface modes into model context; validation rejects direct hidden-intent/private-plan echoes and records leak, realization, and violation evidence in the runtime aspect ledger. Tests derive expectations from policy, schema, selected private-plan records, and violation codes rather than generated prose.

**Information disclosure runtime aspect**  
Generic runtime aspect implementing bounded reveal control for mystery-rationing behavior. Content policy selects which disclosure units may be visible in a turn, validation checks structured `disclosure_events` and budget/failure codes, and tests use policy/schema/ledger fields rather than story prose as oracles.

**Preview (experiment preview)**  
Diagnostics or non-committed views of model or graph output used for review; must not be treated as committed player truth. Operational docs should point engineers to seam and contract docs for exact behavior.

**RAG (retrieval-augmented generation)**  
Retrieval of grounded context packs for prompts, implemented in `ai_stack/rag.py`, with path- and module-sensitive behavior (e.g. `content/modules/` vs `content/published/` semantics).

**LangGraph (GoC runtime graph)**  
`RuntimeTurnGraphExecutor` in `ai_stack/langgraph_runtime.py` orchestrates the GoC slice turn pipeline (interpret → retrieve → canonical resolve → director → model → validate → commit → render → package). See `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §3 for the normative node list.

**LangChain**  
Adapter invocation bridge for structured runtime output under `ai_stack/langchain_integration/`.

**MCP (Model Context Protocol)**  
Tooling surface for operators/developers (`tools/mcp_server/`). MCP tools observe or trigger **allowed** operations; they are not a substitute for runtime authority. See `docs/dev/tooling/mcp-server-developer-guide.md`.

**Writers Room**  
Backend workflow and APIs under `/api/v1/writers-room/...` with optional demo UI in `writers-room/`. Canonical narrative **source** for the live slice remains `content/modules/` unless a product decision states otherwise.

## Data and operations

**Docker Compose stack**  
Root `docker-compose.yml` defines `backend`, `frontend`, `administration-tool`, and `play-service` with example env vars. Default **host** ports differ from bare-metal local dev defaults in `docs/development/LocalDevelopment.md` (e.g. backend port).

**Internal API key / shared secret**  
Shared credentials between backend and play service for trusted internal calls; rotate together. See deployment and operations docs.

## Related

- [How AI fits the platform](../start-here/how-ai-fits-the-platform.md) — layered explanation for mixed audiences.
- [Normative contracts index](../dev/contracts/normative-contracts-index.md) — where binding technical contracts live.
