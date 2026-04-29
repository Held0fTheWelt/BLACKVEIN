"""MVP1 runtime profile resolver — God of Carnage solo experience identity.

Resolves ``god_of_carnage_solo`` as a profile-only object bound to the canonical
``god_of_carnage`` content module. Validates ``selected_player_role`` and produces
the handoff fields consumed by MVP 2 (human_actor_id, npc_actor_ids, actor_lanes).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Guest role slugs: the two Reilles who enter the apartment.
# Determined by narrative design (guests = selectable human roles).
# Actor IDs are verified against characters.yaml at runtime via _resolve_goc_content().
_GOC_GUEST_ROLE_SLUGS: frozenset[str] = frozenset({"annette", "alain"})

# Fallback values used when content file is unreachable (test isolation, container startup).
_GOC_CANONICAL_ACTORS_FALLBACK: list[str] = ["annette", "alain", "veronique", "michel"]
_GOC_CONTENT_HASH_FALLBACK: str = "sha256:fallback"


def _resolve_goc_content(*, allow_fallback: bool = False) -> tuple[list[str], str]:
    """Read canonical actor IDs and content hash from characters.yaml.

    Args:
        allow_fallback: If True, fall back to hardcoded values if file is unreachable (test isolation).
                       If False (default, live mode), raise error if content cannot be read.

    Returns (actor_ids, content_hash).

    Raises RuntimeProfileError if content cannot be read in live mode (FIX-004).
    """
    try:
        from app.repo_root import resolve_wos_repo_root
        import yaml  # pyyaml is in root pyproject.toml dependencies
        repo_root = resolve_wos_repo_root(start=Path(__file__).resolve().parent)
        chars_path = repo_root / "content" / "modules" / "god_of_carnage" / "characters.yaml"
        raw = chars_path.read_bytes()
        content_hash = f"sha256:{hashlib.sha256(raw).hexdigest()[:16]}"
        data = yaml.safe_load(raw) or {}
        actor_ids = list((data.get("characters") or {}).keys())
        if not actor_ids:
            return _GOC_CANONICAL_ACTORS_FALLBACK, content_hash
        return actor_ids, content_hash
    except Exception as exc:
        # FIX-004: Fail live profile resolution if canonical content is missing.
        if not allow_fallback:
            raise RuntimeProfileError(
                code="runtime_profile_not_content_module",
                message="Canonical content god_of_carnage/characters.yaml is missing or unreadable. "
                        "Runtime profile resolution requires canonical content authority.",
                cause=str(exc),
            )
        return _GOC_CANONICAL_ACTORS_FALLBACK, _GOC_CONTENT_HASH_FALLBACK


def _build_selectable_roles(actor_ids: list[str]) -> list[dict[str, str]]:
    """Build selectable player roles from content-resolved actor IDs."""
    return [
        {"role_slug": a, "canonical_actor_id": a, "display_name": a.capitalize()}
        for a in actor_ids if a in _GOC_GUEST_ROLE_SLUGS
    ]


_SELECTABLE_ROLE_SLUGS: frozenset[str] = _GOC_GUEST_ROLE_SLUGS


class RuntimeProfileError(ValueError):
    """Structured error for runtime profile resolution and validation failures."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), **self.details}


@dataclass
class SelectablePlayerRole:
    role_slug: str
    canonical_actor_id: str
    display_name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role_slug": self.role_slug,
            "canonical_actor_id": self.canonical_actor_id,
            "display_name": self.display_name,
        }


@dataclass
class RuntimeProfile:
    """Runtime profile: thin identity binding between a runtime profile id and canonical content.

    Does not own story truth (characters, scenes, relationships, etc.).
    All story truth resides in content/modules/god_of_carnage/.
    """

    runtime_profile_id: str
    content_module_id: str
    runtime_module_id: str
    runtime_mode: str
    requires_selected_player_role: bool
    selectable_player_roles: list[SelectablePlayerRole]
    profile_version: str
    forbidden_story_truth_fields: list[str] = field(default_factory=lambda: [
        "characters", "roles", "rooms", "props", "beats", "scenes",
        "relationships", "endings",
    ])

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": "runtime_profile.v1",
            "runtime_profile_id": self.runtime_profile_id,
            "content_module_id": self.content_module_id,
            "runtime_module_id": self.runtime_module_id,
            "runtime_mode": self.runtime_mode,
            "requires_selected_player_role": self.requires_selected_player_role,
            "selectable_player_roles": [r.to_dict() for r in self.selectable_player_roles],
            "forbidden_story_truth_fields": self.forbidden_story_truth_fields,
            "profile_version": self.profile_version,
        }

    def role_slug_to_canonical_actor_id(self, role_slug: str) -> str | None:
        for r in self.selectable_player_roles:
            if r.role_slug == role_slug:
                return r.canonical_actor_id
        return None


def resolve_runtime_profile(runtime_profile_id: str | None) -> RuntimeProfile:
    """Resolve a runtime profile id to its RuntimeProfile.

    Selectable roles and canonical actor list are resolved from
    content/modules/god_of_carnage/characters.yaml (FIX-007).
    Falls back to hardcoded list if file is unreachable.

    Raises RuntimeProfileError for missing or unknown profile ids.
    """
    if not runtime_profile_id or not runtime_profile_id.strip():
        raise RuntimeProfileError(
            code="runtime_profile_required",
            message="runtime_profile_id is required.",
        )
    rid = runtime_profile_id.strip()
    if rid != "god_of_carnage_solo":
        raise RuntimeProfileError(
            code="runtime_profile_not_found",
            message=f"Unknown runtime profile: {rid!r}. Registered profiles: ['god_of_carnage_solo'].",
            received=rid,
        )
    actor_ids, content_hash = _resolve_goc_content()
    selectable = _build_selectable_roles(actor_ids)
    return RuntimeProfile(
        runtime_profile_id="god_of_carnage_solo",
        content_module_id="god_of_carnage",
        runtime_module_id="solo_story_runtime",
        runtime_mode="solo_story",
        requires_selected_player_role=True,
        selectable_player_roles=[SelectablePlayerRole(**r) for r in selectable],
        profile_version="goc-solo.v1",
    )


def validate_selected_player_role(selected_player_role: str | None, profile: RuntimeProfile) -> str:
    """Validate the selected player role against the profile's allowed roles.

    Raises RuntimeProfileError for missing or invalid roles.
    Returns the validated role slug.
    """
    allowed = [r.role_slug for r in profile.selectable_player_roles]

    if not selected_player_role or not selected_player_role.strip():
        raise RuntimeProfileError(
            code="selected_player_role_required",
            message=(
                f"selected_player_role is required for runtime_profile_id={profile.runtime_profile_id!r}."
            ),
            allowed_values=allowed,
        )

    role = selected_player_role.strip()

    if role not in _SELECTABLE_ROLE_SLUGS:
        raise RuntimeProfileError(
            code="invalid_selected_player_role",
            message=(
                f"selected_player_role must be one of {allowed!r}, received: {role!r}."
            ),
            received=role,
            allowed_values=allowed,
        )

    canonical_id = profile.role_slug_to_canonical_actor_id(role)
    if canonical_id is None:
        raise RuntimeProfileError(
            code="selected_player_role_not_canonical_character",
            message=(
                f"selected_player_role {role!r} does not resolve to a canonical character "
                f"in content_module_id={profile.content_module_id!r}."
            ),
            role_slug=role,
            resolved_from_content=False,
        )

    return role


def build_actor_ownership(selected_player_role: str, profile: RuntimeProfile) -> dict[str, Any]:
    """Build human_actor_id, npc_actor_ids, and actor_lanes from selected role.

    Uses content-resolved canonical actors.
    """
    human_actor_id = profile.role_slug_to_canonical_actor_id(selected_player_role)
    if human_actor_id is None:
        raise RuntimeProfileError(
            code="selected_player_role_not_canonical_character",
            message=f"Role slug {selected_player_role!r} has no canonical actor mapping.",
        )

    # Resolve all canonical actors from content (FIX-007)
    canonical_actors, content_hash = _resolve_goc_content()
    npc_actor_ids = [a for a in canonical_actors if a != human_actor_id]

    actor_lanes: dict[str, str] = {human_actor_id: "human"}
    for npc_id in npc_actor_ids:
        actor_lanes[npc_id] = "npc"

    return {
        "human_actor_id": human_actor_id,
        "npc_actor_ids": npc_actor_ids,
        "actor_lanes": actor_lanes,
        "visitor_present": False,
        "content_hash": content_hash,
    }


def assert_profile_contains_no_story_truth(profile_dict: dict[str, Any]) -> None:
    """Validate that a profile dict contains none of the forbidden story truth fields.

    Raises RuntimeProfileError with code ``runtime_profile_contains_story_truth``
    if any forbidden field is present.
    """
    forbidden = profile_dict.get("forbidden_story_truth_fields") or RuntimeProfile.__dataclass_fields__[
        "forbidden_story_truth_fields"
    ].default_factory()
    found = [f for f in forbidden if f in profile_dict]
    if found:
        raise RuntimeProfileError(
            code="runtime_profile_contains_story_truth",
            message=(
                f"Runtime profile contains forbidden story truth fields: {found!r}. "
                "Story truth must reside in the canonical content module only."
            ),
            forbidden_fields_found=found,
        )


def assert_runtime_module_contains_no_story_truth(template: Any) -> None:
    """FIX-005: Validate that a runtime template (ExperienceTemplate) has no story truth.

    Checks that beats, actions, props lists are empty (derived from content, not authored here).
    Raises RuntimeProfileError with code ``runtime_module_contains_story_truth`` if violated.
    """
    violations = {}
    if hasattr(template, 'beats') and template.beats:
        violations['beats'] = len(template.beats)
    if hasattr(template, 'actions') and template.actions:
        violations['actions'] = len(template.actions)
    if hasattr(template, 'props') and template.props:
        violations['props'] = len(template.props)

    if violations:
        raise RuntimeProfileError(
            code="runtime_module_contains_story_truth",
            message=(
                f"Runtime template {getattr(template, 'id', '?')!r} owns story truth: {violations}. "
                "Beats, actions, and props must be derived from canonical content only."
            ),
            violations=violations,
        )
