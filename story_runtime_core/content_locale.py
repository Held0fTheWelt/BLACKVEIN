"""Compatibility exports for the universal language adapter.

Older runtime code imports ``story_runtime_core.content_locale``. The content
module no longer owns per-module locale files; all names here delegate to
``language_adapter`` until the import surface is renamed throughout the engine.
"""

from __future__ import annotations

from story_runtime_core.language_adapter import (
    build_interaction_surface,
    build_player_attributed_visible_line,
    classify_player_input_from_rules,
    clear_language_adapter_caches,
    default_player_intent_commit_flags,
    greeting_imperative_addressee_fragment,
    greeting_imperative_visible_pair,
    load_session_language_model_directive,
    resolve_content_modules_root,
    resolve_string,
)

clear_content_locale_caches = clear_language_adapter_caches

__all__ = [
    "build_interaction_surface",
    "build_player_attributed_visible_line",
    "classify_player_input_from_rules",
    "clear_content_locale_caches",
    "default_player_intent_commit_flags",
    "greeting_imperative_addressee_fragment",
    "greeting_imperative_visible_pair",
    "load_session_language_model_directive",
    "resolve_content_modules_root",
    "resolve_string",
]
