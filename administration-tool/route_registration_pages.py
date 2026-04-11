"""Öffentliche Seiten und Forum (DS-015)."""

from __future__ import annotations

from flask import Flask, render_template


def register_public_and_forum_routes(app: Flask) -> None:
    @app.route("/")
    def index():
        """Public home page."""
        return render_template("index.html")

    @app.route("/news")
    def news_list():
        """Public news list page. Data loaded by JS from backend API."""
        return render_template("news.html")

    @app.route("/news/<int:news_id>")
    def news_detail(news_id):
        """Public news detail page. Data loaded by JS from backend API."""
        return render_template("news_detail.html", news_id=news_id)

    @app.route("/wiki")
    @app.route("/wiki/<path:slug>")
    def wiki_index(slug=None):
        """Public wiki page. Default slug 'wiki' for main page. Data loaded by JS from backend API."""
        return render_template("wiki_public.html", slug=slug or "wiki")

    @app.route("/forum")
    def forum_index():
        """Forum categories list. Data loaded by JS from backend API."""
        return render_template("forum/index.html")

    @app.route("/forum/categories/<slug>")
    def forum_category(slug):
        """Threads in a category. Data loaded by JS from backend API."""
        return render_template("forum/category.html", category_slug=slug)

    @app.route("/forum/threads/<slug>")
    def forum_thread(slug):
        """Thread detail and posts. Data loaded by JS from backend API."""
        return render_template("forum/thread.html", thread_slug=slug)

    @app.route("/forum/notifications")
    def forum_notifications():
        """Notifications list (requires login). Data loaded by JS from backend API."""
        return render_template("forum/notifications.html")

    @app.route("/forum/saved")
    def forum_saved_threads():
        """Saved threads / bookmarks list (requires login). Data loaded by JS from backend API."""
        return render_template("forum/saved_threads.html")

    @app.route("/users/<int:user_id>/profile")
    def user_profile(user_id):
        """User profile page. Data loaded by JS from backend API."""
        return render_template("user/profile.html", user_id=user_id)

    @app.route("/forum/tags/<slug>")
    def forum_tag_detail(slug):
        """Forum tag detail page with threads. Data loaded by JS from backend API."""
        return render_template("forum/tag_detail.html", tag_slug=slug)
