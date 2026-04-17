# ADR-0003: Single canonical scene identity surface across compile, AI guidance, and commit

## Status

Accepted

## Context

Authored narrative modules are consumed by more than one component (content compiler, optional direct YAML readers in AI/helpers, world-engine narrative commit). Without a single canonical scene identifier vocabulary and a small, tested translation layer, regressions at handoffs can reappear even after point fixes (audit finding class "dual interpretation surfaces").

## Source of derivation (normative)

**Choice: Option A - the canonical Python module is the source of truth.**

- Hand-maintained mapping and defaults live in [`ai_stack/goc_scene_identity.py`](../../ai_stack/goc_scene_identity.py) (`GOC_SCENE_ID_TO_GUIDANCE_PHASE`, `GOC_DEFAULT_GUIDANCE_PHASE_KEY`, `GUIDANCE_PHASE_TO_ESCALATION_ARC_KEY`).
- The canonical module is **not** a generated projection from YAML; YAML remains **authoring** material.
- **Tests** verify bidirectional consistency: every map **value** exists as a top-level phase block in `content/modules/god_of_carnage/direction/scene_guidance.yaml`; every `scene_phases.*.id` in `scenes.yaml` resolves through the map to a real guidance block.
- Changing YAML phase structure or ids **requires** updating the canonical module and tests in the same change.

## Decision

1. Treat **compiler runtime projection** and world-engine **commit resolver** as the **normative** contract for scene row identity at the seam (unchanged from prior draft).
2. **Single owned module:** [`ai_stack/goc_scene_identity.py`](../../ai_stack/goc_scene_identity.py) is the only place that defines runtime `scene_id` -> `scene_guidance.yaml` phase keys and guidance-phase -> escalation-arc subkeys. [`ai_stack/goc_yaml_authority.py`](../../ai_stack/goc_yaml_authority.py) **re-exports** and consumes that module; it must not introduce a second mapping dict.
3. **No local remap (mandatory):**
   - No duplicate scene-id -> guidance dicts outside `goc_scene_identity.py` (enforced by `python tools/verify_goc_scene_identity_single_source.py` in CI and by `test_sole_definition_of_guidance_phase_key_for_scene_id` in `ai_stack/tests/test_goc_scene_identity.py`).
   - No ad hoc `if scene_id == "...": phase = ...` mapping in consumers; use `guidance_phase_key_for_scene_id` (exceptions require ADR amendment or state decision log + expiry).
4. Prefer **contract tests** that load canonical content and assert vocabulary legibility (see `ai_stack/tests/test_goc_scene_identity.py`).

## Consequences

- Positive: Fewer silent failures at seams; CI enforcement against mapping drift.
- Negative: GoC YAML or guidance renames need a coordinated code update.

## Links

- State: [audit_resolution_state_world_of_shadows.md](../governance/audit_resolution/audit_resolution_state_world_of_shadows.md) (finding F-H3)
- Normative contracts: [normative contracts index](../dev/contracts/normative-contracts-index.md)

## Migrated excerpt from MVPs

Source: `docs/MVPs/MVP_Narrative_Governance_And_Revision_Foundation/02_architecture_decisions.md`

**Migrated Decision (ADR-003 — Scene Packet is the execution contract, not a prompt convenience)**

The model call must be built from a typed `NarrativeDirectorScenePacket`. This is not optional retrieval context and not ad hoc prompt interpolation.

**Migrated Consequences**

- runtime model input is inspectable and testable
- policy, legality, actor scope, and constraints are explicit
- generation becomes reproducible enough for regression testing
