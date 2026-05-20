"""
Tag clusters and scene-function satisfaction for dramatic effect gate
(DS-008).
"""

from __future__ import annotations

_EFFECT_TAG_CLUSTERS: dict[str, tuple[str, ...]] = {
    "pressure_intensification": (
        "rage",
        "furious",
        "shout",
        "loud",
        "slam",
        "fight",
        "attack",
        "voice",
        "angry",
        "storm",
        "insult",
    ),
    "interpersonal_blame": (
        "blame",
        "fault",
        "accus",
        "your",
        "you",
        "responsib",
        "deny",
        "denial",
    ),
    "repair_gesture": ("sorry", "apolog", "peace", "calm", "truce", "repair", "stop"),
    "exposure_secret": ("truth", "secret", "reveal", "admit", "confess", "fact", "know", "knew", "hid"),
    "inquiry_probe": ("why", "motive", "reason", "explain", "justify", "because"),
    "ambient_pressure": ("tight", "quiet", "table", "room", "watch", "still", "wait", "look"),
    "silence_evade": ("silence", "nothing", "say", "hold", "still"),
    "pivot_shift": ("turn", "shift", "instead", "leave", "topic", "door", "stay", "here", "apartment", "dinner"),
    "alliance_network": ("side", "sides", "allied", "alliance", "against", "wife", "husband", "spouse"),
}

_SCENE_FUNCTION_TAG_GROUPS: dict[str, tuple[tuple[str, ...], ...]] = {
    "escalate_conflict": (("pressure_intensification", "interpersonal_blame"),),
    "redirect_blame": (("interpersonal_blame",),),
    "reveal_surface": (("exposure_secret",),),
    "probe_motive": (("inquiry_probe",),),
    "repair_or_stabilize": (("repair_gesture",),),
    "establish_pressure": (("ambient_pressure", "pressure_intensification", "interpersonal_blame"),),
    "withhold_or_evade": (("silence_evade", "ambient_pressure"),),
    "scene_pivot": (("pivot_shift",),),
}


def tag_active(low: str, tag: str) -> bool:
    """Describe what ``tag_active`` does in one line (verb-led summary for
    this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        low: ``low`` (str); meaning follows the type and call sites.
        tag: ``tag`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    clusters = _EFFECT_TAG_CLUSTERS.get(tag, ())
    return any(c in low for c in clusters)


def scene_function_tags_satisfied(low: str, scene_function: str) -> bool:
    """Describe what ``scene_function_tags_satisfied`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        low: ``low`` (str); meaning follows the type and call sites.
        scene_function: ``scene_function`` (str); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    groups = _SCENE_FUNCTION_TAG_GROUPS.get(scene_function)
    if not groups:
        return True
    for or_group in groups:
        if not any(tag_active(low, t) for t in or_group):
            return False
    return True
