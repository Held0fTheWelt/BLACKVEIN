# GATE_SCORING_POLICY_GOC.md

Governance and scoring frame for Phase 0 Freeze and implementation of the MVP vertical slice **God of Carnage**. Normative process: `docs/FREEZE_OPERATIONALIZATION_MVP_VSL.md`; quality goals: `docs/ROADMAP_MVP_VSL.md` §11. **Canonical turn schema, seams, and scene direction** are defined in `docs/CANONICAL_TURN_CONTRACT_GOC.md`; **slice boundaries, Reality Anchor, bridge, vocabulary basis** in `docs/VERTICAL_SLICE_CONTRACT_GOC.md`.

---

## 1. Gate families and scoring logic

### 1.1 Families (canonical labels)

Same gate labels are reused in diagnostics and reports (aligned with `CANONICAL_TURN_CONTRACT_GOC.md` §6).

| Gate family | Purpose | Primary inputs |
|---|---|---|
| `slice_boundary` | Scope, out-of-scope grace, no false world claims outside GoC | Slice contract, player input, `failure_markers` |
| `turn_integrity` | Seams respected: proposal ≠ commit ≠ visibility without policy | Canonical turn, seams |
| `dramatic_quality` | Roadmap goals (scene not summary, asymmetry, readable escalation) | Scenario anchors, `visible_output_bundle`, `scene_assessment` |
| `diagnostic_sufficiency` | Operational and dramatic traceability | `graph_diagnostics`, `diagnostics_refs`, replay questions (§5) |

### 1.2 Scoring rules (qualitative)

Each routine evaluation per anchor scenario assigns:

- **pass:** all mandatory checks for the family satisfied; no open `closure_impacting` markers.
- **conditional_pass:** smaller gaps with documented follow-up owner and deadline (FREEZE §5.4); allowed only for **first-cycle mandatory** gaps, not freeze-critical.
- **fail:** seam violation, false truth claim, mandatory diagnostic questions unanswerable, or unresolved `closure_impacting` finding.

**Bundling:** A scenario “passes” when **all** activated families for that scenario reach at least `conditional_pass`, and `turn_integrity` and `diagnostic_sufficiency` are not `fail`.

---

## 2. Review bundles

| Bundle ID | Gate families included | Typical mode | Minimum output |
|---|---|---|---|
| `operator_compact` | `diagnostic_sufficiency` (+ light `slice_boundary`) | compact, operator-first | Short log: health, node order, errors, repro core fields |
| `dramatic_expanded` | `dramatic_quality`, `turn_integrity`, `slice_boundary` | expanded | Scene-function rationale, continuity, visibility |
| `freeze_integrity` | all four families | full | Tabletop trace (§8), link to freeze rules |

**Splitting rule (FREEZE §17.2):** If a bundle is repeatedly skipped or “too broad,” it **must** be split into two bundles with a clear family split; deadlock without split = governance failure (FREEZE §17.4).

---

## 3. Minimal operating mode

- **Named owner role per bundle** in routine operation (may be the same person; must be explicit on the team roster or equivalent).
- **Default bundle:** `operator_compact` — compact, technical.
- **Minimum anchor scenarios** per routine pass: **2**, unless a documented substitute with equivalent coverage exists.
- **Escalation** to `dramatic_expanded` or `freeze_integrity` when compact diagnostics cannot answer **mandatory questions** in §5.
- **Escalation is mandatory** when ambiguity touches truth or seam claims — not optional.

---

## 4. Cadence table (binding)

Designed for a **small team** and **AI-accelerated** workflow (short cycles, explicit backups).

| Routine bundle | Owner role | Cadence | Minimum scenarios | Escalation trigger | Delegate / backup |
|---|---|---|---|---|---|
| `operator_compact` | **Runtime / graph owner** (engineering) | **Weekly** (e.g. end of week or end of each weekly milestone) | 2 | `execution_health` not healthy without explained cause; or non-empty `errors` when success was expected; or `repro_metadata` insufficient for the last failed run | **Backup:** second engineer on the project; if solo, document **interim self-review + logged limitation** and escalate to `dramatic_expanded` within **3 business days** |
| `dramatic_expanded` | **Slice / dramaturgy owner** (content + scene judgment) | **Every 2 weeks** or **end of each sprint** (whichever is shorter) | 2 | Suspicion of summary-not-scene, missing responder asymmetry, or visibility without identifiable commit path | **Backup:** runtime owner performs **checklist-only** pass and files findings; full dramatic sign-off waits for slice owner or freeze_integrity |
| `freeze_integrity` | **Both** runtime owner **and** slice owner **jointly** (same meeting or async sign-off with both names) | **Before execution-task derivation**; **before each milestone** that changes vocabulary or seams; **within 5 business days** of any seam/vocabulary amendment | **2 + 1 thin-edge** | Start of task derivation; or any change to controlled vocabulary, seams, or canonical YAML authority | **Backup:** if one role unavailable, the other runs the bundle **once** with `experiment_preview: true` on the run record and **does not** declare MVP-ready; joint sign-off required before “ready” claims |

**Binding:** The table above is the **authoritative** cadence and delegation rule for Phase 0 GoC freeze operations. Drift without review is a process defect, not an silent excuse to skip gates.

---

## 5. Diagnostics: shared basis and read modes

### 5.1 Shared data basis

**Shared data basis:** Runtime output including **`graph_diagnostics`** as set by `_package_output`: `graph_name`, `graph_version`, `nodes_executed`, `node_outcomes`, `fallback_path_taken`, `execution_health`, `errors`, `capability_audit`, `repro_metadata`, `operational_cost_hints`, plus **`diagnostics_refs`** and canonical turn fields on `RuntimeTurnState`. For a **single compact operator record**, use **`build_operator_canonical_turn_record(state)`** from `ai_stack/goc_turn_seams.py` (post-`package_output` state) — same underlying data, no second truth surface.

**Read modes:** **Filtered views** on the same basis — no second conflicting truth. Expanded mode adds dramatic fields from the canonical turn (`scene_assessment`, `selected_scene_function`, `visible_output_bundle`, continuity).

**Default:** `operator_compact`.

**Automatic escalation to expanded mode when:**

- `turn_integrity` or `dramatic_quality` is doubted, or  
- `validation_outcome` / `committed_result` are missing but visible output **suggests factual** consequences, or  
- `failure_markers` carry `closure_impacting` (§6).

### 5.2 Mandatory questions — technical operator (binding)

An operator pass **must** be able to answer:

1. **Which graph ran?** → `graph_name`, `graph_version`  
2. **Which nodes ran, with what outcome?** → `nodes_executed`, `node_outcomes`  
3. **Was fallback taken?** → `fallback_path_taken`  
4. **Overall health?** → `execution_health`  
5. **What hard errors exist?** → `errors`  
6. **What capabilities were audited?** → `capability_audit`  
7. **Is the run reproducibly documented?** → `repro_metadata` (adapter/path summary when set)  
8. **Rough operational/cost context?** → `operational_cost_hints`  

### 5.3 Mandatory questions — dramatic reviewer (binding)

Everything in §5.2 **plus:**

1. **Which scene function was chosen, and does it support the visible move?** → `selected_scene_function`, `visible_output_bundle`  
2. **Is the responder set plausible for the pressure field?** → `selected_responder_set`, `scene_assessment`  
3. **Is continuity carry-forward visible, not just history text?** → `continuity_impacts`, continuity classes  
4. **Does visibility stay within doctrine?** → `visibility_class_markers`, seams  
5. **Where is the boundary between proposal and committed truth?** → `proposed_state_effects`, `validation_outcome`, `committed_result` — if validator/commit absent, record **explicit gap**; silent OK is forbidden  

### 5.4 CI / reproducibility (binding)

- **CI jobs** that claim to gate merge readiness **must** run with sufficient context that questions **1–7** in §5.2 are answerable from artifacts the CI retains (logs or attached `graph_diagnostics`).
- If `repro_metadata` is **empty or missing** for a failed CI run, `diagnostic_sufficiency` is **`fail`** for that scenario (not `conditional_pass`).
- If `repro_metadata` is missing for a **passing** CI run, `diagnostic_sufficiency` is **`conditional_pass`** with a **documented owner and date** to add repro fields, or **`fail`** if the pipeline claims freeze_integrity / MVP readiness.

---

## 6. Failure-to-response mapping

### 6.1 Qualitative severity ladder

1. **containment-first:** Limit damage; minimal or no new truth claims; player gets scene-coherent clarity.  
2. **review-first:** Session may pause or continue **marked**; **no** “fully valid / MVP-ready” claim until review.  
3. **closure-impacting:** Freeze or release claims not met; task conversion or merge blocked until fixed or formally downgraded (FREEZE §5).

**Default safe-failure:** containment-first with clear diagnostic marking.

### 6.2 Experiment / preview flag (binding)

- **`experiment_preview: true`** is recorded on the run (in `diagnostics_refs` or an equivalent host-level field echoed into diagnostics).  
- When `experiment_preview: true`, the run **must not** be interpreted as MVP-complete, production-ready, or “engine validates / commits” in good standing.  
- **Any** marketing or roadmap language implying MVP readiness **is false** for `experiment_preview` runs.  
- Downgrade from `closure-impacting` to `review-first` for missing validation/commit paths **requires** `experiment_preview: true` **and** truth-safe visible behavior (§6.4).

### 6.3 Truth-safe visible behavior under preview (binding)

When validation or commit paths are absent:

- Player-visible copy **must** use **containment-first** staging: no claim that effects are **validated** or **committed** world truth.  
- Use visibility classes and copy patterns consistent with `non_factual_staging` or explicit “preview” framing **without** inventing lore facts.  
- Violation → `turn_integrity` **fail** and **`closure_impacting`**.

### 6.4 Failure class → response (binding)

| Failure class | Severity | Visible response style | Diagnostic marking | Gate impact |
|---|---|---|---|---|
| `missing_scene_director` | **review-first** | Neutral hold or reduced response; **no** pretense of scene-function choice | `failure_markers` with `failure_class: missing_scene_director` | `dramatic_quality` **fail** or `conditional_pass` with dated owner plan; `turn_integrity` **review-first** |
| `missing_validation_path` | **`closure_impacting`** by default | No output that presents effects as **validated** truth; containment-first | `failure_markers`: `validation_gap` | `turn_integrity` **fail** if visible output implies validation; else **`closure_impacting`** until path exists **or** run is **`experiment_preview: true`** → **review-first** only |
| `missing_commit_path` | **`closure_impacting`** by default | Proposal-only or explicitly non-binding; no factual world claims without `committed_result` | `failure_markers`: `commit_gap` | `turn_integrity` **fail** if factual claims without commit; **`closure_impacting`** unless **`experiment_preview: true`** → **review-first** only |
| `model_fallback` | **containment-first** | Reduced/stub response per fallback policy | `execution_health` + `fallback_path_taken` | `diagnostic_sufficiency` **pass** if explainable; else escalate |
| `graph_error` | **containment-first** to **review-first** by severity | Scene-safe error without new lore | `errors`, `execution_health` | `diagnostic_sufficiency` **fail** if §5.2 questions unanswerable |
| `scope_breach` | **containment-first** | Out-of-scope grace (slice contract §2.3) | `failure_markers`: `scope_breach` | `slice_boundary` **fail** if scope still expanded |
| `validation_reject` | **containment-first** | Visible rejection or alternate move offer | `validation_outcome.status` | `turn_integrity` **pass** if consistent |
| `continuity_inconsistency` | **review-first** | No commit of conflicting effects; hold/clarify | `failure_markers`: `continuity_inconsistency` | `dramatic_quality` **conditional_pass** until resolved |

**Closure vs review-first (summary):**

- **`closure_impacting`:** Missing validation or missing commit on a run that is **not** `experiment_preview: true`, **or** any faked validation/commit claim, **or** freeze_integrity / MVP-ready claims without paths.  
- **`review-first`:** Allowed **only** when `experiment_preview: true` **and** visible output is truth-safe per §6.3; still **blocks** “MVP-ready” language until paths exist.

---

## 7. Controlled vocabulary (gate and review reference)

Identical to `docs/VERTICAL_SLICE_CONTRACT_GOC.md` §5 for **scene / pacing / silence-brevity / continuity / visibility / failure / transition pattern** classes.

**Gate document extensions (review metadata only):**

| Semantic area | Canonical label | Temporary alias allowed? | Cutover rule | Deprecation rule |
|---|---|---|---|---|
| Gate family | `slice_boundary`, `turn_integrity`, `dramatic_quality`, `diagnostic_sufficiency` | no | Rename only via freeze amendment | Old gate names in CI after cutover = error |
| Bundle ID | `operator_compact`, `dramatic_expanded`, `freeze_integrity` | yes (one sprint) in migration table | Document parallel use | Remove alias after cutover |
| Scoring outcome | `pass`, `conditional_pass`, `fail` | no | — | — |
| Run marker | `experiment_preview` (boolean) | no | Add/remove only via freeze amendment | After cutover, stale markers = governance error |

---

## 8. Tabletop trace-through (evidence structure)

Before task conversion (FREEZE §21): evidence that rules, vocabulary, schema, and gates work together.

### 8.1 Scenario mix (minimum)

- at least **one** standard GoC scenario  
- at least **one** thin-edge scenario  
- at least **one** out-of-scope / scope-breach  
- at least **one** anti-seductive scenario (smooth text without scene)  
- at least **one** scenario with **multiple** simultaneous pressure/continuity lines  

### 8.2 Evidence per “full” trace (FREEZE §21.3)

For at least **one** scenario document:

1. Applied freeze rule (slice or turn contract reference)  
2. Vocabulary used (concrete labels)  
3. Gate family affected and outcome  
4. Diagnostic answers to mandatory questions from §5  
5. One precise task implication line  

### 8.3 Success criteria (FREEZE §21.2)

Tabletop passes when: rules apply, vocabulary suffices, starter schema can represent the turn, priorities remain readable under competing lines, diagnostics answer mandatory questions, and tasks derive without semantic drift.

---

## 9. Dependency / escalation matrix

| Upstream freeze item | Affected work block(s) | Missing / weak consequence | Allowed continuation? | Escalation action |
|---|---|---|---|---|
| Canonical turn schema + field ownership (`CANONICAL_TURN_CONTRACT_GOC.md`) | Runtime nodes, persistence, APIs | Incompatible field reads | conditional | Freeze amendment or architecture review within one timebox cycle |
| Seams explicit | Validator, commit, UI/render | Proposal/truth mixed | no for productive player turns | Stop + `turn_integrity` closure-impacting until resolved |
| Scene director §3 turn contract | All director fields | Hidden logic in one model call | conditional only under `experiment_preview` | Escalate to `dramatic_expanded`; reduce scope if needed |
| Slice boundaries + canonical YAML (`VERTICAL_SLICE_CONTRACT_GOC.md`) | Content pipeline, loading | Drift YAML / builtins / writers-room | conditional | Reconcile to YAML authority; §6 binding |
| Controlled vocabulary + cutover | Gates, parsers, diagnostics | Mixed labels | no in CI | Vocabulary migration task |
| Failure-to-response (this document §6) | UX, operations | Unsafe ambiguous failures | conditional | Assign owner; `freeze_integrity` bundle |
| Tabletop §8 | Task conversion | Unreviewed semantics | no | Stop task conversion (FREEZE §22) |

---

## 10. Diagnostic default and escalation flow

1. Every run emits at least **`graph_diagnostics`**.  
2. **Default:** evaluate with `operator_compact` and §5.2 questions.  
3. If any mandatory question is unanswerable **or** dramatic inconsistency is suspected → **automatic** `dramatic_expanded`.  
4. If seams or truth claims remain unclear → `freeze_integrity` before further productive claims.  
5. **Governance:** Skipping escalation when weakness is known = governance failure (FREEZE §17.4).

---

## 11. Cross-references

- **`docs/VERTICAL_SLICE_CONTRACT_GOC.md`** — Slice, Reality Anchor, bridge, vocabulary, assets, dry-run  
- **`docs/CANONICAL_TURN_CONTRACT_GOC.md`** — Turn schema, seams, director, pattern inventory  
