"""Manage-/Editor-Routen (DS-015 facade; DS-016 section split)."""

from __future__ import annotations

from flask import Flask

from route_registration_manage_sections import (
    register_manage_data_ops_and_platform_pages,
    register_manage_entry_and_core_pages,
    register_manage_inspector_legacy_redirects,
    register_manage_narrative_governance_pages,
    register_manage_observability_pages,
    register_manage_research_governance_pages,
    register_manage_operational_governance_pages,
    register_manage_slogans_and_game_pages,
)


def register_manage_routes(app: Flask) -> None:
    register_manage_entry_and_core_pages(app)
    register_manage_slogans_and_game_pages(app)
    register_manage_inspector_legacy_redirects(app)
    register_manage_narrative_governance_pages(app)
    register_manage_data_ops_and_platform_pages(app)
    register_manage_research_governance_pages(app)
    register_manage_operational_governance_pages(app)
    register_manage_observability_pages(app)
