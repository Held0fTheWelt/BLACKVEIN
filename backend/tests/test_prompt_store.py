"""Prompt Store service and API tests."""

from __future__ import annotations

import json

from app.extensions import db
from app.models import PromptStorePrompt
from app.services.prompts.prompt_store_service import seed_prompt_store_from_files


def _write_prompt_seed(root, *, template: str = "Hello {name}", seed_version: str = "test.v1") -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "prompt_collection.v1",
        "seed_version": seed_version,
        "prompts": [
            {
                "prompt_key": "test.prompt",
                "name": "Test Prompt",
                "category": "tests",
                "prompt_type": "runtime_fragment",
                "domain": "ai_stack",
                "tags": ["runtime", "test"],
                "description": "A prompt used by Prompt Store tests.",
                "template": template,
                "variables": ["name"],
                "source_path": "tests/prompt_store",
                "source_symbol": "TEST_PROMPT",
                "metadata": {"domain": "test"},
            }
        ],
    }
    (root / "test_prompts.json").write_text(json.dumps(payload), encoding="utf-8")


def test_seed_prompt_store_preserves_live_edits_by_default(app, tmp_path):
    _write_prompt_seed(tmp_path, template="Hello {name}")
    with app.app_context():
        first = seed_prompt_store_from_files(root=tmp_path, actor="test")
        assert first["inserted"] == 1
        row = db.session.get(PromptStorePrompt, "test.prompt")
        assert row is not None
        row.template = "Live edited {name}"
        db.session.commit()

        _write_prompt_seed(tmp_path, template="Seed changed {name}", seed_version="test.v2")
        preserved = seed_prompt_store_from_files(root=tmp_path, actor="test", overwrite=False)
        assert preserved["skipped_existing"] == 1
        assert db.session.get(PromptStorePrompt, "test.prompt").template == "Live edited {name}"

        overwritten = seed_prompt_store_from_files(root=tmp_path, actor="test", overwrite=True)
        assert overwritten["updated"] == 1
        row = db.session.get(PromptStorePrompt, "test.prompt")
        assert row.template == "Seed changed {name}"
        assert row.seed_version == "test.v2"


def test_prompt_store_admin_routes_seed_list_update_and_bundle(app, client, admin_headers, tmp_path):
    _write_prompt_seed(tmp_path, template="Hello {name}")
    app.config["WOS_PROMPT_STORE_DIR"] = str(tmp_path)
    app.config["INTERNAL_RUNTIME_CONFIG_TOKEN"] = "prompt-store-internal-token"

    seed_response = client.post("/api/v1/admin/prompt-store/seed", json={}, headers=admin_headers)
    assert seed_response.status_code == 200
    assert seed_response.get_json()["data"]["inserted"] == 1

    list_response = client.get("/api/v1/admin/prompt-store/prompts", headers=admin_headers)
    assert list_response.status_code == 200
    prompts = list_response.get_json()["data"]["prompts"]
    assert prompts[0]["prompt_key"] == "test.prompt"
    assert prompts[0]["prompt_type"] == "runtime_fragment"
    assert prompts[0]["domain"] == "ai_stack"
    assert "test" in prompts[0]["tags"]
    assert "template" not in prompts[0]

    update_response = client.patch(
        "/api/v1/admin/prompt-store/prompts/test.prompt",
        json={
            "name": "Edited Prompt",
            "description": "Edited in the admin UI.",
            "category": "edited",
            "prompt_type": "runtime_prompt",
            "domain": "world_engine",
            "tags": ["edited"],
            "template": "Good evening {name}",
            "variables": ["name"],
            "is_active": True,
        },
        headers=admin_headers,
    )
    assert update_response.status_code == 200
    edited = update_response.get_json()["data"]["prompt"]
    assert edited["name"] == "Edited Prompt"
    assert edited["prompt_type"] == "runtime_prompt"
    assert edited["domain"] == "world_engine"
    assert edited["tags"] == ["edited"]
    assert edited["template"] == "Good evening {name}"
    assert edited["current_content_hash"] != edited["seed_content_hash"]

    forbidden = client.get("/api/v1/internal/prompt-store/bundle")
    assert forbidden.status_code == 403

    bundle_response = client.get(
        "/api/v1/internal/prompt-store/bundle",
        headers={"X-Internal-Config-Token": "prompt-store-internal-token"},
    )
    assert bundle_response.status_code == 200
    bundle = bundle_response.get_json()["data"]
    assert bundle["count"] == 1
    assert bundle["prompts"][0]["template"] == "Good evening {name}"


def test_prompt_store_update_rejects_invalid_variables(client, admin_headers, app, tmp_path):
    _write_prompt_seed(tmp_path)
    app.config["WOS_PROMPT_STORE_DIR"] = str(tmp_path)
    client.post("/api/v1/admin/prompt-store/seed", json={}, headers=admin_headers)

    response = client.patch(
        "/api/v1/admin/prompt-store/prompts/test.prompt",
        json={"variables": "name"},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "prompt_value_invalid"


def test_prompt_store_list_filters_by_type_domain_tag_and_drift(app, client, admin_headers, tmp_path):
    _write_prompt_seed(tmp_path, template="Hello {name}")
    app.config["WOS_PROMPT_STORE_DIR"] = str(tmp_path)
    client.post("/api/v1/admin/prompt-store/seed", json={}, headers=admin_headers)
    client.patch(
        "/api/v1/admin/prompt-store/prompts/test.prompt",
        json={"template": "Edited {name}"},
        headers=admin_headers,
    )

    response = client.get(
        "/api/v1/admin/prompt-store/prompts?prompt_type=runtime_fragment&domain=ai_stack&tag=test&drift=edited",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.get_json()["data"]
    assert data["count"] == 1
    assert data["prompts"][0]["prompt_key"] == "test.prompt"
    assert "runtime_fragment" in data["prompt_types"]
    assert "ai_stack" in data["domains"]
    assert "test" in data["tags"]
