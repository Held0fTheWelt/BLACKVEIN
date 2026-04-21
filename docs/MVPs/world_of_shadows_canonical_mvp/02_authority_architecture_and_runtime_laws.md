# Authority, architecture, and runtime laws

## The constitutional law set remains canonical

The strongest concise expression of World of Shadows runtime discipline still comes from the later canonical protocol and v21 package.
These twelve laws remain canonical:

1. **One truth boundary.**
2. **Commit is truth.**
3. **Turn 0 is canonical.**
4. **Ordinary player route purity.**
5. **Publish-bound authoritative birth.**
6. **Fail closed on authority seams.**
7. **Fail closed on internal auth.**
8. **Degraded-safe stays explicit.**
9. **Story persistence incidents stay visible.**
10. **Non-graph seams remain testable.**
11. **Payloads self-classify.**
12. **Release honesty is mandatory.**

These laws survived repeated later audits because they are still the best anti-drift compact for the system.

## Canonical ownership model

### World-engine
The world-engine is the sole live story-truth host.
It owns:

- story-session lifecycle,
- Turn 0 birth and later turn execution,
- validation and commit authority,
- committed runtime state,
- and truth-aligned render inputs for the ordinary player route.

### Backend
The backend owns:

- auth and policy,
- publishing and activation control,
- platform persistence outside the live story-truth host,
- admin/API surfaces,
- and governance / review / release integration.

### Shared support layers
- `story_runtime_core` owns shared runtime-support contracts.
- `ai_stack` owns retrieval, orchestration, semantic planning, model invocation, and related support logic.
- `content/` owns authored module material.
- `frontend/` owns the player shell.
- `administration-tool/` owns operator-facing administration and diagnosis.

None of those support layers gets to self-authorize story truth.

## Canonical turn truth model

The canonical turn model, as preserved across the slice contracts and broader MVP documents, is:

1. player input enters the runtime,
2. interpretation happens in scene and module context,
3. scene direction and support systems prepare bounded turn context,
4. AI may propose dramatic content and state effects,
5. validation determines whether proposed effects are lawful,
6. commit determines what becomes canonical,
7. visible output is shaped from committed truth or explicitly lawful player-safe statuses,
8. post-commit continuity updates remain below canonical commit authority.

Nothing on the ordinary player route may silently outrun that chain.

## Scene identity and slice authority

The GoC slice establishes another important law in practice:

- scene identity has one canonical mapping surface,
- downstream consumers may not invent silent remap layers,
- and any scene identity change must update validation and tests in the same change set.

That is a concrete anti-drift requirement, not an implementation detail.

## Publish, fallback, and truth

The active slice preserves a lawful distinction between:

- **published canonical experience content**,
- and **bounded builtin GoC fallback** used for demo, local fallback, or explicit compatibility cases.

Builtin fallback may exist, but it must not silently override published canon or become a second truth boundary by convenience.

## Projection governance

Several surfaces are useful but subordinate:

- OpenAPI,
- Postman collections,
- diagnostic projections,
- retrieval summaries,
- and operator-friendly summaries.

They may clarify the system, but they are not higher authority than runtime contracts, code, and validated behavior.

## MCP boundary

The source set is clear that MCP belongs to the **control plane**:

- tools,
- context support,
- diagnostics,
- audit surfaces,
- and operator/developer orchestration.

It must not become an alternate story-truth authority.

## Canonical architecture reading

The correct consolidated reading is:

- world-engine is the only live story-truth host,
- backend governs publish/policy/admin/platform concerns,
- support layers assist but do not self-authorize truth,
- ordinary-player and operator routes stay separated,
- projections stay projections,
- and closure claims remain subordinate to code and proof.
