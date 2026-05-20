"""Compatibility import for the AI-stack language I/O adapter.

The implementation lives in ``ai_stack.language_io.language_adapter``. Keep this
module as a narrow re-export while downstream packages migrate.
"""

from ai_stack.language_io.language_adapter import *  # noqa: F401,F403
