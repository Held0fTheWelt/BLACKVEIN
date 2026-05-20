from __future__ import annotations

import os
import json
import socket
import subprocess
import sys
import tempfile
import time
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import pytest

from app.services.game import game_service
from app.services.game.game_service import GameServiceError


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stderr_log_tail(path: Path, *, max_chars: int = 12_000) -> str:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(stderr log unreadable: {exc})"
    if len(raw) <= max_chars:
        return raw
    return f"... (truncated, full file: {path})\n" + raw[-max_chars:]


@pytest.fixture
def backend_content_feed_endpoint() -> str:
    payload = {
        "templates": [
            {
                "id": "god_of_carnage_solo",
                "title": "God of Carnage - Published Integration",
                "kind": "solo_story",
                "join_policy": "owner_only",
                "summary": "Published authored payload from backend feed.",
                "max_humans": 1,
                "min_humans_to_start": 1,
                "persistent": False,
                "initial_beat_id": "courtesy",
                "roles": [
                    {
                        "id": "annette",
                        "display_name": "Annette",
                        "description": "Human-playable role",
                        "mode": "human",
                        "initial_room_id": "hallway",
                        "can_join": True,
                    },
                    {
                        "id": "veronique",
                        "display_name": "Veronique",
                        "description": "NPC",
                        "mode": "npc",
                        "initial_room_id": "living_room",
                    },
                ],
                "rooms": [
                    {
                        "id": "hallway",
                        "name": "Hallway",
                        "description": "Start",
                        "exits": [
                            {"direction": "inside", "target_room_id": "living_room", "label": "Inside"}
                        ],
                        "prop_ids": [],
                        "action_ids": [],
                        "artwork_prompt": None,
                    },
                    {
                        "id": "living_room",
                        "name": "Living Room",
                        "description": "Conflict room",
                        "exits": [],
                        "prop_ids": [],
                        "action_ids": [],
                        "artwork_prompt": None,
                    },
                ],
                "props": [],
                "actions": [],
                "beats": [
                    {
                        "id": "courtesy",
                        "name": "Courtesy",
                        "description": "Start beat",
                        "summary": "Summary",
                    }
                ],
                "tags": ["authored"],
                "style_profile": "retro_pulp",
            }
        ]
    }

    class _FeedHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/api/v1/game/content/published":
                self.send_response(404)
                self.end_headers()
                return
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):  # pragma: no cover - test noise suppression
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _FeedHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/api/v1/game/content/published"
    finally:
        server.shutdown()
        thread.join(timeout=2.0)
        server.server_close()


@pytest.fixture
def play_service_endpoint(backend_content_feed_endpoint: str) -> dict[str, str]:
    pytest.importorskip("uvicorn")
    repo_root = Path(__file__).resolve().parents[2]
    world_engine_dir = repo_root / "world-engine"
    port = _free_port()

    env = os.environ.copy()
    # Isolate from parent env: World Engine import requires test mode or a non-empty shared secret.
    env["FLASK_ENV"] = "test"
    env["PLAY_SERVICE_SHARED_SECRET"] = "integration-shared-secret"
    env["PLAY_SERVICE_INTERNAL_API_KEY"] = "ops-key"
    env["BACKEND_CONTENT_SYNC_ENABLED"] = "true"
    env["BACKEND_CONTENT_FEED_URL"] = backend_content_feed_endpoint
    env["BACKEND_CONTENT_TIMEOUT_SECONDS"] = "5.0"
    env["BACKEND_CONTENT_SYNC_INTERVAL_SECONDS"] = "0.0"
    # StoryRuntimeManager builds RAG at import/lifespan; dense embeddings can download ONNX and
    # encode the corpus — often >45s on cold CI. Integration tests only need HTTP bridge + sparse RAG.
    env["WOS_RAG_DISABLE_EMBEDDINGS"] = "1"
    # Inherited CI env (e.g. postgres run store, proxies) can block startup or localhost probes.
    env["RUN_STORE_BACKEND"] = "json"
    env.pop("RUN_STORE_URL", None)
    env["NO_PROXY"] = "127.0.0.1,localhost"
    for _proxy_key in (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ):
        env.pop(_proxy_key, None)

    _fd, stderr_log_str = tempfile.mkstemp(
        prefix="wos_world_engine_playservice_",
        suffix=".stderr.log",
    )
    os.close(_fd)
    stderr_log = Path(stderr_log_str)
    stderr_fh = open(stderr_log, "w", encoding="utf-8", errors="replace", buffering=1)
    stderr_closed = False
    proc: subprocess.Popen | None = None
    keep_stderr_log = False
    try:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--log-level",
                "warning",
            ],
            cwd=str(world_engine_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=stderr_fh,
        )

        base_url = f"http://127.0.0.1:{port}"
        # Lifespan (RAG corpus build, template sync from feed) can still be slow on shared CI runners.
        deadline = time.time() + 120.0
        ready = False
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                response = httpx.get(f"{base_url}/api/health", timeout=2.0)
                if response.status_code == 200:
                    ready = True
                    break
            except Exception:
                pass
            time.sleep(0.2)

        if not ready:
            keep_stderr_log = True
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            stderr_fh.flush()
            stderr_fh.close()
            stderr_closed = True
            tail = _stderr_log_tail(stderr_log)
            raise RuntimeError(
                "world-engine test server did not become ready in time "
                "(lifespan/RAG/template sync may be slow; WOS_RAG_DISABLE_EMBEDDINGS=1 is set for this fixture). "
                f"uvicorn stderr log: {stderr_log}\n{tail}"
            )

        if proc.poll() is not None:
            keep_stderr_log = True
            stderr_fh.flush()
            stderr_fh.close()
            stderr_closed = True
            tail = _stderr_log_tail(stderr_log)
            raise RuntimeError(
                f"world-engine test server exited before readiness (exit code {proc.returncode}). "
                f"uvicorn stderr log: {stderr_log}\n{tail}"
            )

        yield {
            "public_url": base_url,
            "internal_url": base_url,
            "internal_key": "ops-key",
        }
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if not stderr_closed:
            try:
                stderr_fh.flush()
                stderr_fh.close()
            except OSError:
                pass
        if not keep_stderr_log:
            try:
                stderr_log.unlink(missing_ok=True)
            except OSError:
                pass


def test_backend_to_playservice_happy_path(app, play_service_endpoint):
    with app.app_context():
        app.config["PLAY_SERVICE_PUBLIC_URL"] = play_service_endpoint["public_url"]
        app.config["PLAY_SERVICE_INTERNAL_URL"] = play_service_endpoint["internal_url"]
        app.config["PLAY_SERVICE_INTERNAL_API_KEY"] = play_service_endpoint["internal_key"]
        app.config["PLAY_SERVICE_SHARED_SECRET"] = "integration-shared-secret"
        app.config["PLAY_SERVICE_REQUEST_TIMEOUT"] = 10

        templates = game_service.list_templates()
        # apartment_confrontation_group is a stable builtin group template
        assert any(item.get("id") == "apartment_confrontation_group" for item in templates)

        # Test with apartment_confrontation_group (group run) instead of god_of_carnage_solo
        # god_of_carnage_solo is now runtime-profile-only and requires canonical player roles
        created = game_service.create_run(
            template_id="apartment_confrontation_group",
            account_id="acct:integration",
            display_name="Integration User",
            character_id="char:integration",
        )
        run_id = created["run"]["id"]
        assert run_id

        join = game_service.resolve_join_context(
            run_id=run_id,
            account_id="acct:integration",
            display_name="Integration User",
            character_id="char:integration",
        )
        assert join.run_id == run_id
        assert join.participant_id
        assert join.role_id

        details = game_service.get_run_details(run_id)
        assert details["run"]["id"] == run_id
        assert details["template"]["id"] == "apartment_confrontation_group"
        assert details["lobby"] is None or isinstance(details["lobby"], dict)

        transcript = game_service.get_run_transcript(run_id)
        assert transcript["run_id"] == run_id
        assert isinstance(transcript["entries"], list)

        terminated = game_service.terminate_run(run_id, actor_display_name="integration_test", reason="e2e_gate")
        assert terminated["run_id"] == run_id
        assert terminated["terminated"] is True
        assert terminated["actor_display_name"] == "integration_test"
        assert terminated["reason"] == "e2e_gate"


def test_backend_contract_failure_on_missing_required_field_with_live_playservice(app, play_service_endpoint):
    with app.app_context():
        app.config["PLAY_SERVICE_PUBLIC_URL"] = play_service_endpoint["public_url"]
        app.config["PLAY_SERVICE_INTERNAL_URL"] = play_service_endpoint["internal_url"]
        app.config["PLAY_SERVICE_INTERNAL_API_KEY"] = play_service_endpoint["internal_key"]
        app.config["PLAY_SERVICE_SHARED_SECRET"] = "integration-shared-secret"
        app.config["PLAY_SERVICE_REQUEST_TIMEOUT"] = 10

        with pytest.raises(GameServiceError) as exc:
            game_service.create_run(
                template_id="",
                account_id="acct:integration",
                display_name="Integration User",
            )

        assert exc.value.status_code in {400, 404, 422}
