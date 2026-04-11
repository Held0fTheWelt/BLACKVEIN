"""God of Carnage solo builtin experience template (SSOT fragment).

Canonical dramatic YAML remains under content/modules/god_of_carnage/; this template
must stay title-aligned (VERTICAL_SLICE_CONTRACT_GOC).
"""

from __future__ import annotations

from .experience_template_models import (
    ExperienceKind,
    ExperienceTemplate,
    JoinPolicy,
)
from .goc_solo_builtin_catalog import (
    goc_solo_action_templates,
    goc_solo_beat_templates,
    goc_solo_prop_templates,
)
from .goc_solo_builtin_roles_rooms import goc_solo_role_templates, goc_solo_room_templates


def build_god_of_carnage_solo() -> ExperienceTemplate:
    # Secondary surface only: canonical dramatic source is content/modules/god_of_carnage/
    # (VERTICAL_SLICE_CONTRACT_GOC.md §6.1). Title must match YAML module title or runtime
    # emits scope_breach when host_experience_template is wired.
    return ExperienceTemplate(
        id="god_of_carnage_solo",
        title="God of Carnage",
        kind=ExperienceKind.SOLO_STORY,
        join_policy=JoinPolicy.OWNER_ONLY,
        summary=(
            "A authored single-adventure slice for a tense apartment confrontation. One human player"
            " enters a controlled dramatic scene that already uses the multiplayer runtime model,"
            " authored beats, props, and operational observability."
        ),
        max_humans=1,
        initial_beat_id="courtesy",
        tags=["authored", "single-adventure", "social-drama", "better-tomorrow"],
        roles=goc_solo_role_templates(),
        rooms=goc_solo_room_templates(),
        props=goc_solo_prop_templates(),
        actions=goc_solo_action_templates(),
        beats=goc_solo_beat_templates(),
    )
