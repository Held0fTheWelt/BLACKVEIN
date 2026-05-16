"""Shared policy for Langfuse observation tree selection.

The root trace is controlled by the existing enabled/sample-rate settings. This
policy controls optional child observations so operators can keep a minimal,
targeted, or full trace tree without changing runtime behavior.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


OBSERVATION_TREE_MINIMAL = "minimal"
OBSERVATION_TREE_GRAPH_PATH = "graph_path"
OBSERVATION_TREE_MODEL_IO = "model_io"
OBSERVATION_TREE_RETRIEVAL = "retrieval"
OBSERVATION_TREE_RUNTIME_ASPECTS = "runtime_aspects"
OBSERVATION_TREE_SCENE_PROJECTION = "scene_projection"
OBSERVATION_TREE_NARRATOR = "narrator"
OBSERVATION_TREE_SCORES = "scores"
OBSERVATION_TREE_EVIDENCE = "evidence"

OBSERVATION_TREE_ORDER: tuple[str, ...] = (
    OBSERVATION_TREE_MINIMAL,
    OBSERVATION_TREE_GRAPH_PATH,
    OBSERVATION_TREE_MODEL_IO,
    OBSERVATION_TREE_RETRIEVAL,
    OBSERVATION_TREE_RUNTIME_ASPECTS,
    OBSERVATION_TREE_SCENE_PROJECTION,
    OBSERVATION_TREE_NARRATOR,
    OBSERVATION_TREE_SCORES,
    OBSERVATION_TREE_EVIDENCE,
)

DEFAULT_ENABLED_OBSERVATION_TREES: tuple[str, ...] = (OBSERVATION_TREE_MINIMAL,)

OBSERVATION_TREE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": OBSERVATION_TREE_MINIMAL,
        "label": "Minimal path",
        "description": "Root trace plus the compact path summary span.",
    },
    {
        "id": OBSERVATION_TREE_GRAPH_PATH,
        "label": "Graph phases",
        "description": "Intent, validation, commit and branch phase spans.",
    },
    {
        "id": OBSERVATION_TREE_MODEL_IO,
        "label": "Model I/O",
        "description": "Model route/invoke detail and generation observations.",
    },
    {
        "id": OBSERVATION_TREE_RETRIEVAL,
        "label": "Retrieval",
        "description": "RAG phase spans and retriever observations.",
    },
    {
        "id": OBSERVATION_TREE_RUNTIME_ASPECTS,
        "label": "Runtime aspects",
        "description": "Aspect ledger spans for authority, pacing, memory, voice and validation.",
    },
    {
        "id": OBSERVATION_TREE_SCENE_PROJECTION,
        "label": "Scene projection",
        "description": "Visible projection, LDSS fallback and scene-envelope spans.",
    },
    {
        "id": OBSERVATION_TREE_NARRATOR,
        "label": "Narrator",
        "description": "Narrator phase and NarrativeRuntimeAgent spans.",
    },
    {
        "id": OBSERVATION_TREE_SCORES,
        "label": "Scores",
        "description": "Langfuse score writes for deterministic contract evidence.",
    },
    {
        "id": OBSERVATION_TREE_EVIDENCE,
        "label": "Evidence probes",
        "description": "Nested local evidence spans such as ADR-0041 capability probes.",
    },
)

_VALID_TREE_IDS = frozenset(OBSERVATION_TREE_ORDER)


def observation_tree_catalog() -> list[dict[str, str]]:
    """Return a JSON-serializable catalog for administration UIs."""
    return [dict(item) for item in OBSERVATION_TREE_CATALOG]


def normalize_enabled_observation_trees(value: Any) -> list[str]:
    """Normalize persisted/API values to known tree IDs in stable order.

    Accepted convenience values:
    - ``"all"`` / ``"*"`` or a list containing either selects all trees.
    - ``"none"`` selects no optional child observations.
    - ``None`` falls back to the minimal traceable path.
    """
    if value is None:
        return list(DEFAULT_ENABLED_OBSERVATION_TREES)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        lowered = raw.lower()
        if lowered in {"all", "*"}:
            return list(OBSERVATION_TREE_ORDER)
        if lowered == "none":
            return []
        values: Iterable[Any] = (raw,)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        values = value
    else:
        return list(DEFAULT_ENABLED_OBSERVATION_TREES)

    seen: set[str] = set()
    for item in values:
        token = str(item or "").strip().lower()
        if token in {"all", "*"}:
            return list(OBSERVATION_TREE_ORDER)
        if token == "none":
            return []
        if token in _VALID_TREE_IDS:
            seen.add(token)

    return [tree_id for tree_id in OBSERVATION_TREE_ORDER if tree_id in seen]


def classify_observation_tree(
    name: str,
    *,
    as_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> str:
    """Classify a Langfuse observation or score into an operator-selectable tree."""
    n = (name or "").strip().lower()
    obs_type = (as_type or "").strip().lower()
    md = metadata if isinstance(metadata, Mapping) else {}
    phase = str(md.get("phase") or "").strip().lower()

    if obs_type == "score":
        return OBSERVATION_TREE_SCORES

    if n == "story.graph.path_summary":
        return OBSERVATION_TREE_MINIMAL

    if (
        "narrator" in n
        or phase == "narrator"
        or "narrative_runtime_agent" in n
        or n.startswith("story.narrative_agent")
    ):
        return OBSERVATION_TREE_NARRATOR

    if (
        obs_type == "generation"
        or n.startswith("story.model.")
        or n in {
            "story.phase.model_route",
            "story.phase.model_invoke",
            "story.phase.primary_parse",
            "story.phase.model_fallback",
        }
        or "generation" in n
        or "model_invoke" in n
    ):
        return OBSERVATION_TREE_MODEL_IO

    if obs_type == "retriever" or "retrieval" in n or ".rag." in n:
        return OBSERVATION_TREE_RETRIEVAL

    if (
        "ldss" in n
        or "scene_projection" in n
        or n.startswith("story.visible.")
        or n.startswith("story.scene.")
        or n.endswith(".visible.project")
    ):
        return OBSERVATION_TREE_SCENE_PROJECTION

    if (
        phase == "runtime_aspect"
        or ".aspect" in n
        or "aspect_" in n
        or n.endswith(".aspect_summary")
        or n.startswith("story.input.")
        or n.startswith("story.action.")
        or n.startswith("story.beat.")
        or n.startswith("story.energy.")
        or n.startswith("story.pacing.")
        or n.startswith("story.time.")
        or n.startswith("story.sensory.")
        or n.startswith("story.genre.")
        or n.startswith("story.tone.")
        or n.startswith("story.improv.")
        or n.startswith("story.disclosure.")
        or n.startswith("story.expectation.")
        or n.startswith("story.momentum.")
        or n.startswith("story.capability.")
        or n.startswith("story.authority.")
        or n.startswith("story.npc.")
        or n.startswith("story.voice.")
        or n.startswith("story.memory.")
    ):
        return OBSERVATION_TREE_RUNTIME_ASPECTS

    if "evidence" in n or "adr0041" in n or "semantic_capability" in n:
        return OBSERVATION_TREE_EVIDENCE

    if n.startswith("story.phase.") or n.startswith("story.branch.") or n.startswith("validation_"):
        return OBSERVATION_TREE_GRAPH_PATH

    return OBSERVATION_TREE_GRAPH_PATH


def should_emit_observation(
    enabled_observation_trees: Any,
    name: str,
    *,
    as_type: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> bool:
    """Return whether an optional child observation should be emitted."""
    enabled = set(normalize_enabled_observation_trees(enabled_observation_trees))
    tree_id = classify_observation_tree(name, as_type=as_type, metadata=metadata)
    return tree_id in enabled
