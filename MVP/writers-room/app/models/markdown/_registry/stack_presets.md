# Runtime Stack Presets

These presets are for real runtime use rather than abstract taxonomy.
They are ordered from lightest to heaviest.

## Fastest General Use
- `preset.runtime.minimal`
- `preset.runtime.session_resume`

## Strong Scene Leadership
- `preset.runtime.scene_director`
- `preset.runtime.one_room_social_conflict`

## Information-Heavy Play
- `preset.runtime.investigation`

## Campaign / Region Setup
- `preset.runtime.campaign_bootstrap`

## Scenario-Specific Chamber Play
- `preset.runtime.god_of_carnage.quick`
- `preset.runtime.god_of_carnage.director`

## Subconscious Layer Guidance
When a player-facing character is active, add:
- `template.characters.subconscious.quick` for light stacks
- `template.characters.subconscious.standard` for director stacks
- one matching implementation subconscious file in scenario-specific stacks

## Practical Recommendation
Start with the lightest stack that can still carry the scene.
Only add heavier support when the current scene genuinely needs it.

### Good Default Choices
- quick test or chat play: `preset.runtime.minimal`
- central conversation scene: `preset.runtime.scene_director`
- contained social collapse: `preset.runtime.one_room_social_conflict`
- mystery handling: `preset.runtime.investigation`
- session restart: `preset.runtime.session_resume`
- campaign opening: `preset.runtime.campaign_bootstrap`
- God of Carnage style opening: `preset.runtime.god_of_carnage.quick` or `preset.runtime.god_of_carnage.director`
