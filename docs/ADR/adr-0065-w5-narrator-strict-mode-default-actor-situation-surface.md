# ADR-0065: W5 Narrator Strict Mode Becomes the Default Actor-Situation Surface

## Status

Proposed

## Date

2026-05-21

## Intellectual property rights

Repository authorship and licensing: see project **LICENSE**; contact maintainers for clarification.

## Privacy and confidentiality

This ADR contains no personal data. Implementers must follow the repository privacy and confidentiality policies, avoid committing secrets, and keep narrator/admin diagnostics free of private actor motive text unless an existing visibility contract already allows it.

## Related ADRs

- [ADR-0033](adr-0033-live-runtime-commit-semantics.md) - live runtime commit semantics. W5 remains downstream of committed/persisted runtime substrate.
- [ADR-0038](adr-0038-canonical-turn-lifecycle-single-commit-path.md) - canonical turn lifecycle and single commit path.
- [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) - gate tests must assert semantic contracts, not hardcoded route or field-presence oracles.
- [ADR-0061](adr-0061-director-pause-mode-for-gathering-interruption.md) - Director pause/gathering semantics remain authoritative.
- [ADR-0063](adr-0063-w5-actor-tracking.md) - W5 Actor Tracking is the actor-tracking authority this ADR promotes for narrator strict mode.

## Context

Phase 6B-3B introduced `W5_AST_NARRATOR_STRICT_ENABLED` as an opt-in, default-off migration flag. With strict mode enabled, narrator path payloads stop exposing `source_facts.transition_from_previous` as primary actor-situation input; the same legacy transition payload is demoted under `source_facts._legacy_compat["transition_from_previous"]`, and narrator prompts are instructed to use the W5 narrator projection as the actor-situation authority.

Phase 6B-4 completed a post-migration W5 fallback inventory and found zero newly-dead branches. Phase 6B-4.5 repaired the MVP04 diagnostics-envelope route oracle after an unrelated HTTP route refactor; it did not change W5 or narrator runtime behavior. The current active W5 packages are:

- `ai_stack/actor_tracking`
- `world-engine/app/story_runtime/manager/actor_tracking/`

Retired actor-situation package names must not be imported or recreated.

## Problem

`transition_from_previous` is a legacy narrator transition surface. It is useful as a compatibility breadcrumb, but it cannot remain the primary actor-situation authority because it does not carry the complete W5 contract:

- It does not represent Who / Where / What / How / Why as a closed, truth-leveled projection.
- It cannot distinguish OBSERVED location truth from inferred or projected narrative framing.
- It does not make How first-class.
- It cannot prevent inferred Why from being read as observed truth.
- It is easy for tests to turn into false green checks by asserting only that a field is present.
- Its hard-cut guidance is authored transition support, not a complete current actor-situation surface.

Leaving strict mode default-off makes the legacy surface continue to shape default narrator prompt behavior even after W5 has become the higher-level actor-tracking authority.

## Decision

In a future phase, after the safety gates in this ADR are green, W5 narrator strict mode will become the default actor-situation surface for narrator prompts, narrator path source facts, admin diagnostics, and observability.

This ADR is planning only. It does not flip `W5_AST_NARRATOR_STRICT_ENABLED`, remove `transition_from_previous`, remove `_legacy_compat`, remove strict-off fallback prompts, remove malformed-W5 safety fallbacks, mutate committed events, or change committed output.

The future permanent posture is:

- W5 narrator projection is the primary narrator actor-situation authority.
- `transition_from_previous` is not authoritative.
- `_legacy_compat["transition_from_previous"]` remains available during rollout as diagnostics-only evidence.
- Explicit opt-out and malformed/missing-W5 safety behavior stay in place until their own removal phase or ADR retires them.

## Current Behavior

`W5_AST_NARRATOR_STRICT_ENABLED` is opt-in and default-off.

With strict mode disabled, narrator source facts keep `source_facts["transition_from_previous"]` as a first-class legacy input, and the narrator prompt retains a fallback paragraph naming that legacy transition block.

With strict mode enabled, narrator source facts demote that payload into `source_facts["_legacy_compat"]["transition_from_previous"]` and mark W5 as authoritative. The strict prompt tells the narrator to use W5 `who_summary`, `where_summary`, `what_summary`, `how_summary`, and `why_summary`, not the legacy transition block.

Admin diagnostics already compute `w5.location_changed_this_turn` from W5 history first under both postures. The legacy parity label is still exposed so operators can compare the rollout state.

## Proposed Future Behavior

After parity tests are rewritten and the required gates pass, `W5_AST_NARRATOR_STRICT_ENABLED` is flipped to default-on. The default narrator path then behaves like today's explicit strict mode:

- top-level `source_facts.transition_from_previous` is absent from the primary narrator contract;
- `source_facts.w5_projection` is the current actor-situation surface;
- `_legacy_compat["transition_from_previous"]` is diagnostics-only while the rollout remains reversible;
- prompt guidance names W5 as the actor-situation authority;
- old-payload and malformed-W5 safety fallbacks remain until a later phase proves they can be retired.

Later phases may remove the strict-off prompt paragraph and may further demote or remove `_legacy_compat["transition_from_previous"]`, but only after the rollback window and diagnostics requirements are satisfied.

## Why `transition_from_previous` Is No Longer Authoritative

`transition_from_previous` answers a narrow transition question: how this narrator block relates to the previous one. It can preserve hard-cut breadcrumbs and operator parity evidence, but it is not the canonical actor-situation model.

W5 is the model that carries source, truth level, freshness, visibility, per-actor situation, and projection consumer. Once W5 exists and is projected for the narrator, treating a legacy transition block as equally authoritative creates two competing narrator inputs. The future default must remove that ambiguity: `transition_from_previous` may explain compatibility history; W5 states the current actor situation.

## How W5 Narrator Projection Replaces `transition_from_previous`

The W5 narrator projection replaces the legacy transition surface by providing the narrator with a structured actor-situation projection:

- `who_summary` identifies the relevant actor(s), their presence, and scope.
- `where_summary` supplies current location, location change, and replacement guidance for hard-cut transition framing.
- `what_summary` supplies observed or declared action/state/topic facts without absorbing How.
- `how_summary` supplies manner, tone, intensity, channel, pace, physicality, and method as first-class projection data.
- `why_summary` supplies inferred motive or dramatic function only as soft truth.

Hard-cut guidance must be derived from W5 `where_summary` and transition metadata in the projection, not from the legacy top-level `transition_from_previous` block.

## Strict Mode Handling By W5 Dimension

**Who:** The narrator uses W5 actor identity, actor type, visibility, and actor knowledge scope. It must not invent another actor-situation source from prompt prose.

**Where:** The narrator uses W5 current location and location-change metadata. `location_changed` and hard-cut replacement guidance must come from the W5 projection or its diagnostics, not from top-level `transition_from_previous`.

**What:** The narrator uses W5 action/state/topic facts according to their truth attribution. What remains separate from How.

**How:** How remains first-class. Manner, tone, intensity, method, physicality, style, and channel stay in `how_summary` or equivalent W5 How fields; they must not be folded into `what_summary`.

**Why:** Why remains inferred / soft truth unless a future ADR defines an explicit engine-owned commit path for observed motive. Narrator prompts and diagnostics must never present inferred Why as observed truth.

## How Remains First-class

Strict mode must preserve How as its own narrator input. Tone, manner, intensity, method, physicality, pace, and channel are not decoration on What; they are W5 How evidence and must be projected, tested, and observed separately from action/state/topic facts.

Any future prompt rewrite or diagnostics cleanup that collapses `how_summary` into `what_summary` violates this ADR and ADR-0063.

## Inferred Why Remains Soft Truth

Strict mode may surface inferred Why only as inferred / soft truth. It may help the narrator avoid incoherent motivation, but it must not be narrated, logged, or diagnosed as observed substrate truth.

Any future promotion from inferred Why to observed motive requires a separate engine-owned commit path and ADR. Until then, inferred Why stays visibly attributed as inferred and remains bounded by actor knowledge scope.

## `_legacy_compat` During Transition

`_legacy_compat["transition_from_previous"]` is a temporary rollout and diagnostics surface. It allows operator parity checks and safe comparison against older committed narrator blocks without making the legacy payload authoritative.

During Phase 6B-5C and until a later removal phase:

- `_legacy_compat` may remain present under default-on strict mode;
- it is not primary input for narrator generation;
- tests may assert that it is demoted, labeled non-authoritative, and ignored by strict prompts;
- admin diagnostics may expose whether this compatibility breadcrumb is present;
- a later ADR or follow-up phase must decide when to remove it.

## Rollout Plan

**Phase 6B-5A - ADR and test plan.** Author this ADR and update migration/inventory docs. No runtime behavior changes, no flags flipped, no legacy branch removed.

**Phase 6B-5B - strict-mode parity test rewrite.** Rewrite narrator projection, narrator prompt, and admin diagnostics tests so default-on strict behavior is the expected semantic contract. Tests must still prove opt-out and malformed-W5 fallback behavior while the rollback path exists.

**Phase 6B-5C - default-on flip.** Flip `W5_AST_NARRATOR_STRICT_ENABLED` to default-on only after Phase 6B-5B gates are green. Keep explicit disable support during rollout.

**Phase 6B-5D - strict-off prompt fallback paragraph removal.** Remove only the prompt paragraph that tells the narrator to use the legacy `transition_from_previous` fallback, after default-on has stabilized and rollback coverage remains explicit.

**Phase 6B-5E - `_legacy_compat` transition demotion/removal decision.** Either further demote or remove `_legacy_compat["transition_from_previous"]`, but only after admin diagnostics and observability no longer require it. If removal changes public diagnostics contracts, author a follow-up ADR first.

**Phase 6B-5F - fresh inventory pass.** Re-run the W5 legacy-consumer inventory after strict default-on to classify any newly dead, still-needed opt-out, malformed-W5 safety, old-payload compatibility, or diagnostics-only branches.

Narrator-consequence W5-first builders, frontend/WebSocket player-view upgrades, substrate consolidation, and NPC legacy bundle retirement remain separately scoped ADRs or phases.

## Rollback Plan

During rollout, `W5_AST_NARRATOR_STRICT_ENABLED` can be explicitly disabled to restore the strict-off path.

The strict-off path remains available until the removal phase that explicitly deletes it. Malformed or missing W5 narrator projection still falls back safely according to the existing safety branches. `_legacy_compat["transition_from_previous"]` remains available for diagnostics until a later ADR or approved follow-up phase removes it.

Rollback must not mutate committed events. It can only change future read/prompt behavior through the flag posture.

## Observability Requirements

MVP04 observability and Langfuse diagnostics must continue to prove semantic evidence, not field presence. Empty diagnostics must not be treated as success.

Observability must expose enough state to distinguish:

- W5 narrator projection used as primary authority;
- strict mode enabled by default versus explicitly disabled;
- malformed/missing-W5 fallback reason;
- W5 snapshot id and actor count where available;
- whether How is present;
- whether inferred Why is present and labeled as inferred;
- location change source from W5 history/projection;
- `_legacy_compat` presence while it remains in the contract.

No observability field may convert inferred Why into observed truth or imply that the legacy transition block is authoritative under strict mode.

## Admin Diagnostics Requirements

Admin diagnostics must show W5 metadata as primary:

- `w5.narrator_strict_enabled` reflects the effective strict posture;
- location change evidence is computed from W5 history/projection, not from top-level `transition_from_previous`;
- legacy transition parity is either demoted or absent according to the rollout phase;
- malformed-W5 failures are visible and do not masquerade as successful W5 evidence;
- empty W5 diagnostics fail semantic gates instead of passing field-presence checks.

Diagnostics may keep compatibility breadcrumbs while they are labeled non-authoritative.

## Test Gates

The following gates are required before the default-on flip:

- Narrator projection tests prove W5 supplies current location, `location_changed`, and hard-cut guidance replacement.
- Narrator prompt tests prove no legacy `transition_from_previous` primary guidance remains under the default-on posture.
- Admin diagnostics prove W5 metadata is primary and legacy transition parity is demoted.
- MVP03 LDSS gate remains green.
- MVP04 observability diagnostics gate remains green.
- No committed output mutation is introduced.
- No Actor Lane, Canonical Path, Commit/Readiness, `validation_outcome`, ADR-0033, ADR-0061, ADR-0063, or W5 validation semantics are weakened.
- Inferred Why is never presented as observed truth.
- How is not folded into What.
- Opt-out, malformed-W5, old-payload, and public compatibility behavior remains tested while each compatibility path exists.

## Acceptance Criteria

Phase 6B-5A is accepted when:

- ADR-0065 exists with status Proposed.
- Migration docs record that this phase is planning only.
- No runtime behavior changed.
- No W5 flag default changed.
- No legacy branch was removed.
- The next executable step is Phase 6B-5B parity-test rewrite.

The later default-on phase is accepted only when all test gates above pass and the scoped diff contains no committed-output mutation.

## Rejected Alternatives

**Flip strict mode immediately.** Rejected because parity tests still need to be rewritten to assert W5 semantics as the default, not merely the presence of legacy-compatible fields.

**Delete `transition_from_previous` and `_legacy_compat` in the same change as the flip.** Rejected because rollback and admin parity require a temporary diagnostics breadcrumb.

**Keep `transition_from_previous` as equal primary authority.** Rejected because it preserves two competing actor-situation surfaces and weakens the W5 authority migration.

**Treat inferred Why as observed narrator truth.** Rejected because it violates ADR-0063 and risks leaking soft motive inference as fact.

**Fold How into What to simplify prompts.** Rejected because How is a first-class W5 dimension.

**Update gates to check only field presence.** Rejected because MVP04 must detect false green and false red behavior through semantic evidence.

## Risks And Mitigations

**Risk: default-on strict mode changes narrator style.** Mitigation: rewrite parity tests first, compare W5 hard-cut/location guidance against current strict-on behavior, and keep explicit disable during rollout.

**Risk: malformed W5 projection creates empty narrator evidence.** Mitigation: keep malformed-W5 fallback and require diagnostics to identify fallback reason instead of passing empty W5 envelopes.

**Risk: admin dashboards depend on legacy parity labels.** Mitigation: keep `_legacy_compat` and parity labels during rollout, then retire them in a separately gated phase.

**Risk: tests become false green.** Mitigation: MVP03 and MVP04 gates must assert semantic evidence, non-empty diagnostics, and no legacy primary guidance under strict default-on.

**Risk: W5 authority weakens Actor Lane or Canonical Path contracts.** Mitigation: W5 remains downstream of commit and cannot authorize actor-lane behavior, advance canonical path, or rewrite committed events.

## Required Follow-up Phases

- Phase 6B-5B: strict-mode parity test rewrite.
- Phase 6B-5C: default-on flip for `W5_AST_NARRATOR_STRICT_ENABLED`.
- Phase 6B-5D: removal of the strict-off narrator prompt fallback paragraph.
- Phase 6B-5E: removal or further demotion of `_legacy_compat["transition_from_previous"]`.
- Phase 6B-5F: fresh inventory pass after narrator strict default-on.
