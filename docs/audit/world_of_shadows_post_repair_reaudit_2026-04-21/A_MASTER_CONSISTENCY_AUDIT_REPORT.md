# Master consistency audit report — post-repair re-audit

## Executive summary

I re-audited the **repaired** World of Shadows package with the repaired repository bundle as the primary source base. The result is materially better than the pre-repair state: the package now has a real active canonical route, a clearer authority model, a better-bounded mirror lane, and a more honest player-shell posture for support obligations.

The repaired MVP **does still define one coherent World of Shadows product**, and it does so more convincingly than the prior package. The active route, GoC contract lane, authored module lane, runtime authority docs, player-shell surfaces, and targeted world-engine / AI-stack tests now reinforce each other rather than merely coexisting.

The strongest carried chain is still:

**authored module truth → publish/feed truth → runtime activation / commit authority → player-safe observation and shell continuity → operator-only diagnostic visibility**.

That chain still carries.

The largest remaining problems are no longer foundational architecture contradictions. They are now **routing, evidence-lane, and proof-posture inconsistencies**:

1. some entrypoint READMEs still point humans to the older parent canonical spine instead of the active recomposed route;
2. some audit/evidence READMEs still point to the older 2026-04-20 repair bundle instead of the 2026-04-21 repair-implementation bundle;
3. the detailed companion README still uses naming that partially competes with the active route;
4. proof-route language is stronger inside the active route than in some top-level doc entry surfaces;
5. UI/support obligations are now honestly named, but still not equally replay-proven in this environment.

So the package is **improved and coherent enough to function as the current canonical experience definition**, but it still bears **named arrangement tensions** and **proof-posture follow-up obligations**. The remaining work is mostly about eliminating residual route ambiguity and aligning evidence-lane language with the repaired reality, not about rediscovering the product.

## Sources audited

The whole repaired package was inventoried structurally. I did **not** line-read all ~10,000 files individually. I did directly read the load-bearing canonical, architectural, evidence, UI, implementation, test, and lineage-bearing artifacts that determine MVP truth, and I spot-checked the broader lineage families to confirm carry-forward of concepts that the active slice does not fully replay.

Primary directly read artifact families included:

- root and docs entrypoints (`README.md`, `docs/README.md`, `docs/start-here/README.md`, `docs/MVPs/README.md`)
- detailed canonical companion set and active recomposed route
- GoC normative contract family
- technical runtime and writers-room/publishing continuity docs
- user-facing player/runtime docs
- repair implementation report, validation record, and post-repair tension record
- frontend player-shell template and route logic
- operator/admin inspection workbench template
- backend governance and writers-room route surfaces
- world-engine runtime managers and targeted tests
- AI-stack MCP surface test
- representative older lineage docs under `mvp/docs/`
- mirror-lane notices and root GoC mirror files

## Audit method

1. Structural package inventory of the repaired bundle.
2. Direct content reading of authority-bearing, experience-bearing, proof-bearing, and tension-bearing artifacts.
3. Cross-check of the active recomposed route against root README/doc entrypoints and audit entrypoints.
4. Cross-check of authoring/publish/runtime/player/operator continuity across docs, code, and tests.
5. Fresh focused validation:
   - `world-engine`: backend feed, shell readout, runtime manager tests
   - `ai_stack`: MCP canonical surface tests
   - selected markdown link checks for the active route and entrypoint docs
6. Environment-bounded replay attempt for frontend route tests, with transparent failure recording.
7. Post-repair recomposition judgment focused on remaining ambiguity, not on reductive cleanup.

## Major consistency findings

### 1. The repaired package now has a real canonical center

This is the biggest improvement. The active canonical reading route under:

- `docs/MVPs/world_of_shadows_canonical_mvp/active_recomposed_route/`

is real, readable, and conceptually sound. It separates:

- active canon,
- GoC normative contracts,
- source lineage,
- evidence/support lanes,
- mirrors and residue.

This materially reduces the previous “multiple equal centers” problem.

### 2. Authority and stage continuity still carry strongly

The repaired package still carries the core constitutional logic well:

- world-engine owns live story truth,
- backend owns policy/publish/governance/orchestration,
- frontend owns ordinary player routes,
- administration-tool owns operator/admin surfaces,
- writers-room participates in review support but not self-publish,
- AI assists but does not outrank commit.

This remains coherent across:

- `active_recomposed_route/02_authority_and_stage_continuity.md`
- `docs/technical/runtime/runtime-authority-and-state-flow.md`
- `docs/technical/content/writers-room-and-publishing-flow.md`
- `world-engine/app/runtime/manager.py`
- `world-engine/app/story_runtime/manager.py`
- `backend/app/api/v1/writers_room_routes.py`
- `backend/app/api/v1/ai_stack_governance_routes.py`

### 3. God of Carnage remains properly central

GoC still functions as the proof-bearing vertical slice rather than as an orphan relic. The repaired route keeps GoC connected to the broader WoS product identity, and the authored module, normative contract lane, runtime tests, and player-facing docs still line up.

### 4. UI/UX truthfulness improved materially

The player shell now explicitly classifies support surfaces as:

- implemented now,
- partial,
- obligation,
- external/operator-only.

That is a major improvement over leaving help/recap/save-load/accessibility implied. The shell now tells the truth about what is present and what is not yet fully productized.

### 5. Broader WoS target families are better preserved than before

Memory depth, emotional/consciousness layers, recovery intelligence, multi-session continuity, learned-policy shadow lane, and authoring analytics are now better protected against silent loss through the active route’s target-layer and carry-forward mapping.

They still are **not equally replay-proven**, but they are no longer structurally easy to erase.

## Important gaps that opened up or remain open

### G-01 — entrypoint routing drift remains

`docs/README.md` still names the older parent README as the primary canonical spine and still highlights the older 2026-04-20 repair bundle. `docs/audit/README.md` does the same in the audit lane. This means the repaired package now contains a stronger active route than some of its own index surfaces admit.

### G-02 — evidence-lane “current bundle” ambiguity remains

There are now at least two obviously authoritative-seeming repair bundles:

- `docs/audit/world_of_shadows_canonical_mvp_repair_2026-04-20/`
- `docs/audit/world_of_shadows_canonical_mvp_repair_implementation_2026-04-21/`

The later one is the stronger current repair-implementation lane, but not every entrypoint routes the reader there.

### G-03 — the companion README still partly competes with the active route

`docs/MVPs/world_of_shadows_canonical_mvp/README.md` correctly says the active route is the first-pass spine, but then uses the heading **“Primary canonical spine”** for the detailed split sequence and still points its proof route to the older repair bundle. That wording reintroduces semantic competition.

### G-04 — proof posture is cleaner, but not fully normalized

The active route’s proof doc is more honest than before and includes fresh spot-checks, but the broader doc lattice still mixes:

- carried-forward evidence,
- older preferred repair bundles,
- latest repair implementation evidence,
- and current entrypoint guidance.

So the proof burden is better framed but not fully normalized around one current evidence route.

### G-05 — player support obligations remain only partly proven

The package is now honest that recap/help/save-load/accessibility are not equally closed. That is correct. But this is still a genuine product-surface gap, not merely a documentation issue.

### G-06 — frontend replay is still environment-bounded here

The repaired shell is structurally stronger and its routes/tests exist, but this environment still lacks Flask, so direct replay of `frontend/tests/test_routes_extended.py` was not possible in this pass.

## Concepts that still carry strongly

- World of Shadows as a governed narrative-runtime platform
- world-engine as the sole live truth boundary
- GoC as the current proof-bearing slice within a broader WoS identity
- authored-source → publish → runtime → player-safe shell continuity
- proposal/validation/commit distinction
- operator-vs-player surface separation
- writers-room as support/review ecosystem rather than self-publish authority
- emotional/social runtime readout bridges inside the active slice
- source-lineage preservation as a first-class anti-loss rule
- mirror-lane bounding as an explicit package rule

## Concepts that no longer fully carry in their current form

These are not concept failures. They are **arrangement failures** or **naming failures** in their current placement:

- “current canonical route” at `docs/README.md` level
- “current audit / repair bundle” at `docs/audit/README.md` level
- “primary canonical spine” naming inside the detailed companion README
- “preferred proof route” language that still points to the older repair bundle
- “fully current evidence posture” across the docs lattice

## Arrangement problems

1. **Residual dual-center navigation**: active route exists, but some entrypoints still point elsewhere.
2. **Historical bundle overhang**: older repair bundle still looks live-current in places.
3. **Competing canonical wording**: detailed companion README partially competes with the active route rather than supporting it cleanly.
4. **Proof-lane fragmentation**: carried-forward evidence and current repair evidence are both present, but not consistently staged.
5. **UI support truth still depends on cross-reading**: the shell is honest, but supporting docs are not yet uniformly routed through the same current truth posture.

## Recompositon decisions

The correct response is **not** another large rewrite of the canon. The active route already did the hard conceptual work.

The correct response is a **delta recomposition**:

- keep the active route as the canonical first-pass spine;
- keep the detailed companion set as a deeper canonical companion family;
- keep GoC normative contracts separate and clearly superior to mirrors;
- keep source-lineage material visible as enduring target truth;
- but normalize the remaining doc entrypoints and evidence entrypoints so they stop competing with the repaired reality.

That means:

- rewrite `docs/README.md` to route first to the active recomposed route and the current repair-implementation lane;
- rewrite `docs/audit/README.md` so the 2026-04-21 repair-implementation bundle is the current repair/evidence entry;
- adjust `docs/MVPs/world_of_shadows_canonical_mvp/README.md` so the detailed sequence no longer calls itself the “Primary canonical spine” in a way that competes with the active route;
- adjust the proof-posture doc(s) so the current evidence route is singular and explicit.

## Remaining tensions

- frontend replay remains environment-bounded here;
- recap/help/save-load/accessibility remain unevenly proven;
- broader WoS target families remain more canonically preserved than live-proven;
- mirrors and duplicate lanes still physically exist and therefore still require discipline;
- backend transitional retirement is still not a fully closed claim.

## Final judgment on experience coherence and completeness

**Judgment:** the repaired package is now **coherent and complete enough to function as the canonical World of Shadows experience definition**, but it still bears **named route-normalization and proof-posture tensions** that should remain visible.

It is no longer the fragmented sprawl it was before. The remaining weaknesses are now mostly **entrypoint and evidence-lane consistency problems**, plus a smaller set of still-open player-support and replay-proof obligations.
