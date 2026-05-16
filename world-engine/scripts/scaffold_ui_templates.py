"""Scaffold World-Engine runtime diagnostic UI assets."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "app" / "web"

PAGE_HEAD = """<header class="ui-page-head">
  <p class="ui-eyebrow">World-Engine</p>
  <h1>{title}</h1>
  <p class="ui-subtle">{subtitle}</p>
</header>
<div id="ui-page-banner" class="ui-banner" hidden></div>
"""

SESSION_PICKER = """<div class="ui-toolbar ui-card">
  <label for="ui-session-id">Story session</label>
  <input id="ui-session-id" type="text" class="ui-input" placeholder="session id" autocomplete="off">
  <button type="button" class="ui-btn" id="ui-session-apply">Apply</button>
  <button type="button" class="ui-btn ui-btn-ghost" id="ui-session-refresh">Refresh list</button>
  <select id="ui-session-select" class="ui-input" aria-label="Known sessions"></select>
</div>
"""

FILES = {
    "templates/ui/_session_picker.html": SESSION_PICKER,
}


def main() -> None:
    for rel, content in FILES.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print("wrote", path)


if __name__ == "__main__":
    main()
