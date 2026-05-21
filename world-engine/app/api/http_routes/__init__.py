"""World-engine HTTP route modules.

The public import surface remains ``app.api.http``; these modules keep the
route concerns separate while registering handlers on one shared router.
"""

from .common import router

__all__ = ["router"]
