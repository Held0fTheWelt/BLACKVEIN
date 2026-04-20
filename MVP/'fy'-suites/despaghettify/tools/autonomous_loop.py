"""Autonomous despag loop state machine — file-backed session for CLI + agents."""
from __future__ import annotations

import json
import re
import subprocess
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from despaghettify.tools.repo_paths import despag_hub_dir, despag_hub_rel_posix, repo_root

try:
    ROOT = repo_root()
except RuntimeError:
    ROOT = Path.cwd()
try:
    HUB = despag_hub_dir(ROOT)
except RuntimeError:
    HUB = Path(__file__).resolve().parents[1]
try:
    HUB_REL = despag_hub_rel_posix(ROOT)
except RuntimeError:
    HUB_REL = HUB.name
STATE_DIR = HUB / "state" / "artifacts" / "autonomous_loop"
STATE_FILE = STATE_DIR / "autonomous_state.json"
INPUT_LIST = HUB / "despaghettification_implementation_input.md"
SETUP_JSON = HUB / "spaghetti-setup.json"

OPEN_DS_ROW = re.compile(r"^\|\s*\*\*(DS-\d+)\*\*\s*\|")


def ds_numeric_id(ds: str) -> int:
    """
    Implement ``ds_numeric_id`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        ds: Ds for this call. Declared type: ``str``. (positional or keyword)

    Returns:
        Value typed as ``int`` for downstream use.

    """
    m = re.fullmatch(r"(?i)DS-(\d+)", ds.strip())
    if not m:
        return -1
    return int(m.group(1), 10)


def open_ds_row_still_open(open_ids: list[str], solved_ds: str) -> bool:
    """True if the numeric DS id still appears in the open list (any zero-padding)."""
    n = ds_numeric_id(solved_ds)
    if n < 0:
        return True
    return any(ds_numeric_id(x) == n for x in open_ids)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git_head() -> str | None:
    git_dir = ROOT / ".git"
    if not git_dir.exists():
        return None
    try:
        cp = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if cp.returncode != 0:
            return None
        return (cp.stdout or "").strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_dirty_paths(allowed_prefixes: tuple[str, ...]) -> list[str]:
    """Return modified paths under git that are not under allowed ignored prefixes."""
    try:
        cp = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if cp.returncode != 0:
            return []
    except (OSError, subprocess.SubprocessError):
        return []
    bad: list[str] = []
    for line in (cp.stdout or "").splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[-1].strip()
        ok = any(path.replace("\\", "/").startswith(p) for p in allowed_prefixes)
        if not ok:
            bad.append(path)
    return bad


def collect_open_ds_ids_from_md(md: str) -> list[str]:
    """
    Implement ``collect_open_ds_ids_from_md`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        md: Md for this call. Declared type: ``str``. (positional or keyword)

    Returns:
        Ordered collection typed as ``list[str]``; may be empty.

    """
    start = md.find("## Information input list")
    end = md.find("## Recommended implementation order")
    if start == -1 or end == -1 or end <= start:
        return []
    section = md[start:end]
    seen: set[str] = set()
    for line in section.splitlines():
        m = OPEN_DS_ROW.match(line)
        if m:
            seen.add(m.group(1))
    return sorted(seen, key=lambda s: int(s.split("-")[1]))


def collect_open_ds_ids() -> list[str]:
    """
    Implement ``collect_open_ds_ids`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Returns:
        Ordered collection typed as ``list[str]``; may be empty.

    """
    if not INPUT_LIST.is_file():
        return []
    return collect_open_ds_ids_from_md(INPUT_LIST.read_text(encoding="utf-8", errors="replace"))


def load_state() -> dict[str, Any] | None:
    """
    Read State from configuration, disk, or remote sources.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Returns:
        Mapping typed as ``dict[str, Any] | None``; keys and values follow caller contracts.

    """
    if not STATE_FILE.is_file():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def save_state(data: dict[str, Any]) -> None:
    """
    Persist State so it survives the current process.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        data:
            Primary payload or structured input for the operation, typed as ``dict[str,
            Any]``. (positional or keyword)

    Returns:
        This routine returns ``None``; effects are via parameters, state, or I/O.

    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data["updated_at_utc"] = _utc_now()
    STATE_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


AdvanceKind = Literal["backlog_implement", "backlog_solve", "main_check", "main_solve"]


@dataclass
class AdvanceResult:
    """
    Group state and helpers for ``Advanceresult`` within this module.

    Attributes:
        ``exit_code``, ``message``, ``ok``, ``state`` are part of the public shape of this type.

    """
    ok: bool
    exit_code: int
    message: str
    state: dict[str, Any] | None = None


def _validate_state_shape(s: dict[str, Any]) -> str | None:
    if s.get("schema_version") != 1:
        return "schema_version must be 1"
    for k in ("session_id", "phase", "last_kind"):
        if k not in s:
            return f"missing field {k}"
    if s["phase"] not in ("backlog", "main"):
        return "invalid phase"
    if s["last_kind"] not in ("init", "backlog_implement", "backlog_solve", "main_check", "main_solve"):
        return "invalid last_kind"
    return None


def init_session(*, force: bool) -> tuple[int, str, dict[str, Any]]:
    """Create new autonomous session state. Returns (exit_code, message, state)."""
    if load_state() is not None and not force:
        return 2, "autonomous_state.json already exists; use --force to re-init", {}
    open_now = collect_open_ds_ids()
    phase: Literal["backlog", "main"] = "backlog" if open_now else "main"
    head = _git_head()
    state: dict[str, Any] = {
        "schema_version": 1,
        "session_id": str(uuid.uuid4()),
        "phase": phase,
        "last_kind": "init",
        "open_ds_at_init": list(open_now),
        "last_open_ds_snapshot": list(open_now),
        "recent_check_json_paths": [],
        "head_sha_expected": head,
        "stall_counter": 0,
        "events": [{"at_utc": _utc_now(), "kind": "init", "ds": None, "check_json": None}],
    }
    save_state(state)
    return 0, "initialized", state


def _append_event(state: dict[str, Any], kind: str, ds: str | None, check_json: str | None) -> None:
    ev = state.setdefault("events", [])
    ev.append({"at_utc": _utc_now(), "kind": kind, "ds": ds, "check_json": check_json})
    if len(ev) > 500:
        del ev[:-400]


def advance(
    kind: AdvanceKind,
    *,
    ds: str | None,
    check_json: str | None,
) -> AdvanceResult:
    """
    Implement ``advance`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Args:
        kind: Kind for this call. Declared type: ``AdvanceKind``. (positional or keyword)
        ds: Ds for this call. Declared type: ``str | None``. (keyword-only)
        check_json: Check Json for this call. Declared type: ``str | None``. (keyword-only)

    Returns:
        Value typed as ``AdvanceResult`` for downstream use.

    """
    state = load_state()
    if state is None:
        return AdvanceResult(False, 2, "no session; run autonomous-init first", None)
    err = _validate_state_shape(state)
    if err:
        return AdvanceResult(False, 2, f"invalid state: {err}", None)

    open_now = collect_open_ds_ids()
    phase = state["phase"]
    last = state["last_kind"]

    if kind == "backlog_solve":
        if phase != "backlog":
            return AdvanceResult(False, 2, "backlog_solve only allowed in backlog phase", None)
        if not ds or ds_numeric_id(ds) < 0:
            return AdvanceResult(False, 2, "backlog_solve requires --ds DS-nnn", None)
        ds_norm = ds.strip()
        if open_ds_row_still_open(open_now, ds_norm):
            return AdvanceResult(
                False,
                2,
                f"{ds_norm} still listed as open in Information input list; close the row before advance",
                None,
            )
        _append_event(state, "backlog_solve", ds_norm, None)
        state["last_kind"] = "backlog_solve"
        state["last_open_ds_snapshot"] = list(open_now)
        head = _git_head()
        if head:
            state["head_sha_expected"] = head
        # Enter main when backlog drained
        if not open_now:
            state["phase"] = "main"
        save_state(state)
        return AdvanceResult(True, 0, f"recorded backlog_solve for {ds_norm}", state)

    if kind == "backlog_implement":
        if phase != "backlog":
            return AdvanceResult(False, 2, "backlog_implement only allowed in backlog phase", None)
        if not ds or ds_numeric_id(ds) < 0:
            return AdvanceResult(False, 2, "backlog_implement requires --ds DS-nnn", None)
        ds_norm = ds.strip()
        if not open_now or not open_ds_row_still_open(open_now, ds_norm):
            return AdvanceResult(
                False,
                2,
                f"{ds_norm} not listed as open in Information input list; use backlog-solve after closing the row",
                None,
            )
        if not check_json or not check_json.strip():
            return AdvanceResult(False, 2, "backlog_implement requires --check-json (repo-relative path)", None)
        rel = check_json.strip().replace("\\", "/")
        abs_path = (ROOT / rel).resolve()
        try:
            abs_path.relative_to(ROOT.resolve())
        except ValueError:
            return AdvanceResult(False, 2, "check_json must stay under repository root", None)
        if not abs_path.is_file():
            return AdvanceResult(False, 2, f"check_json not found: {rel}", None)
        try:
            payload = json.loads(abs_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            return AdvanceResult(False, 2, f"invalid check_json: {e}", None)
        if payload.get("kind") != "despaghettify_check" and "ast" not in payload:
            return AdvanceResult(
                False,
                2,
                "check_json must be hub check output (kind despaghettify_check or top-level ast)",
                None,
            )
        paths = state.setdefault("recent_check_json_paths", [])
        paths.append(rel)
        state["recent_check_json_paths"] = paths[-8:]
        _append_event(state, "backlog_implement", ds_norm, rel)
        state["last_kind"] = "backlog_implement"
        state["last_open_ds_snapshot"] = list(open_now)
        head = _git_head()
        if head:
            state["head_sha_expected"] = head
        save_state(state)
        return AdvanceResult(True, 0, f"recorded backlog_implement for {ds_norm} ({rel})", state)

    if kind == "main_check":
        if phase == "backlog" and open_now:
            return AdvanceResult(False, 2, "main_check not allowed while backlog DS rows remain", None)
        if check_json:
            paths = state.setdefault("recent_check_json_paths", [])
            paths.append(check_json)
            state["recent_check_json_paths"] = paths[-8:]
        _append_event(state, "main_check", None, check_json)
        state["last_kind"] = "main_check"
        state["last_open_ds_snapshot"] = list(open_now)
        state["phase"] = "main"
        head = _git_head()
        if head:
            state["head_sha_expected"] = head
        save_state(state)
        return AdvanceResult(True, 0, "recorded main_check", state)

    if kind == "main_solve":
        if phase != "main":
            return AdvanceResult(False, 2, "main_solve only in main phase", None)
        if last not in ("main_check", "main_solve"):
            return AdvanceResult(False, 2, "main_solve must follow main_check (or another main_solve)", None)
        if not ds or ds_numeric_id(ds) < 0:
            return AdvanceResult(False, 2, "main_solve requires valid --ds", None)
        ds_norm = ds.strip()
        if open_ds_row_still_open(open_now, ds_norm):
            return AdvanceResult(
                False,
                2,
                f"{ds_norm} still open after solve; close before advance",
                None,
            )
        _append_event(state, "main_solve", ds_norm, None)
        state["last_kind"] = "main_solve"
        state["last_open_ds_snapshot"] = list(open_now)
        head = _git_head()
        if head:
            state["head_sha_expected"] = head
        save_state(state)
        return AdvanceResult(True, 0, f"recorded main_solve for {ds_norm}", state)

    return AdvanceResult(False, 2, "unknown kind", None)


def status_json() -> dict[str, Any]:
    """
    Implement ``status_json`` for the surrounding module workflow.

    Module context: ``'fy'-suites/despaghettify/tools/autonomous_loop.py`` — keep this
    routine aligned with sibling helpers in the same package.

    Returns:
        Mapping typed as ``dict[str, Any]``; keys and values follow caller contracts.

    """
    state = load_state()
    open_now = collect_open_ds_ids()
    if state is None:
        return {"active": False, "open_ds": open_now}
    err = _validate_state_shape(state)
    next_hints: list[str] = []
    if err:
        next_hints.append(f"invalid_state:{err}")
    else:
        if state["phase"] == "backlog":
            if open_now:
                next_hints.append(
                    "allowed: autonomous-advance --kind backlog-implement --ds DS-… --check-json <path> "
                    "(after an implementation slice; DS row stays open until goal met)"
                )
                next_hints.append("allowed: autonomous-advance --kind backlog-solve --ds DS-… (only after closing the row in the input list)")
            else:
                next_hints.append("allowed: autonomous-advance --kind main-check [--check-json path]")
        else:
            if state["last_kind"] == "init" and not state.get("open_ds_at_init"):
                next_hints.append("allowed: autonomous-advance --kind main-check")
            elif state["last_kind"] == "main_check":
                if open_now:
                    next_hints.append("allowed: autonomous-advance --kind main-solve --ds DS-…")
                next_hints.append("allowed: autonomous-advance --kind main-check (refresh)")
            elif state["last_kind"] == "main_solve":
                next_hints.append("allowed: autonomous-advance --kind main-check [--check-json path]")
            elif state["last_kind"] == "init" and state.get("open_ds_at_init"):
                next_hints.append(
                    "allowed: backlog-implement (slice + --check-json) while row open; backlog-solve only after row closed"
                )
    return {
        "active": True,
        "state_path": str(STATE_FILE.relative_to(ROOT)),
        "session_id": state.get("session_id"),
        "phase": state.get("phase"),
        "last_kind": state.get("last_kind"),
        "open_ds": open_now,
        "head_sha_expected": state.get("head_sha_expected"),
        "next_hints": next_hints,
        "recent_check_json_paths": state.get("recent_check_json_paths", []),
    }


def verify(
    *,
    allow_dirty: bool,
    setup_json: Path | None = None,
) -> tuple[int, list[str]]:
    """
    Returns (exit_code, messages).
    0 = ok, 1 = advisory warnings, 2 = hard failure.
    """
    msgs: list[str] = []
    state = load_state()
    if state is None:
        return 0, ["no autonomous_state.json; nothing to verify"]

    err = _validate_state_shape(state)
    if err:
        return 2, [f"invalid state: {err}"]

    exp = state.get("head_sha_expected")
    if isinstance(exp, str) and exp:
        head = _git_head()
        if head and head != exp:
            return 2, [f"HEAD {head[:12]}… does not match head_sha_expected {exp[:12]}…"]

    if not allow_dirty:
        dirty = _git_dirty_paths(
            (
                ".state_tmp/",
                f"{HUB_REL}/state/",
                "htmlcov/",
                ".pytest_cache/",
            )
        )
        if dirty:
            return 2, ["dirty worktree (use --allow-dirty to bypass): " + ", ".join(dirty[:12])]

    open_now = collect_open_ds_ids()
    snap = state.get("last_open_ds_snapshot") or []
    if sorted(open_now) != sorted(snap) and state.get("last_kind") not in ("init", "backlog_implement"):
        msgs.append(f"info: open_ds changed since snapshot (now={open_now}, snapshot={snap})")

    stall_advisory = False
    # Stall heuristic: last two check JSONs identical ast block
    paths = state.get("recent_check_json_paths") or []
    if len(paths) >= 2:
        p1, p2 = paths[-2], paths[-1]
        f1, f2 = ROOT / p1, ROOT / p2
        if f1.is_file() and f2.is_file():
            try:
                j1 = json.loads(f1.read_text(encoding="utf-8"))
                j2 = json.loads(f2.read_text(encoding="utf-8"))
                if j1.get("ast") == j2.get("ast") and open_now:
                    msgs.append(
                        "advisory: identical AST in last two check reports with open_ds remaining (anti-stall)"
                    )
                    stall_advisory = True
            except (OSError, json.JSONDecodeError):
                msgs.append("warning: could not compare check JSONs")

    # trigger-eval optional (informational; does not raise exit code alone)
    setup_path = setup_json or SETUP_JSON
    if setup_path.is_file() and paths:
        lastp = ROOT / paths[-1]
        if lastp.is_file():
            try:
                from despaghettify.tools import metrics_bundle as mb  # noqa: PLC0415

                setup = json.loads(setup_path.read_text(encoding="utf-8"))
                chk = json.loads(lastp.read_text(encoding="utf-8"))
                bundle = mb.build_metrics_bundle(check_payload=chk, setup=setup)
                msgs.append(
                    "trigger_eval: fires="
                    + str(bundle["trigger_policy_fires"])
                    + f" m7={bundle['m7']} m7_ref={bundle['m7_ref']}"
                )
            except Exception as e:  # noqa: BLE001
                msgs.append(f"metrics/trigger-eval skipped: {e}")

    return (1 if stall_advisory else 0), msgs
