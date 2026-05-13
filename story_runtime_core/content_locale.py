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
    "default_player_intent_commit_flags",
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


def _normalize_room_direction_fragment(phrase: str, *, lang: str) -> str:
    """Strip common German/English path prefixes for ``action_toward_room`` templates."""
    p = (phrase or "").strip().rstrip(".").strip()
    if not p:
        return ""
    low = p.lower()
    lg = (lang or "de").strip().lower()[:2] or "de"
    prefs = (
        (
            "in die ",
            "in das ",
            "in den ",
            "in der ",
            "ins ",
            "in ",
            "zur ",
            "zum ",
            "nach ",
            "zu ",
            "auf die ",
            "auf das ",
        )
        if lg == "de"
        else ("to the ", "to ", "toward ", "towards ", "into ", "in ")
    )
    for pref in prefs:
        if low.startswith(pref):
            p = p[len(pref) :].strip()
            low = p.lower()
            break
    if not p:
        return (phrase or "").strip().rstrip(".")
    return p[0].upper() + p[1:] if len(p) > 1 else p.upper()


# Kinds for which rendering raw input as quoted speech is permitted.
_SPEECH_PROJECTION_KINDS: frozenset[str] = frozenset(
    {"speech", "question", "social_speech_action"}
)


def build_player_attributed_visible_line(
    *,
    name: str,
    raw: str,
    input_kind: str,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
    projection_key: str | None = None,
    projection_captures: dict[str, Any] | None = None,
) -> str:
    """Diegetic one-line shell outcome for committed human input (speech / action / mixed).

    When ``projection_key`` is set (from ``player_input_rules.yaml`` classification), the
    template is resolved from module locale with ``name``/``raw`` plus any captures.
    """
    raw_s = str(raw or "").strip()
    pk = str(projection_key or "").strip()
    caps = dict(projection_captures or {})
    if pk:
        if "speech" in caps and str(caps.get("speech") or "").strip():
            caps.setdefault("raw", str(caps["speech"]).strip())
        if "room" in caps and str(caps.get("room") or "").strip():
            caps["room"] = _normalize_room_direction_fragment(str(caps["room"]), lang=lang)
        merged: dict[str, Any] = {"name": name, "raw": raw_s, **caps}
        return resolve_string(
            module_id,
            pk,
            lang,
            content_modules_root=content_modules_root,
            **merged,
        )
    ik = str(input_kind or "speech").strip().lower()
    # intent_only / reaction are verbal-intent kinds — keep as speech.
    # ambiguous must NOT collapse to speech; it needs its own non-dialogue surface.
    if ik in ("intent_only", "reaction"):
        ik = "speech"
    is_question = raw_s.rstrip().endswith("?")
    if ik in _SPEECH_PROJECTION_KINDS:
        key = "player_outcome.speech_question" if (is_question or ik == "question") else "player_outcome.speech_statement"
    elif ik in ("action", "perception", "movement_action", "perception_action"):
        key = "player_outcome.action_display"
    elif ik == "mixed":
        key = "player_outcome.mixed_display"
    elif ik == "object_interaction":
        key = "player_outcome.object_take"
    elif ik in ("social_nonverbal_action",):
        key = "player_outcome.action_display"
    elif ik in ("physical_action", "hostile_action"):
        key = "player_outcome.physical_action_attempt"
    elif ik in ("wait_or_observe",):
        key = "player_outcome.wait_or_observe"
    elif ik == "ambiguous":
        key = "player_outcome.ambiguous_action"
    else:
        # unclear / unknown / meta — use action_display (no dialogue quotes)
        key = "player_outcome.action_display"
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


def default_player_intent_commit_flags(player_input_kind: str) -> dict[str, bool]:
    """Public helper: booleans aligned with PLAYER-ACTION-INTENT-01 commit expectations."""
    d = _intent_defaults_from_kind(player_input_kind)
    return {k: bool(d[k]) for k in d}


def _intent_defaults_from_kind(player_input_kind: str) -> dict[str, Any]:
    k = (player_input_kind or "").strip().lower()
    if k in ("action", "movement_action"):
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k in ("perception", "perception_action"):
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k in ("mixed", "mixed_action_speech"):
        return {
            "player_action_committed": True,
            "player_speech_committed": True,
            "narrator_response_expected": True,
            "npc_response_expected": True,
        }
    if k in ("speech", "question", "meta"):
        return {
            "player_action_committed": False,
            "player_speech_committed": True,
            "narrator_response_expected": False,
            "npc_response_expected": True,
        }
    if k == "social_speech_action":
        return {
            "player_action_committed": True,
            "player_speech_committed": True,
            "narrator_response_expected": False,
            "npc_response_expected": True,
        }
    if k == "social_nonverbal_action":
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": False,
            "npc_response_expected": True,
        }
    if k == "object_interaction":
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k in ("physical_action", "hostile_action"):
        return {
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k == "wait_or_observe":
        return {
            "player_action_committed": False,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    if k == "ambiguous":
        return {
            "player_action_committed": False,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    return {
        "player_action_committed": False,
        "player_speech_committed": False,
        "narrator_response_expected": True,
        "npc_response_expected": True,
    }


def _no_rule_result(rule_id: str) -> dict[str, Any]:
    return {
        "player_input_kind": "unclear",
        "semantic_category": "unclear",
        "speech_projection_allowed": False,
        "deterministic_intent_rule": rule_id,
        "projection_key": None,
        "captures": {},
        **_intent_defaults_from_kind("unclear"),
    }


def classify_player_input_from_rules(
    raw_text: str,
    *,
    module_id: str,
    lang_hint: str = "de",
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    """First-match ordered rules from ``player_input_rules.yaml`` (PLAYER-ACTION-INTENT-01)."""
    root = resolve_content_modules_root(content_modules_root)
    rules = _load_player_rules_cached(str(_player_rules_path(module_id, root)))
    cls = rules.get("classification_rules")
    if not isinstance(cls, list) or not cls:
        return _no_rule_result("no_rules")
    lg = (lang_hint or "de").strip().lower()[:2] or "de"
    text = str(raw_text or "").strip()
    if not text:
        return _no_rule_result("no_rule_match")
    for row in cls:
        if not isinstance(row, dict):
            continue
        wl = str(row.get("when_lang") or row.get("scope_lang") or "").strip().lower()[:2]
        if wl and wl != lg:
            continue
        pat = row.get("pattern") or row.get("match")
        if isinstance(pat, dict):
            pat = pat.get(lg) or pat.get("de") or pat.get("en")
        if not isinstance(pat, str) or not pat.strip():
            continue
        try:
            m = re.match(pat.strip(), text)
        except re.error:
            continue
        if not m:
            continue
        then = row.get("then") if isinstance(row.get("then"), dict) else {}
        captures: dict[str, str] = {}
        cg = then.get("capture_groups")
        if isinstance(cg, dict):
            for cap_name, idx in cg.items():
                if not isinstance(cap_name, str):
                    continue
                gi: int | None = None
                if isinstance(idx, int):
                    gi = idx
                elif isinstance(idx, str) and idx.isdigit():
                    gi = int(idx)
                if gi is None or gi < 1 or gi > len(m.groups()):
                    continue
                gval = m.group(gi)
                captures[cap_name] = (str(gval) if gval is not None else "").strip()
        rid = str(row.get("id") or "matched_rule")
        pik = str(then.get("player_input_kind") or "unclear").strip().lower()
        pk = str(then.get("projection_key") or "").strip() or None
        out: dict[str, Any] = {
            "player_input_kind": pik,
            "semantic_category": pik,
            "speech_projection_allowed": pik in _SPEECH_PROJECTION_KINDS,
            "deterministic_intent_rule": rid,
            "projection_key": pk,
            "captures": captures,
        }
        for fld in (
            "player_action_committed",
            "player_speech_committed",
            "narrator_response_expected",
            "npc_response_expected",
        ):
            if fld in then:
                out[fld] = bool(then.get(fld))
            else:
                d = _intent_defaults_from_kind(pik)
                out[fld] = d[fld]
        # STAGING-OPENING-LOCALE-LDSS-AND-ACTION-CONTEXT-REPAIR-01 P5: pass-through
        # for movement_return_intent and other rule-level metadata flags that downstream
        # affordance resolvers consume. Keep the surface explicit, not wildcard, so the
        # contract is auditable.
        for optional_flag in ("movement_return_intent",):
            if optional_flag in then:
                out[optional_flag] = bool(then.get(optional_flag))
        return out
    return _no_rule_result("no_rule_match")
