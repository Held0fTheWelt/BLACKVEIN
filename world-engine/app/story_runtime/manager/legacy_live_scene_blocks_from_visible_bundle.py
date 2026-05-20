"""Legacy live-scene block facade.

Exports compatibility live-scene block extraction from visible bundles while the original method remains chunked.
"""
from __future__ import annotations

import sys

from ._deps import *
from ._legacy_loader import exec_top_level

exec_top_level(__name__, '_live_scene_blocks_from_visible_bundle')
_live_scene_blocks_from_visible_bundle_impl = _live_scene_blocks_from_visible_bundle


def _live_scene_blocks_from_visible_bundle(*args, **kwargs):
    package = sys.modules.get("app.story_runtime.manager")
    target = getattr(package, "_live_scene_blocks_from_visible_bundle", None) if package is not None else None
    if target is not None and target is not _live_scene_blocks_from_visible_bundle:
        return target(*args, **kwargs)
    return _live_scene_blocks_from_visible_bundle_impl(*args, **kwargs)


__all__ = [
    "_live_scene_blocks_from_visible_bundle",
    "_live_scene_blocks_from_visible_bundle_impl",
]
