from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SERVICE_DIRS = ('frontend', 'administration-tool', 'backend', 'world-engine', 'ai_stack', 'story_runtime_core', 'writers-room')
ROLE_MAP = {
    'admin': {
        'summary': 'Operate the administration interface and content governance surfaces.',
        'paths': ('administration-tool/', 'backend/app/api/v1/', 'docs/admin/', 'docs/governance/'),
    },
    'developer': {
        'summary': 'Implement and debug the repository across backend, engine, frontend, and AI stack surfaces.',
        'paths': ('backend/', 'world-engine/', 'frontend/', 'ai_stack/', 'story_runtime_core/', 'tests/'),
    },
    'operator': {
        'summary': 'Start, monitor, and troubleshoot the local stack and runtime-facing services.',
        'paths': ('docker-up.py', 'docker-compose.yml', 'docs/operations/', 'docs/testing/', '.github/workflows/'),
    },
    'writer': {
        'summary': 'Work with narrative content, Writers-Room flow, and module governance.',
        'paths': ('writers-room/', 'content/modules/', 'docs/MVPs/', 'docs/start-here/', 'backend/app/api/v1/writers_room_routes.py'),
    },
    'player': {
        'summary': 'Understand the player-facing experience and where the live runtime begins.',
        'paths': ('frontend/', 'docs/user/', 'docs/start-here/', 'world-engine/'),
    },
}


def _existing(paths: list[str], root: Path) -> list[str]:
    return [p for p in paths if (root / p).exists()]


def collect_repository_context(root: Path) -> dict[str, Any]:
    docs_root = root / 'docs'
    docs_dirs = sorted(p.name for p in docs_root.iterdir() if p.is_dir()) if docs_root.is_dir() else []
    services = [name for name in SERVICE_DIRS if (root / name).exists()]
    workflows = sorted(p.name for p in (root / '.github/workflows').glob('*.yml')) if (root / '.github/workflows').is_dir() else []
    key_docs = [
        'README.md',
        'docs/start-here/README.md',
        'docs/technical/README.md',
        'docs/testing/README.md',
        'docs/operations/RUNBOOK.md',
        'tests/TESTING.md',
        'docker-up.py',
        'tests/run_tests.py',
    ]
    return {
        'services': services,
        'docs_dirs': docs_dirs,
        'workflows': workflows,
        'key_docs': _existing(key_docs, root),
    }


def _simple_overview(context: dict[str, Any]) -> str:
    services = ', '.join(context['services'])
    lines = [
        '# World of Shadows — simple overview',
        '',
        'World of Shadows is a multi-service narrative platform.',
        f'The repository currently exposes these major service/package areas: **{services}**.',
        '',
        '## What starts the local stack',
        '',
        '- `docker-up.py` is the operator-friendly entry path for Docker Compose.',
        '- `docker-compose.yml` declares the main local stack services.',
        '- `tests/run_tests.py` is the canonical multi-suite test runner.',
        '',
        '## Where to begin reading',
        '',
    ]
    lines.extend(f'- `{item}`' for item in context['key_docs'])
    return "\n".join(lines) + "\n"


def _technical_reference(context: dict[str, Any]) -> str:
    lines = [
        '# World of Shadows — technical reference',
        '',
        '## Repository service map',
        '',
    ]
    lines.extend(f'- `{svc}/`' for svc in context['services'])
    lines.extend([
        '',
        '## Documentation domains',
        '',
        ', '.join(context['docs_dirs']),
        '',
        '## Automation and gates',
        '',
        ', '.join(context['workflows']),
        '',
        '## Canonical operational entrypoints',
        '',
        '- `docker-up.py` — local Docker lifecycle',
        '- `docker-compose.yml` — stack declaration',
        '- `tests/run_tests.py` — multi-suite test runner',
        '- `.github/workflows/` — GitHub Actions CI gates',
    ])
    return "\n".join(lines) + "\n"


def _role_doc(role: str, root: Path) -> str:
    info = ROLE_MAP[role]
    lines = [
        f'# {role.capitalize()} documentation',
        '',
        info['summary'],
        '',
        '## Relevant repository paths',
        '',
    ]
    lines.extend(f'- `{p}`' for p in _existing(list(info['paths']), root))
    return "\n".join(lines) + "\n"


def generate_documentation(root: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    context = collect_repository_context(root)
    generated: list[str] = []
    simple = out_dir / 'simple' / 'PLATFORM_OVERVIEW.md'
    technical = out_dir / 'technical' / 'SYSTEM_REFERENCE.md'
    simple.parent.mkdir(parents=True, exist_ok=True)
    technical.parent.mkdir(parents=True, exist_ok=True)
    simple.write_text(_simple_overview(context), encoding='utf-8')
    technical.write_text(_technical_reference(context), encoding='utf-8')
    generated.extend([simple.relative_to(root).as_posix(), technical.relative_to(root).as_posix()])
    roles_root = out_dir / 'roles'
    for role in ROLE_MAP:
        role_path = roles_root / role / 'README.md'
        role_path.parent.mkdir(parents=True, exist_ok=True)
        role_path.write_text(_role_doc(role, root), encoding='utf-8')
        generated.append(role_path.relative_to(root).as_posix())
    return {
        'suite': 'documentify',
        'generated_count': len(generated),
        'services': context['services'],
        'docs_dirs': context['docs_dirs'],
        'workflows': context['workflows'],
        'generated_files': generated,
    }


def render_markdown(summary: dict[str, Any], out_dir: Path, root: Path) -> str:
    lines = ['# Documentify generation report', '', '## Summary', '']
    lines.append(f"- **generated_count**: `{summary['generated_count']}`")
    lines.append(f"- **output_root**: `{out_dir.relative_to(root).as_posix()}`")
    lines.extend(['', '## Services', ''])
    lines.extend(f'- `{svc}`' for svc in summary.get('services', []))
    lines.extend(['', '## Generated files', ''])
    lines.extend(f'- `{path}`' for path in summary.get('generated_files', []))
    return "\n".join(lines) + "\n"


def write_generation_bundle(root: Path, out_dir_rel: str, json_rel: str, md_rel: str) -> dict[str, Any]:
    out_dir = root / out_dir_rel
    summary = generate_documentation(root, out_dir)
    json_path = root / json_rel
    md_path = root / md_rel
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2), encoding='utf-8')
    md_path.write_text(render_markdown(summary, out_dir, root), encoding='utf-8')
    return summary
