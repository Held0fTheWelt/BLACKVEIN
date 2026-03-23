# World of Shadows Prompt Models — Refactored Pack

This pack separates **templates** from **implementations**.

## Structure
- `markdown/` contains reusable prompt templates.
- `markdown/_registry/` contains IDs, presets, and indexing metadata.
- `implementations/` contains concrete scenario files.

## Reference Model
- Directories are for humans.
- `id` is the canonical machine-stable reference.
- `base` links fast or deep variants back to their conceptual root.
- `inject_with` lists useful companion prompts for runtime stacking.
- `depends_on` marks prompts that usually need to be loaded first.

## Added in V2
- Canon/adaptation map for scenario aliasing
- Relationship map for chamber-play alliance shifts
- Dedicated quick and director runtime stacks for the scenario
- Expanded God of Carnage implementation split into characters, locations, and scene beats

## Added in V3
- Runtime-oriented preset files under `markdown/_presets/`
- Clear load order and drop order for real prompt stacking
- Dedicated presets for minimal play, scene direction, one-room social conflict, investigation, campaign bootstrap, and session resume
- Scenario-specific runtime presets for the God of Carnage implementation

## Added in V4
- Dedicated subconscious prompt templates for inner voice, agitation, and intuition support
- Runtime presets updated so player-facing stacks can carry a separate inner layer without mixing it into scene narration
- God of Carnage player-role implementations now include matching subconscious files for Penelope and Michael
