"""Manage-/Editor-Routen (DS-015)."""

from __future__ import annotations

from flask import Flask, render_template, redirect, url_for


def register_manage_routes(app: Flask) -> None:
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

    @app.route("/manage/mcp-operations")
    def manage_mcp_operations():
        """MCP operations cockpit: overview, activity, diagnostics, logs, actions (backend admin APIs via proxy)."""
        return render_template("manage/mcp_operations.html")
