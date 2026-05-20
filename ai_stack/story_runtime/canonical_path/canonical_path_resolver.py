"""Canonical path resolver.

Loads `content/modules/<module>/canonical_path/` step files, the schema, the
theme coverage map, and `direction/beat_library/` beat patterns into typed
in-memory structures consumable by the Live Dramatic Scene Simulator (LDSS).

Resolution rules:
  - Each step file's `mandatory_beats` may reference a pattern via
    `beat_pattern_ref`. The resolver looks the pattern up in the beat library,
    merges the step's `beat_pattern_params` against the pattern's parameter
    declarations, and produces a fully-expanded beat structure.
  - Inline director_instruction blocks (no `beat_pattern_ref`) pass through
    as-is.
  - Validation surfaces missing required params, unknown pattern refs, and
    missing step files referenced from `next_point.step_id`.

The resolver is read-only and side-effect-free. It is constructed once per
content module and cached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


CANONICAL_PATH_DIR_NAME = "canonical_path"
BEAT_LIBRARY_DIR_NAME = "beat_library"
DIRECTION_DIR_NAME = "direction"
SCHEMA_FILE_NAME = "_schema.yaml"
INDEX_FILE_NAME = "index.yaml"
THEME_COVERAGE_MAP_FILE_NAME = "theme_coverage_map.yaml"
BEAT_LIBRARY_INDEX_FILE_NAME = "_index.yaml"


class CanonicalPathResolveError(Exception):
    """Raised when the canonical path or beat library cannot be resolved."""


@dataclass
class BeatPattern:
    id: str
    category: str
    purpose: str
    parameter_specs: list[dict[str, Any]]
    expands_to: dict[str, Any]
    raw: dict[str, Any]

    def required_param_names(self) -> list[str]:
        return [
            str(p.get("name") or "").strip()
            for p in self.parameter_specs
            if bool(p.get("required"))
        ]


@dataclass
class ResolvedBeat:
    id: str
    order: int
    duration_target_seconds: int
    player_status: str
    pattern_id: str | None
    pattern_category: str | None
    pattern_params: dict[str, Any]
    director_instruction: dict[str, Any]
    forces_response_from: dict[str, Any] | None
    raw: dict[str, Any]

    def is_narrator_beat(self) -> bool:
        return self.pattern_category == "narrator" or "narrator_perception_only" in self.director_instruction

    def is_speech_beat(self) -> bool:
        return self.pattern_category == "npc_speak" or "npc_speak" in self.director_instruction


@dataclass
class CanonicalStep:
    sequence: int
    id: str
    path_id: str
    name: str
    mode: str
    scene_anchor: dict[str, Any]
    duration_target_seconds: int
    duration_max_seconds: int
    location_ref: dict[str, Any] | None
    support_refs: list[dict[str, Any]]
    object_refs: list[dict[str, Any]]
    present: dict[str, Any]
    preconditions: dict[str, Any]
    mandatory_beats: list[ResolvedBeat]
    themes_realized_here: list[dict[str, Any]]
    state_changes_committed: list[dict[str, Any]]
    next_step_unlock_when: dict[str, Any]
    next_point: dict[str, Any]
    raw: dict[str, Any]

    def next_step_id(self) -> str | None:
        nxt = self.next_point.get("step_id")
        if not nxt:
            return None
        s = str(nxt).strip()
        return s or None


@dataclass
class CanonicalPath:
    content_module_id: str
    module_root: Path
    canonical_path_dir: Path
    schema: dict[str, Any]
    theme_coverage_map: dict[str, Any]
    beat_patterns: dict[str, BeatPattern]
    steps: list[CanonicalStep]
    steps_by_id: dict[str, CanonicalStep] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    def first_step_id(self) -> str | None:
        if not self.steps:
            return None
        return self.steps[0].id

    def get_step(self, step_id: str) -> CanonicalStep | None:
        if not step_id:
            return None
        return self.steps_by_id.get(step_id.strip())

    def next_step_id_after(self, step_id: str) -> str | None:
        step = self.get_step(step_id)
        if not step:
            return None
        nxt = step.next_step_id()
        if nxt and nxt in self.steps_by_id:
            return nxt
        return None


# ---------------------------------------------------------------------------
# Module-level cache
# ---------------------------------------------------------------------------

_resolver_cache: dict[str, CanonicalPath] = {}


def load_canonical_path(
    module_root: Path,
    *,
    content_module_id: str = "",
    use_cache: bool = True,
) -> CanonicalPath:
    """Load and resolve the canonical path for a content module.

    `module_root` must be the path of `content/modules/<module>/`.
    """
    module_root = Path(module_root).resolve()
    cache_key = str(module_root)
    if use_cache and cache_key in _resolver_cache:
        return _resolver_cache[cache_key]

    canonical_path_dir = module_root / CANONICAL_PATH_DIR_NAME
    if not canonical_path_dir.is_dir():
        raise CanonicalPathResolveError(
            f"canonical_path directory not found under {module_root!s}"
        )

    schema = _read_yaml(canonical_path_dir / SCHEMA_FILE_NAME)
    theme_map = _read_yaml(canonical_path_dir / THEME_COVERAGE_MAP_FILE_NAME, optional=True)

    beat_library_dir = module_root / DIRECTION_DIR_NAME / BEAT_LIBRARY_DIR_NAME
    beat_patterns = _load_beat_patterns(beat_library_dir)

    raw_steps = _load_raw_steps(canonical_path_dir)
    diagnostics: list[str] = []
    resolved_steps: list[CanonicalStep] = []

    for raw_step in raw_steps:
        step = _resolve_step(raw_step, beat_patterns, diagnostics)
        if step:
            resolved_steps.append(step)

    resolved_steps.sort(key=lambda s: s.sequence)
    steps_by_id = {s.id: s for s in resolved_steps}

    _validate_next_step_chain(resolved_steps, steps_by_id, diagnostics)

    canonical_path = CanonicalPath(
        content_module_id=content_module_id or module_root.name,
        module_root=module_root,
        canonical_path_dir=canonical_path_dir,
        schema=schema,
        theme_coverage_map=theme_map or {},
        beat_patterns=beat_patterns,
        steps=resolved_steps,
        steps_by_id=steps_by_id,
        diagnostics=diagnostics,
    )

    if use_cache:
        _resolver_cache[cache_key] = canonical_path

    return canonical_path


def clear_resolver_cache() -> None:
    """Drop the cached resolver. Used by tests."""
    _resolver_cache.clear()


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def _read_yaml(path: Path, *, optional: bool = False) -> dict[str, Any]:
    if not path.exists():
        if optional:
            return {}
        raise CanonicalPathResolveError(f"required yaml not found: {path!s}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise CanonicalPathResolveError(
            f"yaml root must be a mapping in {path!s}, got {type(data).__name__}"
        )
    return data


def _load_beat_patterns(beat_library_dir: Path) -> dict[str, BeatPattern]:
    if not beat_library_dir.is_dir():
        raise CanonicalPathResolveError(
            f"beat library directory not found under {beat_library_dir!s}"
        )
    patterns: dict[str, BeatPattern] = {}
    for yaml_path in sorted(beat_library_dir.glob("*.yaml")):
        if yaml_path.name == BEAT_LIBRARY_INDEX_FILE_NAME:
            continue
        raw = _read_yaml(yaml_path)
        body = raw.get("beat_pattern")
        if not isinstance(body, dict):
            continue
        pattern_id = str(body.get("id") or "").strip()
        if not pattern_id:
            continue
        patterns[pattern_id] = BeatPattern(
            id=pattern_id,
            category=str(body.get("category") or "").strip(),
            purpose=str(body.get("purpose") or "").strip(),
            parameter_specs=list(body.get("parameters") or []),
            expands_to=dict(body.get("expands_to") or {}),
            raw=body,
        )
    return patterns


def _load_raw_steps(canonical_path_dir: Path) -> list[dict[str, Any]]:
    raw_steps: list[dict[str, Any]] = []
    for yaml_path in sorted(canonical_path_dir.glob("*.yaml")):
        name = yaml_path.name
        if name.startswith("_") or name == INDEX_FILE_NAME or name == THEME_COVERAGE_MAP_FILE_NAME:
            continue
        raw = _read_yaml(yaml_path)
        body = raw.get("canonical_path_step")
        if not isinstance(body, dict):
            continue
        raw_steps.append(body)
    return raw_steps


# ---------------------------------------------------------------------------
# Step / beat resolution
# ---------------------------------------------------------------------------

def _resolve_step(
    raw_step: dict[str, Any],
    beat_patterns: dict[str, BeatPattern],
    diagnostics: list[str],
) -> CanonicalStep | None:
    step_id = str(raw_step.get("id") or "").strip()
    if not step_id:
        diagnostics.append("step missing id; skipped")
        return None

    sequence = int(raw_step.get("sequence") or 0)
    raw_beats = raw_step.get("mandatory_beats") or []
    if not isinstance(raw_beats, list):
        diagnostics.append(f"{step_id}: mandatory_beats must be a list")
        return None

    resolved_beats: list[ResolvedBeat] = []
    for idx, raw_beat in enumerate(raw_beats):
        if not isinstance(raw_beat, dict):
            diagnostics.append(f"{step_id}: beat #{idx} is not a mapping")
            continue
        resolved = _resolve_beat(step_id, raw_beat, beat_patterns, diagnostics)
        if resolved:
            resolved_beats.append(resolved)

    resolved_beats.sort(key=lambda b: b.order)

    return CanonicalStep(
        sequence=sequence,
        id=step_id,
        path_id=str(raw_step.get("path_id") or "").strip(),
        name=str(raw_step.get("name") or "").strip(),
        mode=str(raw_step.get("mode") or "").strip(),
        scene_anchor=dict(raw_step.get("scene_anchor") or {}),
        duration_target_seconds=int(raw_step.get("duration_target_seconds") or 0),
        duration_max_seconds=int(raw_step.get("duration_max_seconds") or 0),
        location_ref=raw_step.get("location_ref") if isinstance(raw_step.get("location_ref"), dict) else None,
        support_refs=list(raw_step.get("support_refs") or []),
        object_refs=list(raw_step.get("object_refs") or []),
        present=dict(raw_step.get("present") or {}),
        preconditions=dict(raw_step.get("preconditions") or {}),
        mandatory_beats=resolved_beats,
        themes_realized_here=list(raw_step.get("themes_realized_here") or []),
        state_changes_committed=list(raw_step.get("state_changes_committed") or []),
        next_step_unlock_when=dict(raw_step.get("next_step_unlock_when") or {}),
        next_point=dict(raw_step.get("next_point") or {}),
        raw=raw_step,
    )


def _resolve_beat(
    step_id: str,
    raw_beat: dict[str, Any],
    beat_patterns: dict[str, BeatPattern],
    diagnostics: list[str],
) -> ResolvedBeat | None:
    beat_id = str(raw_beat.get("id") or "").strip()
    if not beat_id:
        diagnostics.append(f"{step_id}: beat missing id; skipped")
        return None

    order = int(raw_beat.get("order") or 0)
    duration = int(raw_beat.get("duration_target_seconds") or 0)
    player_status = str(raw_beat.get("player_status") or "spectator_blocked").strip()

    pattern_ref = raw_beat.get("beat_pattern_ref")
    inline_director = raw_beat.get("director_instruction")
    forces_response = raw_beat.get("forces_response_from")
    if isinstance(forces_response, dict):
        forces_response_dict: dict[str, Any] | None = dict(forces_response)
    else:
        forces_response_dict = None

    pattern_params: dict[str, Any] = dict(raw_beat.get("beat_pattern_params") or {})
    director_instruction: dict[str, Any] = {}
    pattern_id: str | None = None
    pattern_category: str | None = None

    if pattern_ref:
        pattern_id = str(pattern_ref).strip()
        pattern = beat_patterns.get(pattern_id)
        if not pattern:
            diagnostics.append(
                f"{step_id}#{beat_id}: unknown beat_pattern_ref {pattern_id!r}"
            )
            return None
        pattern_category = pattern.category
        missing = [
            name for name in pattern.required_param_names()
            if name and name not in pattern_params
        ]
        if missing:
            diagnostics.append(
                f"{step_id}#{beat_id}: pattern {pattern_id!r} missing required params: {missing}"
            )
        director_instruction = _expand_pattern(pattern, pattern_params)
    elif isinstance(inline_director, dict):
        director_instruction = dict(inline_director)
    else:
        diagnostics.append(
            f"{step_id}#{beat_id}: neither beat_pattern_ref nor director_instruction provided"
        )

    return ResolvedBeat(
        id=beat_id,
        order=order,
        duration_target_seconds=duration,
        player_status=player_status,
        pattern_id=pattern_id,
        pattern_category=pattern_category,
        pattern_params=pattern_params,
        director_instruction=director_instruction,
        forces_response_from=forces_response_dict,
        raw=raw_beat,
    )


def _expand_pattern(pattern: BeatPattern, params: dict[str, Any]) -> dict[str, Any]:
    """Produce a concrete director_instruction dict for a pattern + params.

    The beat library `expands_to` blocks are descriptive YAML — they document
    intent rather than provide a strict template engine. For pattern categories
    the renderer needs to act on, we project the params into a canonical
    director_instruction shape that the renderer consumes deterministically.
    """
    category = pattern.category
    if category == "narrator":
        return _expand_narrator_pattern(pattern, params)
    if category == "npc_speak":
        return _expand_npc_speak_pattern(pattern, params)
    if category == "dialog_chain":
        return _expand_dialog_chain_pattern(pattern, params)
    if category == "structural":
        return _expand_structural_pattern(pattern, params)
    if category == "recurrent":
        return _expand_recurrent_pattern(pattern, params)
    return dict(pattern.expands_to)


def _expand_narrator_pattern(pattern: BeatPattern, params: dict[str, Any]) -> dict[str, Any]:
    instruction: dict[str, Any] = {}
    if pattern.id == "narrator_perception_block":
        instruction["narrator_perception_only"] = list(params.get("perception_lines") or [])
        if params.get("sensory_anchors"):
            instruction["sensory_anchors"] = list(params["sensory_anchors"])
        if params.get("filler_action_visible"):
            instruction["filler_action_visible"] = dict(params["filler_action_visible"])
    elif pattern.id == "silence_perception_pause":
        instruction["narrator_perception_only"] = list(params.get("perception_lines") or [])
        instruction["silence_duration_seconds"] = int(params.get("silence_duration_seconds") or 0)
        instruction["trigger_after_beat"] = params.get("trigger_after_beat")
        instruction["closes_window_when"] = params.get("closes_window_when") or "duration_elapsed"
        if params.get("body_marker_visible"):
            instruction["body_marker_visible"] = list(params["body_marker_visible"])
    elif pattern.id == "type_into_device_with_speech_confirm":
        actor = params.get("actor")
        confirmed_token = params.get("confirmed_token")
        instruction["narrator_perception_only"] = [
            f"{actor} types into {params.get('device_ref')}."
        ]
        instruction["npc_speak"] = {
            "actor": actor,
            "intent": "read_back_the_corrected_token_while_typing",
            "required_facts": [f"confirmed_token: {confirmed_token}"],
            "quote_anchor": params.get("quote_anchor"),
            "paraphrase_policy": "short_anchor_quote_allowed",
            "minimum_visible": "the corrected token, half-spoken while typing",
        }
        instruction["typing_rhythm"] = params.get("typing_rhythm") or "single_strike_then_pause"
    return instruction


def _expand_npc_speak_pattern(pattern: BeatPattern, params: dict[str, Any]) -> dict[str, Any]:
    npc_speak = {
        "actor": params.get("actor"),
        "intent": params.get("intent"),
        "required_facts": list(params.get("required_facts") or []),
        "quote_anchor": params.get("quote_anchor"),
        "paraphrase_policy": params.get("paraphrase_policy") or "structural_paraphrase_required",
        "minimum_visible": params.get("minimum_visible"),
        "forbidden_drift": list(params.get("forbidden_drift") or []),
    }
    if "tone_hint" in params:
        npc_speak["tone_hint"] = params["tone_hint"]
    if pattern.id == "single_word_challenge":
        npc_speak["intent"] = npc_speak.get("intent") or "object_to_target_word_with_a_single_word_question"
        npc_speak["required_facts"] = list(npc_speak.get("required_facts") or [])
        target = params.get("challenge_target_word")
        if target and not any(str(f).startswith("challenge_target_word") for f in npc_speak["required_facts"]):
            npc_speak["required_facts"].append(f"challenge_target_word: {target}")
        npc_speak["paraphrase_policy"] = "short_anchor_quote_allowed"
        npc_speak["minimum_visible"] = npc_speak.get("minimum_visible") or "single word as question, at most three words"
        npc_speak["max_words"] = int(params.get("max_words") or 1)
        npc_speak["question_inflection_required"] = bool(params.get("question_inflection_required", True))
    elif pattern.id == "amiable_echo":
        echoed = params.get("echoed_phrase_token")
        npc_speak["intent"] = npc_speak.get("intent") or "echo_the_chosen_phrasing_to_seal_the_compromise"
        npc_speak["required_facts"] = list(npc_speak.get("required_facts") or [])
        if echoed and not any(str(f).startswith("echoed_phrase_token") for f in npc_speak["required_facts"]):
            npc_speak["required_facts"].append(f"echoed_phrase_token: {echoed}")
        npc_speak["word_count_target"] = int(params.get("word_count_target") or 4)
        npc_speak["tone_hint"] = params.get("tone") or npc_speak.get("tone_hint") or "friendly_confirmation"
    elif pattern.id == "scripted_monologue_segmented":
        npc_speak["segments"] = list(params.get("segments") or [])
        npc_speak["inter_segment_max_pause_seconds"] = int(params.get("inter_segment_max_pause_seconds") or 2)
    return {"npc_speak": npc_speak}


def _expand_dialog_chain_pattern(pattern: BeatPattern, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "forces_response_from": {
            "actor": params.get("target_actor"),
            "intent": params.get("target_intent"),
            "required_state_change": params.get("required_state_change"),
            "max_delay_seconds": int(params.get("max_delay_seconds") or 6),
            "failure_handling": params.get("failure_handling") or "regenerate_target_response",
            "target_pattern_ref": params.get("target_pattern_ref"),
            "chain_can_extend": bool(params.get("chain_can_extend", False)),
            "source_beat_id": params.get("source_beat_id"),
        }
    }


def _expand_structural_pattern(pattern: BeatPattern, params: dict[str, Any]) -> dict[str, Any]:
    if pattern.id == "consequence_irreversible_commit":
        return {
            "state_change": {
                "trigger_beat_id": params.get("trigger_beat_id"),
                "state_key": params.get("state_key"),
                "to_value": params.get("to_value"),
                "from_value": params.get("from_value"),
                "rollback_policy": params.get("rollback_policy") or "never",
                "visibility_scope": params.get("visibility_scope") or "all_actors_in_room",
                "surface_in_committed_truth": bool(params.get("surface_in_committed_truth", True)),
            }
        }
    if pattern.id == "player_intrusion_redirect_strict":
        return {
            "player_intrusion_window": {
                "between": [params.get("between_beat_a"), params.get("between_beat_b")],
                "allowed": list(params.get("allowed") or []),
                "forbidden": list(params.get("forbidden") or []),
                "redirect_kind": params.get("redirect_kind") or "narrator_perception_redirect",
                "redirect_narrator_line_template": params.get("redirect_narrator_line_template"),
                "log_to_runtime_intelligence": bool(params.get("log_to_runtime_intelligence", True)),
            }
        }
    return dict(pattern.expands_to)


def _expand_recurrent_pattern(pattern: BeatPattern, params: dict[str, Any]) -> dict[str, Any]:
    if pattern.id == "phone_interruption_recurrent":
        theme_arc = pattern.raw.get("theme_arc_carried") or {}
        caller_actor = str(theme_arc.get("actor") or "").strip()
        caller_facts_key = f"{caller_actor}_visible_facts" if caller_actor else None
        visible_facts: list[Any] = []
        if caller_facts_key and caller_facts_key in params:
            visible_facts = list(params.get(caller_facts_key) or [])
        elif "caller_visible_facts" in params:
            visible_facts = list(params.get("caller_visible_facts") or [])
        return {
            "phone_interruption": {
                "caller_actor": caller_actor,
                "call_partner": params.get("call_partner"),
                "call_topic": params.get("call_topic"),
                "interrupted_in_step_id": params.get("interrupted_in_step_id"),
                "interrupted_at_beat_id": params.get("interrupted_at_beat_id"),
                "caller_visible_facts": visible_facts,
                "call_audible_duration_seconds": int(params.get("call_audible_duration_seconds") or 30),
                "returns_to_room_with": params.get("returns_to_room_with") or "apology_then_return",
                "leaves_phone_in_view": bool(params.get("leaves_phone_in_view", True)),
            }
        }
    return dict(pattern.expands_to)


def _validate_next_step_chain(
    steps: list[CanonicalStep],
    steps_by_id: dict[str, CanonicalStep],
    diagnostics: list[str],
) -> None:
    for step in steps:
        nxt = step.next_step_id()
        if nxt and nxt not in steps_by_id:
            diagnostics.append(
                f"{step.id}: next_point.step_id {nxt!r} does not exist"
            )
