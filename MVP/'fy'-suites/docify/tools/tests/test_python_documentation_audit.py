from __future__ import annotations

from pathlib import Path

import json

from docify.tools.python_documentation_audit import audit_file, main


def test_audit_file_flags_missing_module_docstring(tmp_path: Path) -> None:
    path = tmp_path / "sample.py"
    path.write_text("def public() -> int:\n    return 1\n", encoding="utf-8")
    findings = audit_file(path, rel_path="sample.py", include_private=False)
    kinds = {f.kind for f in findings}
    assert "module" in kinds
    assert "function" in kinds


def test_audit_skips_visit_methods_on_private_visitor(tmp_path: Path) -> None:
    path = tmp_path / "visitor.py"
    path.write_text(
        "import ast\n\n"
        "class _V(ast.NodeVisitor):\n"
        "    def visit_Name(self, node: ast.Name) -> None:\n"
        "        return None\n",
        encoding="utf-8",
    )
    findings = audit_file(path, rel_path="visitor.py", include_private=False)
    names = {f.name for f in findings}
    assert "visit_Name" not in names


def test_json_mode_can_emit_shared_envelope(tmp_path: Path) -> None:
    src = tmp_path / "pkg"
    src.mkdir()
    py_file = src / "sample.py"
    py_file.write_text("def f():\n    return 1\n", encoding="utf-8")
    out = tmp_path / "audit.json"
    env = tmp_path / "audit.envelope.json"
    code = main(
        [
            "--repo-root",
            str(tmp_path),
            "--root",
            "pkg",
            "--json",
            "--out",
            str(out),
            "--envelope-out",
            str(env),
            "--exit-zero",
        ]
    )
    assert code == 0
    assert out.is_file()
    assert env.is_file()
    payload = json.loads(env.read_text(encoding="utf-8"))
    assert payload["envelopeVersion"] == "1"
    assert isinstance(payload["findings"], list)
    assert payload["deprecations"]
    dep_md = env.with_suffix(env.suffix + ".deprecations.md")
    assert dep_md.is_file()
