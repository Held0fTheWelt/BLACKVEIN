from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import yaml

REQUIRED_WORKFLOWS = (
    'backend-tests.yml',
    'admin-tests.yml',
    'engine-tests.yml',
    'ai-stack-tests.yml',
    'quality-gate.yml',
    'pre-deployment.yml',
    'compose-smoke.yml',
)
REQUIRED_HUB_SCRIPTS = (
    'despag-check',
    'wos-despag',
    'postmanify',
    'docify',
    'contractify',
    'fy-platform',
    'dockerify',
    'testify',
    'documentify',
)


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8', errors='replace') if path.is_file() else ''


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    return data if isinstance(data, dict) else {}


def _module_ast(path: Path) -> ast.Module | None:
    source = _read(path)
    if not source:
        return None
    return ast.parse(source)


def _find_named_value(module: ast.Module | None, variable_name: str) -> ast.AST | None:
    if module is None:
        return None
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == variable_name:
                    return node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == variable_name:
            return node.value
    return None


def _literal_from_module(path: Path, variable_name: str) -> Any:
    module = _module_ast(path)
    value_node = _find_named_value(module, variable_name)
    if value_node is None:
        return None
    try:
        return ast.literal_eval(value_node)
    except Exception:
        return None


def _dict_keys_from_module(path: Path, variable_name: str) -> list[str]:
    module = _module_ast(path)
    value_node = _find_named_value(module, variable_name)
    if not isinstance(value_node, ast.Dict):
        return []
    keys: list[str] = []
    for key_node in value_node.keys:
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            keys.append(key_node.value)
    return keys


def _workflow_on_payload(data: dict[str, Any]) -> Any:
    if 'on' in data:
        return data['on']
    if True in data:
        return data[True]
    return {}


def audit_test_governance(root: Path) -> dict[str, Any]:
    pyproject_text = _read(root / 'pyproject.toml')
    run_tests_path = root / 'tests/run_tests.py'
    workflows_dir = root / '.github/workflows'
    workflow_files = sorted(p.name for p in workflows_dir.glob('*.yml'))
    scripts: dict[str, str] = {}
    in_scripts = False
    for line in pyproject_text.splitlines():
        if line.strip() == '[project.scripts]':
            in_scripts = True
            continue
        if in_scripts and line.startswith('['):
            break
        if in_scripts and '=' in line:
            key, _, value = line.partition('=')
            scripts[key.strip()] = value.strip().strip('"')
    suite_targets = _dict_keys_from_module(run_tests_path, 'SUITE_PYTEST_TARGETS')
    all_sequence = list(_literal_from_module(run_tests_path, 'ALL_SUITE_SEQUENCE') or [])
    display_names = _literal_from_module(run_tests_path, 'SUITE_DISPLAY_NAMES') or {}
    workflow_summary = {}
    for wf in workflow_files:
        data = _load_yaml(workflows_dir / wf)
        jobs = data.get('jobs') if isinstance(data.get('jobs'), dict) else {}
        on_payload = json.dumps(_workflow_on_payload(data))
        workflow_summary[wf] = {
            'job_count': len(jobs),
            'has_path_filters': 'paths' in on_payload,
            'workflow_dispatch': 'workflow_dispatch' in on_payload,
        }
    findings = []
    missing_workflows = [wf for wf in REQUIRED_WORKFLOWS if wf not in workflow_files]
    if missing_workflows:
        findings.append({'id': 'TESTIFY-MISSING-WORKFLOWS', 'severity': 'high', 'summary': f"Missing workflows: {', '.join(missing_workflows)}"})
    missing_scripts = [name for name in REQUIRED_HUB_SCRIPTS if name not in scripts]
    if missing_scripts:
        findings.append({'id': 'TESTIFY-MISSING-HUB-SCRIPTS', 'severity': 'high', 'summary': f"Missing root pyproject suite scripts: {', '.join(missing_scripts)}"})
    if 'backend' not in suite_targets or 'ai_stack' not in suite_targets:
        findings.append({'id': 'TESTIFY-RUNNER-DRIFT', 'severity': 'medium', 'summary': 'tests/run_tests.py no longer exposes the expected multi-suite targets.'})
    warnings = []
    if 'frontend-tests.yml' not in workflow_files:
        warnings.append('No standalone frontend-tests.yml workflow detected; frontend quality currently relies on broader gates or local runner usage.')
    strengths = []
    if not missing_workflows:
        strengths.append('Core GitHub Actions workflow set is present for backend, admin, engine, AI stack, quality gate, pre-deployment, and compose smoke.')
    if not missing_scripts:
        strengths.append('Root pyproject exports all fy-suite console scripts, including dockerify, testify, and documentify.')
    if all_sequence:
        strengths.append(f"tests/run_tests.py declares canonical --suite all order: {', '.join(all_sequence)}.")
    if suite_targets:
        strengths.append(f"tests/run_tests.py declares explicit suite targets for: {', '.join(sorted(suite_targets))}.")
    component_pyprojects = []
    for rel in ('backend/pyproject.toml', 'frontend/pyproject.toml', 'administration-tool/pyproject.toml', 'world-engine/pyproject.toml', 'ai_stack/pyproject.toml', 'story_runtime_core/pyproject.toml'):
        p = root / rel
        component_pyprojects.append({'path': rel, 'exists': p.is_file()})
    return {
        'suite': 'testify',
        'summary': {
            'workflow_count': len(workflow_files),
            'runner_suite_count': len(suite_targets),
            'hub_script_count': len(scripts),
            'finding_count': len(findings),
            'warning_count': len(warnings),
        },
        'runner': {
            'suite_targets': sorted(suite_targets),
            'all_sequence': all_sequence,
            'display_names': display_names,
        },
        'hub_pyproject': {
            'scripts': scripts,
            'packages_where_clause_present': "where = [\"'fy'-suites\"]" in pyproject_text,
        },
        'workflows': workflow_summary,
        'component_pyprojects': component_pyprojects,
        'strengths': strengths,
        'warnings': warnings,
        'findings': findings,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    lines = ['# Testify audit report', '', '## Summary', '']
    for key, value in payload.get('summary', {}).items():
        lines.append(f'- **{key}**: `{value}`')
    lines.extend(['', '## Runner coverage', ''])
    lines.append(f"- `tests/run_tests.py` suites: `{payload.get('runner', {}).get('suite_targets', [])}`")
    lines.append(f"- `--suite all` order: `{payload.get('runner', {}).get('all_sequence', [])}`")
    lines.extend(['', '## Workflow coverage', ''])
    for name, data in sorted(payload.get('workflows', {}).items()):
        lines.append(f"- **{name}** — jobs: `{data.get('job_count')}`, path filters: `{data.get('has_path_filters')}`, workflow_dispatch: `{data.get('workflow_dispatch')}`")
    lines.extend(['', '## Strengths', ''])
    for item in payload.get('strengths', []):
        lines.append(f'- {item}')
    lines.extend(['', '## Warnings', ''])
    if payload.get('warnings'):
        for item in payload['warnings']:
            lines.append(f'- {item}')
    else:
        lines.append('- None.')
    lines.extend(['', '## Findings', ''])
    if payload.get('findings'):
        for item in payload['findings']:
            lines.append(f"- `{item['id']}` ({item['severity']}): {item['summary']}")
    else:
        lines.append('- None.')
    return "\n".join(lines) + "\n"


def write_audit_bundle(root: Path, json_rel: str, md_rel: str) -> dict[str, Any]:
    payload = audit_test_governance(root)
    json_path = root / json_rel
    md_path = root / md_rel
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    md_path.write_text(render_markdown(payload), encoding='utf-8')
    return payload
