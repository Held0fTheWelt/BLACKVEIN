"""Closed-enum contract surface for ``narrator_consequence_realization.v1``.

This module is the PR-B delivery for the NPC Interactivity roadmap. It
projects the existing ``narrator_consequence_plan`` (built by
``ai_stack.narrator_consequence_contracts.build_narrator_consequence_plan``)
together with the rendered ``visible_output_bundle.scene_blocks`` into a
closed-enum dict that diagnostic surfaces can read uniformly. The dict
always carries either ``visible_block_emitted=True`` (with a non-null
``realized_block_id``) or an explicit ``non_realization_reason`` string, so
the operator never has to infer realization status from the absence of a
block.

Authoritative governance:

* :doc:`docs/ADR/adr-0057-canon-safe-player-freedom-and-affordance-inference`
  (Phase-1 amendment names ``narrator_consequence_realization.v1`` and
  prescribes the ``safety`` triple ``no_new_people`` / ``no_new_rooms`` /
  ``no_plot_facts``).
* :doc:`docs/ADR/adr-0062-director-realization-thin-path` (composition path
  PR-B rides on; the existing thin-path narrator fold lives in the manager
  per ADR-0062).
* :doc:`docs/implementation_logs/pr_b_live_effect_propagation_piv` (PR-B PIV
  artifact -- enumerates the consumers and the guardrails).

Vocabulary discipline (ADR-0039 + Phase-1 amendment):

* Closed enums for ``block_type`` and ``non_realization_reason``. Any other
  value is a contract violation.
* Semantic capability names only. No Pi / Pi-numbered runtime keys.
* No verb / room / actor / locale literal whitelists; the realization is
  projected from the plan + bundle structure, not from raw text.
* No hardcoded narrative text; the block id and the consequence text live in
  the existing visible bundle. This module only inspects structure.

This module is intentionally pure (no I/O). It does not import the PR-0
diagnostic snapshot stub.
"""

from __future__ import annotations

from typing import Any, Final


SCHEMA_VERSION: Final[str] = "narrator_consequence_realization.v1"


# ---------------------------------------------------------------------------
# Closed enums
# ---------------------------------------------------------------------------


BLOCK_TYPE_NARRATOR: Final[str] = "narrator"
BLOCK_TYPE_ENVIRONMENT_INTERACTION: Final[str] = "environment_interaction"

REALIZATION_BLOCK_TYPES: Final[frozenset[str]] = frozenset(
    {BLOCK_TYPE_NARRATOR, BLOCK_TYPE_ENVIRONMENT_INTERACTION}
)


# ``source`` carries the provenance of the consequence the realization
# observed. The two values mirror the consequence plan's own ``source``
# field (authored detail vs. AI-semantic plausible inference); a third value
# names the fallback when the plan came in empty (e.g. meta / speech-only /
# unknown target paths where no consequence is meaningful).
SOURCE_SCENE_AFFORDANCE_DETAIL: Final[str] = "scene_affordance_detail"
SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE: Final[str] = "ai_semantic_plausible_inference"
SOURCE_TEMPLATE_FALLBACK: Final[str] = "template_fallback"
SOURCE_NO_CONSEQUENCE_APPLICABLE: Final[str] = "no_consequence_applicable"

REALIZATION_SOURCES: Final[frozenset[str]] = frozenset(
    {
        SOURCE_SCENE_AFFORDANCE_DETAIL,
        SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE,
        SOURCE_TEMPLATE_FALLBACK,
        SOURCE_NO_CONSEQUENCE_APPLICABLE,
    }
)


# ``non_realization_reason`` carries the structured reason a
# ``requires_model_realization=True`` plan failed to produce a visible
# narrator / environment_interaction block. The values are closed semantic
# tokens; never paraphrased prose.
NON_REALIZATION_REASON_REALIZATION_NOT_REQUIRED: Final[str] = "realization_not_required"
NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE: Final[str] = (
    "no_narrator_block_in_visible_bundle"
)
NON_REALIZATION_REASON_BUNDLE_MISSING: Final[str] = "visible_output_bundle_missing"
NON_REALIZATION_REASON_PLAN_MISSING: Final[str] = "narrator_consequence_plan_missing"
NON_REALIZATION_REASON_VALIDATION_GATED: Final[str] = "validation_gated_realization"

NON_REALIZATION_REASONS: Final[frozenset[str]] = frozenset(
    {
        NON_REALIZATION_REASON_REALIZATION_NOT_REQUIRED,
        NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE,
        NON_REALIZATION_REASON_BUNDLE_MISSING,
        NON_REALIZATION_REASON_PLAN_MISSING,
        NON_REALIZATION_REASON_VALIDATION_GATED,
    }
)


REQUIRED_CONTRACT_KEYS: Final[tuple[str, ...]] = (
    "schema_version",
    "source",
    "requires_model_realization",
    "realized_block_id",
    "non_realization_reason",
    "visible_block_emitted",
    "block_type",
    "safety",
)


REQUIRED_SAFETY_KEYS: Final[tuple[str, ...]] = (
    "no_new_people",
    "no_new_rooms",
    "no_plot_facts",
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _coerce_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _block_type_of(scene_block: dict[str, Any]) -> str | None:
    bt = _coerce_string(scene_block.get("block_type") or scene_block.get("type"))
    return bt.lower() if bt is not None else None


def _block_id_of(scene_block: dict[str, Any]) -> str | None:
    return _coerce_string(
        scene_block.get("block_id")
        or scene_block.get("entry_id")
        or scene_block.get("id")
    )


def _find_realization_block(
    scene_blocks: list[Any] | None,
) -> tuple[dict[str, Any] | None, str | None]:
    """Return (block, block_type) for the first narrator / environment_interaction block."""
    if not isinstance(scene_blocks, list):
        return None, None
    for entry in scene_blocks:
        if not isinstance(entry, dict):
            continue
        bt = _block_type_of(entry)
        if bt in REALIZATION_BLOCK_TYPES:
            return entry, bt
    return None, None


def _normalize_source(plan_source: Any) -> str:
    text = _coerce_string(plan_source)
    if text is None:
        return SOURCE_NO_CONSEQUENCE_APPLICABLE
    lowered = text.lower()
    if lowered == SOURCE_SCENE_AFFORDANCE_DETAIL:
        return SOURCE_SCENE_AFFORDANCE_DETAIL
    if lowered == SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE:
        return SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE
    if lowered == SOURCE_TEMPLATE_FALLBACK:
        return SOURCE_TEMPLATE_FALLBACK
    return SOURCE_NO_CONSEQUENCE_APPLICABLE


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


def build_narrator_consequence_realization(
    *,
    narrator_consequence_plan: dict[str, Any] | None,
    visible_scene_blocks: list[Any] | None,
    validation_gated: bool = False,
) -> dict[str, Any]:
    """Project consequence plan + visible bundle onto the realization contract.

    The function **always** returns a dict carrying every key in
    ``REQUIRED_CONTRACT_KEYS``. The contract makes the realization status
    explicit on every turn:

    * When the plan asks for model realization (``requires_model_realization
      is True``) and the visible bundle contains a ``narrator`` /
      ``environment_interaction`` block: ``visible_block_emitted=True``,
      ``realized_block_id=<block id>``, ``non_realization_reason=None``.
    * When the plan asks for model realization but no such block exists:
      ``visible_block_emitted=False``, ``realized_block_id=None``,
      ``non_realization_reason`` populated with the closed-enum reason.
    * When the plan does not require realization (``False``):
      ``visible_block_emitted`` reflects whether such a block was emitted
      anyway (it usually is, because the consequence is authored detail);
      ``non_realization_reason`` is
      ``"realization_not_required"`` in that case.
    * When no plan exists (meta / unknown / speech-only paths):
      ``non_realization_reason="narrator_consequence_plan_missing"``.

    Safety triple discipline (Phase-1 amendment): The triple ``no_new_people``,
    ``no_new_rooms``, ``no_plot_facts`` is **always** ``True`` for blocks
    surfaced by this contract, because (a) the upstream policy
    (``player_freedom_policy.plausible_affordance_inference.forbidden_scope``)
    declares ``new_people_or_animals``, ``new_exits_or_rooms``, and
    ``decisive_plot_information`` forbidden, and (b) the resolver already
    fails-closed on those (``canonical_risk=high`` ->
    ``needs_clarification`` -> no successful commit). The contract surfaces
    the guarantee as a positive assertion the diagnostic UI can rely on.

    Args:
        narrator_consequence_plan: dict emitted by
            ``ai_stack.narrator_consequence_contracts.build_narrator_consequence_plan``
            (may be ``None`` for meta / unknown / speech-only paths).
        visible_scene_blocks: list of scene block dicts from
            ``visible_output_bundle.scene_blocks``; may be empty or ``None``.
        validation_gated: ``True`` when the actor-lane validation rejected
            the turn before render, so the absence of a block is gating-
            related rather than realization-related.

    Returns:
        A dict with every key in ``REQUIRED_CONTRACT_KEYS``.
    """
    plan = narrator_consequence_plan if isinstance(narrator_consequence_plan, dict) else None
    requires_model_realization = bool(
        plan.get("requires_model_realization") if plan is not None else False
    )
    source = _normalize_source(plan.get("source") if plan is not None else None)
    block, block_type = _find_realization_block(visible_scene_blocks)
    realized_block_id = _block_id_of(block) if block is not None else None
    visible_block_emitted = block is not None

    non_realization_reason: str | None
    if visible_block_emitted:
        non_realization_reason = None
    elif validation_gated:
        non_realization_reason = NON_REALIZATION_REASON_VALIDATION_GATED
    elif plan is None:
        non_realization_reason = NON_REALIZATION_REASON_PLAN_MISSING
    elif not requires_model_realization:
        non_realization_reason = NON_REALIZATION_REASON_REALIZATION_NOT_REQUIRED
    elif visible_scene_blocks is None:
        non_realization_reason = NON_REALIZATION_REASON_BUNDLE_MISSING
    else:
        non_realization_reason = NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE

    safety: dict[str, bool] = {
        "no_new_people": True,
        "no_new_rooms": True,
        "no_plot_facts": True,
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "source": source,
        "requires_model_realization": requires_model_realization,
        "realized_block_id": realized_block_id,
        "non_realization_reason": non_realization_reason,
        "visible_block_emitted": visible_block_emitted,
        "block_type": block_type,
        "safety": safety,
    }


__all__ = [
    "SCHEMA_VERSION",
    "BLOCK_TYPE_NARRATOR",
    "BLOCK_TYPE_ENVIRONMENT_INTERACTION",
    "REALIZATION_BLOCK_TYPES",
    "SOURCE_SCENE_AFFORDANCE_DETAIL",
    "SOURCE_AI_SEMANTIC_PLAUSIBLE_INFERENCE",
    "SOURCE_TEMPLATE_FALLBACK",
    "SOURCE_NO_CONSEQUENCE_APPLICABLE",
    "REALIZATION_SOURCES",
    "NON_REALIZATION_REASON_REALIZATION_NOT_REQUIRED",
    "NON_REALIZATION_REASON_NO_NARRATOR_BLOCK_IN_BUNDLE",
    "NON_REALIZATION_REASON_BUNDLE_MISSING",
    "NON_REALIZATION_REASON_PLAN_MISSING",
    "NON_REALIZATION_REASON_VALIDATION_GATED",
    "NON_REALIZATION_REASONS",
    "REQUIRED_CONTRACT_KEYS",
    "REQUIRED_SAFETY_KEYS",
    "build_narrator_consequence_realization",
]
