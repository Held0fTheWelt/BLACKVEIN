# Content and Experience Contract

## Player-Facing Contract

- Responses must remain scene- and pressure-aligned.
- Character voice differentiation must remain visible.
- Turn continuity must preserve meaningful context.
- Re-entry, interruption, and exchange choreography must stay readable.
- The slice must feel directed but still playable under free input.

## Content Lifecycle Contract

- Structured authored content is canonical source.
- Publish validation gates are mandatory before runtime activation.
- Activation and rollback controls are required to prevent drift between intent and runtime behavior.

Source precedence for the MVP slice:
1. Canonical YAML module assets
2. Published activation surface
3. Runtime committed state
4. Visible projection surfaces

## UX Contract

- Player shell must explain current scene, actionable options, turn effects, and short history.
- Operator-specific diagnostics must not leak into ordinary player flow.
- Accessibility, clarity, and support obligations remain part of MVP acceptance.

Minimum player-visible quality signals:
- user action consequence appears in later turns
- character responses are bounded to scene identity
- interaction does not degrade into generic roleplay chat tone

## Governance Contract

- Experience claims require matching evidence.
- Review, audit, and correction lanes stay explicit.
- Boundaries between canonical behavior and reference-only historical records remain visible.

If a turn cannot satisfy validation/commit requirements, output must degrade in a governed way (containment, non-factual staging, or explicit failure posture) instead of faking canonical truth.
