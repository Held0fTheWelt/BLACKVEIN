#!/usr/bin/env python3
"""
Bootstrap and run the World of Shadows stack via docker compose.

Usage:
  python docker-up.py init-env     Create .env with generated secrets
  python docker-up.py up            Start containers with local Langfuse observability
  python docker-up.py --no-langfuse up
                                   Start app containers without local Langfuse
  python docker-up.py langfuse-up   Explicit alias for local Langfuse observability startup
  python docker-up.py init-production-redis
                                   Generate production Redis passwords, TLS certs, ACL files
  python docker-up.py --production-redis up
                                   Start with hardened separate app/Langfuse Redis instances
  python docker-up.py build         Build images only
  python docker-up.py restart       Restart running containers
  python docker-up.py stop          Stop containers
  python docker-up.py down          Remove containers

Exit codes (up command):
  0 = Success (containers healthy, admin user created)
  1 = Docker compose failed
  2 = Backend migrations failed
  3 = Admin user creation failed
  4 = Langfuse initialization failed (when LANGFUSE_* credentials are provided)
  5 = Backend health check failed
  6 = Environment (.env) validation failed
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"
LANGFUSE_COMPOSE = REPO_ROOT / "docker-compose.langfuse.yml"
REDIS_PRODUCTION_COMPOSE = REPO_ROOT / "docker-compose.redis-production.yml"
REDIS_PRODUCTION_DIR = REPO_ROOT / ".docker" / "redis-production"
ENV_FILE = REPO_ROOT / ".env"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# Stable platform secrets that must be locally generated if missing
REQUIRED_SECRETS = {
    "SECRET_KEY": 32,  # (bytes for generation)
    "JWT_SECRET_KEY": 32,
    "SECRETS_KEK": 32,
    "PLAY_SERVICE_SHARED_SECRET": 24,
    "PLAY_SERVICE_INTERNAL_API_KEY": 24,
    "FRONTEND_SECRET_KEY": 24,
    # Backend GET /api/v1/internal/runtime-config and play-service fetch must share this token (docker-compose).
    "INTERNAL_RUNTIME_CONFIG_TOKEN": 24,
    # Local Langfuse self-hosting secrets (used only when docker-compose.langfuse.yml is included).
    "NEXTAUTH_SECRET": 32,
    "SALT": 24,
    "ENCRYPTION_KEY": 32,
    "LANGFUSE_DB_PASSWORD": 24,
    "CLICKHOUSE_PASSWORD": 24,
    "MINIO_ROOT_PASSWORD": 24,
    "APP_REDIS_PASSWORD": 24,
    "LANGFUSE_REDIS_PASSWORD": 24,
}

# Keys that have default/fallback values and don't need generation
OPTIONAL_WITH_DEFAULTS = {
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "OLLAMA_BASE_URL": "http://localhost:11434/api",
    "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "ANTHROPIC_VERSION": "2023-06-01",
    "REDIS_URL": "redis://redis:6379/0",
    "LANGFUSE_HOST": "http://langfuse-web:3000",
    "LANGFUSE_BASE_URL": "http://langfuse-web:3000",
    "LANGFUSE_MCP_BASE_URL": "http://localhost:3000",
    "LANGFUSE_ENVIRONMENT": "local",
    "LANGFUSE_RELEASE": "local-dev",
    "LANGFUSE_SAMPLE_RATE": "1.0",
    "LANGFUSE_CAPTURE_PROMPTS": "true",
    "LANGFUSE_CAPTURE_OUTPUTS": "true",
    "LANGFUSE_CAPTURE_RETRIEVAL": "true",
    "LANGFUSE_REDACTION_MODE": "strict",
    "WOS_LANGFUSE_TRACING_ENVIRONMENT": "local",
    "WOS_LANGFUSE_LOCAL_EVIDENCE": "1",
    "WOS_LANGFUSE_EVIDENCE_SCOPE": "local_langfuse",
    "WOS_LANGFUSE_PROOF_LEVEL": "local_only",
    "WOS_LANGFUSE_EVIDENCE_ENVIRONMENT": "local",
    "WOS_LANGFUSE_LIVE_OR_STAGING_EVIDENCE": "false",
    "WOS_LANGFUSE_BOOTSTRAP_OVERWRITE": "false",
    "WOS_PROMPT_STORE_SEED_OVERWRITE": "false",
    "NEXTAUTH_URL": "http://localhost:3000",
    "CLICKHOUSE_USER": "langfuse",
    "MINIO_ROOT_USER": "langfuse",
    "APP_REDIS_USERNAME": "wos_app",
    "APP_REDIS_TLS_ENABLED": "false",
    "APP_REDIS_TLS_CA_PATH": "/certs/app-redis/ca.crt",
    "LANGFUSE_REDIS_TLS_ENABLED": "false",
    "LANGFUSE_REDIS_TLS_CA_PATH": "/certs/langfuse-redis/ca.crt",
    "LANGFUSE_REDIS_TLS_CERT_PATH": "/certs/langfuse-redis/redis.crt",
    "LANGFUSE_REDIS_TLS_KEY_PATH": "/certs/langfuse-redis/redis.key",
    "LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED": "true",
    "LANGFUSE_REDIS_KEY_PREFIX": "langfuse:",
    "LANGFUSE_WEB_PORT": "3000",
    "LANGFUSE_MINIO_API_PORT": "9090",
    "LANGFUSE_MINIO_CONSOLE_PORT": "9091",
    "LANGFUSE_TELEMETRY_ENABLED": "true",
}

# Slots materialized in .env as empty strings when missing.
# Provider API keys are intentionally excluded: store them through Backend AI Runtime Governance /
# encrypted secret storage so runtime containers do not receive provider secrets from Compose.
OPTIONAL_SECRET_KEYS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


def _generate_secret(num_bytes: int) -> str:
    """Generate a strong random secret (URL-safe base64)."""
    return secrets.token_urlsafe(num_bytes)


def _generate_secret_for_key(key: str, num_bytes: int) -> str:
    """Generate a key-specific secret value accepted by local infrastructure."""
    if key == "ENCRYPTION_KEY":
        # Langfuse self-hosting expects a 256-bit hex key (`openssl rand -hex 32`).
        return secrets.token_hex(32)
    return _generate_secret(num_bytes)


def _platform_secret_needs_generation(raw: str | None) -> bool:
    """True if a REQUIRED_SECRETS slot is empty or still carries .env.example placeholders."""
    v = (raw or "").strip()
    if not v:
        return True
    if v == "__AUTO_GENERATED_DO_NOT_EDIT__":
        return True
    lowered = v.lower()
    if lowered in ("change-me", "changeme", "change_me", "replace-me", "replaceme"):
        return True
    return False


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse .env file into a dictionary. Preserves order and ignores comments."""
    env_dict = {}
    if not path.is_file():
        return env_dict
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    env_dict[key.strip()] = value.strip()
    except Exception as e:
        print(f"Warning: Could not read {path}: {e}", file=sys.stderr)
    return env_dict


def _write_env_file(path: Path, env_dict: dict[str, str], example_path: Path | None = None) -> None:
    """Write .env file, preserving structure from example if available."""
    content = ""

    # If example exists, use its structure and fill in values
    if example_path and example_path.is_file():
        try:
            with open(example_path, "r", encoding="utf-8") as f:
                for line in f:
                    # Preserve comments and blank lines
                    if line.strip().startswith("#") or not line.strip():
                        content += line
                    elif "=" in line:
                        key, _, _ = line.partition("=")
                        key = key.strip()
                        if key in env_dict:
                            content += f"{key}={env_dict[key]}\n"
                        else:
                            # Preserve lines not in env_dict as-is
                            content += line
                    else:
                        content += line
        except Exception as e:
            print(f"Warning: Could not read example file {example_path}: {e}", file=sys.stderr)
            # Fall back to simple dict output
            for key, value in env_dict.items():
                content += f"{key}={value}\n"
    else:
        # No example file, just write the dict
        for key, value in env_dict.items():
            content += f"{key}={value}\n"

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Error: Could not write {path}: {e}", file=sys.stderr)
        sys.exit(1)


def _rediss_url(username: str, password: str, host: str, ca_path: str) -> str:
    """Build a Redis TLS URL with URL-escaped ACL credentials."""
    quoted_user = quote(username, safe="")
    quoted_password = quote(password, safe="")
    quoted_ca_path = quote(ca_path, safe="/:")
    return (
        f"rediss://{quoted_user}:{quoted_password}@{host}:6379/0"
        f"?ssl_cert_reqs=required&ssl_ca_certs={quoted_ca_path}"
    )


def _redis_username_is_valid(username: str) -> bool:
    if not username or username == "default":
        return False
    return all(ch.isalnum() or ch in "._-" for ch in username)


def _ensure_production_redis_env(force: bool = False) -> bool:
    """Ensure .env contains production Redis ACL/TLS variables."""
    if not ENV_FILE.is_file():
        _ensure_env_secrets()
    else:
        _ensure_env_secrets(force=False)

    env_to_write = _read_env_file(ENV_FILE)
    updated = False

    for key, num_bytes in (
        ("APP_REDIS_PASSWORD", 32),
        ("LANGFUSE_REDIS_PASSWORD", 32),
    ):
        cur = env_to_write.get(key, "")
        if force or key not in env_to_write or _platform_secret_needs_generation(cur):
            env_to_write[key] = _generate_secret_for_key(key, num_bytes)
            updated = True

    for key, default_value in (
        ("APP_REDIS_USERNAME", "wos_app"),
        ("LANGFUSE_REDIS_USERNAME", "langfuse"),
    ):
        cur = env_to_write.get(key, "").strip()
        if force or not cur:
            env_to_write[key] = default_value
            updated = True

    fixed_values = {
        "APP_REDIS_TLS_ENABLED": "true",
        "APP_REDIS_TLS_CA_PATH": "/certs/app-redis/ca.crt",
        "LANGFUSE_REDIS_TLS_ENABLED": "true",
        "LANGFUSE_REDIS_TLS_CA_PATH": "/certs/langfuse-redis/ca.crt",
        "LANGFUSE_REDIS_TLS_CERT_PATH": "/certs/langfuse-redis/redis.crt",
        "LANGFUSE_REDIS_TLS_KEY_PATH": "/certs/langfuse-redis/redis.key",
        "LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED": "true",
        "LANGFUSE_REDIS_KEY_PREFIX": "langfuse:",
    }
    for key, value in fixed_values.items():
        if env_to_write.get(key, "").strip() != value:
            env_to_write[key] = value
            updated = True

    app_url = _rediss_url(
        env_to_write["APP_REDIS_USERNAME"],
        env_to_write["APP_REDIS_PASSWORD"],
        "redis",
        env_to_write["APP_REDIS_TLS_CA_PATH"],
    )
    langfuse_url = _rediss_url(
        env_to_write["LANGFUSE_REDIS_USERNAME"],
        env_to_write["LANGFUSE_REDIS_PASSWORD"],
        "langfuse-redis",
        env_to_write["LANGFUSE_REDIS_TLS_CA_PATH"],
    )
    for key, value in (
        ("APP_REDIS_URL", app_url),
        ("LANGFUSE_REDIS_CONNECTION_STRING", langfuse_url),
    ):
        if env_to_write.get(key, "").strip() != value:
            env_to_write[key] = value
            updated = True

    if updated:
        _write_env_file(ENV_FILE, env_to_write, ENV_EXAMPLE)
    return updated


def _validate_production_redis_env(env_dict: dict[str, str]) -> list[str]:
    """Return production Redis hardening violations."""
    errors: list[str] = []
    required = (
        "APP_REDIS_USERNAME",
        "APP_REDIS_PASSWORD",
        "APP_REDIS_URL",
        "APP_REDIS_TLS_ENABLED",
        "APP_REDIS_TLS_CA_PATH",
        "LANGFUSE_REDIS_USERNAME",
        "LANGFUSE_REDIS_PASSWORD",
        "LANGFUSE_REDIS_CONNECTION_STRING",
        "LANGFUSE_REDIS_TLS_ENABLED",
        "LANGFUSE_REDIS_TLS_CA_PATH",
        "LANGFUSE_REDIS_TLS_CERT_PATH",
        "LANGFUSE_REDIS_TLS_KEY_PATH",
        "LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED",
    )
    for key in required:
        if not env_dict.get(key, "").strip():
            errors.append(f"{key} is required")

    for key in ("APP_REDIS_USERNAME", "LANGFUSE_REDIS_USERNAME"):
        value = env_dict.get(key, "").strip()
        if value and not _redis_username_is_valid(value):
            errors.append(f"{key} must be a named ACL user using only letters, numbers, '.', '_' or '-'")

    for key in ("APP_REDIS_PASSWORD", "LANGFUSE_REDIS_PASSWORD"):
        if _platform_secret_needs_generation(env_dict.get(key, "")):
            errors.append(f"{key} must be a generated non-placeholder secret")

    if env_dict.get("APP_REDIS_PASSWORD") == env_dict.get("LANGFUSE_REDIS_PASSWORD"):
        errors.append("APP_REDIS_PASSWORD and LANGFUSE_REDIS_PASSWORD must be different")

    if not _value_truthy(env_dict.get("APP_REDIS_TLS_ENABLED")):
        errors.append("APP_REDIS_TLS_ENABLED must be true")
    if not _value_truthy(env_dict.get("LANGFUSE_REDIS_TLS_ENABLED")):
        errors.append("LANGFUSE_REDIS_TLS_ENABLED must be true")
    if not _value_truthy(env_dict.get("LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED")):
        errors.append("LANGFUSE_REDIS_TLS_REJECT_UNAUTHORIZED must be true")

    app_url = env_dict.get("APP_REDIS_URL", "").strip()
    langfuse_url = env_dict.get("LANGFUSE_REDIS_CONNECTION_STRING", "").strip()
    parsed_app = urlparse(app_url)
    parsed_langfuse = urlparse(langfuse_url)

    if parsed_app.scheme != "rediss":
        errors.append("APP_REDIS_URL must use rediss://")
    if parsed_langfuse.scheme != "rediss":
        errors.append("LANGFUSE_REDIS_CONNECTION_STRING must use rediss://")
    if parsed_app.hostname and parsed_langfuse.hostname and parsed_app.hostname == parsed_langfuse.hostname:
        errors.append("App Redis and Langfuse Redis must use separate hosts/instances")
    if not parsed_app.username or not parsed_app.password:
        errors.append("APP_REDIS_URL must include ACL username and password")
    if not parsed_langfuse.username or not parsed_langfuse.password:
        errors.append("LANGFUSE_REDIS_CONNECTION_STRING must include ACL username and password")

    return errors


def _run_checked(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{' '.join(cmd)} failed: {detail}")


def _ensure_mode_readable(path: Path) -> None:
    try:
        path.chmod(0o644)
    except OSError:
        pass


def _ensure_production_redis_certs(force: bool = False) -> bool:
    """Generate local TLS material for the production Redis compose override."""
    openssl = shutil.which("openssl")
    if not openssl:
        raise RuntimeError("openssl is required to generate Redis TLS certificates")

    ca_dir = REDIS_PRODUCTION_DIR / "ca"
    certs_dir = REDIS_PRODUCTION_DIR / "certs"
    ca_key = ca_dir / "ca.key"
    ca_crt = ca_dir / "ca.crt"
    generated = False

    ca_dir.mkdir(parents=True, exist_ok=True)
    certs_dir.mkdir(parents=True, exist_ok=True)

    if force or not ca_key.is_file() or not ca_crt.is_file():
        _run_checked([openssl, "genrsa", "-out", str(ca_key), "4096"])
        _run_checked(
            [
                openssl,
                "req",
                "-x509",
                "-new",
                "-nodes",
                "-key",
                str(ca_key),
                "-sha256",
                "-days",
                "825",
                "-out",
                str(ca_crt),
                "-subj",
                "/CN=WorldOfShadows Redis Local CA",
            ]
        )
        generated = True

    _ensure_mode_readable(ca_crt)
    try:
        ca_key.chmod(0o600)
    except OSError:
        pass

    for label, dns_name in (("app", "redis"), ("langfuse", "langfuse-redis")):
        service_dir = certs_dir / label
        service_dir.mkdir(parents=True, exist_ok=True)
        key_path = service_dir / "redis.key"
        csr_path = service_dir / "redis.csr"
        crt_path = service_dir / "redis.crt"
        ca_copy = service_dir / "ca.crt"
        ext_path = service_dir / "redis.ext"

        if force or not key_path.is_file() or not crt_path.is_file() or not ca_copy.is_file():
            ext_path.write_text(
                "\n".join(
                    [
                        "authorityKeyIdentifier=keyid,issuer",
                        "basicConstraints=CA:FALSE",
                        "keyUsage=digitalSignature,keyEncipherment",
                        "extendedKeyUsage=serverAuth",
                        f"subjectAltName=DNS:{dns_name},DNS:localhost,IP:127.0.0.1",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            _run_checked([openssl, "genrsa", "-out", str(key_path), "2048"])
            _run_checked(
                [
                    openssl,
                    "req",
                    "-new",
                    "-key",
                    str(key_path),
                    "-out",
                    str(csr_path),
                    "-subj",
                    f"/CN={dns_name}",
                ]
            )
            _run_checked(
                [
                    openssl,
                    "x509",
                    "-req",
                    "-in",
                    str(csr_path),
                    "-CA",
                    str(ca_crt),
                    "-CAkey",
                    str(ca_key),
                    "-CAcreateserial",
                    "-out",
                    str(crt_path),
                    "-days",
                    "825",
                    "-sha256",
                    "-extfile",
                    str(ext_path),
                ]
            )
            shutil.copyfile(ca_crt, ca_copy)
            generated = True

        for path in (key_path, crt_path, ca_copy):
            if path.is_file():
                _ensure_mode_readable(path)

    return generated


def _write_acl_file(path: Path, username: str, password: str) -> bool:
    content = f"user default off\nuser {username} on >{password} ~* &* +@all\n"
    old = path.read_text(encoding="utf-8") if path.is_file() else None
    if old == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return True


def _ensure_production_redis_assets(env_dict: dict[str, str], force: bool = False) -> bool:
    updated = _ensure_production_redis_certs(force=force)
    updated = (
        _write_acl_file(
            REDIS_PRODUCTION_DIR / "app-users.acl",
            env_dict["APP_REDIS_USERNAME"],
            env_dict["APP_REDIS_PASSWORD"],
        )
        or updated
    )
    updated = (
        _write_acl_file(
            REDIS_PRODUCTION_DIR / "langfuse-users.acl",
            env_dict["LANGFUSE_REDIS_USERNAME"],
            env_dict["LANGFUSE_REDIS_PASSWORD"],
        )
        or updated
    )
    return updated


def _ensure_production_redis_setup(force: bool = False) -> tuple[bool, bool]:
    """Materialize production Redis env, TLS certs, ACL files, then validate."""
    env_updated = _ensure_production_redis_env(force=force)
    env_dict = _read_env_file(ENV_FILE)
    errors = _validate_production_redis_env(env_dict)
    if errors:
        raise RuntimeError("; ".join(errors))
    assets_updated = _ensure_production_redis_assets(env_dict, force=force)
    return env_updated, assets_updated


def _ensure_env_secrets(force: bool = False) -> bool:
    """
    Ensure .env exists with all required stable secrets.

    Returns True if .env was created or updated, False if already complete.

    If force=True, regenerate all secrets even if they exist.
    If force=False (default), preserve existing values and only generate missing ones.
    """
    # Read existing .env if present
    existing_env = _read_env_file(ENV_FILE) if ENV_FILE.is_file() else {}

    # Determine which secrets to generate
    env_to_write = existing_env.copy()
    updated = False

    for key, num_bytes in REQUIRED_SECRETS.items():
        cur = env_to_write.get(key, "")
        if force or key not in env_to_write or _platform_secret_needs_generation(cur):
            env_to_write[key] = _generate_secret_for_key(key, num_bytes)
            updated = True

    # Ensure optional defaults are present
    for key, default_value in OPTIONAL_WITH_DEFAULTS.items():
        if key not in env_to_write or not env_to_write[key].strip():
            env_to_write[key] = default_value
            updated = True

    # Ensure optional runtime credential slots exist (empty default). Provider keys are excluded;
    # use Backend AI Runtime Governance / encrypted secret storage for those.
    # Only add missing *keys* — never replace existing values.
    for key in OPTIONAL_SECRET_KEYS:
        if key not in env_to_write:
            env_to_write[key] = ""
            updated = True

    # Write the updated env file
    if updated or not ENV_FILE.is_file():
        _write_env_file(ENV_FILE, env_to_write, ENV_EXAMPLE)
        return True

    return False


def _resolve_compose_path(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    else:
        p = p.resolve()
    return p


def _compose_executable() -> list[str]:
    docker = shutil.which("docker")
    if docker:
        r = subprocess.run(
            [docker, "compose", "version"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        if r.returncode == 0:
            return [docker, "compose"]
    legacy = shutil.which("docker-compose")
    if legacy:
        return [legacy]
    print('Error: Neither "docker compose" nor "docker-compose" found in PATH.', file=sys.stderr)
    sys.exit(1)


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _env_falsey(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"0", "false", "no", "off"}


def _value_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _with_langfuse_enabled(args: argparse.Namespace) -> bool:
    if bool(getattr(args, "no_langfuse", False)):
        return False
    if bool(getattr(args, "with_langfuse", False)):
        return True
    if _env_falsey("WOS_DOCKER_WITH_LANGFUSE"):
        return False
    # Local observability is part of the default setup. Operators can opt out with
    # --no-langfuse or WOS_DOCKER_WITH_LANGFUSE=0 for app-only workflows.
    return True


def _with_production_redis(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "production_redis", False)) or _env_truthy("WOS_DOCKER_PRODUCTION_REDIS")


def _compose_prefix(args: argparse.Namespace) -> list[str]:
    cmd = _compose_executable()
    files = list(args.file) if args.file else [str(DEFAULT_COMPOSE)]
    production_redis = _with_production_redis(args)
    if production_redis and not _with_langfuse_enabled(args):
        print(
            "Error: --production-redis requires the Langfuse override so app Redis and Langfuse Redis are both hardened.",
            file=sys.stderr,
        )
        sys.exit(1)
    if _with_langfuse_enabled(args):
        langfuse_file = str(LANGFUSE_COMPOSE)
        resolved_files = {_resolve_compose_path(f) for f in files}
        if LANGFUSE_COMPOSE.resolve() not in resolved_files:
            files.append(langfuse_file)
    if production_redis:
        production_file = str(REDIS_PRODUCTION_COMPOSE)
        resolved_files = {_resolve_compose_path(f) for f in files}
        if REDIS_PRODUCTION_COMPOSE.resolve() not in resolved_files:
            files.append(production_file)
    for f in files:
        p = _resolve_compose_path(f)
        if not p.is_file():
            print(f"Error: Compose file not found: {p}", file=sys.stderr)
            sys.exit(1)
        cmd.extend(["-f", str(p)])
    if args.project_name:
        cmd.extend(["-p", args.project_name])
    return cmd


def _ensure_dotenv_before_compose(compose_args: list[str], args: argparse.Namespace | None = None) -> None:
    """Ensure .env exists with required secrets before compose (build/up/restart need substitution + env_file)."""
    if not compose_args:
        return
    head = compose_args[0]
    if head not in ("up", "build", "restart"):
        return

    if not ENV_FILE.is_file():
        print(f"Setting up local environment file: {ENV_FILE}", file=sys.stderr)
        created = _ensure_env_secrets()
        if created:
            print(
                f"\n[OK] Created {ENV_FILE} with auto-generated stable secrets.\n"
                f"  IMPORTANT: Add provider credentials in Administration Tool -> AI Runtime Governance; Compose does not inject provider keys.\n"
                f"  Other secrets are already generated and should not be changed.\n",
                file=sys.stderr,
            )
    else:
        # Ensure existing .env has all required secrets
        updated = _ensure_env_secrets()
        if updated:
            print(
                f"\n[OK] Updated {ENV_FILE} with missing stable secrets.\n"
                f"  Add provider API keys via Administration Tool -> AI Runtime Governance when needed.\n",
                file=sys.stderr,
            )

    if args is not None and _with_production_redis(args):
        try:
            env_updated, assets_updated = _ensure_production_redis_setup(force=False)
        except RuntimeError as exc:
            print(f"ERROR: Production Redis setup failed: {exc}", file=sys.stderr)
            sys.exit(6)
        if env_updated or assets_updated:
            print(
                f"[OK] Production Redis password/TLS/ACL setup materialized under {REDIS_PRODUCTION_DIR}.",
                file=sys.stderr,
            )


def _run(args: argparse.Namespace, compose_args: list[str]) -> int:
    cmd = _compose_prefix(args) + compose_args
    if getattr(args, "dry_run", False):
        print(" ".join(shlex_quote(a) for a in cmd))
        return 0
    _ensure_dotenv_before_compose(compose_args, args=args)
    print("$", " ".join(cmd), flush=True)
    exit_code = subprocess.call(cmd, cwd=REPO_ROOT)
    if exit_code == 0 and compose_args and compose_args[0] == "up":
        gate_code = _bootstrap_gate_after_up(local_langfuse=_with_langfuse_enabled(args))
        if gate_code != 0:
            return gate_code
    return exit_code


def _initialize_admin_user_in_backend() -> None:
    """Create default admin user 'admin' with password 'Admin123' if it doesn't exist.

    Retries while the backend is still starting (migrations / health). Previously a single
    connection failure caused a silent skip — no admin row — with exit code 0.

    Raises:
        RuntimeError: If the endpoint returns an error or the backend stays unreachable.
    """
    init_url = "http://localhost:8000/api/v1/internal/bootstrap/admin-user"
    payload = {
        "username": "admin",
        "password": "Admin123",
        "create_if_missing": True,
    }
    data = json.dumps(payload).encode("utf-8")

    max_attempts = 45
    delay_sec = 2.0
    last_url_exc: BaseException | None = None

    for attempt in range(max_attempts):
        req = Request(
            init_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=15) as response:
                raw = response.read().decode("utf-8")
                response_data = json.loads(raw)

            if response.status != 200:
                raise RuntimeError(
                    f"Admin user initialization returned unexpected status {response.status}: {raw[:400]}"
                )

            if response_data.get("data", {}).get("created"):
                print("[OK] Admin user created (admin / Admin123).", file=sys.stderr)
            else:
                print("[OK] Admin user already exists.", file=sys.stderr)
            return

        except HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", errors="replace")[:800]
            except Exception:
                pass
            raise RuntimeError(
                f"Admin user endpoint HTTP {e.code}: {detail or e.reason}"
            ) from e

        except URLError as e:
            last_url_exc = e
            if attempt < max_attempts - 1:
                time.sleep(delay_sec)
                continue
            raise RuntimeError(
                "Admin user creation: backend unreachable after "
                f"{max_attempts} attempts (~{int(max_attempts * delay_sec)}s). "
                f"Last error: {last_url_exc}"
            ) from last_url_exc

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Backend returned invalid JSON during admin user creation: {str(e)}"
            ) from e


def _initialize_langfuse_in_backend(*, local_langfuse: bool = False) -> None:
    """Initialize Langfuse configuration in the backend database from optional environment credentials.

    Runtime settings normally come from the backend database/admin UI. This bootstrap only imports
    LANGFUSE_* credentials when they are explicitly present in .env.

    Raises:
        RuntimeError: If provided Langfuse credentials are incomplete or initialization fails.
    """
    # Read Langfuse config from .env
    env_dict = _read_env_file(ENV_FILE)

    public_key = env_dict.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = env_dict.get("LANGFUSE_SECRET_KEY", "").strip()

    # Runtime-only setup: no env toggle. If no keys are provided, keep the database setting as-is.
    if not public_key and not secret_key:
        return

    if not public_key or not secret_key:
        raise RuntimeError("Langfuse credentials are incomplete: set both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY, or manage them in backend settings")

    try:
        init_url = "http://localhost:8000/api/v1/internal/observability/initialize"
        base_url = env_dict.get("LANGFUSE_BASE_URL") or env_dict.get("LANGFUSE_HOST") or "https://cloud.langfuse.com"
        if local_langfuse:
            base_url = "http://langfuse-web:3000"
        payload = {
            "enabled": True,
            "public_key": public_key,
            "secret_key": secret_key,
            "base_url": base_url,
            "environment": env_dict.get("LANGFUSE_ENVIRONMENT", "local" if local_langfuse else "development"),
            "release": env_dict.get("LANGFUSE_RELEASE", "local-dev" if local_langfuse else "unknown"),
            "sample_rate": float(env_dict.get("LANGFUSE_SAMPLE_RATE", "1.0")),
            "capture_prompts": env_dict.get("LANGFUSE_CAPTURE_PROMPTS", "true").lower() == "true",
            "capture_outputs": env_dict.get("LANGFUSE_CAPTURE_OUTPUTS", "true").lower() == "true",
            "capture_retrieval": env_dict.get("LANGFUSE_CAPTURE_RETRIEVAL", "false").lower() == "true",
            "redaction_mode": env_dict.get("LANGFUSE_REDACTION_MODE", "strict"),
            "overwrite_existing": _value_truthy(env_dict.get("WOS_LANGFUSE_BOOTSTRAP_OVERWRITE")),
        }

        import json
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            init_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urlopen(req, timeout=5) as response:
            response_data = json.loads(response.read().decode("utf-8"))

            if response.status == 200 and response_data.get("ok"):
                response_payload = response_data.get("data") if isinstance(response_data, dict) else {}
                if isinstance(response_payload, dict) and response_payload.get("skipped_existing"):
                    print("[OK] Langfuse observability already configured; bootstrap import skipped.", file=sys.stderr)
                else:
                    print("[OK] Langfuse observability initialized in database.", file=sys.stderr)
            else:
                raise RuntimeError(f"Backend rejected Langfuse initialization: {response_data.get('error', {}).get('message', 'Unknown error')}")

    except URLError as e:
        raise RuntimeError(f"Langfuse initialization failed: backend unreachable ({str(e)})")

    except json.JSONDecodeError as e:
        raise RuntimeError(f"Langfuse initialization failed: backend returned invalid JSON ({str(e)})")

    except Exception as e:
        raise RuntimeError(f"Langfuse initialization failed: {str(e)}")


def _bootstrap_gate_after_up(*, local_langfuse: bool = False) -> int:
    """Check backend health, create admin user, initialize Langfuse, and guide bootstrap.

    Exit codes (per ADR-0030):
        0: Success (bootstrap complete or required—either way, stack is operational)
        2: Migrations failed (inferred from admin user creation table-not-found error)
        3: Admin user creation failed (database error, constraints, etc.)
        4: Langfuse initialization failed (configured but failed)
        5: Backend healthcheck timeout or unresponsive
        6: Bootstrap status check failed (unexpected response)
    """
    # Step 1: Check bootstrap status
    status_url = "http://localhost:8000/api/v1/bootstrap/public-status"
    req = Request(status_url, headers={"Accept": "application/json"})

    try:
        with urlopen(req, timeout=2.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError as e:
        print(
            "ERROR: Backend is not responding to health checks.\n"
            "Check: docker ps | grep backend\n"
            "If backend is running, check logs: docker logs worldofshadows-backend-1\n",
            file=sys.stderr,
        )
        return 5  # Exit code 5: Backend unreachable
    except json.JSONDecodeError as exc:
        print(f"ERROR: Backend returned invalid JSON: {exc}", file=sys.stderr)
        return 6  # Exit code 6: Unexpected response
    except Exception as exc:
        print(f"ERROR: Unexpected error checking bootstrap status: {exc}", file=sys.stderr)
        return 6

    # Step 2: Create admin user for bootstrap access (CRITICAL)
    try:
        _initialize_admin_user_in_backend()
    except RuntimeError as e:
        error_msg = str(e)
        # Distinguish between migration failure and other errors
        if "users" in error_msg.lower() or "table" in error_msg.lower():
            print(f"ERROR: Database migrations incomplete: {error_msg}", file=sys.stderr)
            print("Recovery: Restart containers so migrations re-run:\n  docker-compose down && python docker-up.py up\n", file=sys.stderr)
            return 2  # Exit code 2: Migrations failed
        else:
            print(f"ERROR: Admin user creation failed: {error_msg}", file=sys.stderr)
            print("Recovery: Check backend logs and retry:\n  docker logs worldofshadows-backend-1\n  python docker-up.py up\n", file=sys.stderr)
            return 3  # Exit code 3: Admin user creation failed

    # Step 3: Import Langfuse credentials from .env when explicitly provided.
    try:
        _initialize_langfuse_in_backend(local_langfuse=local_langfuse)
    except RuntimeError as e:
        print(f"ERROR: Langfuse initialization failed: {str(e)}", file=sys.stderr)
        print("Recovery: Check LANGFUSE_* credentials in .env, remove them, or manage Langfuse in backend settings:\n  python docker-up.py up\n", file=sys.stderr)
        return 4  # Exit code 4: Langfuse failed

    # Step 4: Report final bootstrap status
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        print("WARNING: Bootstrap status response format unexpected", file=sys.stderr)
        return 0

    if data.get("bootstrap_required"):
        print(
            "Bootstrap is required before normal operation is considered complete.\n"
            "Containers are up; finish bootstrap when you are ready.\n"
            "Next steps:\n"
            "  1) Open web setup: http://localhost:5001/manage/operational-governance/bootstrap\n"
            "  2) Select preset + initialize trust-anchor/first provider\n"
            "  3) After bootstrap, reload resolved runtime config from Administration Center so play-service can bind\n"
            "CLI fallback (if web unavailable):\n"
            "  - POST /api/v1/admin/bootstrap/initialize with admin JWT\n",
            file=sys.stderr,
        )
        return 0  # Not an error; operator must use web UI

    print("[OK] Stack is ready.")
    return 0  # Success


def shlex_quote(s: str) -> str:
    if sys.platform == "win32":
        if not s or any(c in s for c in ' \t\n"'):
            return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return s
    import shlex

    return shlex.quote(s)


def _wants_build(args: argparse.Namespace) -> bool:
    return not getattr(args, "no_build", False)


def _up_args(args: argparse.Namespace, services: list[str]) -> list[str]:
    out = ["up", "-d"]
    if _wants_build(args):
        out.append("--build")
    return out + services


def cmd_default(args: argparse.Namespace, services: list[str]) -> int:
    return _run(args, _up_args(args, services))


def cmd_up(args: argparse.Namespace, services: list[str]) -> int:
    return _run(args, _up_args(args, services))


def cmd_langfuse_up(args: argparse.Namespace, services: list[str]) -> int:
    """Start the stack with local Langfuse Compose override enabled."""
    setattr(args, "with_langfuse", True)
    return cmd_up(args, services)


def cmd_production_redis_up(args: argparse.Namespace, services: list[str]) -> int:
    """Start the stack with production Redis hardening override enabled."""
    setattr(args, "with_langfuse", True)
    setattr(args, "production_redis", True)
    return cmd_up(args, services)


def cmd_build(args: argparse.Namespace, services: list[str]) -> int:
    build_args: list[str] = ["build"]
    if getattr(args, "no_cache", False):
        build_args.append("--no-cache")
    if getattr(args, "pull", False):
        build_args.append("--pull")
    return _run(args, build_args + services)


def cmd_restart(args: argparse.Namespace, services: list[str]) -> int:
    return _run(args, ["restart", *services])


def cmd_stop(args: argparse.Namespace, services: list[str]) -> int:
    return _run(args, ["stop", *services])


def cmd_down(args: argparse.Namespace, services: list[str]) -> int:
    if services:
        print(
            'Note: "down" always affects the whole project; extra service names are ignored.',
            file=sys.stderr,
        )
    down_args = ["down"]
    if args.volumes:
        down_args.append("--volumes")
    return _run(args, down_args)


def cmd_init_env(args: argparse.Namespace, services: list[str]) -> int:
    """Initialize or update local .env with stable secrets."""
    force = getattr(args, "force", False)

    created = _ensure_env_secrets(force=force)
    if created or force:
        print(f"\n{'[OK] Created' if not ENV_FILE.is_file() else '[OK] Updated'} {ENV_FILE}")
        print(f"\nNext steps:")
        print("  1. Add provider credentials in Administration Tool -> AI Runtime Governance / secret storage as needed")
        print(f"  2. Run: python docker-up.py up  (starts app + local Langfuse)")
        print(f"     App-only fallback: python docker-up.py --no-langfuse up")
        print(f"\nOther secrets (SECRET_KEY, JWT_SECRET_KEY, etc.) are auto-generated and should not be changed.")
        return 0

    print(f"[OK] {ENV_FILE} already exists with all required secrets and defaults.")
    print(f"  To regenerate secrets, use: python docker-up.py init-env --force")
    return 0


def cmd_init_production_redis(args: argparse.Namespace, services: list[str]) -> int:
    """Initialize production Redis passwords, TLS certs, ACL files, and URLs."""
    force = getattr(args, "force", False)
    try:
        env_updated, assets_updated = _ensure_production_redis_setup(force=force)
    except RuntimeError as exc:
        print(f"ERROR: Production Redis setup failed: {exc}", file=sys.stderr)
        return 6

    if env_updated:
        print(f"[OK] Updated {ENV_FILE} with production Redis URL/TLS/ACL settings.")
    else:
        print(f"[OK] {ENV_FILE} already contains production Redis URL/TLS/ACL settings.")

    if assets_updated:
        print(f"[OK] Generated Redis ACL/TLS material under {REDIS_PRODUCTION_DIR}.")
    else:
        print(f"[OK] Redis ACL/TLS material already exists under {REDIS_PRODUCTION_DIR}.")

    print("Next step: python docker-up.py --production-redis up")
    return 0


def cmd_validate_production_redis(args: argparse.Namespace, services: list[str]) -> int:
    """Validate production Redis environment and generated local assets."""
    env_dict = _read_env_file(ENV_FILE)
    errors = _validate_production_redis_env(env_dict)
    required_assets = (
        REDIS_PRODUCTION_DIR / "app-users.acl",
        REDIS_PRODUCTION_DIR / "langfuse-users.acl",
        REDIS_PRODUCTION_DIR / "certs" / "app" / "ca.crt",
        REDIS_PRODUCTION_DIR / "certs" / "app" / "redis.crt",
        REDIS_PRODUCTION_DIR / "certs" / "app" / "redis.key",
        REDIS_PRODUCTION_DIR / "certs" / "langfuse" / "ca.crt",
        REDIS_PRODUCTION_DIR / "certs" / "langfuse" / "redis.crt",
        REDIS_PRODUCTION_DIR / "certs" / "langfuse" / "redis.key",
    )
    for path in required_assets:
        if not path.is_file():
            errors.append(f"Missing generated Redis asset: {path}")

    if errors:
        print("Production Redis validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("Recovery: python docker-up.py init-production-redis", file=sys.stderr)
        return 6

    print("[OK] Production Redis password/TLS/ACL setup is complete.")
    return 0


def cmd_ensure_env(args: argparse.Namespace, services: list[str]) -> int:
    """Alias for init-env."""
    return cmd_init_env(args, services)


def cmd_gate(args: argparse.Namespace, services: list[str]) -> int:
    """MVP operational gate: fail if backend is unreachable or bootstrap is required.

    Exit 0  — backend healthy, bootstrap complete, stack ready.
    Exit 1  — bootstrap required (stack up but not initialized).
    Exit 2  — backend unreachable (not started or crashed).
    Exit 3  — unexpected error parsing backend response.

    Use before running MVP tests to confirm the stack is operational:
      python docker-up.py gate
    """
    backend_url = getattr(args, "backend_url", None) or "http://localhost:8000"
    status_url = f"{backend_url.rstrip('/')}/api/v1/bootstrap/public-status"

    print(f"Docker-up gate: checking {status_url}", file=sys.stderr)

    req = Request(status_url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=5) as response:
            raw = response.read().decode("utf-8")
    except URLError as exc:
        print(f"GATE FAIL: Backend unreachable at {status_url}: {exc}", file=sys.stderr)
        print("docker_up_gate_result: FAIL — backend_unreachable", flush=True)
        return 2
    except Exception as exc:
        print(f"GATE ERROR: {exc}", file=sys.stderr)
        return 3

    try:
        payload = json.loads(raw)
    except Exception as exc:
        print(f"GATE ERROR: Cannot parse backend response: {exc}", file=sys.stderr)
        return 3

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        print("GATE FAIL: Backend response missing 'data' field.", file=sys.stderr)
        return 3

    if data.get("bootstrap_required"):
        print(
            "GATE FAIL: Bootstrap is required. Run web setup or CLI bootstrap before the MVP gate.",
            file=sys.stderr,
        )
        print("docker_up_gate_result: FAIL — bootstrap_required", flush=True)
        return 1

    print("GATE PASS: Backend healthy, bootstrap complete.", file=sys.stderr)
    print("docker_up_gate_result: PASS", flush=True)
    return 0


def cmd_reset(args: argparse.Namespace, services: list[str]) -> int:
    """Reset local Docker state: remove containers, images, and volumes. Preserve .env."""
    if not getattr(args, "force", False):
        print(
            "This will remove:\n"
            "  - All containers in this Docker Compose project\n"
            "  - Images built locally (not base images)\n"
            "  - Named volumes (if --volumes used)\n"
            "\n"
            ".env will be PRESERVED so secrets and settings survive the reset.\n"
            "\n"
            "Proceed? Use --force to confirm:",
            file=sys.stderr,
        )
        return 1

    print("Resetting local Docker state...", file=sys.stderr)
    cmd = _compose_prefix(args) + ["down", "--rmi", "local"]
    if getattr(args, "volumes", False):
        cmd.append("--volumes")

    print("$", " ".join(cmd), flush=True)
    exit_code = subprocess.call(cmd, cwd=REPO_ROOT)
    if exit_code == 0:
        print(f"\n[OK] Reset complete. .env preserved.", file=sys.stderr)
        print(f"  To restart: python docker-up.py up", file=sys.stderr)
    return exit_code


def main() -> None:
    # Shared flags so ``--dry-run`` works before or after the subcommand (e.g. ``up --dry-run``).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Print commands only; do not run.",
    )
    common.add_argument(
        "--with-langfuse",
        action="store_true",
        default=argparse.SUPPRESS,
        help=f"Include {LANGFUSE_COMPOSE.name} for local observability (default).",
    )
    common.add_argument(
        "--no-langfuse",
        action="store_true",
        default=argparse.SUPPRESS,
        help=f"Do not include {LANGFUSE_COMPOSE.name}; start app-only stack.",
    )
    common.add_argument(
        "--production-redis",
        action="store_true",
        default=argparse.SUPPRESS,
        help=f"Include {REDIS_PRODUCTION_COMPOSE.name}; auto-materialize Redis password/TLS/ACL setup.",
    )

    parser = argparse.ArgumentParser(
        description="Docker Compose: default = stack up with rebuild (up -d --build).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
        parents=[common],
    )
    parser.add_argument(
        "-f",
        "--file",
        action="append",
        metavar="FILE",
        help=f"Compose file (repeatable). Default: {DEFAULT_COMPOSE.name}. Relative paths are from repo root.",
    )
    parser.add_argument(
        "-p",
        "--project-name",
        metavar="NAME",
        help="Compose project name (-p).",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help='For default and "up": skip image build (up -d only).',
    )
    parser.add_argument(
        "--volumes",
        action="store_true",
        help='For "down" only: remove named volumes.',
    )
    sub = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        help="Without COMMAND: up -d --build (rebuild).",
        required=False,
    )

    p_up = sub.add_parser(
        "up",
        aliases=["start"],
        help="Start stack (default: with --build).",
        parents=[common],
    )
    p_up.add_argument("services", nargs="*", help="Optional: only these services.")
    p_up.set_defaults(_handler=cmd_up)

    p_langfuse_up = sub.add_parser(
        "langfuse-up",
        aliases=["observability-up"],
        help="Start stack with local Langfuse observability override.",
        parents=[common],
    )
    p_langfuse_up.add_argument("services", nargs="*", help="Optional: only these services.")
    p_langfuse_up.set_defaults(_handler=cmd_langfuse_up)

    p_production_redis_up = sub.add_parser(
        "production-redis-up",
        aliases=["prod-redis-up"],
        help="Start stack with production Redis password/TLS/ACL hardening.",
        parents=[common],
    )
    p_production_redis_up.add_argument("services", nargs="*", help="Optional: only these services.")
    p_production_redis_up.set_defaults(_handler=cmd_production_redis_up)

    p_build = sub.add_parser(
        "build",
        help="Build images (use --no-cache after Dockerfile changes).",
        parents=[common],
    )
    p_build.add_argument("services", nargs="*", help="Optional: only these services.")
    p_build.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not use cache when building images.",
    )
    p_build.add_argument(
        "--pull",
        action="store_true",
        help="Always pull newer base images before building.",
    )
    p_build.set_defaults(_handler=cmd_build)

    p_restart = sub.add_parser("restart", help="Restart without build.", parents=[common])
    p_restart.add_argument("services", nargs="*", help="Optional: only these services.")
    p_restart.set_defaults(_handler=cmd_restart)

    p_stop = sub.add_parser("stop", help="Stop containers (not down).", parents=[common])
    p_stop.add_argument("services", nargs="*", help="Optional: only these services.")
    p_stop.set_defaults(_handler=cmd_stop)

    p_down = sub.add_parser("down", help="Tear down stack (remove network).", parents=[common])
    p_down.add_argument("services", nargs="*", help="Ignored for down (compatibility).")
    p_down.set_defaults(_handler=cmd_down)

    p_init_env = sub.add_parser(
        "init-env",
        help="Initialize/ensure local .env with auto-generated stable secrets.",
        parents=[common],
    )
    p_init_env.add_argument(
        "--force",
        action="store_true",
        help="Regenerate all secrets, overwriting existing values.",
    )
    p_init_env.set_defaults(_handler=cmd_init_env)

    p_init_production_redis = sub.add_parser(
        "init-production-redis",
        aliases=["init-prod-redis"],
        help="Generate production Redis credentials, TLS certs, ACL files, and URLs.",
        parents=[common],
    )
    p_init_production_redis.add_argument(
        "--force",
        action="store_true",
        help="Regenerate Redis passwords and TLS certificates.",
    )
    p_init_production_redis.set_defaults(_handler=cmd_init_production_redis)

    p_validate_production_redis = sub.add_parser(
        "validate-production-redis",
        aliases=["validate-prod-redis"],
        help="Validate production Redis password/TLS/ACL setup.",
        parents=[common],
    )
    p_validate_production_redis.set_defaults(_handler=cmd_validate_production_redis)

    p_ensure_env = sub.add_parser(
        "ensure-env",
        help="Alias for init-env.",
        parents=[common],
    )
    p_ensure_env.add_argument("--force", action="store_true")
    p_ensure_env.set_defaults(_handler=cmd_ensure_env)

    p_reset = sub.add_parser(
        "reset",
        help="Remove local Docker state; preserve .env.",
        parents=[common],
    )
    p_reset.add_argument(
        "--force",
        action="store_true",
        help="Proceed without confirmation.",
    )
    p_reset.add_argument(
        "--volumes",
        action="store_true",
        help="Also remove named volumes.",
    )
    p_reset.set_defaults(_handler=cmd_reset)

    p_gate = sub.add_parser(
        "gate",
        help="MVP operational gate: fail if backend unreachable or bootstrap required.",
        parents=[common],
    )
    p_gate.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend base URL to check (default: http://localhost:8000).",
    )
    p_gate.set_defaults(_handler=cmd_gate)

    args = parser.parse_args()
    handler = getattr(args, "_handler", None)
    services = list(getattr(args, "services", []) or [])

    if handler is None:
        code = cmd_default(args, services)
    else:
        code = handler(args, services)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
