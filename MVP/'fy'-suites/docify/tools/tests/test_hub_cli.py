from __future__ import annotations

from pathlib import Path

from docify.tools.hub_cli import main, parse_open_doc_ids


def test_parse_open_doc_ids_sorts_and_dedupes() -> None:
    md = """
## Backlog
| **DOC-002** | a |
| **DOC-001** | b |
| **DOC-002** | dup |
"""
    assert parse_open_doc_ids(md) == ["DOC-001", "DOC-002"]


def test_open_doc_cli_with_explicit_input(tmp_path: Path, capsys) -> None:
    """CLI must not require monorepo pyproject when --input points at a backlog file."""
    p = tmp_path / "documentation_implementation_input.md"
    p.write_text(
        "| **DOC-001** | cat | slice | OPEN | note |\n",
        encoding="utf-8",
    )
    code = main(["open-doc", "--input", str(p)])
    assert code == 0
    assert capsys.readouterr().out.strip() == "DOC-001"


def test_open_doc_monorepo_default_uses_repo_when_available(tmp_path: Path, monkeypatch, capsys) -> None:
    """When --input is omitted, behaviour still depends on repo_root (smoke only in-layout)."""
    from docify.tools import hub_cli as hc

    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / "pyproject.toml").write_text('name = "world-of-shadows-hub"\n', encoding="utf-8")
    suites = root / "'fy'-suites"
    hub = suites / "docify"
    hub.mkdir(parents=True)
    (hub / "documentation_implementation_input.md").write_text(
        "| **DOC-042** | x | y | OPEN | z |\n",
        encoding="utf-8",
    )

    def fake_root() -> Path:
        return root.resolve()

    monkeypatch.setattr(hc, "repo_root", fake_root)
    code = hc.main(["open-doc"])
    assert code == 0
    assert capsys.readouterr().out.strip() == "DOC-042"
