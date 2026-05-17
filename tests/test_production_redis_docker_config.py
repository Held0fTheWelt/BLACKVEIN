from __future__ import annotations

import importlib.util
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION_COMPOSE = REPO_ROOT / "docker-compose.redis-production.yml"
DOCKER_UP = REPO_ROOT / "docker-up.py"
ENV_EXAMPLE = REPO_ROOT / ".env.example"


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


def _load_docker_up_module():
    spec = importlib.util.spec_from_file_location("docker_up_under_test", DOCKER_UP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_production_redis_compose_enforces_tls_acl_and_separate_instances() -> None:
    text = PRODUCTION_COMPOSE.read_text(encoding="utf-8")

    app_redis = _service_block(text, "redis")
    langfuse_redis = _service_block(text, "langfuse-redis")
    backend = _service_block(text, "backend")
    langfuse_web = _service_block(text, "langfuse-web")
    langfuse_worker = _service_block(text, "langfuse-worker")

    for block in (app_redis, langfuse_redis):
        assert "--port" in block
        assert "--tls-port" in block
        assert "--aclfile" in block
        assert "/usr/local/etc/redis/users.acl" in block
        assert "ports:" not in block

    assert "APP_REDIS_URL" in backend
    assert "./.docker/redis-production/app-users.acl" in app_redis
    assert "./.docker/redis-production/langfuse-users.acl" in langfuse_redis
    assert "maxmemory-policy" in langfuse_redis

    for block in (langfuse_web, langfuse_worker):
        assert "REDIS_CONNECTION_STRING" in block
        assert "REDIS_USERNAME" in block
        assert 'REDIS_TLS_ENABLED: "true"' in block
        assert "REDIS_TLS_CA_PATH: /certs/langfuse-redis/ca.crt" in block
        assert 'REDIS_TLS_REJECT_UNAUTHORIZED: "true"' in block


def test_docker_up_exposes_production_redis_commands_and_generation_contract() -> None:
    text = DOCKER_UP.read_text(encoding="utf-8")

    assert 'REDIS_PRODUCTION_COMPOSE = REPO_ROOT / "docker-compose.redis-production.yml"' in text
    assert "--production-redis" in text
    assert "init-production-redis" in text
    assert "validate-production-redis" in text
    assert "production-redis-up" in text
    assert "WOS_DOCKER_PRODUCTION_REDIS" in text
    assert "APP_REDIS_PASSWORD" in text
    assert "LANGFUSE_REDIS_PASSWORD" in text
    assert "user default off" in text
    assert "rediss://" in text


def test_env_example_contains_production_redis_placeholders() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    for key in (
        "APP_REDIS_USERNAME=wos_app",
        "APP_REDIS_PASSWORD=CHANGEME",
        "APP_REDIS_URL=",
        "APP_REDIS_TLS_ENABLED=false",
        "LANGFUSE_REDIS_USERNAME=",
        "LANGFUSE_REDIS_PASSWORD=CHANGEME",
        "LANGFUSE_REDIS_CONNECTION_STRING=",
        "LANGFUSE_REDIS_TLS_ENABLED=false",
        "LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED=true",
    ):
        assert key in text


def test_production_redis_validator_rejects_shared_plaintext_or_untls_config() -> None:
    docker_up = _load_docker_up_module()

    errors = docker_up._validate_production_redis_env(
        {
            "APP_REDIS_USERNAME": "default",
            "APP_REDIS_PASSWORD": "same",
            "APP_REDIS_URL": "redis://default:same@redis:6379/0",
            "APP_REDIS_TLS_ENABLED": "false",
            "APP_REDIS_TLS_CA_PATH": "/certs/app-redis/ca.crt",
            "LANGFUSE_REDIS_USERNAME": "default",
            "LANGFUSE_REDIS_PASSWORD": "same",
            "LANGFUSE_REDIS_CONNECTION_STRING": "redis://default:same@redis:6379/0",
            "LANGFUSE_REDIS_TLS_ENABLED": "false",
            "LANGFUSE_REDIS_TLS_CA_PATH": "/certs/langfuse-redis/ca.crt",
            "LANGFUSE_REDIS_TLS_CERT_PATH": "/certs/langfuse-redis/redis.crt",
            "LANGFUSE_REDIS_TLS_KEY_PATH": "/certs/langfuse-redis/redis.key",
            "LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED": "false",
        }
    )

    joined = "\n".join(errors)
    assert "rediss://" in joined
    assert "separate hosts/instances" in joined
    assert "must be true" in joined
    assert "must be different" in joined
    assert "named ACL user" in joined
