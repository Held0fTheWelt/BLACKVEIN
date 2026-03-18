#!/usr/bin/env python3
"""Enhanced runtime/mode management for WorldOfShadows and ClaudeClockwork projects."""
import json
import sys
from pathlib import Path
from datetime import datetime


def get_mode_state_file():
    """Get the mode state file path."""
    cc_path = Path("/mnt/d/ClaudeClockwork/.claude/state/mode_state.json")
    if cc_path.exists():
        return cc_path
    local_path = Path(".claude/state/mode_state.json")
    return local_path


class RuntimeManager:
    """Manages execution mode state and operations."""

    VALID_MODES = ["default", "adaptive", "claude-min"]

    MODE_DESCRIPTIONS = {
        "default": "Pure Ollama Agent Mode - execute all skills with Ollama agents only",
        "adaptive": "Adaptive Mode - support both Ollama and Claude agents, choose optimal route",
        "claude-min": "Claude Minimal Mode - execute with Claude API agents (minimized costs)",
    }

    MODE_DETAILS = {
        "default": {
            "description": "Pure Ollama Agent Mode",
            "allows_ollama": True,
            "allows_claude": False,
            "allows_hybrid": False,
            "use_case": "Cost-effective, privacy-focused execution using local models",
        },
        "adaptive": {
            "description": "Adaptive Mode",
            "allows_ollama": True,
            "allows_claude": True,
            "allows_hybrid": True,
            "use_case": "Optimal routing - chooses best agent type per task",
        },
        "claude-min": {
            "description": "Claude Minimal Mode",
            "allows_ollama": False,
            "allows_claude": True,
            "allows_hybrid": False,
            "use_case": "Cloud-based execution with minimized API costs",
        },
    }

    def __init__(self):
        """Initialize RuntimeManager."""
        self.state_file = get_mode_state_file()

    def load_mode(self) -> str:
        """Load current execution mode."""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())
                return data.get("active_mode", "default")
            except Exception:
                return "default"
        return "default"

    def save_mode(self, mode: str) -> bool:
        """Save mode to state file."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "active_mode": mode,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            self.state_file.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            print(f"Error saving mode: {e}", file=sys.stderr)
            return False

    def set_mode(self, mode: str) -> dict:
        """Set execution mode."""
        if mode not in self.VALID_MODES:
            return {
                "status": "error",
                "message": f"Invalid mode: {mode}. Valid modes: {', '.join(self.VALID_MODES)}",
                "valid_modes": self.VALID_MODES,
            }

        if self.save_mode(mode):
            return {
                "status": "ok",
                "message": f"✅ Runtime set to: {mode}",
                "mode": mode,
                "description": self.MODE_DESCRIPTIONS[mode],
            }
        else:
            return {
                "status": "error",
                "message": "Failed to save mode to state file",
            }

    def get_current_mode(self) -> dict:
        """Get current execution mode."""
        mode = self.load_mode()
        return {
            "status": "ok",
            "message": f"Current mode: {mode}",
            "mode": mode,
            "description": self.MODE_DESCRIPTIONS[mode],
        }

    def list_modes(self) -> dict:
        """List all available modes."""
        current = self.load_mode()
        modes = {
            mode: self.MODE_DESCRIPTIONS[mode]
            for mode in self.VALID_MODES
        }
        return {
            "status": "ok",
            "message": f"Available modes: {', '.join(self.VALID_MODES)}. Active: {current}",
            "modes": modes,
            "active_mode": current,
        }

    def show_menu(self) -> dict:
        """Show interactive menu."""
        current = self.load_mode()
        modes = [
            {
                "number": i + 1,
                "key": mode,
                "name": self.MODE_DETAILS[mode]["description"],
                "description": self.MODE_DETAILS[mode]["use_case"],
                "active": mode == current,
            }
            for i, mode in enumerate(self.VALID_MODES)
        ]

        return {
            "status": "ok",
            "action": "menu",
            "active_mode": current,
            "modes": modes,
            "message": "Mode selection menu",
            "interactive": True,
            "menu_type": "interactive",
            "choices": {
                str(i + 1): {
                    "mode": mode,
                    "name": self.MODE_DETAILS[mode]["description"],
                }
                for i, mode in enumerate(self.VALID_MODES)
            },
        }

    def show_info(self) -> dict:
        """Show detailed mode information."""
        current = self.load_mode()
        return {
            "status": "ok",
            "action": "info",
            "active_mode": current,
            "modes": self.MODE_DETAILS,
            "message": f"Mode info retrieved. Current mode: {current}",
        }


def main():
    """CLI interface for runtime manager."""
    manager = RuntimeManager()

    if len(sys.argv) > 1:
        action = sys.argv[1]

        if action == "menu":
            result = manager.show_menu()
        elif action == "list":
            result = manager.list_modes()
        elif action == "get":
            result = manager.get_current_mode()
        elif action == "info":
            result = manager.show_info()
        elif action == "set":
            if len(sys.argv) > 2:
                mode = sys.argv[2]
                result = manager.set_mode(mode)
            else:
                result = {"status": "error", "message": "Mode required for 'set' action"}
        else:
            result = {"status": "error", "message": f"Unknown action: {action}"}

        print(json.dumps(result, indent=2))
    else:
        result = manager.show_menu()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
