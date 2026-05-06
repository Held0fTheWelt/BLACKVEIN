"""``langchain_reviver_compat`` patches ``Reviver`` defaults for LangGraph serde."""
from __future__ import annotations

import warnings

from ai_stack.langchain_reviver_compat import ensure_langchain_reviver_explicit_core


def test_reviver_default_emits_no_allowed_objects_pending_warning() -> None:
    ensure_langchain_reviver_explicit_core()
    from langchain_core.load.load import Reviver

    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        Reviver()

    pending = [
        w
        for w in recorded
        if w.category.__name__ == "LangChainPendingDeprecationWarning"
        and "allowed_objects" in str(w.message)
    ]
    assert not pending, [str(w.message) for w in pending]
