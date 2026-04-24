"""Composable manage-area route registration (DS-016; split from `route_registration_manage`)."""

from __future__ import annotations

from flask import Flask, redirect, render_template, url_for


def register_manage_entry_and_core_pages(app: Flask) -> None:
    @app.route("/manage")
    def manage_index():
        """Management area entry; redirects to login or dashboard (news)."""
        return render_template("manage/dashboard.html")

    @app.route("/manage/login")
    def manage_login():
        """Management login page (JWT via backend API)."""
        return render_template("manage/login.html")

    @app.route("/manage/news")
    def manage_news():
        """News management (list, create, edit, publish, unpublish, delete)."""
        return render_template("manage/news.html")

    @app.route("/manage/users")
    def manage_users():
        """User administration (admin only; table, edit, role, role_level, ban, unban)."""
        return render_template("manage/users.html")

    @app.route("/manage/roles")
    def manage_roles():
        """Role management (admin only): list, create, edit, delete roles."""
        return render_template("manage/roles.html")

    @app.route("/manage/areas")
    def manage_areas():
        """Area management (admin only): list, create, edit, delete areas."""
        return render_template("manage/areas.html")

    @app.route("/manage/feature-areas")
    def manage_feature_areas():
        """Feature/view to area access mapping (admin only)."""
        return render_template("manage/feature_areas.html")

    @app.route("/manage/wiki")
    def manage_wiki():
        """Wiki editor (markdown source, preview, save)."""
        return render_template("manage/wiki.html")


def register_manage_slogans_and_game_pages(app: Flask) -> None:
    @app.route("/manage/slogans")
    def manage_slogans():
        """Slogan management (moderator+): CRUD, activate/deactivate, placement resolution."""
        return render_template("manage/slogans.html")

    @app.route("/manage/game/content")
    def manage_game_content():
        """Authored game content management for experiences, publishing, and inspection."""
        return render_template("manage/game_content.html")

    @app.route("/manage/game-content")
    def manage_game_content_alt():
        """Authored game content management for experiences, publishing, and inspection (alternate URL)."""
        return render_template("manage/game_content.html")

    @app.route("/manage/game/operations")
    def manage_game_operations():
        """Runtime operations dashboard for active runs and transcripts."""
        return render_template("manage/game_operations.html")

    @app.route("/manage/game-operations")
    def manage_game_operations_alt():
        """Runtime operations dashboard for active runs and transcripts (alternate URL)."""
        return render_template("manage/game_operations.html")


def register_manage_inspector_legacy_redirects(app: Flask) -> None:
    @app.route("/manage/inspector-workbench")
    def manage_inspector_workbench():
        """Canonical unified Inspector Suite workbench."""
        return render_template("manage/inspector_workbench.html")

    @app.route("/manage/ai-stack/governance")
    def manage_ai_stack_governance():
        """Legacy path redirected permanently to canonical Inspector workbench."""
        return redirect(url_for("manage_inspector_workbench"), code=308)

    @app.route("/manage/ai-stack-governance")
    def manage_ai_stack_governance_alt():
        """Legacy alias redirected permanently to canonical Inspector workbench."""
        return redirect(url_for("manage_inspector_workbench"), code=308)

    @app.route("/manage/inspector-suite")
    def manage_inspector_suite():
        """Legacy path redirected permanently to canonical Inspector workbench."""
        return redirect(url_for("manage_inspector_workbench"), code=308)

    @app.route("/manage/inspector-suite/turn")
    def manage_inspector_suite_turn():
        """Legacy alias redirected permanently to canonical Inspector workbench."""
        return redirect(url_for("manage_inspector_workbench"), code=308)


def register_manage_narrative_governance_pages(app: Flask) -> None:
    @app.route("/manage/narrative/overview")
    def manage_narrative_overview():
        """Narrative governance overview page."""
        return render_template("manage/narrative_governance/overview.html")

    @app.route("/manage/narrative/runtime")
    def manage_narrative_runtime():
        """Narrative governance runtime configuration page."""
        return render_template("manage/narrative_governance/runtime.html")

    @app.route("/manage/narrative/runtime-health")
    def manage_narrative_runtime_health():
        """Narrative governance runtime health page."""
        return render_template("manage/narrative_governance/runtime_health.html")

    @app.route("/manage/narrative/packages")
    def manage_narrative_packages():
        """Narrative governance packages page."""
        return render_template("manage/narrative_governance/packages.html")

    @app.route("/manage/narrative/policies")
    def manage_narrative_policies():
        """Narrative governance policies page."""
        return render_template("manage/narrative_governance/policies.html")

    @app.route("/manage/narrative/findings")
    def manage_narrative_findings():
        """Narrative governance findings page."""
        return render_template("manage/narrative_governance/findings.html")

    @app.route("/manage/narrative/revisions")
    def manage_narrative_revisions():
        """Narrative governance revisions page."""
        return render_template("manage/narrative_governance/revisions.html")

    @app.route("/manage/narrative/evaluations")
    def manage_narrative_evaluations():
        """Narrative governance evaluations page."""
        return render_template("manage/narrative_governance/evaluations.html")

    @app.route("/manage/narrative/notifications")
    def manage_narrative_notifications():
        """Narrative governance notifications page."""
        return render_template("manage/narrative_governance/notifications.html")


def register_manage_data_ops_and_platform_pages(app: Flask) -> None:
    @app.route("/manage/data")
    def manage_data():
        """Data export/import (admin only)."""
        return render_template("manage/data.html")

    @app.route("/manage/forum")
    def manage_forum():
        """Forum management (moderation, categories, reports)."""
        return render_template("manage/forum.html")

    @app.route("/manage/analytics")
    def manage_analytics():
        """Community analytics dashboard."""
        return render_template("manage_analytics.html")

    @app.route("/manage/moderator-dashboard")
    def manage_moderator_dashboard():
        """Moderator dashboard with queue and recent actions."""
        return render_template("manage_moderator_dashboard.html")

    @app.route("/manage/diagnosis")
    def manage_diagnosis():
        """Aggregated system diagnosis for operators (backend GET /api/v1/admin/system-diagnosis)."""
        return render_template("manage/diagnosis.html")

    @app.route("/manage/play-service-control")
    def manage_play_service_control():
        """Application-level Play-Service desired state, test, and apply (backend admin APIs via proxy)."""
        return render_template("manage/play_service_control.html")

    @app.route("/manage/world-engine-console")
    def manage_world_engine_console():
        """World Engine diagnostic and operator console (backend JWT proxy to play service)."""
        return render_template("manage/world_engine_console.html")

    @app.route("/manage/world-engine-control-center")
    def manage_world_engine_control_center():
        """Canonical World-Engine Control Center (aggregated posture + safe controls)."""
        return render_template("manage/world_engine_control_center.html")

    @app.route("/manage/mcp-operations")
    def manage_mcp_operations():
        """MCP operations cockpit: overview, activity, diagnostics, logs, actions (backend admin APIs via proxy)."""
        return render_template("manage/mcp_operations.html")


def register_manage_research_governance_pages(app: Flask) -> None:
    """Strategic research-domain visibility (layered governance; not a full research IDE)."""

    @app.route("/manage/research/overview")
    def manage_research_overview():
        return render_template("manage/research_governance/overview.html")

    @app.route("/manage/research/source-intake")
    def manage_research_source_intake():
        return render_template("manage/research_governance/source_intake.html")

    @app.route("/manage/research/extraction-tuning")
    def manage_research_extraction_tuning():
        return render_template("manage/research_governance/extraction_tuning.html")

    @app.route("/manage/research/findings")
    def manage_research_findings():
        return render_template("manage/research_governance/findings.html")

    @app.route("/manage/research/canonical-truth")
    def manage_research_canonical_truth():
        return render_template("manage/research_governance/canonical_truth.html")

    @app.route("/manage/research/mcp-workbench")
    def manage_research_mcp_workbench():
        return render_template("manage/research_governance/mcp_workbench.html")


def register_manage_operational_governance_pages(app: Flask) -> None:
    @app.route("/manage/ai-runtime-governance")
    def manage_ai_runtime_governance():
        """Canonical AI Runtime Governance control plane."""
        return render_template("manage/operational_governance.html", active_section="overview")

    @app.route("/manage/operational-governance")
    def manage_operational_governance():
        """Operational settings and AI runtime governance dashboard."""
        return render_template("manage/operational_governance.html", active_section="overview")

    @app.route("/manage/operational-governance/bootstrap")
    def manage_operational_governance_bootstrap():
        """Bootstrap and trust-anchor operational controls."""
        return render_template("manage/operational_governance.html", active_section="bootstrap")

    @app.route("/manage/operational-governance/providers")
    def manage_operational_governance_providers():
        """Provider governance controls."""
        return render_template("manage/operational_governance.html", active_section="providers")

    @app.route("/manage/operational-governance/models")
    def manage_operational_governance_models():
        """Model governance controls."""
        return render_template("manage/operational_governance.html", active_section="models")

    @app.route("/manage/operational-governance/routes")
    def manage_operational_governance_routes():
        """Task route governance controls."""
        return render_template("manage/operational_governance.html", active_section="routes")

    @app.route("/manage/operational-governance/runtime")
    def manage_operational_governance_runtime():
        """Runtime mode and resolved config controls."""
        return render_template("manage/operational_governance.html", active_section="runtime")

    @app.route("/manage/operational-governance/costs")
    def manage_operational_governance_costs():
        """Cost, usage, and budget controls."""
        return render_template("manage/operational_governance.html", active_section="costs")

    @app.route("/manage/ai-stack/release-readiness")
    def manage_ai_stack_release_readiness():
        """AI Stack release readiness gates dashboard."""
        return render_template("manage/ai_stack_release_readiness.html")

    @app.route("/manage/runtime-dashboard")
    def manage_runtime_dashboard():
        """Unified AI/runtime dashboard with blocker-first operator summary."""
        return render_template("manage/runtime_dashboard.html")

    @app.route("/manage/rag-operations")
    def manage_rag_operations():
        """RAG operations console for retrieval diagnostics and safe actions."""
        return render_template("manage/rag_operations.html")

    @app.route("/manage/ai-orchestration")
    def manage_ai_orchestration():
        """AI orchestration console for LangGraph and LangChain runtime visibility."""
        return render_template("manage/ai_orchestration.html")

    @app.route("/manage/runtime-settings")
    def manage_runtime_settings():
        """Controlled presets and bounded advanced runtime settings."""
        return render_template("manage/runtime_settings.html")

    @app.route("/manage/runtime/config-truth")
    def manage_runtime_config_truth():
        """Runtime configuration truth — configured vs. effective vs. loaded."""
        return render_template("manage/runtime_config_truth.html")


def register_manage_observability_pages(app: Flask) -> None:
    @app.route("/manage/observability-settings")
    def manage_observability_settings():
        """Langfuse observability service configuration (admin-only)."""
        return render_template("manage/observability_settings.html")

    @app.route("/manage/observability-settings/langfuse")
    def manage_observability_langfuse():
        """Langfuse observability service configuration (alternate URL)."""
        return render_template("manage/observability_settings.html")
