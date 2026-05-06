# ADR-0035: Story Opening Economy, Warmup, and Phase Alignment

## Status

Proposed

## Date

2026-05-06

## Context

Canonical content modules already describe an early dramaturgical phase that favors **orientation over escalation**. Example (God of Carnage): `phase_1` / “Polite Opening” in `content/modules/god_of_carnage/scenes.yaml` and `direction/scene_guidance.yaml` — ritual civility, light framing, **no** substantive disagreement yet, triggers intentionally inactive.

Separately, several runtime layers optimize for **immediate visible narrative mass** and **dramatic pressure**:

- Opening-generation prompts currently emphasize establishing tension and stakes early (`world-engine` story runtime opening prompt construction).
- LDSS validation historically expects visible NPC participation (dramatic mass, passivity gates) on ordinary turns; deterministic fallback stubs may emit **mid-conflict** sample dialogue despite phase semantics (`ai_stack/live_dramatic_scene_simulator.py`).
- Product and literary goals (see [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md)) favor a **literary narrator**: atmosphere and perception, not a synopsis of the entire plot before play begins.

Together these forces can produce an **exposition-heavy opening**: cast, conflict spine, and moral stakes spelled out before the player has taken an action — contradicting both canonical phase intent and the literary principle that strong openings often **withhold** context (single image, skew, or invitation to infer).

**Reference dramaturgy (film shooting script):** `resources/carnage-2011.pdf` (*Carnage*, Roman Polanski shooting script dated 2011-01-30) sequences the opening in a way we treat as **normative inspiration** for “economy + handover” (not a literal transcript for the interactive module). Extracted structure of the **first beats**:

1. **Title / form** — script identification only.
2. **Part A — Background without living-room dialogue (EXT. PLAYGROUND — DAY):** Pure **scene description**: Brooklyn playground, winter light, the two boys, verbal abuse, shove, strike with the branch, injured child, crowd. No character dialogue yet; the audience receives the **precipitating event** through **action and image**, not through a narrator explaining morals.
3. **Part B — Into the scene (INT. LONGSTREET APARTMENT — DEN — DAY):** **Slugline + spatial description** (narrow den, light, table objects, laptop). **Blocking and social temperature** in prose (“these two couples are not close… serious, cordial and tolerant”). **Then** the first **spoken** lines begin — Penelope **reads** the prepared statement (the incident restated as *in-world document text*, not as omniscient voiceover dumping the whole evening).

That split matches the product intent: **(1)** premise / fact pattern / “why we meet” can be **longer** if it is **shown** (action, document, ritual) rather than **told** as argumentative recap; **(2)** entering the playable space is a **second movement** — room, bodies, mood — before dialogue does the heavy lifting. **Narrator-style support** in our engine should mirror the screenplay’s **scene description** function: complete **sensory and social imagination** at hinge moments, **without** parroting what a dialogue block or obvious staging already conveys.

> **Licensing:** The PDF may be subject to copyright; keep distribution and CI policy aligned with your license. The ADR cites it as a **dramaturgical reference**, not as text to ship verbatim.

> **Repository:** `resources/carnage-2011.pdf` is present in-repo for maintainer analysis; clones may omit large binaries via sparse checkout — the structural claims above remain valid without the file.

Opening **readiness** and **truthful degradation** remain governed by [ADR-0033](adr-0033-live-runtime-commit-semantics.md); this ADR does **not** relax opening-evidence requirements. It defines **what kind** of opening text is desirable once evidence exists.

## Problem Statement

1. **Semantic drift:** Canonical phase 1 (“warmup / polite framing”) can be undermined by runtime defaults that prioritize confrontation-like NPC lines or plot recap.
2. **Economy vs. encyclopedia:** Player-facing first beats risk reading like half the synopsis instead of a **hook** (orientation without resolving the whole arc).
3. **Unclear contract:** We lack an explicit product/engine agreement on **opening composition**: how much scene-setting vs. how much withheld until play advances.

## Decision (Future State — Design Intent)

This section describes **intended behavior after intentional implementation work**. No subsystem is obligated until this ADR is accepted and broken down into tasks.

### D1 — Opening economy principle

The **first committed player-visible narrative beat** after session acceptance should prioritize:

- **Grounding:** place, time-quality (evening, indoor ritual), who is present — shown through observable behavior or setting detail, not exhaustive backstory.
- **Invitation:** one clear dramatic question or imbalance in the room — **without** naming every faction’s moral thesis upfront.
- **Restraint:** defer systematic exposition (full incident recap, legal framing, character dossiers) to **later beats** driven by player curiosity or escalation.

“Economy” here means **fewer predicates per sentence**, not fewer tokens arbitrarily.

### D2 — Phase alignment

Runtime-generated openings (narrator + NPC lanes as applicable) should **honor the active content-module phase** when `current_scene_id` / phase metadata maps to an early phase:

- Early-phase openings avoid **trigger-shaped conflict** and **attack-shaped NPC dialogue** unless the phase definition explicitly allows them.
- Phase transitions remain **engine-owned** (authoritative content rules); the opening text must not pretend a phase transition occurred.

### D3 — Two-part opening (product default for GoC-style modules)

For drawing-room and similar modules, the **first session narrative** should be composable as **at least two committed narrative movements** (not necessarily two HTTP requests — see Open Questions), each delivered as **one or more typed blocks** so the player shell can hand over attention **block by block** (typewriter pacing per [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md)):

| Part | Dramaturgic job | Typical lane mix (illustrative) |
|------|-----------------|----------------------------------|
| **Part 1 — Background / premise** | Establish *why we are here* and the off-stage fact pattern the characters already share — enough that later lines land, **without** playing the whole fight in advance. | Narrator-forward; optional brief documentary-style framing if the module contract allows; NPC lines stay **non-accusatory** and phase-1 compatible. |
| **Part 2 — Into the scene** | Land the **room**: physical layout, ritual (seating, drink, food), who faces whom; let subtext breathe; end on an **invitation to play** (silence, glance, social trap) rather than on an NPC attack line. | Narrator inserts **complete imagination** (sensory, spatial, social temperature) at **hinge moments**; NPC speech favors ritual and avoidance until the player steers. |

**Narrator bar:** Interjections should **not** restate what the block stream already shows (e.g. repeating dialogue the player just read). They add what **staging alone cannot**: atmosphere, timing, social nuance — the script’s “intelligent narrator” role, not a wikipedia voiceover.

**Typewriter:** The shell’s typewriter is a **first-read experience** instrument: within each committed envelope, blocks reveal in order so the player is **guided into fiction** rather than wall-of-text dumped. Policy details (last-block-only vs. per-block) remain under ADR-0034; this ADR only requires that **opening envelopes are authored** so that block boundaries **match** natural handover beats.

### D4 — Deterministic and degraded openings

Deterministic / mock / fallback openings must **not** contradict phase-1 civility when simulating God-of-Carnage-style modules unless diagnostics explicitly label an intentional stress scenario. Degraded output remains truthful under ADR-0033 but should not become the **canonical literary template** for production tone.

### D5 — Relationship to shell contract

[ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) continues to govern **how** blocks render (lanes, typewriter). This ADR governs **what literary posture** the committed bundle should carry at session start.

## Non-goals (This ADR)

- Replacing content-module YAML with runtime-authored story truth.
- Removing NPC visibility or validation gates globally — any relaxation applies **only** to explicitly designated opening beats and must be specified in a follow-on technical ADR or task list.
- Guaranteeing LLM creativity (“beautiful sentences”) — only **constraints** and **composition rules**.

## Consequences

### Positive

- Shared vocabulary (**economy**, **warmup**, **phase alignment**) for narrative, engine, and QA.
- Clear rationale when rejecting prompts or stubs that recap the whole arc at minute zero.

### Negative / Risks

- Stricter opening composition may require validation rule updates and golden-fixture refreshes.
- Tension with pipelines tuned for “always show NPC speaking early” — requires deliberate redesign where necessary.

## Open Questions (Elaborate Before Implementation)

1. **Single vs. multi-step warmup:** Is warmup always one committed narrator-heavy envelope, or do we ever commit an explicit two-phase UI (“scene established” → “your move”)?
2. **NPC silence threshold:** Under phase 1, what is the minimum acceptable NPC surface — ambient action only vs. one polite line — without violating LDSS passivity policies?
3. **Provider-backed vs. deterministic openings:** Under MVP gates, when must openings remain deterministic LDSS vs. provider-generated — does literary economy change MVP acceptance criteria?
4. **Module variability:** Should economy rules be **per-module** overrides (e.g. thriller vs. drawing-room drama) in `module.yaml` or direction packs?
5. **Localization:** Economy rules apply to German-first GoC text — how do we regression-test without brittle line matchers?

## Verification (Deferred)

Until implementation exists:

- No mandatory gate beyond document review and stakeholder **acceptance** of this ADR.

After implementation:

- Targeted tests on opening envelopes (golden texts or structured assertions), scoped per agreed tasks — invoked via `python tests/run_tests.py` per suite touched.

## References

- `resources/carnage-2011.pdf` — *Carnage* (2011) shooting script; opening sequencing (playground → apartment) as dramaturgical reference
- `content/modules/god_of_carnage/direction/opening_sequence.yaml` — canonical two-part opening + narrator bar + premise seeds (bundled as `opening_sequence` in GoC YAML slice)
- `content/modules/god_of_carnage/scenes.yaml` — `session_opening` pointer; phase_1 polite opening
- `content/modules/god_of_carnage/direction/scene_guidance.yaml` — phase guidance
- `content/modules/god_of_carnage/direction/system_prompt.md` — phase semantics (“structural, not stage directions”)
- `world-engine/app/story_runtime/manager.py` — `_build_opening_prompt` (opening prompt construction)
- `ai_stack/live_dramatic_scene_simulator.py` — deterministic LDSS blocks and validation commentary
- [ADR-0033](adr-0033-live-runtime-commit-semantics.md) — opening readiness / commit truth
- [ADR-0034](adr-0034-player-facing-narrative-shell-contract.md) — player shell / narrator lane presentation

## Acceptance Criteria for ADR Promotion

Move from **Proposed** to **Accepted** when:

1. Narrative governance and runtime owners confirm Open Questions are resolved or explicitly deferred with owners.
2. At least one concrete implementation epic outline references this ADR (issue or planning doc link).
