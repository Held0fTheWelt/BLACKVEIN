from __future__ import annotations

from ._deps import *
from ._legacy_loader import exec_top_level

exec_top_level(__name__, '_record_visible_projection_aspect')


__all__ = ['_record_visible_projection_aspect']
