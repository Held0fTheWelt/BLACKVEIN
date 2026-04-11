# Task: Implement despaghettification (wave by wave)

*Path:* `despaghettify/spaghetti-solve-task.md` — Overview: [README.md](README.md).

**Counterpart** to [spaghetti-check-task.md](spaghetti-check-task.md): there, metrics are collected and **Latest structure scan** (including **M7**) is maintained — **without** changing code. The check maintains the **DS table** and **proposed** implementation order when trigger policy is met (**M7 >= 25%** or **any category >= 45%**); below that threshold the scan section is enough. **Here**, the implementation agent **reviews the recommended implementation order**, proposes **revisions** if needed, then **independently** implements per Despaghettify rules **wave by wave** or **task by task** (typically **one session ≈ one wave** or a clearly bounded phase slice), until the agreed list is **done** and a factual **success** message is allowed.

## Binding sources

| Document | Role |
|----------|------|
| [despaghettification_implementation_input.md](despaghettification_implementation_input.md) | Canonical: **information input list**, **recommended implementation order**, § *DS-ID → primary workstream*, § *Latest structure scan* field **Open hotspots** (solve track **must** clear or update resolved items — see Phase 2); after each wave follow § *Maintaining this file during structural waves*. |
| [state/EXECUTION_GOVERNANCE.md](state/EXECUTION_GOVERNANCE.md) | **Completion gate**, pre/post artefacts, state from evidence — mandatory for every structural wave. |
| [state/WORKSTREAM_INDEX.md](state/WORKSTREAM_INDEX.md) | Slugs and mapping to `artifacts/workstreams/<slug>/pre|post/`. |
| Matching `state/WORKSTREAM_*_STATE.md` | Read before start; update after the wave from post evidence. |
| [spaghetti-check-task.md](spaghetti-check-task.md) | Optionally re-run after **large** waves or at the end to align the **structure scan** with the repo; DS / phase sections only when the check prescribes them via M7 trigger policy (otherwise scan is enough). |

## Do not

- Do **not** touch `docs/archive/documentation-consolidation-2026/*` (see check task).
- Do **not** make closure or success claims without satisfying the **completion gate** from `EXECUTION_GOVERNANCE.md`.
- Do **not** work the same **DS-ID** in parallel with another owner (coordination in the input list).
- No “silent” shortcut: missing pre/post or missing pre→post comparison = **stop**, not keep writing.

## Phase 1 — Review implementation order (and revise if needed)

1. **Read the input list:** § *Information input list* and § *Recommended implementation order* in full; read **Open hotspots** under § *Latest structure scan* (known structural pain called out there); reconcile **DS-ID → workstream** table.
2. **Consistency check:** every phase row references **existing** DS-IDs; dependencies (interfaces before bulk moves, collisions from *collision hint*) are **plausible** and match the repo.
3. **Contradiction stop rule:** contradiction between repo, state documents, and table → stop; record in the affected `WORKSTREAM_*_STATE.md` or in the input list under *open hotspots* / phase notes; adjust order **only** after clarification.
4. **Revision:** if order must change, update the **same** input list (phase table, short logic/notes); no parallel “secret plan” file.

## Phase 2 — Loop: one wave per clear unit

Per **wave** (or per **DS-ID** if one-ID-one-wave is explicitly agreed):

1. **Read state:** `EXECUTION_GOVERNANCE.md`, `WORKSTREAM_INDEX.md`, matching `WORKSTREAM_*_STATE.md`.
2. **Pre:** create artefacts under `despaghettify/state/artifacts/workstreams/<slug>/pre/` (naming and minimum content per input list / governance — at least human-readable + preferably machine-readable).
3. **Implementation:** code/structure per **direction** in the DS row; preserve behaviour; keep relevant tests / CI green.
4. **Post:** artefacts under `…/post/`; document **pre→post** comparison.
5. **State & input list:** `WORKSTREAM_*_STATE.md` and [despaghettification_implementation_input.md](despaghettification_implementation_input.md) per § *Maintaining this file during structural waves* (table, scan when measurably changed, implementation order when priority shifts, optional work log).
6. **Open hotspots — solve track owns resolution in the list:** Still in the **same** PR/commit as the wave, edit the **Open hotspots** cell (or bullet block) under § *Latest structure scan* in the input list **without** waiting for a new [spaghetti-check-task.md](spaghetti-check-task.md) run (the check may skip DS/hotspot edits when trigger policy is not met). Rules:
   - If this wave **fully** fixes a named hotspot (function split, module boundary, or other item explicitly listed there): **remove** that fragment from **Open hotspots**, or replace the cell with **—** when nothing remains; optionally add one short clause in the work log or next scan *as-of* line: `Open hotspots: cleared <name> (DS-xxx, PR …)`.
   - If the wave **only mitigates** part of a hotspot: **rewrite** the hotspot text to the **remaining** risk (shorter, concrete); do not delete the entry while risk remains.
   - If the wave **does not** touch a hotspot: **leave** that part of **Open hotspots** unchanged for this wave.
   - Do **not** use **Open hotspots** to invent new DS work — new structural rows still belong in the **information input list** table when trigger policy is met (or by explicit team agreement); this step is for **closing or narrowing** items already recorded as known structure problems.
7. **Next wave:** start only when steps 5–6 are done for the current ID/phase and no open contradictions violate the gate.

**Session discipline:** prefer **one** completed wave per session over half waves across many chats — easier review, PRs, and traceability.

## Phase 3 — Closure and success message

**Success** may only be claimed when **all** DS / phase units planned in the agreed § *Recommended implementation order* have passed the **completion gate** **and** the input list reflects the state (completed rows marked, order consistent). Where waves targeted **Open hotspots**, those entries must be **updated or cleared** per step 6 so the “known structural problems” list does not contradict the repo.

**Success message (minimum content):**

- Which **DS-ID(s)** / phases are **done** (reference input list and workstream state).
- Briefly: **tests / CI** (what ran) and where **pre/post** live.
- Optional: pointer to a follow-up [spaghetti-check-task.md](spaghetti-check-task.md) run if numbers matter for stakeholders.

Do **not** treat as overall success: partially done list, missing artefacts, or “almost green” without documented pre→post comparison.

## Relationship to the check task

| Aspect | [spaghetti-check-task.md](spaghetti-check-task.md) | spaghetti-solve-task.md (this document) |
|--------|---------------------------------------------------|------------------------------------------|
| Change code | No | Yes (structural, wave-wise) |
| Input list | Scan **always**; DS table + order **only propose** when M7 trigger policy is met (see check task) | **Review/revise** order, then maintain table/scan/log **during implementation**; **independently** maintain **Open hotspots** when waves resolve them (step 6) |
| Pre/post artefacts | Only for an explicit wave via another process | **Mandatory** per wave per governance |

---

*Goal:* From the **analysis track** (check) to the **execution track** (solve) without a governance gap — until the Despaghettify list is factually complete.
