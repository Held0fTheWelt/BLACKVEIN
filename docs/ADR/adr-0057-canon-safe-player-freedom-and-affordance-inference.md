# ADR-0057: Canon-Safe Player Freedom and Affordance Inference

Status: Accepted

Date: 2026-05-18

## Context

The live runtime must let the selected player character move, observe, wait,
and interact freely after the narrator handoff. The canonical path remains the
directed story spine, but it must not behave like a rail that forbids ordinary
movement or mundane object use.

The content module cannot become a second exhaustive database of every possible
object or container content. Where authored content is silent, the engine needs
a semantic AI contract that can fill small, local gaps without breaking canon.

## Decision

The runtime separates three surfaces:

1. Player local context: the player's current room, perception, and immediate
   interaction state.
2. Canonical path: the directed narrator/dialogue spine.
3. Canon-safe inferred affordances: AI-resolved mundane, reversible details that
   are not promoted to canonical facts.

Free movement, perception, waiting, and mundane object interaction may update
player local context, but they hold the current canonical step unless content
explicitly marks a progression point. If a required participant is away or
temporarily prevented, the Director may stage a social hold instead of spending
mandatory dialogue.

When the content catalog has no exact object match, the semantic resolver may
commit an inferred target only when the AI marks it with the safety fields
required by the module's player_freedom_policy. The engine must not contain
object-specific or verb-specific maps for this decision.

## Consequences

- No verb maps, locale maps, or object-specific engine branches are introduced.
- Known content ids remain preferred.
- Plausible inferred details are narrator-realized and local to runtime state.
- Object interactions that require semantic realization use the model path
  instead of a deterministic empty/template short path.
- Free actions without a resolved AI semantic payload are represented as
  `semantic_resolution_required` with `needs_clarification` action policy.
  They must not be guessed into a generic `interact` verb by engine maps, and
  they must still keep the full Director/model runtime path rather than falling
  into deterministic short-path handling.
- Multi-turn runtime smoke tests must preserve the same boundary: unresolved
  free-text inputs may produce a safe `establish_situational_pressure` semantic
  move and `establish_pressure` scene function while still exercising the full
  Director/model path. Tests must not force keyword-derived scene functions such
  as `escalate_conflict`, `withhold_or_evade`, or `probe_motive` unless resolved
  action, speech, or semantic-move evidence exists.
- Prior continuity may still influence the responder set, secondary reactor
  enablement, social asymmetry, and pattern-variation diagnostics for an
  unresolved move. It does not by itself justify changing the safe
  `establish_pressure` scene-function default.
- Breadth/playability and long-run operator-readiness regressions should
  therefore count non-preview execution, resolver evidence, gate credibility,
  responder variation, and explainable degradation for unresolved player text.
  They should not treat scene-function diversity as required coverage until the
  fixture supplies resolved action, speech, or semantic-move evidence.
- Recoverable validation rejects on unresolved free text can be
  `degraded_explainable` / `conditional_pass` for operator-readiness coverage
  when diagnostics preserve validation status, alignment summary, and fallback
  path evidence. Tests should not require a hard dramatic-quality `fail` where
  the runtime reports an explainable recoverable degradation.
- The canonical path can wait while the player explores, instead of wandering.
