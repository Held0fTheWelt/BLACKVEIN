# God of Carnage acceptance and experience proof matrix

## Why this document exists

God of Carnage is the current proof-bearing center of the World of Shadows MVP.
That makes it dangerous to describe too vaguely.

If the GoC slice is reduced to "dramatic dialogue with continuity," later cleanups can lose the specific behaviors the slice was actually proving.
This matrix turns those behaviors into a compact acceptance layer.

## Acceptance reading rule

These are not broad redesign wishes.
They are the player-facing and runtime-facing seams that already recur across the later proof corpus and the earlier MVP intent.

A seam belongs in this matrix when all three are true:

1. it materially changes the player experience,
2. it appears repeatedly in the audited source family,
3. and losing it would weaken the distinction between World of Shadows and generic conversational play.

## Canonical GoC acceptance matrix

| Experience seam | What the player should feel | Current support | Stronger proof still worth keeping or adding |
|---|---|---|---|
| Scene identity stays canonical | the runtime knows which dramatic surface is live and does not drift silently between scene interpretations | ai-stack scene-identity support, slice contracts, later closure corpus | keep direct tests aligned with any future scene-map change |
| Character-addressed response framing | the player can tell who is responding and why this response belongs to that character line | later character-addressed response hardening and visible-line framing work | preserve route-level and shell-level replay coverage |
| Side and pair geometry | social alliances, temporary pairings, and asymmetric relation lines remain legible | later GoC dramatic geometry closures | keep explicit examples in proof corpus so the geometry is not compressed away |
| Room and object pressure | the room is active dramatic pressure, not decorative stage dressing | active slice reports and experience closures | retain concrete scenarios where objects and room facts re-enter later turns |
| Carry-forward wound and consequence | the player's move leaves pressure behind and later turns still remember it | continuity, wound, and social-state support surfaces | continue direct continuity tests under re-entry and longer turn runs |
| Immediate prior-turn continuity reuse | the next visible turn clearly reacts to the last committed exchange instead of resetting tone | current active slice closure corpus | keep player-shell and runtime tests proving this remains visible |
| Delayed continuity reuse after an intervening turn | earlier pressure can come back even after the conversation briefly moves elsewhere | later delayed-reuse closures | keep at least one durable regression test around this seam |
| Interruption and re-entry pressure | social conflict can cut across turns and return without flattening into neutral chat turns | interruption and shell re-entry hardening | preserve tests that combine transcript progression with re-entry behavior |
| Multi-speaker relay and handoff | more than one social line can remain alive without collapsing into one bland narrator voice | later multi-speaker and micro-weave proof surfaces | keep representative relay scenarios alive in the proof bundle |
| Shell framing around the latest committed truth | the shell shows the most recent committed dramatic state instead of generic replay text | world-engine shell readout tests and packaged shell-loop proof | re-run frontend route-level shell framing when the replay environment is ready |
| Authored module authority | the runtime feels authored without becoming rigid, and fallback does not silently replace canon | content/module contracts, publish/runtime continuity docs, GoC fallback governance | keep published-path vs fallback-path distinctions explicit in tests and docs |

## Minimum acceptance standard for future refactors

A future refactor should not be called safe if it leaves GoC "working" while any of these degrade materially:

- character distinction becomes vague,
- continuity becomes shallow or purely local,
- room/object pressure stops mattering,
- relay/multi-party dynamics flatten,
- the shell can no longer show the latest committed framing clearly,
- or authored module authority becomes interchangeable with convenience fallback.

That would be a functional regression of the MVP, not just a wording change.

## Recommended proof discipline

When time or environment constraints force selective replay, priority should stay with seams that prove the difference between governed dramatic runtime and generic chat:

1. commit-aligned visible framing,
2. continuity reuse,
3. room/object pressure,
4. multi-speaker relay,
5. authored-canon vs fallback discipline.

## Anti-loss rule

If a future MVP summary mentions GoC without making these acceptance seams legible, that summary is incomplete and should not replace this canonical layer.
