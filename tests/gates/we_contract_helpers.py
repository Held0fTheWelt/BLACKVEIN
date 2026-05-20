"""World-engine contract helpers for gate tests (AST + import oracles, no source substring greps).

These utilities parse ``world-engine/app/api/http.py`` and the package-based
``story_runtime/manager`` sources as structured AST instead of scanning raw
source text, and validate import boundaries for LDSS.
"""

from __future__ import annotations

import ast
import configparser
import textwrap
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


def _manager_package_dir(manager_path: Path) -> Path | None:
    """Return the package directory for the current manager layout, if present."""
    if manager_path.is_dir():
        return manager_path
    if manager_path.name == "manager.py":
        candidate = manager_path.with_suffix("")
        if candidate.is_dir():
            return candidate
    return None


def _read_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def _literal_source_from_chunk(path: Path) -> str:
    tree = _read_ast(path)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "SOURCE" for target in node.targets):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, str):
            raise AssertionError(f"SOURCE in {path} must be a string literal")
        return value
    raise AssertionError(f"SOURCE literal not found in {path}")


def _legacy_method_tree(manager_path: Path, method_name: str) -> ast.Module:
    package_dir = _manager_package_dir(manager_path)
    if package_dir is None:
        return _read_ast(manager_path)

    legacy_dir = package_dir / "_legacy_sources"
    chunk_prefix = f"method__{method_name}"
    chunks = sorted(legacy_dir.glob(f"{chunk_prefix}_*.py"))
    if not chunks:
        raise AssertionError(f"Legacy source chunks for {method_name} not found in {legacy_dir}")
    source = "".join(_literal_source_from_chunk(path) for path in chunks)
    source = textwrap.dedent(source.lstrip("\\\n"))
    if source.startswith("    def "):
        source = "\n".join(line[4:] if line.startswith("    ") else line for line in source.splitlines())
    return ast.parse(source)


def _find_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    fn = _module_function(tree, name)
    if fn is not None:
        return fn
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == name:
                return item
    return None


def _manager_import_tree(manager_path: Path) -> ast.Module:
    package_dir = _manager_package_dir(manager_path)
    if package_dir is None:
        return _read_ast(manager_path)
    return _read_ast(package_dir / "_imports_00.py")


def _manager_ldss_builder_tree(manager_path: Path) -> ast.Module:
    package_dir = _manager_package_dir(manager_path)
    if package_dir is None:
        return _read_ast(manager_path)
    return _read_ast(package_dir / "ldss_narrative_queue.py")


def _manager_diagnostics_tree(manager_path: Path) -> ast.Module:
    package_dir = _manager_package_dir(manager_path)
    if package_dir is None:
        return _read_ast(manager_path)
    return _read_ast(package_dir / "diagnostics_api.py")


def assert_story_runtime_manager_exposes_diagnostics_api(manager_py: Path) -> None:
    """StoryRuntimeManager must define envelope / gov accessors (AST method names, not source layout)."""
    package_dir = _manager_package_dir(manager_py)
    if package_dir is not None:
        runtime_tree = _read_ast(package_dir / "runtime_manager.py")
        runtime_class = next(
            (node for node in runtime_tree.body if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager"),
            None,
        )
        assert runtime_class is not None, "StoryRuntimeManager class not found in runtime_manager.py"
        bases = {base.id for base in runtime_class.bases if isinstance(base, ast.Name)}
        assert "_DiagnosticsApiMixin" in bases, "StoryRuntimeManager must include _DiagnosticsApiMixin"

    tree = _manager_diagnostics_tree(manager_py)
    methods = {
        item.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        for item in node.body
        if isinstance(item, ast.FunctionDef)
    }
    if not methods:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "StoryRuntimeManager":
                methods = {n.name for n in node.body if isinstance(n, ast.FunctionDef)}
                break
    assert "get_last_diagnostics_envelope" in methods, "StoryRuntimeManager.get_last_diagnostics_envelope missing"
    assert "get_narrative_gov_summary" in methods, "StoryRuntimeManager.get_narrative_gov_summary missing"


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

    mtree = _manager_import_tree(manager_py)
    imported = _import_names_from_live_dramatic_import(mtree)
    assert "run_ldss" in imported, "manager package must import run_ldss from ai_stack.live_dramatic_scene_simulator"
    assert "build_scene_turn_envelope_v2" in imported, (
        "manager package must import build_scene_turn_envelope_v2 from ai_stack.live_dramatic_scene_simulator"
    )

    builder_tree = _manager_ldss_builder_tree(manager_py)
    ldss_fn = _module_function(builder_tree, "_build_ldss_scene_envelope")
    assert ldss_fn is not None, "_build_ldss_scene_envelope must exist in manager LDSS builder module"

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


def _module_function(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _assignment_value(func: ast.FunctionDef, target_name: str) -> ast.AST | None:
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == target_name:
                return node.value
    return None


def _dict_entry_value(dict_node: ast.Dict, key_name: str) -> ast.AST | None:
    for key, value in zip(dict_node.keys, dict_node.values):
        if isinstance(key, ast.Constant) and key.value == key_name:
            return value
    return None


def assert_finalize_committed_turn_assigns_diagnostics_envelope(manager_py: Path) -> None:
    """``_finalize_committed_turn`` must call ``build_diagnostics_envelope`` and write ``event['diagnostics_envelope']``."""
    tree = _legacy_method_tree(manager_py, "_finalize_committed_turn")
    finalize = _find_function(tree, "_finalize_committed_turn")
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
    tree = _legacy_method_tree(manager_py, "_finalize_committed_turn")
    finalize = _find_function(tree, "_finalize_committed_turn")
    assert finalize is not None
    calls = _collect_called_names(finalize)
    assert "_build_ldss_scene_envelope" in calls, "_finalize_committed_turn must call _build_ldss_scene_envelope"


def assert_goc_module_gate_in_finalize(manager_py: Path) -> None:
    """``GOD_OF_CARNAGE_MODULE_ID`` must be referenced in ``_finalize_committed_turn`` (GoC-only diagnostics path)."""
    tree = _legacy_method_tree(manager_py, "_finalize_committed_turn")
    finalize = _find_function(tree, "_finalize_committed_turn")
    assert finalize is not None
    names = {n.id for n in ast.walk(finalize) if isinstance(n, ast.Name)}
    assert "GOD_OF_CARNAGE_MODULE_ID" in names, "_finalize_committed_turn must reference GOD_OF_CARNAGE_MODULE_ID"


def assert_scene_turn_envelope_committed_to_event(manager_py: Path) -> None:
    """``_finalize_committed_turn`` must assign ``event['scene_turn_envelope']`` when an envelope exists."""
    tree = _legacy_method_tree(manager_py, "_finalize_committed_turn")
    finalize = _find_function(tree, "_finalize_committed_turn")
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


def assert_ldss_scene_envelope_requires_human_actor(manager_py: Path) -> None:
    """``_build_ldss_scene_envelope`` must return ``None`` when no human actor is projected."""
    tree = _manager_ldss_builder_tree(manager_py)
    fn = _module_function(tree, "_build_ldss_scene_envelope")
    assert fn is not None, "_build_ldss_scene_envelope must exist in manager LDSS builder module"

    human_assignment = _assignment_value(fn, "human_actor_id")
    assert human_assignment is not None, "_build_ldss_scene_envelope must derive human_actor_id"

    guarded_return = False
    for node in ast.walk(fn):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.UnaryOp)
            and isinstance(test.op, ast.Not)
            and isinstance(test.operand, ast.Name)
            and test.operand.id == "human_actor_id"
        ):
            continue
        for item in node.body:
            if isinstance(item, ast.Return) and isinstance(item.value, ast.Constant) and item.value.value is None:
                guarded_return = True
                break
    assert guarded_return, "_build_ldss_scene_envelope must return None when human_actor_id is empty"


def assert_ldss_input_builder_preserves_human_actor_id(ldss_py: Path) -> None:
    """``build_ldss_input_from_session`` must pass human actor identity into LDSS state and actor lanes."""
    tree = ast.parse(ldss_py.read_text(encoding="utf-8"))
    fn = _module_function(tree, "build_ldss_input_from_session")
    assert fn is not None, "build_ldss_input_from_session must exist"
    arg_names = {arg.arg for arg in [*fn.args.args, *fn.args.kwonlyargs]}
    assert "human_actor_id" in arg_names, "build_ldss_input_from_session must accept human_actor_id"

    story_state = _assignment_value(fn, "story_session_state")
    actor_lanes = _assignment_value(fn, "actor_lane_context")
    assert isinstance(story_state, ast.Dict), "story_session_state must be built as a structured dict"
    assert isinstance(actor_lanes, ast.Dict), "actor_lane_context must be built as a structured dict"

    state_human = _dict_entry_value(story_state, "human_actor_id")
    lane_human = _dict_entry_value(actor_lanes, "human_actor_id")
    assert isinstance(state_human, ast.Name) and state_human.id == "human_actor_id"
    assert isinstance(lane_human, ast.Name) and lane_human.id == "human_actor_id"

    forbidden = _dict_entry_value(actor_lanes, "ai_forbidden_actor_ids")
    assert isinstance(forbidden, ast.List), "actor lanes must expose ai_forbidden_actor_ids"
    assert any(isinstance(item, ast.Name) and item.id == "human_actor_id" for item in forbidden.elts)


def assert_run_tests_registers_mvp4_preset(run_tests_py: Path) -> None:
    """``tests/run_tests.py`` must register the MVP4 CLI preset structurally, not by source substring."""
    tree = ast.parse(run_tests_py.read_text(encoding="utf-8"))
    has_cli_arg = False
    has_suite_assignment = False

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add_argument":
            if node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == "--mvp4":
                has_cli_arg = True
        if not isinstance(node, ast.If):
            continue
        test = node.test
        if not (
            isinstance(test, ast.Attribute)
            and test.attr == "mvp4"
            and isinstance(test.value, ast.Name)
            and test.value.id == "args"
        ):
            continue
        for item in node.body:
            if not isinstance(item, ast.Assign):
                continue
            for target in item.targets:
                if not (
                    isinstance(target, ast.Attribute)
                    and target.attr == "suite"
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "args"
                ):
                    continue
                if isinstance(item.value, ast.List):
                    values = {
                        elt.value for elt in item.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    }
                    if "gates" in values:
                        has_suite_assignment = True

    assert has_cli_arg, "tests/run_tests.py must register --mvp4 via argparse"
    assert has_suite_assignment, "--mvp4 preset must include the gates suite"


def _pytest_markers_from_ini(ini_path: Path) -> set[str]:
    if not ini_path.exists():
        return set()
    parser = configparser.ConfigParser()
    parser.read(ini_path, encoding="utf-8")
    if not parser.has_option("pytest", "markers"):
        return set()
    markers: set[str] = set()
    for line in parser.get("pytest", "markers").splitlines():
        token = line.strip().split(":", 1)[0].strip()
        if token:
            markers.add(token)
    return markers


def assert_pytest_marker_registered(marker: str, ini_paths: tuple[Path, ...]) -> None:
    """Check pytest marker registration through INI parsing instead of raw substring matching."""
    markers = set().union(*(_pytest_markers_from_ini(path) for path in ini_paths))
    assert marker in markers, f"{marker} marker must be registered in pytest.ini"


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


MVP4_EXECUTE_TURN_INTEGRATION_TIMEOUT_SECONDS = 300


def assert_manager_get_narrative_gov_summary_calls_builder(manager_py: Path) -> None:
    """``StoryRuntimeManager.get_narrative_gov_summary`` must call ``build_narrative_gov_summary`` (AST oracle)."""
    tree = _manager_diagnostics_tree(manager_py)
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "get_narrative_gov_summary":
                    calls = _collect_called_names(item)
                    assert "build_narrative_gov_summary" in calls, (
                        "get_narrative_gov_summary must call build_narrative_gov_summary"
                    )
                    return
    raise AssertionError("StoryRuntimeManager.get_narrative_gov_summary not found")


def assert_narrative_gov_template_renders_panel_contract(runtime_html: Path) -> None:
    """Admin runtime surface must expose narrative gov contract keys and authenticated admin fetch."""
    text = runtime_html.read_text(encoding="utf-8")
    assert 'data-testid="narrative-gov-summary"' in text, "runtime.html must expose data-testid for narrative gov root"
    runtime_js = runtime_html.resolve().parents[3] / "static" / "narrative_governance_runtime.js"
    js_text = runtime_js.read_text(encoding="utf-8") if runtime_js.is_file() else ""
    combined = text + "\n" + js_text
    assert "/api/v1/admin/narrative/runtime/gov-summary" in combined, (
        "narrative runtime UI must fetch authenticated admin gov-summary route"
    )
    assert "narrative_governance_runtime.js" in text, "runtime.html must load narrative_governance_runtime.js"
    for key in NARRATIVE_GOV_JSON_KEYS:
        assert key in combined, f"narrative runtime UI must reference panel key {key!r}"


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
        "tests/test_mvp4_diagnostics_integration.py",
        "-k",
        "test_execute_turn_produces_diagnostics_envelope",
        "-q",
        "--no-cov",
        "--tb=short",
    ]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(we),
            env=env,
            capture_output=True,
            text=True,
            timeout=MVP4_EXECUTE_TURN_INTEGRATION_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise AssertionError(
            "execute_turn diagnostics envelope integration timed out after "
            f"{MVP4_EXECUTE_TURN_INTEGRATION_TIMEOUT_SECONDS}s:\n"
            f"{exc.stdout or ''}\n{exc.stderr or ''}"
        ) from exc
    assert proc.returncode == 0, (
        "execute_turn diagnostics envelope integration must pass (see world-engine test):\n"
        f"{proc.stdout}\n{proc.stderr}"
    )
