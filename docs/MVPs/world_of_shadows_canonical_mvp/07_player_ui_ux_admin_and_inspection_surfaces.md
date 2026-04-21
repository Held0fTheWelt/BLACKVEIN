# Player UI/UX, admin, and inspection surfaces

## Why UI is canonical MVP truth

The source set repeatedly shows that UI and operator surfaces are not decorative polish.
They are part of whether the runtime is actually legible, playable, diagnosable, and honest.

A dramatic runtime that cannot make its state understandable or keep player and operator surfaces separated has not actually finished the MVP seam.

## The four questions the session shell must answer

The direct UI-usability material preserved a very concrete requirement family.
The ordinary player shell must answer these questions immediately:

1. **What is happening right now?**
2. **What changed this turn?**
3. **What can I do next?**
4. **Where is deeper help if I need it?**

That four-question model is now canonical rather than merely a side usability note.

## Canonical player-shell hierarchy

The strongest consistent hierarchy across the source set is:

- **Primary:** scene panel and current situation
- **Secondary:** interaction panel and execute action
- **Tertiary:** history / transcript context
- **Diagnostic:** expandable inspection for the right audience

This hierarchy matters because World of Shadows is supposed to feel like guided dramatic play, not a stack of raw payload panes.

## Canonical shell expectations

### Scene clarity
The current scene and live dramatic situation should be legible above the fold.

### Turn-effect clarity
Recent deltas and consequences should be understandable in plain language.
The player should feel that their move changed something.

### Action clarity
The input form should remain obvious and easy to reach.
The next action affordance should never feel hidden.

### History clarity
The player needs enough transcript context to feel continuity rather than single-turn isolation.

### Diagnostic discipline
Deep diagnostics may exist, but they must not dominate the ordinary player route.

## Player support and accessibility obligations

The earlier package family treated player support as a real MVP seam, not optional polish.
The repaired canonical reading keeps that obligation visible.

At minimum, the player-support lane should make room for:

- recap or transcript footholds when continuity pressure is high,
- help or deeper explanation paths that do not spill operator-only detail onto the ordinary player route,
- re-entry, resume, save/load, and bounded recovery behavior under explicit provenance rules,
- plain-language degraded messages when runtime recovery or authoritative refresh fails,
- language and localization clarity,
- and keyboard/form/status behavior that remains usable without privileged knowledge.

The current package proves these unevenly.
It is stronger on:

- shell re-entry and runtime recovery,
- authoritative observation refresh,
- transcript preview and "what changed" shell framing,
- and player-safe separation from operator-only diagnostics.

It is weaker on:

- a fully productized save/load UI on the ordinary player shell,
- evaluator-grade accessibility proof beyond the carried-forward obligation,
- and equally strong evidence for recap/help behavior across all surfaces.

That is why these obligations now belong in the canonical surface document instead of being left implicit.

## Re-entry and shell-loop continuity

The shell loop is more than "frontend exists."
The active source set treats all of these as part of the canonical seam:

- session creation,
- initial shell hydration,
- turn execution,
- transcript refresh,
- runtime readout framing,
- re-entry and resume behavior,
- and continuity when the player returns to a live session.

## Player-facing transport discipline

One of the most easily lost UI truths is that the repository exposes more than one session-facing surface:

- the committed **story-turn / transcript path**,
- operator-oriented **projection / bundle surfaces**,
- and a **live-room WebSocket-style snapshot path**.

Those surfaces may coexist, but they do not all mean the same thing.

The canonical rule is:

- the ordinary player route stays anchored to the **commit-aligned story path**,
- operator bundles remain operator surfaces,
- and any live-room snapshot path must either
  - clearly remain a secondary live-presence surface, or
  - be explicitly productized and tested as part of the player-facing contract.

What may **not** happen is silent drift where two player-visible paths imply different truths without documentation, tests, and audience classification making that difference legible.

## Ordinary-player vs operator separation

One of the strongest preserved laws is route purity.
The ordinary player route must not leak:

- operator panes,
- privileged diagnostics,
- preview material presented as truth,
- alternate runtime feeds masquerading as canonical output,
- or privileged copy/export controls.

Players should get player-safe status and committed results.
Operators should get the deeper provenance and diagnosis surfaces.

## Administration and inspection surfaces remain canonical

The administration layer is still part of the MVP picture.
It includes:

- diagnostics and auditing,
- publish / activation control,
- governance and release surfaces,
- service health,
- observability,
- and inspector-style diagnosis.

These surfaces are not supposed to disappear just because the player route becomes cleaner.

## Concrete inspection domains must remain legible

The earlier complete MVPs were more specific than later summaries.
Inspection is not just “there is some debugging”.
The preserved inspection family includes at least these domains:

- domain records,
- carrier paths,
- transformation traces,
- active conflicts,
- threshold states,
- effect surfaces,
- degraded-mode visibility,
- lineage graph,
- runtime state snapshots,
- and route / audience classification.

Those are the kinds of things operators need to inspect without turning the ordinary player route into an operator dashboard.

## Capability-gated console surfaces remain part of the MVP picture

The source set also preserved two complementary console ideas:

- an **engine-near lightweight ops surface** for readiness and direct runtime-near health,
- and a **capability-gated administration console** for observe / operate / author workflows.

The canonical expectations are:

- **observe** may inspect readiness, state, diagnostics, and run/session detail,
- **operate** may add operational controls such as terminating or recovering runs,
- **author** may add bounded authoring or session-creation actions where governance allows.

This is still part of the MVP because diagnosis, activation, and runtime honesty are operational product value, not afterthoughts.

## Canonical reading

UI/UX and admin surfaces are part of MVP truth because they decide whether:

- the player understands the scene,
- the player sees what changed,
- the player can act without friction,
- the system keeps privileged material off the ordinary route,
- player-visible transport surfaces remain governable,
- and operators can inspect the runtime without contaminating canon.


## Governance pages and high-priority operator journeys

The older complete MVPs were also more concrete about what the administration-tool must let an operator do quickly.
The following journeys remain canonical:

- inspect runtime health without manual log-diving,
- inspect package history and perform emergency rollback,
- compare preview package against active package,
- review findings and revision candidates,
- resolve conflicts inline,
- inspect evaluation deltas and coverage gaps,
- and acknowledge or react to notifications.

These are not separate from UX quality.
They are the operator UX counterpart to player-shell clarity.

## Runtime-health visibility belongs on overview, not only in deep diagnostics

A recurring source-supported UI rule is that important degradation must be visible early.
That includes:

- elevated corrective retry,
- elevated safe fallback,
- threshold-crossing degradation in important scenes,
- and changes that appear after package or policy shifts.

The canonical expectation is therefore that runtime health is visible from an overview surface and not hidden behind specialist drilling.

## Package history, preview comparison, and rollback should stay easy to reach

The earlier governance material preserved three operator UX priorities that remain worth carrying forward directly:

1. emergency rollback should be reachable quickly,
2. preview-vs-active comparison should combine manifest, policy, evaluation delta, and readiness in one place,
3. and revision conflicts should be visible inline rather than requiring deep navigation before an operator can even see the problem.

Even when the exact page layout changes, those priorities remain canonical.

## Notifications are part of honest operations

The older MVP family also preserved a notification surface for:

- failed evaluations,
- urgent review items,
- live fallback spikes,
- budget warnings,
- and delivery-state visibility.

The administration-tool is therefore not only a place to open static pages.
It is supposed to support timely operator attention when quality or runtime posture moves out of bounds.

## MCP operations cockpit remains a bounded admin surface

The MCP material adds one more concrete UI truth:
operators need a cockpit-level view of control-plane activity without turning the UI into a second runtime authority.

The preserved cockpit expectations are:

- suite overview,
- recent activity timeline,
- case-based diagnostics,
- structured logs,
- and only a narrow set of safe actions.

This belongs in the canonical UI family because otherwise MCP becomes architecturally important while remaining operationally invisible.
