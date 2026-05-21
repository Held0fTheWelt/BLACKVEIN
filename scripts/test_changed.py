#!/usr/bin/env python3
"""Select focused test commands for changed backend, ai_stack, and world-engine files."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Rule:
    prefix: str
    suites: tuple[str, ...] = ()
    direct_targets: tuple[str, ...] = ()
    reason: str = ""


@dataclass
class Selection:
    suites: set[str] = field(default_factory=set)
    root_targets: set[str] = field(default_factory=set)
    backend_targets: set[str] = field(default_factory=set)
    world_engine_targets: set[str] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)


SERVICE_SUITES = {
    "activity": "backend_service_activity",
    "ai_stack": "backend_service_ai_stack",
    "analytics": "backend_service_analytics",
    "common": "backend_service_common",
    "content": "backend_service_content",
    "data": "backend_service_data",
    "game": "backend_service_game",
    "governance": "backend_service_governance",
    "identity": "backend_service_identity",
    "improvement": "backend_service_improvement",
    "inspector": "backend_service_inspector",
    "mcp": "backend_service_mcp",
    "prompts": "backend_service_prompts",
    "story_runtime": "backend_service_story_runtime",
    "system": "backend_service_system",
    "writers_room": "backend_service_writers_room",
}


AI_STACK_PACKAGE_SUITES = {
    "actor_tracking": "ai_stack_actor_tracking",
    "capabilities": "ai_stack_capabilities",
    "contracts": "ai_stack_contracts",
    "langchain": "ai_stack_langchain",
    "langfuse": "ai_stack_langfuse",
    "langgraph": "ai_stack_langgraph",
    "language_io": "ai_stack_language_io",
    "mcp": "ai_stack_mcp",
    "prompt_store": "ai_stack_prompt_store",
    "quality_lab": "ai_stack_quality_lab",
    "rag": "ai_stack_rag",
    "research": "ai_stack_research",
    "telemetry": "ai_stack_telemetry",
}


STORY_RUNTIME_SUITES = {
    "canonical_path": "ai_stack_story_runtime_canonical_path",
    "director": "ai_stack_story_runtime_director",
    "dramatic_effect": "ai_stack_story_runtime_dramatic_effect",
    "god_of_carnage": "ai_stack_story_runtime_god_of_carnage",
    "narrative": "ai_stack_story_runtime_narrative",
    "narrator": "ai_stack_story_runtime_narrator",
    "npc_agency": "ai_stack_story_runtime_npc_agency",
    "semantic_planner": "ai_stack_story_runtime_semantic_planner",
    "turn": "ai_stack_story_runtime_turn",
}


RULES: tuple[Rule, ...] = (
    Rule("scripts/test_changed.py", direct_targets=("tests/test_changed_test_selection.py",), reason="changed-file selector"),
    Rule("world-engine/app/api/http_routes/narrative_web_routes.py", ("engine_http_ws", "engine_observability"), reason="world-engine narrative HTTP observability routes"),
    Rule("world-engine/app/api/http_routes/story_turn_routes.py", ("engine_http_ws", "engine_runtime", "engine_observability"), reason="world-engine story turn HTTP route"),
    Rule("world-engine/app/api/http_routes/story_session_lifecycle_routes.py", ("engine_http_ws", "engine_story_manager_session"), reason="world-engine story session HTTP route"),
    Rule("backend/app/api/v1/game", ("backend_play",), reason="backend game/play API"),
    Rule("backend/app/api/v1/game_routes.py", ("backend_play",), reason="backend game/play API"),
    Rule("backend/app/api/v1/ai_stack", ("backend_service_ai_stack", "backend_routes_core"), reason="backend ai_stack API"),
    Rule("backend/app/api/v1/narrative_governance", ("backend_service_governance", "backend_routes_core"), reason="backend governance API"),
    Rule("backend/app/api/v1/operational_governance", ("backend_service_governance", "backend_routes_core"), reason="backend governance API"),
    Rule("backend/app/api/v1/research_domain_governance", ("backend_service_governance", "backend_routes_core"), reason="backend research governance API"),
    Rule("backend/app/api/v1/security_governance", ("backend_service_governance", "backend_routes_core"), reason="backend security governance API"),
    Rule("backend/app/api", ("backend_routes_core",), reason="backend API route"),
    Rule("backend/app/content", ("backend_content",), reason="backend content compiler/module loader"),
    Rule("backend/app/runtime", ("backend_runtime",), reason="backend runtime package"),
    Rule("backend/app/models/world_engine", ("backend_play", "backend_runtime"), reason="backend world-engine models"),
    Rule("backend/app/models/backend", ("backend_service_identity", "backend_rest"), reason="backend administration/service models"),
    Rule("world-engine/app/api", ("engine_http_ws",), reason="world-engine HTTP/WS API"),
    Rule("world-engine/app/observability", ("engine_observability",), reason="world-engine observability"),
    Rule(
        "world-engine/app/story_runtime/manager/actor_tracking",
        direct_targets=(
            "world-engine/tests/test_story_runtime_w5_admin_diagnostics.py",
            "world-engine/tests/test_story_runtime_w5_narrator_projection.py",
            "world-engine/tests/test_story_runtime_w5_player_view.py",
            "world-engine/tests/test_story_session_w5_round_trip.py",
        ),
        reason="world-engine actor_tracking manager helpers",
    ),
    Rule("world-engine/app/story_runtime/manager/session", ("engine_story_manager_session",), reason="world-engine session manager"),
    Rule("world-engine/app/story_runtime/manager", ("engine_runtime",), reason="world-engine story runtime manager"),
    Rule("world-engine/app/story_runtime/shell_readout", ("engine_runtime",), reason="world-engine shell readout"),
    Rule("world-engine/app/story_runtime_shell_readout.py", ("engine_runtime",), reason="world-engine shell readout facade"),
    Rule("world-engine/app/store", ("engine_persistence",), reason="world-engine persistence"),
    Rule("world-engine/app/auth", ("engine_foundation",), reason="world-engine auth/config foundation"),
    Rule("world-engine/app/config.py", ("engine_foundation",), reason="world-engine config"),
    Rule("tests/gates", ("gates",), reason="repository gate helper/test"),
)


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def run_git(args: list[str]) -> list[str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def changed_paths(*, base: str, staged: bool) -> list[str]:
    if staged:
        paths = run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    else:
        paths = run_git(["diff", "--name-only", "--diff-filter=ACMR", base])
        paths.extend(run_git(["ls-files", "--others", "--exclude-standard"]))
    return sorted({normalize_path(path) for path in paths})


def add_service_suite(path: str, selection: Selection) -> bool:
    prefix = "backend/app/services/"
    if not path.startswith(prefix):
        return False
    parts = path[len(prefix) :].split("/", 1)
    suite = SERVICE_SUITES.get(parts[0])
    if suite:
        selection.suites.add(suite)
        selection.notes.append(f"{path}: {suite} (backend service package)")
    else:
        selection.suites.add("backend_services")
        selection.notes.append(f"{path}: backend_services (unknown service subpackage)")
    return True


def add_ai_stack_suite(path: str, selection: Selection) -> bool:
    if not path.startswith("ai_stack/") or path.startswith("ai_stack/tests/"):
        return False
    rel = path[len("ai_stack/") :]
    if rel.startswith("story_runtime/"):
        parts = rel[len("story_runtime/") :].split("/", 1)
        suite = STORY_RUNTIME_SUITES.get(parts[0])
        if suite:
            selection.suites.add(suite)
            selection.notes.append(f"{path}: {suite} (ai_stack story_runtime package)")
            return True
        if parts[0] == "session_loop":
            selection.suites.add("ai_stack_graph")
            selection.notes.append(f"{path}: ai_stack_graph (session loop graph integration)")
            return True
    package = rel.split("/", 1)[0]
    suite = AI_STACK_PACKAGE_SUITES.get(package)
    if suite:
        selection.suites.add(suite)
        selection.notes.append(f"{path}: {suite} (ai_stack package)")
    else:
        selection.suites.add("ai_stack_rest")
        selection.notes.append(f"{path}: ai_stack_rest (unmapped ai_stack package)")
    return True


def add_test_file(path: str, selection: Selection) -> bool:
    if not (path.endswith(".py") and "/test_" in f"/{path}"):
        return False
    if path.startswith("backend/tests/"):
        selection.backend_targets.add(path[len("backend/") :])
    elif path.startswith("world-engine/tests/"):
        selection.world_engine_targets.add(path[len("world-engine/") :])
    elif path.startswith("ai_stack/tests/") or path.startswith("tests/"):
        selection.root_targets.add(path)
    else:
        return False
    selection.notes.append(f"{path}: direct test file")
    return True


def select_for_paths(paths: list[str]) -> Selection:
    selection = Selection()
    for raw in paths:
        path = normalize_path(raw)
        if not path:
            continue
        if add_test_file(path, selection):
            continue
        if add_service_suite(path, selection):
            continue
        if add_ai_stack_suite(path, selection):
            continue
        matched = False
        for rule in RULES:
            if path.startswith(rule.prefix):
                selection.suites.update(rule.suites)
                for target in rule.direct_targets:
                    if target.startswith("world-engine/"):
                        selection.world_engine_targets.add(target[len("world-engine/") :])
                    elif target.startswith("backend/"):
                        selection.backend_targets.add(target[len("backend/") :])
                    else:
                        selection.root_targets.add(target)
                if rule.reason:
                    targets = ", ".join((*rule.suites, *rule.direct_targets))
                    selection.notes.append(f"{path}: {targets} ({rule.reason})")
                matched = True
                break
        if matched:
            continue
        if path.startswith("backend/"):
            selection.suites.add("backend_rest")
            selection.notes.append(f"{path}: backend_rest (fallback)")
        elif path.startswith("world-engine/"):
            selection.suites.add("engine_rest")
            selection.notes.append(f"{path}: engine_rest (fallback)")
        elif path.startswith("ai_stack/"):
            selection.suites.add("ai_stack_rest")
            selection.notes.append(f"{path}: ai_stack_rest (fallback)")
    return selection


def build_commands(selection: Selection, *, quick: bool) -> list[tuple[Path, dict[str, str] | None, list[str]]]:
    commands: list[tuple[Path, dict[str, str] | None, list[str]]] = []
    if selection.suites:
        cmd = [sys.executable, "tests/run_tests.py", "--suite", *sorted(selection.suites)]
        if quick:
            cmd.extend(["--quick", "--continue-on-failure"])
        commands.append((ROOT, None, cmd))
    if selection.root_targets:
        commands.append((ROOT, None, [sys.executable, "-m", "pytest", *sorted(selection.root_targets), "-q", "--tb=short"]))
    if selection.backend_targets:
        commands.append((ROOT / "backend", None, [sys.executable, "-m", "pytest", *sorted(selection.backend_targets), "-q", "--tb=short"]))
    if selection.world_engine_targets:
        env = dict(os.environ)
        parts = [str(ROOT / "world-engine"), str(ROOT)]
        existing = env.get("PYTHONPATH")
        if existing:
            parts.append(existing)
        env["PYTHONPATH"] = os.pathsep.join(parts)
        commands.append((ROOT / "world-engine", env, [sys.executable, "-m", "pytest", *sorted(selection.world_engine_targets), "-q", "--tb=short"]))
    return commands


def shell_line(cwd: Path, cmd: list[str]) -> str:
    rel = "." if cwd == ROOT else str(cwd.relative_to(ROOT))
    return f"(cd {shlex.quote(rel)} && {' '.join(shlex.quote(part) for part in cmd)})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="Changed files. If omitted, use git diff HEAD plus untracked files.")
    parser.add_argument("--base", default="HEAD", help="Git diff base when no paths are supplied (default: HEAD).")
    parser.add_argument("--staged", action="store_true", help="Use staged changes only when no paths are supplied.")
    parser.add_argument("--run", action="store_true", help="Execute selected commands. Default only prints them.")
    parser.add_argument("--full", action="store_true", help="Do not pass --quick to tests/run_tests.py suite commands.")
    args = parser.parse_args()

    paths = [normalize_path(path) for path in args.paths] if args.paths else changed_paths(base=args.base, staged=args.staged)
    selection = select_for_paths(paths)
    commands = build_commands(selection, quick=not args.full)

    if paths:
        print("Selected from changed paths:")
        for note in selection.notes:
            print(f"  - {note}")
    else:
        print("No changed paths detected.")

    if not commands:
        print("No focused command found.")
        return 0

    print("\nCommands:")
    for cwd, _env, cmd in commands:
        print(f"  {shell_line(cwd, cmd)}")

    if not args.run:
        print("\nDry run. Add --run to execute.")
        return 0

    for cwd, env, cmd in commands:
        print(f"\nRunning: {shell_line(cwd, cmd)}")
        proc = subprocess.run(cmd, cwd=str(cwd), env=env)
        if proc.returncode != 0:
            return proc.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
