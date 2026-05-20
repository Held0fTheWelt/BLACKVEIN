"""DEPRECATED (transitional): bootstrap a W2 ``SessionState`` inside the backend process.

Loads modules and seeds ``canonical_state`` for **tests, tooling, and MCP/dev** — not
where production narrative runs execute (**World Engine** is authoritative).
Rationale: reuse backend content loading without duplicating module graphs in-engine.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.content.module_exceptions import ModuleLoadError, ModuleValidationError
from app.content.module_loader import load_module
from app.content.module_models import ContentModule, ScenePhase
from app.runtime.event_log import RuntimeEventLog
from app.runtime.runtime_models import (
    EventLogEntry,
    SessionState,
    SessionStatus,
    TurnState,
    TurnStatus,
)


class SessionStartError(RuntimeError):
    """Raised when session start fails with a clear reason code."""

    def __init__(self, reason: str, module_id: str, detail: str = ""):
        self.reason = reason  # "module_not_found", "module_invalid", "no_start_scene"
        self.module_id = module_id
        self.detail = detail
        super().__init__(
            f"Session start failed [{reason}] for module '{module_id}': {detail}"
        )


class SessionStartResult(BaseModel):
    """Result of a successful session start.

    Contains the initial SessionState, turn-ready basis (initial TurnState),
    and initial events for logging.
    """

    session: SessionState
    module: ContentModule
    initial_turn: TurnState
    events: list[EventLogEntry] = Field(default_factory=list)


def _resolve_initial_scene(module: ContentModule) -> tuple[str, ScenePhase]:
    """Find the entry scene from the module scene graph, then phase layer.

    The scene graph is the primary node surface when present. The phase layer
    remains usable for modules that have not split scenes into authored nodes.
    No hardcoded IDs; purely data-driven based on ContentModule structure.

    Args:
        module: Loaded ContentModule

    Returns:
        Tuple of (scene_id, ScenePhase) for the initial scene

    Raises:
        SessionStartError: If module has no scene phases
    """
    raw_scene_graph = getattr(module, "scene_graph", {})
    scene_graph = raw_scene_graph if isinstance(raw_scene_graph, dict) else {}
    graph_start = str(scene_graph.get("default_start_node_id") or "").strip()
    graph_nodes = scene_graph.get("nodes") if isinstance(scene_graph.get("nodes"), list) else []
    if graph_start:
        node = next(
            (
                row for row in graph_nodes
                if isinstance(row, dict) and str(row.get("id") or "").strip() == graph_start
            ),
            {},
        )
        phase_id = str(node.get("phase_id") or "").strip() if isinstance(node, dict) else ""
        if phase_id in module.scene_phases:
            return graph_start, module.scene_phases[phase_id]
        return graph_start, ScenePhase(
            id=graph_start,
            name=str(node.get("title") or graph_start) if isinstance(node, dict) else graph_start,
            sequence=int(node.get("sequence") or 1) if isinstance(node, dict) else 1,
            description=str(node.get("summary") or "") if isinstance(node, dict) else "",
            content_focus=[],
            engine_tasks=[],
            active_triggers=[],
        )

    if not module.scene_phases:
        raise SessionStartError(
            "no_start_scene",
            module.metadata.module_id,
            "Module has no scene graph start node or scene phases defined",
        )

    return min(module.scene_phases.items(), key=lambda kv: kv[1].sequence)


def _build_initial_canonical_state(module: ContentModule) -> dict[str, Any]:
    """Build initial canonical world state from module character baselines.

    Iterates all module characters and extracts runtime state fields from
    CharacterDefinition.extras. Provides sensible defaults for fields not
    present in the module.

    Args:
        module: Loaded ContentModule

    Returns:
        Initial canonical_state dict with character state initialized
    """
    characters = {}
    for char_id, char in module.characters.items():
        characters[char_id] = {
            "emotional_state": char.extras.get("emotional_state", 50),
            "escalation_level": char.extras.get("escalation_level", 0),
            "engagement": char.extras.get("engagement", 60),
            "moral_defense": char.extras.get("moral_defense", 60),
        }

    return {"characters": characters}


def start_session(
    module_id: str,
    *,
    root_path: Path | None = None,
    seed: str | None = None,
) -> SessionStartResult:
    """Bootstrap in-process ``SessionState`` from a content module (not a World Engine run).

    Performs the session-start workflow inside this process:
    1. Loads and validates the target module
    2. Determines the initial scene (data-driven from phase sequence)
    3. Constructs initial SessionState with seeded canonical state
    4. Creates turn-ready basis (TurnState for turn 1)
    5. Creates initial events for audit trail

    Args:
        module_id: Identifier of the module to load (e.g., "god_of_carnage")
        root_path: Optional *modules root* (parent of ``<module_id>/``). If omitted,
                  uses the repository ``content/modules`` directory.
        seed: Optional reproducibility seed

    Returns:
        SessionStartResult containing session, initial_turn, and events

    Raises:
        SessionStartError: If module loading fails, initial scene cannot be
            resolved, or module is invalid.
    """
    # Load module
    try:
        module = load_module(module_id, root_path=root_path)
    except ModuleLoadError as e:
        raise SessionStartError("module_not_found", module_id, str(e)) from e
    except ModuleValidationError as e:
        raise SessionStartError("module_invalid", module_id, str(e)) from e

    # Resolve initial scene (data-driven, no hardcoded IDs)
    initial_scene_id, initial_phase = _resolve_initial_scene(module)

    # Build initial canonical state
    canonical_state = _build_initial_canonical_state(module)

    # Construct SessionState (canonical id from YAML; matches compile_module / disk layout)
    session = SessionState(
        module_id=module.metadata.module_id,
        module_version=module.metadata.version,
        current_scene_id=initial_scene_id,
        canonical_state=canonical_state,
        status=SessionStatus.ACTIVE,
        turn_counter=0,
        seed=seed,
    )

    # Turn-ready basis: turn 1 not yet started
    initial_turn = TurnState(
        turn_number=1,
        session_id=session.session_id,
        status=TurnStatus.PENDING,
    )

    # Event logging
    event_log = RuntimeEventLog(session_id=session.session_id, turn_number=None)

    event_log.log(
        "session_started",
        f"Session started: {module_id} v{module.metadata.version}",
        payload={
            "module_id": module_id,
            "module_version": module.metadata.version,
        },
    )

    event_log.log(
        "module_loaded",
        f"Module loaded: {module_id} ({len(module.characters)} characters, {len(module.scene_phases)} phases)",
        payload={
            "module_id": module_id,
            "module_version": module.metadata.version,
            "character_count": len(module.characters),
            "scene_phase_count": len(module.scene_phases),
        },
    )

    event_log.log(
        "initial_scene_resolved",
        f"Initial scene: {initial_scene_id} (sequence {initial_phase.sequence})",
        payload={
            "scene_id": initial_scene_id,
            "scene_name": initial_phase.name,
            "sequence": initial_phase.sequence,
        },
    )

    return SessionStartResult(
        session=session,
        module=module,
        initial_turn=initial_turn,
        events=event_log.flush(),
    )
