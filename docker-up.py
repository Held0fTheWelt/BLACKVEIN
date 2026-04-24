#!/usr/bin/env python3
"""
Run Docker Compose for this repository: bring the stack up with image rebuilds, stop, etc.

This is the supported entry point if you prefer Python over typing ``docker compose``;
it always uses the **repository root** as the Compose working directory (same as
``docker compose -f docker-compose.yml`` from the repo root).

**Local environment & secrets:**

The stack requires stable local secrets in ``.env`` (repo root). ``docker-up.py`` writes
those values **before** Docker Compose runs (including ``docker compose build``): they are
not generated inside Dockerfiles (images stay secret-free).

Use ``init-env`` to create or refresh ``.env`` from ``.env.example`` with generated platform
secrets (SECRET_KEY, JWT_SECRET_KEY, SECRETS_KEK, PLAY_SERVICE_SHARED_SECRET,
INTERNAL_RUNTIME_CONFIG_TOKEN, etc.). A plain ``python docker-up.py`` / ``up`` / ``build`` /
``restart`` also ensures missing or placeholder secrets exist **before** compose executes.

Existing non-placeholder values are preserved; missing or example placeholders are replaced.

After ``init-env``, edit ``.env`` keys as needed:

  - ``OPENAI_API_KEY`` for OpenAI
  - ``OPENROUTER_API_KEY`` for OpenRouter
  - ``ANTHROPIC_API_KEY`` for Anthropic

Ollama does not require an API key by default.

For normal startup, the default behavior ensures ``.env`` is ready:

  python docker-up.py                    # Default: up -d --build with env check
  python docker-up.py up --no-build      # Start with rebuild disabled

**Typical URLs after startup:**
  - Player frontend: http://localhost:5002
  - Backend API:     http://localhost:8000
  - Play service:    http://localhost:8001  (world-engine; browser / WebSocket base)

The backend image includes ``content/modules``; compose sets ``WOS_CONTENT_MODULES_ROOT``
and play-service INTERNAL vs PUBLIC URLs for container vs browser access.

**RAG / AI Engineer Suite:** The backend Dockerfile uses a slim tree under ``/app`` (``app/`` package, no top-level
``backend/`` directory). Compose sets ``WOS_REPO_ROOT=/app`` so RAG ``.wos/`` persistence and ingestion resolve
reliably inside the container. For **host-only** runs (no Docker), set ``WOS_REPO_ROOT`` in ``.env`` to your
World of Shadows **repository root** (the directory that contains ``backend/app/``).

Default (no subcommand): ``docker compose up -d --build`` - images are built and containers
are recreated/started (typical local rebuild workflow). Build contexts in
``docker-compose.yml`` are repo-root (backend and world-engine Dockerfiles expect ``.``).

Subcommands:
  init-env        Initialize local ``.env`` with auto-generated stable secrets.
  ensure-env      Alias for ``init-env``.
  up, start       ``up -d``; by default with ``--build`` (same as running without COMMAND).
  build           ``build`` only (optional ``--no-cache`` / ``--pull``).
  restart         ``restart`` (no build, processes only).
  stop            ``stop``
  down            ``down`` (optional ``--volumes``)
  reset           Remove local Docker state (containers, images, volumes); preserve ``.env``.

Flags:
  --no-build      Omit ``--build`` on default/up (faster when images are current).
  --force         For ``init-env``: regenerate all secrets (overwrite existing).
                  For ``reset``: remove state without confirmation.
  -f FILE         Compose file; may be given multiple times. Relative paths are resolved
                  from the repository root (not the shell cwd).

Requires ``docker compose`` (v2) or legacy ``docker-compose``.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"
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
}

# Keys that have default/fallback values and don't need generation
OPTIONAL_WITH_DEFAULTS = {
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "OLLAMA_BASE_URL": "http://localhost:11434/api",
    "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
    "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
    "ANTHROPIC_VERSION": "2023-06-01",
}

OPTIONAL_SECRET_KEYS = (
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)


def _generate_secret(num_bytes: int) -> str:
    """Generate a strong random secret (URL-safe base64)."""
    return secrets.token_urlsafe(num_bytes)


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
            env_to_write[key] = _generate_secret(num_bytes)
            updated = True

    # Ensure optional defaults are present
    for key, default_value in OPTIONAL_WITH_DEFAULTS.items():
        if key not in env_to_write or not env_to_write[key].strip():
            env_to_write[key] = default_value
            updated = True

    # Ensure known provider API key slots exist but stay blank by default
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


def _compose_prefix(args: argparse.Namespace) -> list[str]:
    cmd = _compose_executable()
    files = args.file if args.file else [str(DEFAULT_COMPOSE)]
    for f in files:
        p = _resolve_compose_path(f)
        if not p.is_file():
            print(f"Error: Compose file not found: {p}", file=sys.stderr)
            sys.exit(1)
        cmd.extend(["-f", str(p)])
    if args.project_name:
        cmd.extend(["-p", args.project_name])
    return cmd


def _ensure_dotenv_before_compose(compose_args: list[str]) -> None:
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
                f"\n✓ Created {ENV_FILE} with auto-generated stable secrets.\n"
                f"  IMPORTANT: Set provider keys in {ENV_FILE} (OPENAI_API_KEY / OPENROUTER_API_KEY / ANTHROPIC_API_KEY) as needed.\n"
                f"  Other secrets are already generated and should not be changed.\n",
                file=sys.stderr,
            )
    else:
        # Ensure existing .env has all required secrets
        updated = _ensure_env_secrets()
        if updated:
            print(
                f"\n✓ Updated {ENV_FILE} with missing stable secrets.\n"
                f"  Review {ENV_FILE} to ensure provider API keys are set where needed.\n",
                file=sys.stderr,
            )


def _run(args: argparse.Namespace, compose_args: list[str]) -> int:
    _ensure_dotenv_before_compose(compose_args)
    cmd = _compose_prefix(args) + compose_args
    if args.dry_run:
        print(" ".join(shlex_quote(a) for a in cmd))
        return 0
    print("$", " ".join(cmd), flush=True)
    exit_code = subprocess.call(cmd, cwd=REPO_ROOT)
    if exit_code == 0 and compose_args and compose_args[0] == "up":
        gate_code = _bootstrap_gate_after_up()
        if gate_code != 0:
            return gate_code
    return exit_code


def _initialize_langfuse_in_backend() -> None:
    """Initialize Langfuse configuration in the backend database from environment variables."""
    # Read Langfuse config from .env
    env_dict = _read_env_file(ENV_FILE)

    enabled = env_dict.get("LANGFUSE_ENABLED", "").lower() == "true"
    public_key = env_dict.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = env_dict.get("LANGFUSE_SECRET_KEY", "").strip()

    # Only initialize if Langfuse is enabled and has credentials
    if not enabled or not secret_key:
        return

    # Try to initialize Langfuse in the database via internal initialization endpoint
    try:
        init_url = "http://localhost:8000/api/v1/internal/observability/initialize"
        payload = {
            "enabled": enabled,
            "public_key": public_key,
            "secret_key": secret_key,
            "base_url": env_dict.get("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"),
            "environment": env_dict.get("LANGFUSE_ENVIRONMENT", "development"),
            "release": env_dict.get("LANGFUSE_RELEASE", "unknown"),
            "sample_rate": float(env_dict.get("LANGFUSE_SAMPLE_RATE", "1.0")),
            "capture_prompts": env_dict.get("LANGFUSE_CAPTURE_PROMPTS", "true").lower() == "true",
            "capture_outputs": env_dict.get("LANGFUSE_CAPTURE_OUTPUTS", "true").lower() == "true",
            "capture_retrieval": env_dict.get("LANGFUSE_CAPTURE_RETRIEVAL", "false").lower() == "true",
            "redaction_mode": env_dict.get("LANGFUSE_REDACTION_MODE", "strict"),
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
            if response.status == 200:
                print("✓ Langfuse observability initialized in database.", file=sys.stderr)
            else:
                print(f"Warning: Langfuse initialization returned status {response.status}", file=sys.stderr)
    except URLError as e:
        # Backend not ready yet, that's OK — initialization will happen on next startup
        pass
    except Exception as e:
        # Silent failure — Langfuse is optional
        pass


def _bootstrap_gate_after_up() -> int:
    """Guide operators through bootstrap setup before normal runtime assumptions."""
    status_url = "http://localhost:8000/api/v1/bootstrap/public-status"
    req = Request(status_url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=2.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError:
        print(
            "Notice: Backend bootstrap status is currently unreachable.\n"
            "If this is the first startup, open the Administration Tool and complete bootstrap:\n"
            "  - Recommended web setup: http://localhost:5002/manage/operational-governance/bootstrap\n"
            "  - CLI fallback: set BOOTSTRAP_RECOVERY_TOKEN + call /api/v1/admin/bootstrap/initialize via curl\n",
            file=sys.stderr,
        )
        return 0
    except Exception as exc:
        print(f"Warning: Could not parse bootstrap status response: {exc}", file=sys.stderr)
        return 0

    # Try to initialize Langfuse in the database (if configured)
    try:
        _initialize_langfuse_in_backend()
    except Exception:
        pass  # Silent failure — Langfuse initialization is optional

    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict):
        return 0
    if data.get("bootstrap_required"):
        print(
            "Bootstrap is required before normal operation is considered complete.\n"
            "Containers are up; finish bootstrap when you are ready.\n"
            "Next steps:\n"
            "  1) Open web setup: http://localhost:5002/manage/operational-governance/bootstrap\n"
            "  2) Select preset + initialize trust-anchor/first provider\n"
            "  3) After bootstrap, reload resolved runtime config from Administration Center so play-service can bind\n"
            "CLI fallback (if web unavailable):\n"
            "  - POST /api/v1/admin/bootstrap/initialize with admin JWT\n",
            file=sys.stderr,
        )
        # Do not fail the docker-up.py process: compose already exited 0; exit 2 breaks scripts/CI that treat non-zero as a broken stack.
        return 0
    print("Bootstrap already initialized. Stack is ready.")
    return 0


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

    if ENV_FILE.is_file() and not force:
        existing = _read_env_file(ENV_FILE)
        missing = [
            k for k in REQUIRED_SECRETS if k not in existing or _platform_secret_needs_generation(existing.get(k))
        ]
        if not missing:
            print(f"✓ {ENV_FILE} already exists with all required secrets.")
            print(f"  To regenerate secrets, use: python docker-up.py init-env --force")
            return 0

    created = _ensure_env_secrets(force=force)
    if created or force:
        print(f"\n{'✓ Created' if not ENV_FILE.is_file() else '✓ Updated'} {ENV_FILE}")
        print(f"\nNext steps:")
        print(f"  1. Edit {ENV_FILE} and set provider API keys as needed (OpenAI/OpenRouter/Anthropic)")
        print(f"  2. Run: python docker-up.py up")
        print(f"\nOther secrets (SECRET_KEY, JWT_SECRET_KEY, etc.) are auto-generated and should not be changed.")
        return 0

    return 0


def cmd_ensure_env(args: argparse.Namespace, services: list[str]) -> int:
    """Alias for init-env."""
    return cmd_init_env(args, services)


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
        print(f"\n✓ Reset complete. .env preserved.", file=sys.stderr)
        print(f"  To restart: python docker-up.py up", file=sys.stderr)
    return exit_code


def main() -> None:
    # Shared flags so ``--dry-run`` works before or after the subcommand (e.g. ``up --dry-run``).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands only; do not run.",
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
