# Content Module Template

This directory is a copy-and-fill authoring skeleton for new World of Shadows
content modules. It is intentionally named `_template` so it is not mistaken for
a published playable module.

Suggested workflow:

1. Copy this directory to `content/modules/<new_module_id>/`.
2. Replace `_template` in `module.yaml` with the new module id.
3. Rename and edit character documents in `characters/`.
4. Fill `locations/`, `objects/`, and `characters/` as authority surfaces before writing
   path, direction, or knowledge files.
5. Fill `canonical_path/` next; this is the directed story spine and should
   reference locations instead of re-describing them.
6. Rename and edit location documents in `locations/opening/`,
   `locations/building/`, and `locations/appartment/`.
7. Update `scene_graph.yaml`, `phase_beat_policy.yaml`, and the knowledge files
   together so runtime node ids, location ids, character ids, and opening beats
   stay aligned.
8. Add non-player-visible director notes under `hints/` (see `hints/index.yaml`);
   they project into `render_support.director_surface_hints` at runtime.

The template keeps the same folder boundaries as the current GoC module:
characters and relationships live under `characters/`; locations are authored
per location under `locations/`.

## Modularity Rules

- Write place descriptions only in `locations/**/*.yaml`.
- Write object descriptions and materiality only in `objects/**/*.yaml`.
- Keep objects one-file-per-object; do not create object compendium files.
- Write character and relationship truth only in `characters/**/*.yaml`.
- Write directed order only in `canonical_path/**/*.yaml`.
- In `canonical_path/`, `direction/`, `knowledge/`, and `scene_graph.yaml`, use
  `location_ref`, `location_refs`, `topology_ref`, `object_refs`,
  `canonical_path_ref`, or `canonical_path_step_id` instead of copying prose.
- Locations may list `inventory_object_ids`; object files carry
  `placement_location_id`.
- Do not add `environment`, `visible_world`, `spatial_model`, or room-summary
  blocks outside `locations/`.
- Keep `scene_graph.yaml` as a runtime index: node ids, phase ids,
  `location_id`, `canonical_path_step_id`, graph edges, and compact runtime notes
  only.
