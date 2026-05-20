"""Content language helpers.

Determines session language surfaces and localized content hints used by narrator and player-visible outputs.
"""
from __future__ import annotations

from ._deps import *

logger = logging.getLogger(__name__)

SESSION_LOOP_LOG_POLICY_VERSION = "session_loop_logging.v1"

SESSION_LOOP_LOG_EVENT_VERSION = "session_loop_log_event.v1"

DEFAULT_SESSION_LANGUAGE = "de"

SESSION_LOOP_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

def _goc_content_modules_root() -> Path:
    return resolve_wos_repo_root() / "content" / "modules"

def _language_code(value: Any, *, fallback: str | None = None) -> str | None:
    text = str(value or "").strip().lower()
    if not text:
        text = str(fallback or "").strip().lower()
    return text[:2] or None

def _read_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}

def _module_authoring_language(
    *,
    module_id: str,
    runtime_projection: dict[str, Any] | None = None,
    content_provenance: dict[str, Any] | None = None,
) -> str:
    """Resolve the module/source language used for no-op output realization."""

    for container in (runtime_projection, content_provenance):
        if not isinstance(container, dict):
            continue
        for key in (
            "module_authoring_language",
            "module_language",
            "content_language",
            "authoring_language",
        ):
            lang = _language_code(container.get(key))
            if lang:
                return lang

    module_dir = _goc_content_modules_root() / str(module_id or "").strip()
    for rel_path in (
        "phase_beat_policy.yaml",
        "canonical_path/index.yaml",
        "direction/opening_sequence.yaml",
        "module.yaml",
    ):
        payload = _read_yaml_dict(module_dir / rel_path)
        lang = _language_code(payload.get("authoring_language"))
        if not lang:
            for section in (
                "phase_beat_policy",
                "canonical_path",
                "opening_sequence",
                "module",
                "content",
            ):
                nested = payload.get(section)
                if isinstance(nested, dict):
                    lang = _language_code(nested.get("authoring_language"))
                    if lang:
                        break
        if not lang and isinstance(payload.get("metadata"), dict):
            lang = _language_code(payload["metadata"].get("authoring_language"))
        if not lang and isinstance(payload.get("content"), dict):
            lang = _language_code(payload["content"].get("authoring_language"))
        if lang:
            return lang
    return DEFAULT_SESSION_LANGUAGE

def _short_sentence(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if not text:
        return ""
    head = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip()
    return head.rstrip(".!?")

def _humanize_source_atom(value: Any) -> str:
    text = re.sub(r"[_\s]+", " ", str(value or "").strip())
    return text

def _compose_souffleuse_visible_source_text(block: dict[str, Any]) -> str:
    facts = block.get("source_facts") if isinstance(block.get("source_facts"), dict) else {}
    payload: dict[str, Any] = {}
    raw_text = str(block.get("text") or "").strip()
    if raw_text.startswith("{"):
        try:
            parsed = json.loads(raw_text)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {}
    identity = payload.get("identity") if isinstance(payload.get("identity"), dict) else {}
    name = _short_sentence(facts.get("character_name") or identity.get("name"))
    public_identity = _short_sentence(facts.get("character_public_identity"))
    baseline = _short_sentence(facts.get("character_baseline_attitude"))
    stance = (
        facts.get("character_situational_stance")
        if isinstance(facts.get("character_situational_stance"), dict)
        else payload.get("situational_stance")
        if isinstance(payload.get("situational_stance"), dict)
        else {}
    )
    atoms = [
        _humanize_source_atom(item)
        for item in (stance.get("stance_atoms") if isinstance(stance, dict) else [])
        if _humanize_source_atom(item)
    ]
    if public_identity and baseline:
        return f"{public_identity}. {baseline}."
    if public_identity:
        return f"{public_identity}."
    if baseline:
        return f"{baseline}."
    if name and atoms:
        return f"{name}: {', '.join(atoms[:3])}."
    if atoms:
        return f"{', '.join(atoms[:3]).capitalize()}."
    return raw_text

def _required_fact_map(required_facts: Any) -> dict[str, Any]:
    facts: dict[str, Any] = {}
    rows = required_facts if isinstance(required_facts, list) else [required_facts]
    for row in rows:
        if isinstance(row, dict):
            for key, value in row.items():
                facts[str(key).strip()] = value
            continue
        text = str(row or "").strip()
        if not text:
            continue
        if ":" in text:
            key, value = text.split(":", 1)
            facts[key.strip()] = value.strip().strip("\"'")
        else:
            facts[text] = True
    return facts

def _scripted_quote(text: str, *, language: str) -> str:
    body = str(text or "").strip()
    if not body:
        return ""
    if str(language or "").strip().lower()[:2] == "de":
        return f"„{body}“"
    return f"\"{body}\""

def _speech_token(value: Any, *, language: str) -> str:
    raw = str(value or "").strip()
    low = raw.lower()
    bare_low = low.strip("?.!,;: ")
    lang = str(language or "").strip().lower()[:2]
    if lang == "de":
        replacements = {
            "armed": "bewaffnet",
            "carrying": "trug",
            "was carrying a stick": "trug einen Stock",
            "with it": "damit",
            "was carrying": "trug",
            "january 11, 2:30 p.m.": "11. Januar, 14:30 Uhr",
            "swelling_and_bruise_upper_lip": "Schwellung und Bluterguss an der Oberlippe",
            "two_broken_incisors": "zwei gebrochene Schneidezähne",
            "nerve_injury_right_incisor": "eine Nervenverletzung am rechten Schneidezahn",
        }
    else:
        replacements = {
            "swelling_and_bruise_upper_lip": "swelling and bruising of the upper lip",
            "two_broken_incisors": "two broken incisors",
            "nerve_injury_right_incisor": "nerve damage to the right incisor",
        }
    if low in replacements:
        return replacements[low]
    if bare_low in replacements:
        suffix = raw[len(raw.rstrip("?.!,;: ")) :]
        return f"{replacements[bare_low]}{suffix}"
    if "_" in raw:
        return raw.replace("_", " ")
    return raw

def _actor_first_name(actor_ref: str) -> str:
    ident = goc_actor_identity(actor_ref)
    return (
        str(ident.get("first_name") or "").strip()
        or str(ident.get("name") or "").strip().split(" ", 1)[0]
        or str(actor_ref or "").strip().replace("_", " ").title()
    )

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
