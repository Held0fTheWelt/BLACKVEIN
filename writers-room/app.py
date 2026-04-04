"""
Writers Room – Flask mini-app for author workflow.

Currently hosts the "Almighty Oracle" page, but uses a shared admin-style layout
and supports login via the main backend API (JWT stored in session).
"""

import importlib.util
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

_here = Path(__file__).resolve().parent
_repo_root = _here.parent
_app_dir = _here / "app"

# Load .env from repo root (WorldOfShadows/.env). Fall back to current working dir.
_env_candidates = [
    Path.cwd() / ".env",
    _repo_root / ".env",
    _here / ".env",
]
for _p in _env_candidates:
    if _p.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_p)
        except ImportError:
            pass
        break

_template_dir = (_app_dir / "templates") if (_app_dir / "templates").exists() else (_here / "templates")
_static_dir = (_app_dir / "static") if (_app_dir / "static").exists() else (_here / "static")

app = Flask(
    __name__,
    template_folder=str(_template_dir),
    static_folder=str(_static_dir),
)
# Security requirement: Flask session secret key MUST be set via environment variable.
# Do NOT use hardcoded defaults in production environments. The secret key is critical
# for session security and should be generated securely and kept confidential.
_secret_key = os.environ.get("WRITERS_ROOM_SECRET_KEY")
if not _secret_key:
    raise ValueError(
        "WRITERS_ROOM_SECRET_KEY environment variable must be explicitly set. "
        "This is required for secure session management. "
        "Generate a secure secret key using: python -c \"import secrets; print(secrets.token_hex(32))\" "
        "and set it in your environment or .env file."
    )
app.secret_key = _secret_key

BACKEND_BASE_URL = (
    os.environ.get("BACKEND_BASE_URL")
    or os.environ.get("BACKEND_API_URL")
    or "http://127.0.0.1:5000"
).rstrip("/")

_service_file = _here / "app" / "services" / "chatgpt_service.py"
_spec = importlib.util.spec_from_file_location("writers_room_chatgpt_service", str(_service_file))
_chatgpt_service = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
if _spec and _spec.loader:
    _spec.loader.exec_module(_chatgpt_service)  # type: ignore[call-arg]
else:  # pragma: no cover
    raise RuntimeError(f"Cannot load chatgpt service module from: {_service_file}")

get_oracle_answer = _chatgpt_service.get_oracle_answer


def _request_writers_room_review(*, token: str, module_id: str, focus: str) -> dict:
    payload = json.dumps({"module_id": module_id, "focus": focus}).encode("utf-8")
    req = urllib.request.Request(
        f"{BACKEND_BASE_URL}/api/v1/writers-room/reviews",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("access_token"):
        flash("Please sign in to use the unified Writers-Room workflow.", "error")
        return redirect(url_for("login"))

    report = None
    if request.method == "POST":
        module_id = request.form.get("module_id", "god_of_carnage").strip() or "god_of_carnage"
        focus = request.form.get("focus", "canon consistency and dramaturgy").strip() or "canon consistency and dramaturgy"
        try:
            report = _request_writers_room_review(
                token=session["access_token"],
                module_id=module_id,
                focus=focus,
            )
        except urllib.error.HTTPError as exc:
            msg = "Writers-Room workflow request failed."
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                msg = error_payload.get("error") or msg
            except Exception:
                pass
            flash(msg, "error")
        except Exception:
            flash("Writers-Room workflow failed (backend unreachable).", "error")
    return render_template("index.html", report=report)


@app.route("/legacy-oracle", methods=["GET", "POST"])
def legacy_oracle():
    answer = None
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        if question:
            answer = get_oracle_answer(question)
        else:
            answer = "You didn't ask anything. Try again!"
    return render_template("index.html", report=None, legacy_answer=answer, legacy_mode=True)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login via backend API; stores JWT in session for later use."""
    if request.method == "GET":
        if session.get("access_token"):
            return redirect(url_for("index"))
        return render_template("login.html", backend_base_url=BACKEND_BASE_URL)

    username = (request.form.get("username") or "").strip()
    password = request.form.get("password") or ""
    if not username or not password:
        flash("Username and password are required.", "error")
        return render_template("login.html", backend_base_url=BACKEND_BASE_URL), 400

    try:
        payload = json.dumps({"username": username, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"{BACKEND_BASE_URL}/api/v1/auth/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode("utf-8"))
            msg = err.get("error") or "Login failed."
        except Exception:
            msg = "Login failed."
        flash(msg, "error")
        return render_template("login.html", backend_base_url=BACKEND_BASE_URL), 401
    except Exception:
        flash("Login failed (backend unreachable).", "error")
        return render_template("login.html", backend_base_url=BACKEND_BASE_URL), 502

    token = (data.get("access_token") or "").strip()
    if not token:
        flash("Login failed (no token).", "error")
        return render_template("login.html", backend_base_url=BACKEND_BASE_URL), 401

    session["access_token"] = token
    session["username"] = (data.get("user") or {}).get("username") or username
    flash(f"Welcome, {session['username']}.", "success")
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
