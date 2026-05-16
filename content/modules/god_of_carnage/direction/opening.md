# Opening Authoring Document

This is the human-editable opening brief for the God of Carnage prototype module.
The machine gate lives in `knowledge/opening_scene_sequence.yaml`; when this file changes, keep
that gate aligned so runtime validation knows which beats were intentionally authored.

## Purpose

The opening must begin outside the apartment, at the edge of a Paris park, and then hand the
session into the Vallon apartment without turning the first playable moment into a trial.

## Exterior Prologue

Location: edge of a Paris park near a basketball court.

Visible world:
- gray autumn sky
- bare trees
- ordinary Paris-suburb background life
- a playground within sight
- bicycles near the boys
- about a dozen boys gathered around the court

Action beats:
- two boys are playing while the others talk excitedly at the edge
- the two boys argue and separate
- one boy grabs a stick
- the other calls something after him, but the words are not audible
- the boy with the stick stops, turns, and strikes
- the injured boy folds over
- the other boys help him up and shout after the attacker
- the attacker kicks over a bicycle as he leaves
- the attacker disappears from view

Narration rule: describe the event concretely and briefly; do not assign final moral blame.

## Interior Handover

The opening then moves to the Vallon apartment. The scene should make the room playable:
doorway, coats, papers, seating, coffee, dessert, art books, tulips, host/guest pressure.

The selected player character is placed in the room without speech, decision, confession, or
private emotion assigned by the narrator.

## First Playable Moment

End on a concrete social pressure point: everyone is present, politeness is still active, and
the player can choose a first gesture, silence, observation, or line.

## Files To Keep In Sync

- `knowledge/opening_scene_sequence.yaml`: event ids and validation coverage.
- `scene_graph.yaml`: scene nodes from exterior prologue through apartment handover.
- `locations.yaml`: place ids referenced by the opening.
- `knowledge/content_access_policy.yaml`: blocked or gated actions/locations/objects.
