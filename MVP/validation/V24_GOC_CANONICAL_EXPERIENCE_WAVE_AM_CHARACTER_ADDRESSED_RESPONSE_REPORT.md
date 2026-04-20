# V24 GoC Canonical Experience — Wave AM Character-Addressed Response + Observation Hardening

## Summary

This wave strengthens the actual runtime/session observation layer so the player can more clearly feel:
- who is answering now,
- why that person or pressure line is answering,
- and what kind of live exchange the scene has become.

The implementation remains architecture-faithful and additive:
- authoritative world-engine state carries the new fields,
- the backend session state path continues to pass that state through,
- the existing frontend play shell renders the new fields in the observation layer.

## Added readout fields

- `who_answers_now`
- `why_this_reply_now`
- `observation_foothold_now`

These fields are compact, state-grounded, and non-directive.
They are derived from authoritative runtime/session state rather than hidden beat guidance.

## What this improves

The player can now more clearly perceive:
- who is socially pressing them,
- what kind of response frame the room has moved into,
- and why the scene is reacting now rather than merely carrying ambient pressure.

This strengthens action-caused conversation without introducing menus, objectives, or explicit next-step guidance.
