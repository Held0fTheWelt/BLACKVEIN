from __future__ import annotations

import pytest

from conftest import captured_templates


@pytest.mark.parametrize(
    ("path", "template_name"),
    [
        ("/", "index.html"),
        ("/news", "news.html"),
        ("/news/42", "news_detail.html"),
        ("/wiki", "wiki_public.html"),
        ("/wiki/lore/city", "wiki_public.html"),
        ("/forum", "forum/index.html"),
        ("/forum/categories/general", "forum/category.html"),
        ("/forum/threads/welcome", "forum/thread.html"),
        ("/forum/notifications", "forum/notifications.html"),
        ("/forum/saved", "forum/saved_threads.html"),
        ("/forum/tags/devlog", "forum/tag_detail.html"),
        ("/users/7/profile", "user/profile.html"),
        ("/manage", "manage/dashboard.html"),
        ("/manage/login", "manage/login.html"),
        ("/manage/news", "manage/news.html"),
        ("/manage/users", "manage/users.html"),
        ("/manage/roles", "manage/roles.html"),
        ("/manage/areas", "manage/areas.html"),
        ("/manage/feature-areas", "manage/feature_areas.html"),
        ("/manage/wiki", "manage/wiki.html"),
        ("/manage/slogans", "manage/slogans.html"),
        ("/manage/data", "manage/data.html"),
        ("/manage/forum", "manage/forum.html"),
        ("/manage/game-content", "manage/game_content.html"),
        ("/manage/game-operations", "manage/game_operations.html"),
        ("/manage/inspector-workbench", "manage/inspector_workbench.html"),
        ("/manage/diagnosis", "manage/diagnosis.html"),
        ("/manage/play-service-control", "manage/play_service_control.html"),
        ("/manage/analytics", "manage_analytics.html"),
        ("/manage/moderator-dashboard", "manage_moderator_dashboard.html"),
    ],
)
def test_html_routes_render_expected_templates(app, client, path: str, template_name: str):
    with captured_templates(app) as templates:
        response = client.get(path)

    assert response.status_code == 200
    assert templates, f"No template rendered for {path}"
    assert templates[-1][0] == template_name


def test_index_template_receives_frontend_context(app, client):
    with captured_templates(app) as templates:
        response = client.get("/?lang=en")

    assert response.status_code == 200
    _, context = templates[-1]
    assert context["backend_api_url"] == app.config["BACKEND_API_URL"]
    assert context["frontend_config"]["apiProxyBase"] == "/_proxy"
    assert context["frontend_config"]["currentLanguage"] == "en"
    assert context["supported_languages"] == ["de", "en"]
    assert isinstance(context["t"], dict)
