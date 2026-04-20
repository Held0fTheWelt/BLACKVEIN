# V24 GoC Canonical Experience — Wave AG Situational Affordance Surfacing Report

## Summary

This pass hardens the existing authoritative runtime-to-shell readout so the player can better perceive what is socially live in the room without being told what to do next.

The implementation stays inside the real MVP-v24 seams:
- authoritative world-engine session state
- existing backend bridge
- existing frontend shell/readout

## Added precision

The shell readout projection now carries three additional compact fields:
- `zone_sensitivity_now`
- `object_sensitivity_now`
- `situational_affordance_now`

These fields are derived from already authoritative state such as:
- current scene id
- last open pressures
- last committed consequences
- current social-state diagnostic summary

## What this improves

The shell now better conveys:
- which zone is socially charged
- which object/surface is socially sensitive
- which kinds of ordinary domestic acts are liable to matter right now
- why the room feels tighter, more trapped, more exposed, or more judgmental

This remains:
- compact
- non-directive
- chamber-play appropriate
- grounded in actual runtime state rather than generic flavor text
