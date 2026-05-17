from __future__ import annotations

import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE = REPO_ROOT / "docker-compose.langfuse.yml"
BASE_COMPOSE = REPO_ROOT / "docker-compose.yml"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
LANGFUSE_ENV_EXAMPLE = REPO_ROOT / ".env.langfuse.example"
DOCKER_UP = REPO_ROOT / "docker-up.py"


def _service_block(text: str, service_name: str) -> str:
    marker = f"\n  {service_name}:\n"
    start = text.find(marker)
    if start == -1 and text.startswith(f"  {service_name}:\n"):
        start = 0
    assert start != -1, f"service {service_name!r} not found"
    remainder = text[start + len(marker) :]
    match = re.search(r"\n  [A-Za-z0-9_-]+:\n", remainder)
    end = start + len(marker) + match.start() if match else len(text)
    return text[start:end]


def test_langfuse_compose_declares_required_self_hosted_services() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    for service in (
        "langfuse-web",
        "langfuse-worker",
        "langfuse-postgres",
        "langfuse-clickhouse",
        "langfuse-minio",
        "langfuse-redis",
    ):
        assert f"  {service}:" in text

    assert "docker.io/langfuse/langfuse:3" in text
    assert "docker.io/langfuse/langfuse-worker:3" in text
    assert "CLICKHOUSE_URL: ${CLICKHOUSE_URL:-http://langfuse-clickhouse:8123}" in text
    assert "LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT: ${LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT:-http://langfuse-minio:9000}" in text


def test_langfuse_uses_dedicated_redis_and_does_not_expose_internal_databases() -> None:
    text = COMPOSE.read_text(encoding="utf-8")
    assert "REDIS_HOST: langfuse-redis" in text
    assert "--maxmemory-policy noeviction" in text
    assert "langfuse-redis-data" in text

    for service in ("langfuse-postgres", "langfuse-clickhouse", "langfuse-redis"):
        block = _service_block(text, service)
        assert "ports:" not in block


def test_runtime_langfuse_env_is_server_only() -> None:
    override = COMPOSE.read_text(encoding="utf-8")
    base = BASE_COMPOSE.read_text(encoding="utf-8")

    backend_block = _service_block(override, "backend")
    play_block = _service_block(override, "play-service")
    runtime_anchor = override[override.index("x-runtime-langfuse-env:") : override.index("services:")]
    assert "LANGFUSE_HOST" in runtime_anchor
    assert "LANGFUSE_SECRET_KEY" in runtime_anchor
    assert "WOS_LANGFUSE_LOCAL_EVIDENCE" in runtime_anchor
    assert "<<: *runtime-langfuse-env" in backend_block
    assert "<<: *runtime-langfuse-env" in play_block

    frontend_block = _service_block(base, "frontend")
    admin_block = _service_block(base, "administration-tool")
    forbidden = ("LANGFUSE_SECRET_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_HOST")
    assert "env_file:" not in frontend_block
    for token in forbidden:
        assert token not in frontend_block
        assert token not in admin_block


def test_runtime_provider_keys_are_not_injected_from_compose_env() -> None:
    base = BASE_COMPOSE.read_text(encoding="utf-8")

    for service in ("backend", "play-service"):
        block = _service_block(base, service)
        assert "OPENAI_API_KEY=${OPENAI_API_KEY}" not in block
        assert "OPENROUTER_API_KEY=${OPENROUTER_API_KEY}" not in block
        assert "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" not in block
        assert "HF_TOKEN=${HF_TOKEN}" not in block
        assert "OPENAI_API_KEY=" in block
        assert "OPENROUTER_API_KEY=" in block
        assert "ANTHROPIC_API_KEY=" in block


def test_env_examples_include_langfuse_placeholders_without_real_keys() -> None:
    example = ENV_EXAMPLE.read_text(encoding="utf-8")
    langfuse_example = LANGFUSE_ENV_EXAMPLE.read_text(encoding="utf-8")
    combined = example + "\n" + langfuse_example

    for key in (
        "LANGFUSE_HOST=http://langfuse-web:3000",
        "LANGFUSE_MCP_BASE_URL=http://localhost:3000",
        "LANGFUSE_PUBLIC_KEY=",
        "LANGFUSE_SECRET_KEY=",
        "NEXTAUTH_SECRET=CHANGEME",
        "SALT=CHANGEME",
        "ENCRYPTION_KEY=CHANGEME",
        "LANGFUSE_DB_PASSWORD=CHANGEME",
        "CLICKHOUSE_USER=langfuse",
        "CLICKHOUSE_PASSWORD=CHANGEME",
        "MINIO_ROOT_USER=langfuse",
        "MINIO_ROOT_PASSWORD=CHANGEME",
        "LANGFUSE_REDIS_PASSWORD=CHANGEME",
        "LANGFUSE_REDIS_TLS_ENABLED=false",
        "LANGFUSE_REDIS_KEY_PREFIX=langfuse:",
        "WOS_LANGFUSE_EVIDENCE_SCOPE=local_langfuse",
        "WOS_LANGFUSE_PROOF_LEVEL=local_only",
        "WOS_LANGFUSE_LIVE_OR_STAGING_EVIDENCE=false",
        "WOS_LANGFUSE_BOOTSTRAP_OVERWRITE=false",
    ):
        assert key in combined

    assert "pk-lf-" not in combined
    assert "sk-lf-" not in combined


def test_world_engine_persistence_env_supports_aead_json_without_local_key_generation() -> None:
    example = ENV_EXAMPLE.read_text(encoding="utf-8")
    base = BASE_COMPOSE.read_text(encoding="utf-8")
    docker_up = DOCKER_UP.read_text(encoding="utf-8")
    play_block = _service_block(base, "play-service")

    assert "RUN_STORE_BACKEND=json" in example
    assert "RUN_STORE_URL=" in example
    assert "WORLD_ENGINE_JSON_AEAD_KEY=" in example
    assert "WORLD_ENGINE_JSON_AEAD_KEY=__AUTO_GENERATED_DO_NOT_EDIT__" not in example

    assert "RUN_STORE_BACKEND=${RUN_STORE_BACKEND:-json}" in play_block
    assert "RUN_STORE_URL=${RUN_STORE_URL:-}" in play_block
    assert "WORLD_ENGINE_JSON_AEAD_KEY=${WORLD_ENGINE_JSON_AEAD_KEY:-}" in play_block

    assert '"WORLD_ENGINE_JSON_AEAD_KEY": 32' not in docker_up


def test_docker_up_has_first_class_langfuse_entrypoint() -> None:
    text = DOCKER_UP.read_text(encoding="utf-8")

    assert 'LANGFUSE_COMPOSE = REPO_ROOT / "docker-compose.langfuse.yml"' in text
    assert "--with-langfuse" in text
    assert "--no-langfuse" in text
    assert "WOS_DOCKER_WITH_LANGFUSE" in text
    assert "langfuse-up" in text
    assert "return True" in text
    assert "_bootstrap_gate_after_up(local_langfuse=_with_langfuse_enabled(args))" in text
    assert 'base_url = "http://langfuse-web:3000"' in text
    assert '"LANGFUSE_MCP_BASE_URL": "http://localhost:3000"' in text
    assert '"LANGFUSE_REDIS_PASSWORD": 24' in text
    assert '"overwrite_existing": _value_truthy(env_dict.get("WOS_LANGFUSE_BOOTSTRAP_OVERWRITE"))' in text


def test_docker_up_default_dry_run_includes_langfuse_override() -> None:
    result = subprocess.run(
        ["python", str(DOCKER_UP), "--dry-run", "up"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"-f {BASE_COMPOSE}" in result.stdout
    assert f"-f {COMPOSE}" in result.stdout
    assert "up -d --build" in result.stdout


def test_docker_up_no_langfuse_dry_run_excludes_override() -> None:
    result = subprocess.run(
        ["python", str(DOCKER_UP), "--no-langfuse", "--dry-run", "up"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert f"-f {BASE_COMPOSE}" in result.stdout
    assert f"-f {COMPOSE}" not in result.stdout
    assert "up -d --build" in result.stdout
