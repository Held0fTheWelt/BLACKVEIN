# Improvement experiment run fixtures

Tracked JSON samples previously lived under `backend/world-engine/app/var/runs/`, which implied a second “world-engine” service root. These files are **fixture / sample payloads** for the improvement loop, not runtime output for the play service.

Do not treat this directory as authoritative runtime state.
