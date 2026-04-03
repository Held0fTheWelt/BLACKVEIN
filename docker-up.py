#!/usr/bin/env python3
"""
Steuert Docker Compose fuer dieses Repo: Stack mit Image-Rebuild, stoppen, etc.

Standard (ohne Unterbefehl): ``docker compose up -d --build`` — Images werden gebaut,
Container neu erstellt/gestartet (typischer lokaler Rebuild-Workflow).

Unterbefehle:
  up, start   ``up -d``; standardmaessig mit ``--build`` (wie ohne COMMAND).
  restart     ``restart`` (ohne Build, nur Prozesse neu starten).
  stop        ``stop``
  down        ``down`` (optional --volumes)

Schalter:
  --no-build  Kein ``--build`` bei up/default (schneller, wenn Images aktuell sind).

Voraussetzung: ``docker compose`` (v2) oder Fallback ``docker-compose``.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_COMPOSE = REPO_ROOT / "docker-compose.yml"


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
    print('Fehler: Weder "docker compose" noch "docker-compose" im PATH gefunden.', file=sys.stderr)
    sys.exit(1)


def _compose_prefix(args: argparse.Namespace) -> list[str]:
    cmd = _compose_executable()
    files = args.file if args.file else [str(DEFAULT_COMPOSE)]
    for f in files:
        p = Path(f)
        if not p.is_file():
            print(f"Fehler: Compose-Datei fehlt: {p}", file=sys.stderr)
            sys.exit(1)
        cmd.extend(["-f", str(p.resolve())])
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


def cmd_restart(args: argparse.Namespace, services: list[str]) -> int:
    return _run(args, ["restart", *services])


def cmd_stop(args: argparse.Namespace, services: list[str]) -> int:
    return _run(args, ["stop", *services])


def cmd_down(args: argparse.Namespace, services: list[str]) -> int:
    if services:
        print(
            'Hinweis: "down" betrifft immer das ganze Projekt; zusaetzliche Dienstnamen werden ignoriert.',
            file=sys.stderr,
        )
    down_args = ["down"]
    if args.volumes:
        down_args.append("--volumes")
    return _run(args, down_args)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Docker Compose: Standard = Stack mit Rebuild (up -d --build).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "-f",
        "--file",
        action="append",
        metavar="FILE",
        help=f"Compose-Datei (mehrfach moeglich). Standard: {DEFAULT_COMPOSE.name}",
    )
    parser.add_argument(
        "-p",
        "--project-name",
        metavar="NAME",
        help="Compose-Projektname (-p).",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help='Bei Standard und "up": kein Image-Build (nur up -d).',
    )
    parser.add_argument(
        "--volumes",
        action="store_true",
        help='Nur bei "down": benannte Volumes mit entfernen.',
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur die Befehle ausgeben, nicht ausfuehren.",
    )
    sub = parser.add_subparsers(
        dest="command",
        metavar="COMMAND",
        help="Ohne COMMAND: up -d --build (Rebuild).",
        required=False,
    )

    p_up = sub.add_parser("up", aliases=["start"], help='Stack hochfahren (Standard: mit --build).')
    p_up.add_argument("services", nargs="*", help="Optional nur diese Dienste.")
    p_up.set_defaults(_handler=cmd_up)

    p_restart = sub.add_parser("restart", help='"restart" ohne Build.')
    p_restart.add_argument("services", nargs="*", help="Optional nur diese Dienste.")
    p_restart.set_defaults(_handler=cmd_restart)

    p_stop = sub.add_parser("stop", help="Container stoppen (ohne down).")
    p_stop.add_argument("services", nargs="*", help="Optional nur diese Dienste.")
    p_stop.set_defaults(_handler=cmd_stop)

    p_down = sub.add_parser("down", help="Stack herunterfahren (Netzwerk entfernen).")
    p_down.add_argument("services", nargs="*", help="Wird bei down ignoriert (Kompatibilitaet).")
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
