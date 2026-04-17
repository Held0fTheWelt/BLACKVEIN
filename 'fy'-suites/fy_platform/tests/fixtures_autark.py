from __future__ import annotations

from pathlib import Path


def create_target_repo(base: Path) -> Path:
    repo = base / 'target_repo'
    (repo / 'src').mkdir(parents=True, exist_ok=True)
    (repo / 'docs' / 'api').mkdir(parents=True, exist_ok=True)
    (repo / 'tests').mkdir(parents=True, exist_ok=True)
    (repo / '.github' / 'workflows').mkdir(parents=True, exist_ok=True)
    (repo / 'docs').mkdir(exist_ok=True)

    (repo / 'pyproject.toml').write_text('[project]\nname = "toy-target"\nversion = "0.1.0"\n', encoding='utf-8')
    (repo / 'src' / 'app.py').write_text('def hello(name: str):\n    return f"Hello, {name}"\n\nclass Service:\n    def run(self):\n        return 1\n', encoding='utf-8')
    (repo / 'tests' / 'run_tests.py').write_text('TEST_TARGETS = {"unit": ["tests"]}\n', encoding='utf-8')
    (repo / '.github' / 'workflows' / 'ci.yml').write_text('name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n', encoding='utf-8')
    (repo / 'docs' / 'README.md').write_text('# Toy Target\n\nA tiny repo for adapter testing.\n', encoding='utf-8')
    (repo / 'docs' / 'api' / 'openapi.yaml').write_text(
        'openapi: 3.0.0\ninfo:\n  title: Toy API\n  version: 1.0.0\npaths:\n  /health:\n    get:\n      tags: [system]\n      summary: Health\n      responses:\n        "200":\n          description: OK\n',
        encoding='utf-8',
    )
    (repo / 'docker-compose.yml').write_text('services:\n  app:\n    image: python:3.11\n', encoding='utf-8')
    (repo / 'docker-up.py').write_text('print("docker up")\n', encoding='utf-8')
    return repo
