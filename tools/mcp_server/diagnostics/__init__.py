"""Operational diagnostics for the wos-mcp server.

Single durable home for end-to-end probes of MCP-exposed tooling. Replaces
the ``scripts/_mcp_*.py`` ad-hoc throwaway scripts that proliferated while
diagnosing stdio-buffering and Cursor-naming issues.

Public surface kept intentionally small. Add new probes as their own modules
under this package, each exposing a single ``run_*_probe(...)`` entry plus a
CLI subcommand wired into :mod:`tools.mcp_server.diagnostics.__main__`.
"""

from tools.mcp_server.diagnostics.opening_quality import (
    Classification,
    ClassificationRow,
    OpeningQualityReport,
    run_opening_quality_probe,
)

__all__ = [
    "Classification",
    "ClassificationRow",
    "OpeningQualityReport",
    "run_opening_quality_probe",
]
