# PHASE0_FREEZE_CLOSURE_NOTE_GOC.md

Phase 0 freeze closure for the **God of Carnage** MVP vertical slice: binding decisions applied to the three freeze artifacts and a short follow-up tabletop for the closed items only.

---

## 1. Summary of decisions

| Topic | Decision |
|---|---|
| **A. Canonical GoC source** | **`content/modules/god_of_carnage/` YAML tree** is the sole canonical slice authority. Builtins and writers-room are secondary; they must not override YAML or be silently merged with it. |
| **B. Scene director** | **Graph-node decomposition** on LangGraph: named director nodes before proposal generation; stateless helpers allowed inside nodes; model may elaborate prose/effects but **must not silently replace** director fields (§3.6 turn contract). |
| **C. Pacing vocabulary** | Frozen set: `standard`, `compressed`, `thin_edge`, `containment`, `multi_pressure` (`VERTICAL_SLICE_CONTRACT_GOC.md` §5). |
| **D. Silence / brevity** | Frozen `silence_brevity_decision.mode` set: `normal`, `brief`, `withheld`, `expanded`. |
| **E. Failure / preview** | Default **`closure_impacting`** for missing validation or commit on non-preview runs. **`experiment_preview: true`** (in `diagnostics_refs` or equivalent) is **required** to allow **`review-first`** instead; it **suppresses any MVP-ready interpretation** of the run. Truth-safe visible behavior is mandatory (§6 Gate policy). |
| **F. Cadence / delegates** | Weekly `operator_compact`, biweekly/sprint-end `dramatic_expanded`, `freeze_integrity` before task derivation and on vocabulary/seam changes; explicit backup roles in §4 Gate policy. |
| **G. Multi-intention scene function** | Single **`selected_scene_function`** via continuity-class severity rank, then lexicographic tie-break on scene-function labels (`CANONICAL_TURN_CONTRACT_GOC.md` §3.5). |
| **H. Terminology** | **Scene function** vocabulary and **transition pattern** vocabulary are disjoint; pattern inventory uses separate columns (`CANONICAL_TURN_CONTRACT_GOC.md` §6.1, §7.2). |
| **I. Seam ambiguity** | Proposal vs validation vs commit vs visible boundaries closed in **`CANONICAL_TURN_CONTRACT_GOC.md` §2.3**. |

---

## 2. Per-artifact delta

### `docs/VERTICAL_SLICE_CONTRACT_GOC.md`

- Translated normative content to **English**.
- Replaced §5 open decision with **binding** controlled vocabulary including **pacing** and **silence/brevity** rows and semantics.
- Added **§6.1 canonical source authority** table and **binding rule**: YAML canonical; builtins/writers-room secondary; **no silent merge** with builtins.
- Updated Reality Anchor and bridge rows to reflect **resolved** director decision (cross-ref) and **YAML canonical** content row.
- Asset inventory: roles column reflects canonical vs secondary.

### `docs/CANONICAL_TURN_CONTRACT_GOC.md`

- Translated normative content to **English**.
- **§3** replaces `[REQUIRES DECISION]` with binding **graph-node decomposition**, responsibilities, deterministic pre-model fields, **§3.5** multi-intention priority rule, **§3.6** model non-overwrite rule.
- **§2.3** adds explicit **semantic closure** for seams.
- **§4** JSON example uses canonical **`pacing_mode`**, **`silence_brevity_decision.mode`**, and **`selected_scene_function`** (no placeholder pacing/silence).
- **§6.1** terminology rule separating scene function vs transition pattern.
- **§7.2** pattern inventory: separate columns for **scene function** vs **transition pattern** (fixes prior column misuse).

### `docs/GATE_SCORING_POLICY_GOC.md`

- Translated normative content to **English**.
- **§4** cadence table **final** with owner **roles**, cadence, minimum scenarios, escalation, **delegate/backup** rules.
- **§5.2–5.3** mandatory questions **binding** (no open decision).
- **§5.4** **CI / reproducibility** consequences for missing `repro_metadata`.
- **§6.2–6.4** **`experiment_preview`**, truth-safe preview behavior, and **failure class → severity** table without ambiguous slash-options.

---

## 3. Semantic drift closure summary

| Risk | Closure |
|---|---|
| Single `selected_scene_function` with multiple intentions | **Closed** by §3.5 priority rule (continuity-class rank + lexicographic tie-break). |
| Scene function vs transition pattern confusion | **Closed** by §6.1 rule and §7.2 table shape. |
| Proposal vs validation vs commit vs visible | **Closed** by §2.3 explicit statements + gate policy §6 for missing paths. |

**Residual risk statement:** Remaining risk is **non-material for task meaning** as long as implementers **do not bypass** named director nodes, **`experiment_preview`** is set honestly, and **YAML** remains the only authoritative content surface for slice truth. Undocumented shortcuts would reintroduce drift but are **out of contract**, not ambiguous contract text.

---

## 4. Follow-up tabletop (closure decisions only)

Illustrative compact traces using **final vocabulary** (no placeholders).

### Scenario 1 — Canonical GoC source authority in practice

| Field | Value |
|---|---|
| **Situation** | Engineer loads experience from builtins for a quick test while YAML has a different scene title in `scenes.yaml`. |
| **selected_scene_function** | `establish_pressure` |
| **selected_responder_set** | `[{ "actor_id": "alain_reille", "reason": "yaml_canonical_cast" }]` |
| **pacing_mode** | `standard` |
| **continuity_impacts** | `[]` (setup) |
| **visibility_class_markers** | `[truth_aligned]` |
| **failure_markers** | `[{ "failure_class": "scope_breach", "note": "builtins_yaml_mismatch_detected" }]` if builtins tried to override |
| **validation_outcome.status** | `not_yet_implemented` |
| **committed_result summary** | No commit until YAML-aligned load path chosen |
| **visible_output summary** | Containment copy; no conflicting canon |
| **transition_pattern** | `diagnostics_only` |
| **Activated gate families** | `slice_boundary`, `turn_integrity`, `diagnostic_sufficiency` |
| **Gate outcome** | **fail** if merged truth shipped; **pass** if runtime uses YAML and builtins only as non-authoritative test |
| **Semantic drift** | **Removed** — single authority rule |

### Scenario 2 — Scene director representation + pacing vocabulary

| Field | Value |
|---|---|
| **Situation** | Normal conflict beat; director nodes run before `invoke_model`. |
| **selected_scene_function** | `escalate_conflict` |
| **selected_responder_set** | `[{ "actor_id": "annette_reille", "reason": "pressure_target" }]` |
| **pacing_mode** | `compressed` |
| **continuity_impacts** | `[{ "class": "blame_pressure", "note": "accusation_landed" }]` |
| **visibility_class_markers** | `[truth_aligned]` |
| **failure_markers** | `[]` |
| **validation_outcome.status** | `not_yet_implemented` |
| **committed_result summary** | Empty until commit seam exists |
| **visible_output summary** | Lines reflect proposal only if commit absent; pacing feels tighter |
| **transition_pattern** | `soft` |
| **Activated gate families** | `dramatic_quality`, `turn_integrity`, `diagnostic_sufficiency` |
| **Gate outcome** | **conditional_pass** until validator/commit nodes land |
| **Semantic drift** | **Reduced** — director fields pinned before model; pacing label concrete |

### Scenario 3 — Failure severity / preview behavior

| Field | Value |
|---|---|
| **Situation** | Internal dry-run without validator/commit; flagged preview. |
| **selected_scene_function** | `probe_motive` |
| **selected_responder_set** | `[{ "actor_id": "penelope_longstreet", "reason": "initiates_probe" }]` |
| **pacing_mode** | `thin_edge` |
| **continuity_impacts** | `[]` |
| **visibility_class_markers** | `[non_factual_staging]` |
| **failure_markers** | `[{ "failure_class": "missing_validation_path" }, { "failure_class": "missing_commit_path" }]` |
| **validation_outcome.status** | `absent` |
| **committed_result summary** | Empty |
| **visible_output summary** | Short staging text; **no** “validated” or “canon locked” implication |
| **transition_pattern** | `diagnostics_only` |
| **Activated gate families** | `turn_integrity`, `diagnostic_sufficiency` |
| **Gate outcome** | **`review-first`** because `experiment_preview: true` + truth-safe copy; **not** MVP-ready |
| **Semantic drift** | **Removed** for “preview looks production-ready” |

### Scenario 4 — Multi-intention scene-function prioritization

| Field | Value |
|---|---|
| **Situation** | Player move both **repairs** rapport and **reveals** a fact; `pacing_mode` = `multi_pressure`. |
| **Candidate functions** | `repair_or_stabilize` vs `reveal_surface` |
| **Priority application** | `reveal_surface` implies higher continuity class (`revealed_fact` > `repair_attempt`) |
| **selected_scene_function** | `reveal_surface` |
| **selected_responder_set** | `[{ "actor_id": "michael_longstreet", "reason": "speaker_of_reveal" }]` |
| **pacing_mode** | `multi_pressure` |
| **continuity_impacts** | `[{ "class": "revealed_fact", "note": "hidden_detail_surfaces" }]` |
| **visibility_class_markers** | `[truth_aligned]` |
| **failure_markers** | `[]` |
| **validation_outcome.status** | `pending` (once implemented) |
| **committed_result summary** | TBD at commit |
| **visible output summary** | Reveal staged post-commit only |
| **transition_pattern** | `hard` (if commit confirms fact) |
| **Activated gate families** | `dramatic_quality`, `turn_integrity` |
| **Gate outcome** | **pass** on priority readability |
| **Semantic drift** | **Removed** — one function chosen by binding rule |

---

## 5. Final readiness statement

**Phase 0 ready for execution-task derivation: Yes.**

**Conditions:**

1. Task specs must reference **YAML** under `content/modules/god_of_carnage/` as canonical content input unless explicitly marked `experiment_preview`.  
2. Runtime work must implement **director graph nodes** before proposal generation per `CANONICAL_TURN_CONTRACT_GOC.md` §3.  
3. Tasks must use **frozen vocabulary** for pacing, silence/brevity, scene function, transition pattern, and failure classes from `VERTICAL_SLICE_CONTRACT_GOC.md` §5.  
4. Until validation and commit seams exist, productive claims require **`experiment_preview: true`** or gates register **`closure_impacting`** per `GATE_SCORING_POLICY_GOC.md` §6.  
5. **`freeze_integrity`** bundle must be executed once per §4 before deriving the first execution-task batch.

**Remaining blockers for *shipping* MVP (not for *deriving tasks*):** validator node, commit node, and projection from `RuntimeTurnState` to the canonical turn remain **implementation** work; they are **specified** and **gated**, not undefined.
