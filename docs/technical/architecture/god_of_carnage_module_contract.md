# God of Carnage Module Contract

## Purpose

This document defines the current authored-content contract for the
`god_of_carnage` module. The module is the reference implementation for a
structured dramatic content tree, but it must not require special engine logic.

The current shape is not the early flat `scenes.yaml` / `triggers.yaml` bundle.
The module is directed by `canonical_path/` and grounded by referenced
locations, objects, characters, knowledge, direction, and policy files.

---

## Module Identity

**Title**: God of Carnage
**Reference**: `god_of_carnage`
**Role**: Reference implementation module for modular story content structure
**Scope**: Four-character apartment drama, beginning with the Parc Mont Sourire
incident and moving through building threshold, apartment civility, social
pressure, and eventual escalation.
**Quality Principle**: This module is the reference, not an exception. All
engine logic must work for any module structured the same way.

---

## File Layout

Current content modules are structured as follows:

```text
content/modules/god_of_carnage/
├── module.yaml
├── canonical_path/
│   ├── index.yaml
│   └── 001_...yaml
├── locations/
│   ├── index.yaml
│   ├── opening/
│   ├── building/
│   └── appartment_vallon/
├── objects/
│   ├── index.yaml
│   ├── opening/
│   ├── building/
│   └── appartment_vallon/<room>/
├── characters/
│   ├── index.yaml
│   ├── definitions/
│   ├── details/
│   └── voices/
├── knowledge/
├── direction/
│   └── beat_library/
├── scene_graph.yaml
├── phase_beat_policy.yaml
├── memory_policy.yaml
├── information_disclosure_policy.yaml
└── narrative_aspect_policy.yaml
```

`canonical_path/` is the directed story spine. It references canonical ids; it
does not re-describe rooms, objects, or character facts. `scene_graph.yaml` is a
runtime index over path and location ids, not a second scene database.

---

## Characters

Four characters, each with formal properties:

### Véronique
- **Role**: Host, moral idealist, parental figure
- **Baseline attitude**: Commitment to civility, defense of children
- **Tension markers**: Protection vs. tolerance, idealism vs. pragmatism
- **Escalation state**: Tracks disappointment level, boundary violations

### Michel
- **Role**: Véronique's spouse, pragmatist
- **Baseline attitude**: Conflict avoidance, business-rational worldview
- **Tension markers**: Loyalty vs. self-preservation, public image vs. private truth
- **Escalation state**: Tracks alignment with Véronique, emotional distance

### Annette
- **Role**: Guest, intellectual combatant, cynical provocateur
- **Baseline attitude**: Challenge conventional morality, expose contradictions
- **Tension markers**: Intellectual dominance, moral relativism
- **Escalation state**: Tracks engagement level, willingness to escalate

### Alain
- **Role**: Annette's spouse, conflict mediator, pragmatist
- **Baseline attitude**: Keep conversation manageable, avoid emotional extremes
- **Tension markers**: Loyalty to spouse vs. social harmony, exhaustion
- **Escalation state**: Tracks mediation effectiveness, emotional fatigue

---

## Relationship Axes

Four primary relationship axes govern character dynamics:

### Axis 1: Spousal Internal (Véronique ↔ Michel vs. Annette ↔ Alain)
- Solidarity within couples vs. cross-couple dynamics
- Baseline: Both couples assume alignment
- Escalation: Spouses split on key judgments (civility worth defending? accusations justified?)

### Axis 2: Host ↔ Guest Power
- Véronique/Michel as authority (their home, their rules) vs. Annette/Alain as challengers
- Baseline: Guests nominally defer to hosts
- Escalation: Guests dominate conversation, hosts lose control

### Axis 3: Moral vs. Pragmatic Worldview
- Véronique's idealism (rules, principles, children as sacred) vs. Annette's cynicism (all positions self-interested)
- Baseline: Tension acknowledged but contained
- Escalation: Mutual contempt, no shared ground

### Axis 4: Latent Dominance / Devaluation
- Individual status claims (who is superior: parent, intellectual, moralist, pragmatist?)
- Baseline: Masks of civility
- Escalation: Contempt for others becomes explicit

---

## Directed Path And Runtime Nodes

The opening path is numbered and ascending. Its early steps move from:

- Parc Mont Sourire edge and basketball court incident,
- the struck boy, bicycle beat, and disappearance,
- dark building hallway with elevator/stairwell pressure,
- living room handover and apartment entry,
- statement on the table, wording dispute, dental consequence, courtesy
  pressure, tulips, and the first playable courtesy gap.

Path steps may carry narrator tasks, action beats, theme ids, quote-anchor
refs, player windows, and handover hints. They reference `location_ref`,
`location_refs`, `object_refs`, `character_refs`, and policy ids instead of
copying the underlying descriptions.

`scene_graph.yaml` may group path steps into runtime nodes for execution and
diagnostics. It must stay compact: ids, phase ids, location ids, edges, and
runtime notes only.

---

## Locations And Objects

Locations live one place per file under `locations/`.

Current GoC location groups:

- `locations/opening/`: Parc Mont Sourire edge, basketball court, playground.
- `locations/building/`: building hallway and stairwell.
- `locations/appartment_vallon/`: apartment entry, living room, hallway,
  kitchen, bathroom, pantry, study, locked bedrooms, and layout policy.

Objects live one object per file under `objects/`, grouped by broad location
and room folders. Location files may list `inventory_object_ids`; object files
carry their placement. A room can be furnished by adding object files without
rewriting the room description.

The engine may expose explicit affordances and prevented actions from these
documents. Prevented actions are not forbidden moral rules; they are in-world
conditions that block or redirect an attempted action.

---

## Dramatic Policy

Escalation and recovery are no longer expressed as a flat trigger list in this
document. Runtime policy is split across:

- `phase_beat_policy.yaml` for coarse phase and beat constraints,
- `characters/details/relationships.yaml` for relationship axes,
- `characters/details/actor_pressure_profiles.yaml` for pressure identities,
- `direction/subtext_policy.yaml` for bounded subtext interpretation,
- `knowledge/content_access_policy.yaml` for what can be surfaced when,
- `knowledge/hard_forbidden_rules.yaml` for validation hard stops,
- `memory_policy.yaml` and aspect policies for runtime continuity.

Natural-language player input is resolved semantically. The engine must not
route social moves, actor targets, or scene candidates through hardcoded
keyword, verb, locale, or actor-alias maps.

---

## Validation Expectations

The Engine validates God of Carnage modules against:

### Structural Validation
- All indexed files referenced by `module.yaml` exist.
- Canonical path ids are unique and ordered.
- Path steps reference existing locations, objects, characters, themes, and
  quote anchors.
- Location adjacency and inventory refs resolve.
- Object placement locations resolve.
- Character voice and relationship refs resolve.
- Runtime nodes in `scene_graph.yaml` reference valid path/location ids.

### Content Validation
- Proposed state deltas match content module structure; no arbitrary new fields.
- Opening event coverage is derived from canonical opening path/knowledge ids.
- Environment state is initialized from canonical locations and objects.
- Quote anchors are used only through the quote policy and moment-locked refs.

### Constraint Validation
- No character is given new facts not in content or committed event log.
- No location/object truth is invented outside canonical files.
- No hidden locale, command translation, verb, or actor-alias map becomes runtime
  authority.
- Player speech is never forced by opening or director policy.

---

## Related Documents

- [MVP Definition](./mvp_definition.md) — Module's role in the MVP
- [AI Story Contract](./ai_story_contract.md) — How AI generates valid proposals for this module
- [Session Runtime Contract](./session_runtime_contract.md) — How Engine validates and applies state changes

---

**Version**: W0 updated for modular content contract (2026-05-18)
**Status**: Reference Implementation
