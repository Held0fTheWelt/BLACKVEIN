# v24 Lean Scope and Keep Rules

## Goal

The v24 package keeps what is needed to complete the runtime/platform path and removes what mainly acted as ballast.

## Keep rules

A surface stays in v24 if at least one of the following is true:

1. it is part of the runtime/platform end-state,
2. it is a direct implementation surface,
3. it is a direct validation surface,
4. it materially reduces drift,
5. it materially improves contract coherence,
6. it materially improves documentation coherence,
7. it is needed to choose or govern the next implementation field.

## Remove rules

A surface may be removed from the package if it is primarily:

- archive/history material,
- presentation material,
- export material,
- side-workflow material not needed for completion,
- or duplicate/support material with low implementation leverage.

## v24 intent

The package should feel:

- smaller than v23,
- easier to understand,
- easier to audit,
- easier to hand to an implementation AI,
- but still broad enough to support the eventual finished runtime path.
