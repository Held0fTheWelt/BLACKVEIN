# Gap and tension record

## Issue list

### PRR-01 — Docs root still routes to older canonical/evidence lanes
- **Type:** structural clutter / authority-lane drift
- **Where:** `docs/README.md`
- **Problem:** still calls `docs/MVPs/world_of_shadows_canonical_mvp/README.md` the primary canonical spine and still highlights `world_of_shadows_canonical_mvp_repair_2026-04-20/`.
- **Why it matters:** weakens the repaired claim that the active recomposed route is now the real first-pass center.
- **Disposition:** rewrite / reroute.

### PRR-02 — Audit root still prefers the older repair bundle
- **Type:** evidence-lane fragmentation
- **Where:** `docs/audit/README.md`
- **Problem:** presents the 2026-04-20 repair package as the active repair package instead of the 2026-04-21 repair-implementation lane.
- **Why it matters:** makes the current evidence posture look older than it is.
- **Disposition:** rewrite / re-rank / bound older bundles as historical support.

### PRR-03 — Companion README still semantically competes with the active route
- **Type:** naming drift / over-fragmentation
- **Where:** `docs/MVPs/world_of_shadows_canonical_mvp/README.md`
- **Problem:** says the active route is primary first-pass, then uses the heading “Primary canonical spine” for the detailed companion sequence.
- **Why it matters:** readers can still mistake the deeper companion family for an equal first-pass route.
- **Disposition:** rename section and update proof-route language.

### PRR-04 — Current evidence route is not singular
- **Type:** proof/evidence mismatch
- **Where:** `docs/README.md`, `docs/audit/README.md`, `docs/MVPs/world_of_shadows_canonical_mvp/README.md`, active route proof docs
- **Problem:** different docs point to different “current” repair/proof bundles.
- **Why it matters:** weakens honest proof reading and encourages audit sprawl.
- **Disposition:** establish one current evidence route, keep older bundles visible but explicitly historical.

### PRR-05 — UI support obligations still remain partial rather than closed
- **Type:** UI/UX gap / proof gap
- **Where:** `frontend/templates/session_shell.html`, `frontend/app/routes.py`, user docs, active route UI doc
- **Problem:** recap/help/save-load/accessibility are named honestly, but not equally implemented or replay-proven.
- **Why it matters:** still a real product gap, not merely a wording issue.
- **Disposition:** preserve as explicit obligation; do not overclaim closure.

### PRR-06 — Frontend rerun remains environment-bounded
- **Type:** proof/evidence limitation
- **Where:** `frontend/tests/test_routes_extended.py` replay attempt in this pass
- **Problem:** Flask unavailable in this environment.
- **Why it matters:** prevents fresh end-to-end-like route replay for the player shell.
- **Disposition:** keep explicit as environment-bounded proof, not as absence of tests.

### PRR-07 — Broader WoS target families still carry more through lineage than through active replay
- **Type:** under-integration / concept durability tension
- **Where:** active route target-layer docs + `mvp/docs/*`
- **Problem:** memory, consciousness, recovery intelligence, analytics, multi-session continuity remain canonically preserved but only partially bridged into current proof.
- **Why it matters:** still vulnerable to future compression if route discipline decays.
- **Disposition:** preserve as enduring target truth and keep carry-forward map visible.

### PRR-08 — Mirrors remain bounded but still physically present
- **Type:** duplicate / near-duplicate risk
- **Where:** root GoC mirrors, embedded `repo/` tree
- **Problem:** improved notices reduce ambiguity, but physical duplication still exists.
- **Why it matters:** accidental drift remains possible if readers bypass route discipline.
- **Disposition:** keep bound; do not silently remove.

## Contradictions or near-contradictions

1. **Active route vs docs root routing**
   - repaired package says the active route is primary first-pass;
   - docs root still foregrounds the older parent spine.

2. **Current repair/evidence bundle naming**
   - the repaired package created a 2026-04-21 repair-implementation lane;
   - audit root still points to 2026-04-20 as the active repair package.

3. **Companion README wording**
   - says active route is first-pass;
   - then labels the deeper sequence as “Primary canonical spine”.

These are not architecture contradictions. They are **navigational and evidence-posture contradictions**.

## Explicit follow-up obligations

- Normalize docs root and audit root to the active route and current repair/evidence lane.
- Normalize the detailed companion README’s naming and proof references.
- Keep frontend support obligations explicit until replayed in a Flask-provisioned environment.
- Preserve broader WoS target families in canonical view without upgrading them to false “implemented now” status.
