"""
Writers Room – Flask mini-app for author workflow.

Currently hosts the "Almighty Oracle" page, but uses a shared admin-style layout
and supports login via the main backend API (JWT stored in session).
"""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for

try:
    from openai import OpenAI  # type: ignore
except ImportError:  # pragma: no cover
    OpenAI = None

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
app.secret_key = (
    os.environ.get("WRITERS_ROOM_SECRET_KEY")
    or os.environ.get("SECRET_KEY")
    or "writers-room-dev-secret-do-not-use-in-production"
)

BACKEND_BASE_URL = (os.environ.get("BACKEND_BASE_URL") or "http://127.0.0.1:5000").rstrip("/")

# API key from environment (set OPENAI_API_KEY or create a .env file)
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if (api_key and OpenAI) else None

if not api_key:
    print("OPENAI_API_KEY not found. Oracle will run in offline mode.")

ORACLE_SYSTEM = """You are the Almighty Oracle – but a completely unreliable one.
You MUST always give WRONG, absurd, or deliberately silly answers.
Be funny, a bit angry, or dizzy. Never give the real answer.
Keep answers concise (1–3 sentences). Answer in the same language as the question."""


@app.route("/", methods=["GET", "POST"])
def index():
    answer = None
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        # Step 2: User input in Variable, zum Prüfen ausgeben
        print(f"[Oracle] User question: {question!r}")
        if question and client:
            # Step 3 & 4: An OpenAI senden, Antwort mit „spicy“ Oracle-Prompt
            answer = ask_oracle(question)
        elif question and not client:
            answer = "🔑 Set OPENAI_API_KEY in your environment, then restart the app."
        else:
            answer = "You didn't ask anything. Try again!"
    return render_template("index.html", answer=answer)


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


def ask_oracle(question: str) -> str:
    """Sendet die Frage an OpenAI und gibt die (absichtlich falsche) Oracle-Antwort zurück."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ORACLE_SYSTEM},
                {"role": "user", "content": question},
            ],
            temperature=0.9,
            max_tokens=150,
        )
        return response.choices[0].message.content or "(The Oracle fell silent.)"
    except Exception as e:
        return f"The Oracle glitched: {e!s}"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
