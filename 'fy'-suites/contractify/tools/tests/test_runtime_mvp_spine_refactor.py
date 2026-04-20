from __future__ import annotations

from pathlib import Path

from contractify.tools.runtime_mvp_spine import PRECEDENCE_RULES, build_runtime_mvp_spine


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_runtime_mvp_spine_refactor_keeps_public_contract_surface(tmp_path: Path) -> None:
    _write(tmp_path / "docs" / "ADR" / "adr-0001-runtime-authority-in-world-engine.md", "# ADR-0001\n")
    _write(tmp_path / "docs" / "ADR" / "adr-0002-backend-session-surface-quarantine.md", "# ADR-0002\n")
    _write(tmp_path / "docs" / "ADR" / "adr-0003-scene-identity-canonical-surface.md", "# ADR-0003\n")
    _write(tmp_path / "docs" / "technical" / "runtime" / "runtime-authority-and-state-flow.md", "# Runtime\n")
    _write(tmp_path / "docs" / "technical" / "architecture" / "backend-runtime-classification.md", "# Backend\n")
    _write(tmp_path / "docs" / "technical" / "architecture" / "canonical_runtime_contract.md", "# Canonical\n")
    _write(tmp_path / "docs" / "technical" / "runtime" / "player_input_interpretation_contract.md", "# Input\n")
    contracts, projections, relations, unresolved, families = build_runtime_mvp_spine(tmp_path)
    assert PRECEDENCE_RULES[0]["tier"] == "runtime_authority"
    assert isinstance(contracts, list)
    assert isinstance(projections, list)
    assert isinstance(relations, list)
    assert isinstance(unresolved, list)
    assert isinstance(families, dict)
