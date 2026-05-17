# Opening Authoring Document

This is the human-editable opening brief for the God of Carnage prototype
module. It is an intent layer, not a second place-description database.

## Authority Map

- Directed opening order: `canonical_path/index.yaml`
- Opening place descriptions: `locations/opening/*.yaml`
- Building threshold and prevented exits: `locations/building/*.yaml`
- Apartment room topology: `locations/appartment_vallon/apartment_layout.yaml`
- Object descriptions and placement: `objects/**/*.yaml`
- Short source quote anchors: `knowledge/opening_quote_anchors.yaml`
- Runtime opening contract: `knowledge/opening_scene_sequence.yaml`

## Purpose

The opening begins outside the apartment with the child incident, crosses into
the Vallon apartment, and keeps the first phase playable for at least twenty
minutes. The dramatic work is not to prove blame quickly; it is to make
procedure, hospitality, word choice, injury, and escape pressure available as
handles the player can touch.

## Exterior Prologue

Use canonical path steps `opening_001_parc_montsouris_edge` through
`opening_003_bicycle_disappearance`.

Location material is sourced from:
- `locations/opening/park_edge.yaml`
- `locations/opening/basketball_court.yaml`
- `locations/opening/playground.yaml`
- `objects/opening/bicycle_rack.yaml`

Action material is owned by the canonical path. The narrator should render the
incident concretely and briefly, but should pull place atmosphere, spatial
depth, and public background from the location refs above.

Narration rule: do not assign final moral blame, do not turn the prologue into
legal exposition, and do not add unseeded adult intervention.

## Threshold And Room

Use canonical path steps `opening_004_dark_building_hallway` through
`opening_007_living_room_arrangement`.

Location and object material is sourced from:
- `locations/building/building_hallway.yaml`
- `locations/building/building_stairwell.yaml`
- `locations/appartment_vallon/apartment_entry.yaml`
- `locations/appartment_vallon/living_room.yaml`
- `locations/appartment_vallon/apartment_layout.yaml`
- `objects/index.yaml`
- `objects/appartment_vallon/living_room/coffee_table.yaml`
- `objects/appartment_vallon/living_room/dining_table.yaml`
- `objects/appartment_vallon/living_room/window.yaml`
- `objects/building/elevator.yaml`

The stairwell and elevator pressure is prevented, not forbidden; the concrete
policy is owned by the referenced location/object files and mirrored by
`knowledge/content_access_policy.yaml`.

The selected player character is placed in the room without speech, decision,
confession, or private emotion assigned by the narrator.

## Statement And Wording

Use canonical path steps `opening_008_statement_on_table` through
`opening_011_courtesy_community_pressure`.

The statement is not a transcript surface. It is a playable object-pressure
surface: who touches it, who reads it, which word becomes too sharp, which word
gets softened, and how the medical consequence changes the room.

Short quote anchors may be used from `knowledge/opening_quote_anchors.yaml`,
but only as brief pressure cues. Do not reproduce long source dialogue or make
any exact phrase mandatory.

## Playable Opening Field

Use canonical path steps `opening_012_tulips_and_hospitality` through
`opening_016_opening_sustained_play_handoff`.

The opening should remain active for at least twenty minutes by keeping several
threads alive at once:

- statement wording
- dental consequence
- hospitality offer
- guest exit pressure
- spouse alignment micro-signals
- first substantive disagreement

End the directed opening on a concrete social pressure point: everyone is
present, politeness is still active, and the player can choose a gesture,
silence, observation, line, or movement attempt without the narrator deciding
their inner position.

## Files To Keep In Sync

- `canonical_path/index.yaml` and `canonical_path/00*.yaml`: directed opening spine.
- `knowledge/opening_scene_sequence.yaml`: event ids and validation coverage.
- `knowledge/opening_quote_anchors.yaml`: short quote cues and source-use limits.
- `knowledge/modularity_policy.yaml`: ownership rules for references versus descriptions.
- `scene_graph.yaml`: compatibility/runtime index that points at canonical path steps.
- `locations/index.yaml` and `locations/**/*.yaml`: place ids referenced by the opening.
- `knowledge/content_access_policy.yaml`: blocked, gated, or prevented actions/locations/objects.
