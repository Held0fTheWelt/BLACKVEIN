#!/usr/bin/env python3
"""
Run Docker Compose for this repository: bring the stack up with image rebuilds, stop, etc.

Default (no subcommand): ``docker compose up -d --build`` - images are built and containers
are recreated/started (typical local rebuild workflow). Compose runs with the repository
root as the working directory; build contexts in ``docker-compose.yml`` are repo-root
(``backend/`` and ``world-engine`` Dockerfiles expect context ``.``).

Subcommands:
  up, start   ``up -d``; by default with ``--build`` (same as running without COMMAND).
  build       ``build`` only (optional ``--no-cache`` / ``--pull``).
  restart     ``restart`` (no build, processes only).
  stop        ``stop``
  down        ``down`` (optional ``--volumes``)

Flags:
  --no-build  Omit ``--build`` on default/up (faster when images are current).
  -f FILE     Compose file; may be given multiple times. Relative paths are resolved
              from the repository root (not the shell cwd).

Requires ``docker compose`` (v2) or legacy ``docker-compose``.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"


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


def _run(args: argparse.Namespace, compose_args: list[str]) -> int:
    cmd = _compose_prefix(args) + compose_args
    if args.dry_run:
        print(" ".join(shlex_quote(a) for a in cmd))
        return 0
    print("$", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=REPO_ROOT)


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
