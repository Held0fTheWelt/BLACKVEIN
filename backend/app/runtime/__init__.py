"""Backend `app.runtime` — W2 session shapes, policies, and in-process simulation.

This package mixes three kinds of code (see ``docs/technical/architecture/backend-runtime-classification.md``):

1. **Canonical reusable** — Pydantic models, validators, presenters, preview dry-run,
   serialization helpers (safe to import; does not imply live execution here).
2. **Deprecated transitional** — In-process ``SessionState`` turn pipeline, in-memory
   session registry, and ``RuntimeManager``/``RuntimeEngine`` (tests and operator
   tooling only). **Not** equivalent to the World Engine live runtime.
3. **Removed legacy** — Former ``app.api.http`` FastAPI shadow play API and
   ``w2_models`` shim (deleted in Block 2).

**Authoritative live runs** execute in the **World Engine** play service; the Flask
app talks to it via ``game_service``, not via this package as a second runtime.
"""

from app.runtime.scene_presenter import (
    CharacterPanelOutput,
    ConflictPanelOutput,
    ConflictTrendSignal,
    RelationshipMovement,
    present_character_panel,
    present_conflict_panel,
    present_all_characters,
)

__all__ = [
    "CharacterPanelOutput",
    "ConflictPanelOutput",
    "ConflictTrendSignal",
    "RelationshipMovement",
    "present_character_panel",
    "present_conflict_panel",
    "present_all_characters",
]
