"""World-engine contract helpers for gate tests (AST + import oracles, no source substring greps).

These utilities parse ``world-engine/app/api/http.py`` and ``manager.py`` as structured
AST instead of scanning raw source text, and validate import boundaries for LDSS.
"""

from __future__ import annotations

import ast
from pathlib import Path


def extract_router_get_routes(http_py: Path) -> list[tuple[str, str]]:
    """Return (path, function_name) for each ``@router.get("...")`` on module-level routes."""
    tree = ast.parse(http_py.read_text(encoding="utf-8"))
    out: list[tuple[str, str]] = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not isinstance(func, ast.Attribute) or func.attr != "get":
                continue
            if not dec.args:
                continue
            arg0 = dec.args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                out.append((arg0.value, node.name))
    return out


def admin_proxy_path_for_api_route(api_relative_path: str) -> str:
    """Administration-tool proxies play-service ``/api`` routes as ``/_proxy/api`` + suffix."""
    if not api_relative_path.startswith("/"):
        raise ValueError(f"Expected absolute-style API suffix, got {api_relative_path!r}")
    return "/_proxy/api" + api_relative_path


def assert_diagnostics_and_narrative_gov_routes_registered(http_py: Path) -> None:
    """Fail if MVP4 internal story routes are missing from the FastAPI router (AST-derived paths)."""
    routes = extract_router_get_routes(http_py)
    by_path = {p: name for p, name in routes}
    diag = "/story/sessions/{session_id}/diagnostics-envelope"
    gov = "/story/runtime/narrative-gov-summary"
    assert diag in by_path, f"Missing GET route {diag!r} in {http_py}"
    assert gov in by_path, f"Missing GET route {gov!r} in {http_py}"
    assert by_path[diag] == "get_story_diagnostics_envelope"
    assert by_path[gov] == "get_narrative_gov_summary"


def assert_story_runtime_manager_exposes_diagnostics_api(manager_py: Path) -> None:
    """StoryRuntimeManager must define envelope / gov accessors (AST method names, not source layout)."""
    tree = ast.parse(manager_py.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
            methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
            assert "get_last_diagnostics_envelope" in methods, "StoryRuntimeManager.get_last_diagnostics_envelope missing"
            assert "get_narrative_gov_summary" in methods, "StoryRuntimeManager.get_narrative_gov_summary missing"
            return
    raise AssertionError("StoryRuntimeManager class not found in manager.py")


def _import_names_from_live_dramatic_import(manager_tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in manager_tree.body:
        if not isinstance(node, ast.ImportFrom) or node.module is None:
            continue
        if not node.module.endswith("live_dramatic_scene_simulator"):
            continue
        for alias in node.names:
            names.add(alias.asname or alias.name)
    return names


def assert_ldss_import_and_module_wiring(manager_py: Path, ldss_py: Path) -> None:
    """LDSS symbols are imported in manager and used in _build_ldss_scene_envelope (import + AST oracle)."""
    from ai_stack.live_dramatic_scene_simulator import (  # noqa: PLC0415 — import contract oracle (wave 02)
        build_scene_turn_envelope_v2,
        run_ldss,
    )

    assert callable(run_ldss) and callable(build_scene_turn_envelope_v2), "LDSS entrypoints must be importable"

    mtree = ast.parse(manager_py.read_text(encoding="utf-8"))
    imported = _import_names_from_live_dramatic_import(mtree)
    assert "run_ldss" in imported, "manager.py must import run_ldss from ai_stack.live_dramatic_scene_simulator"
    assert "build_scene_turn_envelope_v2" in imported, (
        "manager.py must import build_scene_turn_envelope_v2 from ai_stack.live_dramatic_scene_simulator"
    )

    ldss_fn: ast.FunctionDef | None = None
    for node in mtree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "_build_ldss_scene_envelope":
            ldss_fn = node
            break
    assert ldss_fn is not None, "_build_ldss_scene_envelope must exist at module scope in manager.py"

    called = _collect_called_names(ldss_fn)
    assert "run_ldss" in called, "_build_ldss_scene_envelope must call run_ldss"
    assert "build_scene_turn_envelope_v2" in called, "_build_ldss_scene_envelope must call build_scene_turn_envelope_v2"

    # LDSS module must still export core symbols (module-level contract, not layout).
    ltree = ast.parse(ldss_py.read_text(encoding="utf-8"))
    top_names = {n.name for n in ltree.body if isinstance(n, ast.ClassDef)}
    top_names |= {n.name for n in ltree.body if isinstance(n, ast.FunctionDef)}
    for sym in ("SceneTurnEnvelopeV2", "LDSSInput", "LDSSOutput", "NPCAgencyPlan", "run_ldss"):
        assert sym in top_names, f"{sym} must be defined in live_dramatic_scene_simulator.py"


def _collect_called_names(func: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                names.add(fn.id)
            elif isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
                names.add(fn.attr)
    return names


def assert_finalize_committed_turn_assigns_diagnostics_envelope(manager_py: Path) -> None:
    """``_finalize_committed_turn`` must call ``build_diagnostics_envelope`` and write ``event['diagnostics_envelope']``."""
    tree = ast.parse(manager_py.read_text(encoding="utf-8"))
    finalize: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_finalize_committed_turn":
                    finalize = item
                    break
    assert finalize is not None, "_finalize_committed_turn not found on StoryRuntimeManager"

    calls = _collect_called_names(finalize)
    assert "build_diagnostics_envelope" in calls, "_finalize_committed_turn must call build_diagnostics_envelope"

    found_event_assign = False
    for node in ast.walk(finalize):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if not isinstance(tgt, ast.Subscript):
                continue
            if not isinstance(tgt.value, ast.Name) or tgt.value.id != "event":
                continue
            key = tgt.slice
            if isinstance(key, ast.Constant) and key.value == "diagnostics_envelope":
                found_event_assign = True
                break
    assert found_event_assign, "_finalize_committed_turn must assign event['diagnostics_envelope']"


def assert_finalize_committed_turn_calls_ldss_builder(manager_py: Path) -> None:
    """``_finalize_committed_turn`` must invoke ``_build_ldss_scene_envelope`` for LDSS wiring."""
    tree = ast.parse(manager_py.read_text(encoding="utf-8"))
    finalize: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_finalize_committed_turn":
                    finalize = item
                    break
    assert finalize is not None
    calls = _collect_called_names(finalize)
    assert "_build_ldss_scene_envelope" in calls, "_finalize_committed_turn must call _build_ldss_scene_envelope"


def assert_goc_module_gate_in_finalize(manager_py: Path) -> None:
    """``GOD_OF_CARNAGE_MODULE_ID`` must be referenced in ``_finalize_committed_turn`` (GoC-only diagnostics path)."""
    tree = ast.parse(manager_py.read_text(encoding="utf-8"))
    finalize: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_finalize_committed_turn":
                    finalize = item
                    break
    assert finalize is not None
    names = {n.id for n in ast.walk(finalize) if isinstance(n, ast.Name)}
    assert "GOD_OF_CARNAGE_MODULE_ID" in names, "_finalize_committed_turn must reference GOD_OF_CARNAGE_MODULE_ID"


def assert_scene_turn_envelope_committed_to_event(manager_py: Path) -> None:
    """``_finalize_committed_turn`` must assign ``event['scene_turn_envelope']`` when an envelope exists."""
    tree = ast.parse(manager_py.read_text(encoding="utf-8"))
    finalize: ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "_finalize_committed_turn":
                    finalize = item
                    break
    assert finalize is not None
    found = False
    for node in ast.walk(finalize):
        if not isinstance(node, ast.Assign):
            continue
        for tgt in node.targets:
            if not isinstance(tgt, ast.Subscript):
                continue
            if not isinstance(tgt.value, ast.Name) or tgt.value.id != "event":
                continue
            sl = tgt.slice
            if isinstance(sl, ast.Constant) and sl.value == "scene_turn_envelope":
                found = True
                break
    assert found, "_finalize_committed_turn must assign event['scene_turn_envelope']"


NARRATIVE_GOV_JSON_KEYS: tuple[str, ...] = (
    "content_module_health",
    "runtime_profile_health",
    "runtime_module_health",
    "ldss_health",
    "frontend_render_contract_health",
    "actor_lane_health",
    "degradation_health",
)

# Mirrors ``NarrativeGovSummary.to_dict()`` keys in ``ai_stack/diagnostics_envelope.py`` (operator contract surface).
NARRATIVE_GOV_SUMMARY_TO_DICT_KEYS: tuple[str, ...] = (
    "contract",
    "content_module_id",
    "runtime_profile_id",
    "runtime_module_id",
    "last_trace_id",
    "last_story_session_id",
    "last_turn_number",
) + NARRATIVE_GOV_JSON_KEYS


def assert_manager_get_narrative_gov_summary_calls_builder(manager_py: Path) -> None:
    """``StoryRuntimeManager.get_narrative_gov_summary`` must call ``build_narrative_gov_summary`` (AST oracle)."""
    tree = ast.parse(manager_py.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "get_narrative_gov_summary":
                    calls = _collect_called_names(item)
                    assert "build_narrative_gov_summary" in calls, (
                        "get_narrative_gov_summary must call build_narrative_gov_summary"
                    )
                    return
    raise AssertionError("StoryRuntimeManager.get_narrative_gov_summary not found")


def assert_narrative_gov_template_renders_panel_contract(runtime_html: Path) -> None:
    """Admin template JS must reference NarrativeGovSummary JSON keys (machine contract, not prose)."""
    text = runtime_html.read_text(encoding="utf-8")
    assert 'data-testid="narrative-gov-summary"' in text, "runtime.html must expose data-testid for narrative gov root"
    gov_route = "/story/runtime/narrative-gov-summary"
    expected_fetch = admin_proxy_path_for_api_route(gov_route)
    assert expected_fetch in text, f"runtime.html must fetch {expected_fetch} (derived from router path {gov_route})"
    for key in NARRATIVE_GOV_JSON_KEYS:
        assert key in text, f"runtime.html narrative gov script must reference panel key {key!r}"


def assert_mvp4_execute_turn_diagnostics_integration_passes(repo_root: Path) -> None:
    """Behavioral oracle: world-engine integration proves execute_turn returns diagnostics_envelope (wave 02)."""
    import os
    import subprocess
    import sys

    we = repo_root / "world-engine"
    env = os.environ.copy()
    sep = os.pathsep
    roots = [str(we), str(repo_root), str(repo_root / "backend"), str(repo_root / "story_runtime_core")]
    extra = env.get("PYTHONPATH", "").strip()
    env["PYTHONPATH"] = sep.join(roots + ([extra] if extra else []))
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_mvp4_diagnostics_integration.py::test_execute_turn_produces_diagnostics_envelope_annette",
        "-q",
        "--no-cov",
        "--tb=short",
    ]
    proc = subprocess.run(cmd, cwd=str(we), env=env, capture_output=True, text=True, timeout=180)
    assert proc.returncode == 0, (
        "execute_turn diagnostics envelope integration must pass (see world-engine test):\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
