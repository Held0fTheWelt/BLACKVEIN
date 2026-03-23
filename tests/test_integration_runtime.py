import subprocess, json, sys
from pathlib import Path

def run_runtime(action, *args):
    cmd = [sys.executable, "runtime.py", action] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Failed: {result.stderr}")
    return json.loads(result.stdout)

class TestIntegrationRuntime:
    def test_get_returns_valid_json(self):
        result = run_runtime("get")
        assert result["status"] == "ok"
        assert result["mode"] in ["default", "adaptive", "claude-min"]

    def test_set_persists_mode(self):
        run_runtime("set", "adaptive")
        verify = run_runtime("get")
        assert verify["mode"] == "adaptive"
        run_runtime("set", "default")

    def test_list_returns_all_modes(self):
        result = run_runtime("list")
        assert result["status"] == "ok"
        assert "default" in result["modes"]
        assert "adaptive" in result["modes"]
        assert "claude-min" in result["modes"]

    def test_menu_returns_interactive(self):
        result = run_runtime("menu")
        assert result["status"] == "ok"
        assert result["interactive"] is True
        assert len(result["modes"]) == 3

    def test_info_returns_details(self):
        result = run_runtime("info")
        assert result["status"] == "ok"
        for mode in ["default", "adaptive", "claude-min"]:
            assert mode in result["modes"]
            info = result["modes"][mode]
            assert "allows_ollama" in info
            assert "allows_claude" in info

    def test_invalid_mode_rejected(self):
        result = run_runtime("set", "invalid")
        assert result["status"] == "error"
        assert "invalid" in result["message"].lower()
