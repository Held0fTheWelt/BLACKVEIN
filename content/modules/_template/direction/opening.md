# Opening Authoring Document

Use this file as the human-readable brief for the module opening. It is an
intent layer, not a location-description layer.

## Authority Map

- Directed opening order: `canonical_path/index.yaml`
- Opening location authority: `locations/opening/opening_anchor.yaml`
- Threshold authority: `locations/building/threshold.yaml`
- First playable room authority: `locations/appartment/main_room.yaml`
- Object authority: `objects/index.yaml` and one file per object under `objects/`
- Short quote anchor policy: `knowledge/opening_quote_anchors.yaml`
- Runtime opening contract: `knowledge/opening_scene_sequence.yaml`
- Modularity rules: `knowledge/modularity_policy.yaml`

## Purpose

Replace with the opening's job: what image, incident, social pressure, or room
transition must be established before the first playable moment?

## Opening Prologue

Use canonical path steps `opening_001_anchor` and `opening_002_pressure_turn`.
Pull place texture from the referenced location files rather than listing it
again here.

Narration rule: stay concrete and brief; do not assign final moral verdict.
Use quote anchors only as short pressure cues, never as transcript fragments.

## Handover

Use canonical path step `opening_003_handover_to_play`. Pull room topology and
object pressure from the referenced location files.

## First Playable Moment

End on a concrete pressure point where the player may observe, gesture, remain
silent, or speak.

## Files To Keep In Sync

- `canonical_path/index.yaml`
- `knowledge/opening_scene_sequence.yaml`
- `knowledge/opening_quote_anchors.yaml`
- `direction/opening_sequence.yaml`
- `scene_graph.yaml`
- `locations/index.yaml`
- `locations/**/*.yaml`
- `knowledge/modularity_policy.yaml`
- `knowledge/content_access_policy.yaml`
