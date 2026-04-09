"""CLI tests for scripts/g9_threshold_validator.py (roadmap §6.9 arithmetic)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VALIDATOR = _REPO_ROOT / "scripts" / "g9_threshold_validator.py"
_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_TEMPLATE = (
    _REPO_ROOT / "docs" / "goc_evidence_templates" / "g9_experience_score_matrix.template.json"
)


def _run_validator(matrix_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(_VALIDATOR), str(matrix_path)],
        cwd=str(_REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_validator_pass_on_complete_high_scores() -> None:
    r = _run_validator(_FIXTURES / "g9_matrix_all_4_5.json")
    assert r.returncode == 0, r.stderr + r.stdout
    out = json.loads(r.stdout)
    assert out["complete"] is True
    assert out["pass_all"] is True
    assert "goc_roadmap_s5_primary_failure_fallback" in r.stdout


def test_validator_fails_when_failure_scenario_degradation_below_3_5() -> None:
    r = _run_validator(_FIXTURES / "g9_matrix_fail_failure_scenario_degradation.json")
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["complete"] is True
    assert out["pass_all"] is False
    assert out["rules"]["graceful_degradation_ge_3_5_failure_scenarios"] is False


def test_validator_allows_low_degradation_on_non_failure_scenario() -> None:
    """§6.9 degradation floor applies only to failure_oriented rows."""
    r = _run_validator(_FIXTURES / "g9_matrix_non_failure_low_degradation_ok.json")
    assert r.returncode == 0, r.stderr + r.stdout
    out = json.loads(r.stdout)
    assert out["complete"] is True
    assert out["pass_all"] is True


def test_validator_exit_zero_when_scores_incomplete() -> None:
    doc = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    r = _run_validator_write_temp(doc)

    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["complete"] is False


def test_validator_rejects_wrong_failure_oriented_for_s5() -> None:
    doc = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    for row in doc["scenarios"]:
        if row["scenario_id"] == "goc_roadmap_s5_primary_failure_fallback":
            row["failure_oriented"] = False
            break
    r = _run_validator_write_temp(doc)
    assert r.returncode == 1
    assert "conflicts with canonical" in r.stdout


def _run_validator_write_temp(doc: dict) -> subprocess.CompletedProcess[str]:
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as f:
        json.dump(doc, f)
        path = Path(f.name)
    try:
        return _run_validator(path)
    finally:
        path.unlink(missing_ok=True)


def test_public_template_matches_six_canonical_scenario_ids_in_order() -> None:
    doc = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
    ids = [row["scenario_id"] for row in doc["scenarios"]]
    assert ids == [
        "goc_roadmap_s1_direct_provocation",
        "goc_roadmap_s2_deflection_brevity",
        "goc_roadmap_s3_pressure_escalation",
        "goc_roadmap_s4_misinterpretation_correction",
        "goc_roadmap_s5_primary_failure_fallback",
        "goc_roadmap_s6_retrieval_heavy",
    ]
    s5 = next(r for r in doc["scenarios"] if r["scenario_id"].endswith("s5_primary_failure_fallback"))
    assert s5["failure_oriented"] is True
    others = [r for r in doc["scenarios"] if r is not s5]
    assert all(r["failure_oriented"] is False for r in others)
