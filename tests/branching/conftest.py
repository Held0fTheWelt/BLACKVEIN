"""Branching test path setup — no sys.modules surgery needed.

world-engine's branching_turn_executor has no app.* dependencies, so it is
loaded directly by file path in the two test files that need it, bypassing
the app namespace conflict between backend/ and world-engine/ entirely.
"""
