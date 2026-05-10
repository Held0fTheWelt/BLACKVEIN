"""Load player-visible strings and model directives from ``content/modules/<module_id>/locale``.

Engine code references stable keys only; all localized prose lives in module YAML/MD.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "build_player_attributed_visible_line",
    "classify_player_input_from_rules",
    "clear_content_locale_caches",
    "greeting_imperative_addressee_fragment",
    "greeting_imperative_visible_pair",
    "load_session_language_model_directive",
    "resolve_content_modules_root",
    "resolve_string",
]


def resolve_content_modules_root(explicit: Path | None = None) -> Path:
    """Return the ``content/modules`` directory (parent of per-module folders)."""
    if explicit is not None:
        p = explicit.expanduser().resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"content_modules_root is not a directory: {p}")
        return p
    env = (os.environ.get("WOS_REPO_ROOT") or "").strip()
    if env:
        p = (Path(env).expanduser().resolve() / "content" / "modules")
        if p.is_dir():
            return p
    cur = Path(__file__).resolve().parent
    for _ in range(24):
        cand = cur / "content" / "modules"
        if cand.is_dir():
            return cand.resolve()
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError(
        "Cannot resolve content/modules: set WOS_REPO_ROOT to the checkout or container root "
        "that contains content/modules/, or run from a monorepo tree that includes content/modules/."
    )


def _module_strings_path(module_id: str, root: Path) -> Path:
    return root / module_id / "locale" / "module_strings.yaml"


def _player_rules_path(module_id: str, root: Path) -> Path:
    return root / module_id / "locale" / "player_input_rules.yaml"


@lru_cache(maxsize=32)
def _load_module_strings_cached(path_s: str) -> dict[str, Any]:
    p = Path(path_s)
    if not p.is_file():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=32)
def _load_player_rules_cached(path_s: str) -> dict[str, Any]:
    p = Path(path_s)
    if not p.is_file():
        return {}
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=64)
def _load_directive_cached(path_s: str) -> str:
    p = Path(path_s)
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def clear_content_locale_caches() -> None:
    """Reset memoized loaders (tests that swap locale files on disk)."""
    _load_module_strings_cached.cache_clear()
    _load_player_rules_cached.cache_clear()
    _load_directive_cached.cache_clear()


DEFAULT_LOCALE_FALLBACK_MODULE_ID = "god_of_carnage"


def resolve_string(
    module_id: str,
    key: str,
    lang: str,
    *,
    content_modules_root: Path | None = None,
    fallback_module_id: str | None = DEFAULT_LOCALE_FALLBACK_MODULE_ID,
    **placeholders: Any,
) -> str:
    """Format a ``module_strings.yaml`` entry for ``lang`` (fallback: en, then de).

    If ``module_id`` has no ``locale/module_strings.yaml`` (or no ``strings`` map),
    the next candidate is ``fallback_module_id`` (default: ``god_of_carnage``) so
    generic engine surfaces stay operational for unsupported module scopes.
    """
    root = resolve_content_modules_root(content_modules_root)
    primary = str(module_id or "").strip()
    fb = str(fallback_module_id or "").strip()
    chain = [primary] if primary else []
    if fb and fb not in chain:
        chain.append(fb)
    if not chain:
        chain = [fb] if fb else []

    errors: list[str] = []
    for mid in chain:
        path = _module_strings_path(mid, root)
        data = _load_module_strings_cached(str(path))
        strings = data.get("strings")
        if not isinstance(strings, dict):
            errors.append(f"{path}: no strings map")
            continue
        entry = strings.get(key)
        if not isinstance(entry, dict):
            errors.append(f"{path}: unknown key {key!r}")
            continue
        lg = (lang or "de").strip().lower()[:2] or "de"
        template = entry.get(lg) or entry.get("en") or entry.get("de")
        if not isinstance(template, str) or not template.strip():
            errors.append(f"{path}: no template for key={key!r} lang={lg!r}")
            continue
        if placeholders:
            return template.format(**placeholders)
        return template

    raise KeyError(
        f"resolve_string failed for key={key!r} module_id={primary!r}: " + "; ".join(errors) or "no module candidates"
    )


def greeting_imperative_addressee_fragment(
    raw: str,
    *,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
) -> str | None:
    """Return addressee tail for greet-X imperatives, or ``None``."""
    text = str(raw or "").strip()
    if not text:
        return None
    root = resolve_content_modules_root(content_modules_root)
    rules = _load_player_rules_cached(str(_player_rules_path(module_id, root)))
    gi = rules.get("greeting_imperative")
    if not isinstance(gi, dict):
        return None
    lg = (lang or "de").strip().lower()[:2] or "de"
    block = gi.get(lg) if isinstance(gi.get(lg), dict) else None
    if not isinstance(block, dict):
        block = gi.get("en") if isinstance(gi.get("en"), dict) else {}
    pats = block.get("patterns") if isinstance(block.get("patterns"), list) else []
    for pat in pats:
        if not isinstance(pat, str) or not pat.strip():
            continue
        try:
            m = re.match(pat, text)
        except re.error:
            continue
        if not m:
            continue
        frag = str(m.group(1) or "").strip().strip('"„"«»').strip()
        return frag or None
    return None


def greeting_imperative_visible_pair(
    raw: str,
    *,
    addressee: str,
    player_shell_name: str,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
) -> tuple[str, str] | None:
    """Return ``(verbatim_typing, diegetic_attributed_line)`` for greet-X imperatives."""
    add = str(addressee or "").strip()
    if not add:
        return None
    root = resolve_content_modules_root(content_modules_root)
    diegetic = resolve_string(
        module_id,
        "greeting.polite_line",
        lang,
        content_modules_root=root,
        addressee=add,
    )
    outcome = resolve_string(
        module_id,
        "greeting.attributed_outcome",
        lang,
        content_modules_root=root,
        player_shell_name=player_shell_name,
        diegetic=diegetic,
    )
    return (raw, outcome)


def build_player_attributed_visible_line(
    *,
    name: str,
    raw: str,
    input_kind: str,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
) -> str:
    """Diegetic one-line shell outcome for committed human input (speech / action / mixed)."""
    ik = str(input_kind or "speech").strip().lower()
    if ik in ("intent_only", "ambiguous", "reaction"):
        ik = "speech"
    raw_s = str(raw or "").strip()
    is_question = raw_s.rstrip().endswith("?")
    if ik == "action":
        key = "player_outcome.action_display"
    elif ik == "mixed":
        key = "player_outcome.mixed_display"
    elif is_question:
        key = "player_outcome.speech_question"
    else:
        key = "player_outcome.speech_statement"
    return resolve_string(module_id, key, lang, content_modules_root=content_modules_root, name=name, raw=raw_s)


def load_session_language_model_directive(
    *,
    module_id: str,
    lang: str,
    content_modules_root: Path | None = None,
) -> str:
    """Load non-opening session language directive markdown for ``module_id``."""
    root = resolve_content_modules_root(content_modules_root)
    mid = (module_id or "").strip()
    if not mid:
        return ""
    lg = (lang or "de").strip().lower()[:2] or "de"
    for lid in (lg, "en", "de"):
        p = root / mid / "locale" / "model_directives" / f"session_output_language_{lid}.md"
        text = _load_directive_cached(str(p))
        if text.strip():
            return text
    return ""


def classify_player_input_from_rules(
    raw_text: str,
    *,
    module_id: str,
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    """Reserved: ordered ``classification_rules`` in ``player_input_rules.yaml`` (v1: none)."""
    root = resolve_content_modules_root(content_modules_root)
    rules = _load_player_rules_cached(str(_player_rules_path(module_id, root)))
    cls = rules.get("classification_rules")
    if not isinstance(cls, list) or not cls:
        return {"player_input_kind": "unclear", "deterministic_intent_rule": "no_rules"}
    return {"player_input_kind": "unclear", "deterministic_intent_rule": "no_rules"}
