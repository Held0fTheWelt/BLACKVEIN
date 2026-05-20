"""Legacy manager method bindings.

Attaches compatibility-loaded legacy methods to the runtime manager class without reopening the large pre-split manager file.
"""
from __future__ import annotations

from ._deps import *
from ._legacy_loader import load_source

_LEGACY_METHODS = ('_build_narrator_path_opening_state', '_finalize_committed_turn')

def install_legacy_methods(cls):
    for method_name in _LEGACY_METHODS:
        source = load_source("method:" + method_name)
        namespace = {}
        code = "from __future__ import annotations\nclass _MethodHost:\n" + source
        filename = f"app/story_runtime/manager/{{method_name}}.py"
        exec(compile(code, filename, "exec"), globals(), namespace)
        setattr(cls, method_name, getattr(namespace["_MethodHost"], method_name))
    return cls

__all__ = ["install_legacy_methods"]
