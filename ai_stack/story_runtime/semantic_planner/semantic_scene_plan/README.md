# Semantic Scene Plan

This package contains the real Python modules behind
`ai_stack.story_runtime.semantic_planner.semantic_scene_planner`. The public
module remains a small compatibility import path; implementation lives here by
planner responsibility:

- `mappings.py` deterministic planner mappings and external constants
- `utils.py` shared cleaning and lookup helpers
- `content_frame.py` canonical-path and speech-policy assembly
- `dialogue_plan.py` NPC dialogue and dialogue-aware handover policy
- `capability_plan.py` Director capability-manager planning
- `continuity.py` continuity, transition, subtext, and pressure helpers
- `scene_target.py` scene function, pressure function, target, and obligations
- `actor_directives.py` actor directives and base handover policy
- `dramatic_beats.py` dramatic beat assembly
- `enrichment.py` public enrichment builder
