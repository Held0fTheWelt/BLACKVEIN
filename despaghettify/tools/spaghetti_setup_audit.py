"""Read **spaghetti-setup.md** (canonical policy digits) and compare mirrors / scans.

``spaghetti-setup.json`` is a machine mirror — ``setup-audit`` reports drift vs Markdown.
``setup-sync`` writes the JSON mirror from the Markdown tables (after consistency checks).
``check --with-metrics`` JSON is optional for live **Anteil %** vs bars from **MD**.

Does **not** write ``spaghetti-setup.md``; edit policy there, then ``setup-sync`` or hand-edit JSON.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _md_section(md_text: str, heading_prefix: str) -> str:
    """Slice from ``## {heading_prefix}`` (line may continue, e.g. ``(**M7_ref**)``) to the next ``## ``."""
    needle = f"## {heading_prefix}"
    idx = md_text.find(needle)
    if idx < 0:
        raise ValueError(f"spaghetti-setup.md: missing section starting with {needle!r}")
    nxt = md_text.find("\n## ", idx + 1)
    if nxt >= 0:
        return md_text[idx:nxt]
    return md_text[idx:]


def parse_spaghetti_setup_md(md_text: str) -> dict[str, Any]:
    """Extract trigger_bars, weights, m7_ref from Markdown (canonical source)."""
    bars: dict[str, float] = {}
    weights: dict[str, float] = {}
    m7_ref: float | None = None

    bars_sec = _md_section(md_text, "Per-category trigger bars")
    for line in bars_sec.splitlines():
        m_bar = re.match(r"^\|[^|]+\|\s*\*\*C(\d)\*\*\s*\|\s*\*\*([\d.]+)\*\*", line.strip())
        if m_bar:
            bars[f"C{m_bar.group(1)}"] = float(m_bar.group(2))

    w_sec = _md_section(md_text, "M7 category weights")
    for line in w_sec.splitlines():
        m_w = re.match(r"^\|\s*\*\*C(\d)\*\*\s*\|\s*([\d.]+)\s*\|", line.strip())
        if m_w:
            weights[f"C{m_w.group(1)}"] = float(m_w.group(2))

    ref_sec = _md_section(md_text, "Composite reference")
    for line in ref_sec.splitlines():
        m_ref = re.match(
            r"^\|\s*\*\*M7_ref\*\*[^|]*\|\s*\*\*([\d.]+)\*\*\s*\|",
            line.strip(),
        )
        if m_ref:
            m7_ref = float(m_ref.group(1))
            break

    missing_b = [f"C{i}" for i in range(1, 8) if f"C{i}" not in bars]
    missing_w = [f"C{i}" for i in range(1, 8) if f"C{i}" not in weights]
    if missing_b:
        raise ValueError(f"spaghetti-setup.md: missing bars for {missing_b}")
    if missing_w:
        raise ValueError(f"spaghetti-setup.md: missing weights for {missing_w}")
    if m7_ref is None:
        raise ValueError("spaghetti-setup.md: could not parse M7_ref from composite table")

    return {"trigger_bars": bars, "weights": weights, "m7_ref": m7_ref}


def compute_m7_ref(bars: dict[str, float], weights: dict[str, float]) -> float:
    return sum(float(weights[k]) * float(bars[k]) for k in (f"C{i}" for i in range(1, 8)))


SETUP_JSON_SCHEMA_VERSION = 1
SETUP_JSON_DESCRIPTION = (
    "Mirror of spaghetti-setup.md. trigger_bars and m7_ref apply to operational anteil_pct "
    "(real %), not to ast_heuristic_v2 trigger scores."
)


def build_setup_json_document(parsed_md: dict[str, Any]) -> dict[str, Any]:
    """Machine mirror object from ``parse_spaghetti_setup_md`` result (ordered keys for diffs)."""
    bars_in = parsed_md["trigger_bars"]
    weights_in = parsed_md["weights"]
    trigger_bars: dict[str, int | float] = {}
    weights: dict[str, float] = {}
    for i in range(1, 8):
        k = f"C{i}"
        b = float(bars_in[k])
        trigger_bars[k] = int(b) if b == int(b) else b
        weights[k] = float(weights_in[k])
    m7 = float(parsed_md["m7_ref"])
    m7_out = int(m7) if m7 == int(m7) else round(m7, 4)
    return {
        "schema_version": SETUP_JSON_SCHEMA_VERSION,
        "description": SETUP_JSON_DESCRIPTION,
        "trigger_bars": trigger_bars,
        "weights": weights,
        "m7_ref": m7_out,
    }


def validate_md_m7_ref_consistency(parsed_md: dict[str, Any], *, tol: float = 1e-4) -> str | None:
    """Return error message if ``M7_ref`` in the md table disagrees with bars×weights; else ``None``."""
    recomputed = compute_m7_ref(parsed_md["trigger_bars"], parsed_md["weights"])
    tab = float(parsed_md["m7_ref"])
    if abs(recomputed - tab) > tol:
        return (
            f"M7_ref in markdown table ({tab}) != recomputed Σ(weight×bar) ({recomputed:.6f}); "
            "fix the Composite reference row or the bars/weights tables."
        )
    return None


def sync_setup_json_from_md(
    *,
    md_path: Path,
    json_path: Path,
    dry_run: bool = False,
    tol: float = 1e-4,
) -> tuple[int, list[str], dict[str, Any]]:
    """Write ``json_path`` from ``md_path`` tables.

    Returns ``(exit_code, messages, document)`` — exit **0** on success, **2** if md invalid or inconsistent.
    """
    msgs: list[str] = []
    try:
        md_text = md_path.read_text(encoding="utf-8")
        parsed = parse_spaghetti_setup_md(md_text)
    except (OSError, UnicodeError, ValueError) as e:
        return 2, [str(e)], {}

    err = validate_md_m7_ref_consistency(parsed, tol=tol)
    if err:
        return 2, [err], {}

    doc = build_setup_json_document(parsed)
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    if dry_run:
        return 0, [], doc

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(text, encoding="utf-8")
    msgs.append(f"wrote {json_path.as_posix()} from {md_path.as_posix()}")
    return 0, msgs, doc


def load_setup_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def audit_setup(
    *,
    md_path: Path,
    json_path: Path,
    check_json_path: Path | None,
    tol: float = 1e-4,
) -> dict[str, Any]:
    md = parse_spaghetti_setup_md(md_path.read_text(encoding="utf-8"))
    js = load_setup_json(json_path)
    js_bars = {f"C{i}": float(js["trigger_bars"][f"C{i}"]) for i in range(1, 8)}
    js_w = {f"C{i}": float(js["weights"][f"C{i}"]) for i in range(1, 8)}
    js_ref = float(js["m7_ref"])

    md_ref_computed = compute_m7_ref(md["trigger_bars"], md["weights"])
    issues: list[str] = []

    def _cmp(name: str, a: float, b: float) -> None:
        if abs(a - b) > tol:
            issues.append(f"{name}: md={a} json={b}")

    for k in (f"C{i}" for i in range(1, 8)):
        _cmp(f"bar {k}", md["trigger_bars"][k], js_bars[k])
        _cmp(f"weight {k}", md["weights"][k], js_w[k])
    _cmp("m7_ref", md["m7_ref"], js_ref)

    md_internal_ok = abs(md_ref_computed - md["m7_ref"]) <= tol
    if not md_internal_ok:
        issues.append(
            f"M7_ref in md ({md['m7_ref']}) != recomputed from md bars×weights ({md_ref_computed:.4f})"
        )

    scan: dict[str, Any] | None = None
    if check_json_path and check_json_path.is_file():
        chk = json.loads(check_json_path.read_text(encoding="utf-8"))
        mb = (chk.get("metrics_bundle") or {}) if isinstance(chk, dict) else {}
        score = mb.get("score") or {}
        cats = score.get("categories") or {}
        anteil = {k: float(cats[k]["anteil_pct"]) for k in cats if k.startswith("C")}
        m7a = float(score.get("m7_anteil_pct_gewichtet") or mb.get("metric_a", {}).get("m7", 0.0))
        fires = {k: anteil[k] > md["trigger_bars"][k] for k in anteil}
        comp = m7a >= md["m7_ref"]
        scan = {
            "anteil_pct": anteil,
            "m7_anteil_pct_gewichtet": m7a,
            "per_category_would_fire_vs_md_bars": fires,
            "composite_would_fire_vs_md_m7_ref": comp,
            "trigger_policy_would_fire": any(fires.values()) or comp,
        }

    return {
        "canonical": "spaghetti-setup.md",
        "md_path": md_path.as_posix(),
        "json_path": json_path.as_posix(),
        "parsed_md": md,
        "m7_ref_recomputed_from_md": round(md_ref_computed, 4),
        "json_mirror_ok": len(issues) == 0,
        "drift_issues": issues,
        "scan": scan,
    }


def cmd_setup_audit(args: argparse.Namespace) -> int:
    root = _repo_root()
    md = Path(args.setup_md.strip())
    sj = Path(args.setup_json.strip())
    if not md.is_absolute():
        md = root / md
    if not sj.is_absolute():
        sj = root / sj
    cj = Path(args.check_json.strip()) if getattr(args, "check_json", "").strip() else None
    if cj and not cj.is_absolute():
        cj = root / cj

    rep = audit_setup(md_path=md, json_path=sj, check_json_path=cj)
    if getattr(args, "json", False):
        print(json.dumps(rep, indent=2))
    else:
        print("Canonical policy:", rep["canonical"], rep["md_path"])
        print("M7_ref (from md table):", rep["parsed_md"]["m7_ref"])
        print("M7_ref recomputed (bars x weights):", rep["m7_ref_recomputed_from_md"])
        if rep["drift_issues"]:
            print("DRIFT (fix spaghetti-setup.json to match md):")
            for x in rep["drift_issues"]:
                print(" ", x)
        else:
            print("JSON mirror: OK (matches md bars/weights/m7_ref).")
        if rep.get("scan"):
            s = rep["scan"]
            print("Scan vs md bars (Anteil %):")
            for k in sorted(s["anteil_pct"]):
                b = rep["parsed_md"]["trigger_bars"][k]
                a = s["anteil_pct"][k]
                fire = s["per_category_would_fire_vs_md_bars"][k]
                print(f"  {k}: anteil={a:.4f} bar={b} fire={fire}")
            print("  M7_anteil:", round(s["m7_anteil_pct_gewichtet"], 4), "m7_ref(md):", rep["parsed_md"]["m7_ref"])
            print("  composite fire:", s["composite_would_fire_vs_md_m7_ref"])
            print("  any policy fire:", s["trigger_policy_would_fire"])
    return 1 if rep["drift_issues"] else 0


def cmd_setup_sync(args: argparse.Namespace) -> int:
    root = _repo_root()
    md = Path(args.setup_md.strip())
    sj = Path(args.setup_json.strip())
    if not md.is_absolute():
        md = root / md
    if not sj.is_absolute():
        sj = root / sj
    dry = bool(getattr(args, "dry_run", False))
    code, msgs, doc = sync_setup_json_from_md(md_path=md, json_path=sj, dry_run=dry)
    if code != 0:
        for m in msgs:
            print(m, file=sys.stderr)
        return code
    if dry:
        print(
            f"# dry-run: would write {sj.as_posix()} from {md.as_posix()}",
            file=sys.stderr,
        )
        print(json.dumps(doc, indent=2, ensure_ascii=False))
        return 0
    for m in msgs:
        print(m)
    return 0


def main_cli() -> int:
    p = argparse.ArgumentParser(description="Audit or sync spaghetti-setup.md ↔ JSON mirror.")
    p.add_argument(
        "--sync",
        action="store_true",
        help="Write spaghetti-setup.json from Markdown tables (default: audit only).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="With --sync: print JSON to stdout, do not write (stderr shows target path).",
    )
    p.add_argument(
        "--setup-md",
        default="despaghettify/spaghetti-setup.md",
        help="Canonical policy Markdown (repo-relative ok).",
    )
    p.add_argument(
        "--setup-json",
        default="despaghettify/spaghetti-setup.json",
        help="Machine mirror JSON (repo-relative ok).",
    )
    p.add_argument(
        "--check-json",
        default="",
        help="Audit only: optional path to check --with-metrics JSON for Anteil vs md bars.",
    )
    p.add_argument("--json", action="store_true", help="Audit only: emit machine JSON report on stdout.")
    args = p.parse_args()
    if args.sync and (args.check_json.strip() or args.json):
        print("--sync is incompatible with --check-json / --json (use audit mode without --sync).", file=sys.stderr)
        return 2
    if args.sync:
        return cmd_setup_sync(args)
    return cmd_setup_audit(args)


if __name__ == "__main__":
    raise SystemExit(main_cli())
