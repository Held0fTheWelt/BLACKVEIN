"""Tests for spaghetti_setup_audit (canonical md vs json mirror)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


_FIXTURE_MD = """# x

## Per-category trigger bars

| Category | Symbol | Bar |
| -------- | ------ | --- |
| a | **C1** | **10** |
| b | **C2** | **10** |
| c | **C3** | **10** |
| d | **C4** | **10** |
| e | **C5** | **10** |
| f | **C6** | **10** |
| g | **C7** | **10** |

## M7 category weights

| Symbol | Weight |
| ------ | ------ |
| **C1** | 0.2 |
| **C2** | 0.1 |
| **C3** | 0.2 |
| **C4** | 0.15 |
| **C5** | 0.1 |
| **C6** | 0.15 |
| **C7** | 0.1 |

## Composite reference

| Field | Value |
| ----- | ----- |
| **M7_ref** | **10** |
"""


class SpaghettiSetupAuditTests(unittest.TestCase):
    def test_parse_current_repo_setup_md(self) -> None:
        from despaghettify.tools.spaghetti_setup_audit import compute_m7_ref, parse_spaghetti_setup_md

        root = Path(__file__).resolve().parents[3]
        md_path = root / "despaghettify" / "spaghetti-setup.md"
        p = parse_spaghetti_setup_md(md_path.read_text(encoding="utf-8"))
        self.assertEqual(p["trigger_bars"]["C1"], 0.0)
        self.assertEqual(p["weights"]["C1"], 0.2)
        self.assertAlmostEqual(p["m7_ref"], 9.1, places=3)
        self.assertAlmostEqual(compute_m7_ref(p["trigger_bars"], p["weights"]), 9.1, places=3)

    def test_audit_json_matches_md(self) -> None:
        from despaghettify.tools.spaghetti_setup_audit import audit_setup

        root = Path(__file__).resolve().parents[3]
        rep = audit_setup(
            md_path=root / "despaghettify" / "spaghetti-setup.md",
            json_path=root / "despaghettify" / "spaghetti-setup.json",
            check_json_path=None,
        )
        self.assertTrue(rep["json_mirror_ok"], rep["drift_issues"])

    def test_sync_writes_json_matching_fixture_md(self) -> None:
        from despaghettify.tools.spaghetti_setup_audit import audit_setup, sync_setup_json_from_md

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "spaghetti-setup.json"
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            code, msgs, doc = sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            self.assertEqual(code, 0, msgs)
            self.assertEqual(doc["m7_ref"], 10)
            rep = audit_setup(md_path=md_p, json_path=js_p, check_json_path=None)
            self.assertTrue(rep["json_mirror_ok"], rep["drift_issues"])

    def test_sync_rejects_inconsistent_m7_ref(self) -> None:
        from despaghettify.tools.spaghetti_setup_audit import sync_setup_json_from_md

        bad = _FIXTURE_MD.replace("| **M7_ref** | **10** |", "| **M7_ref** | **99** |")
        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "out.json"
            md_p.write_text(bad, encoding="utf-8")
            code, msgs, _doc = sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=False)
            self.assertEqual(code, 2)
            self.assertTrue(msgs)
            self.assertFalse(js_p.is_file())

    def test_sync_dry_run_does_not_create_file(self) -> None:
        from despaghettify.tools.spaghetti_setup_audit import sync_setup_json_from_md

        with tempfile.TemporaryDirectory() as td:
            tdir = Path(td)
            md_p = tdir / "spaghetti-setup.md"
            js_p = tdir / "missing.json"
            md_p.write_text(_FIXTURE_MD, encoding="utf-8")
            code, _msgs, doc = sync_setup_json_from_md(md_path=md_p, json_path=js_p, dry_run=True)
            self.assertEqual(code, 0)
            self.assertFalse(js_p.is_file())
            self.assertEqual(doc["trigger_bars"]["C1"], 10)


if __name__ == "__main__":
    unittest.main()
