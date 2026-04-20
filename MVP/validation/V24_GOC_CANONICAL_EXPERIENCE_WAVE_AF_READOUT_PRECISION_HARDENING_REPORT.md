# Wave AF — Role-Sensitive Situational Readout Precision Hardening

This pass hardens the real MVP v24 runtime/session/shell integration path so the existing play shell can surface more precise socially live readout without a frontend rewrite.

## Real seams used

- `world-engine/app/story_runtime/manager.py`
- `world-engine/app/story_runtime_shell_readout.py`
- `backend/app/api/v1/session_routes.py` (existing pass-through already sufficient)
- `frontend/app/routes.py`
- `frontend/templates/session_shell.html`
- `frontend/static/play_shell.js`

## What is now surfaced more clearly

- room/threshold social meaning
- salient object meaning
- continued wound / still-active pressure
- role-sensitive consequence visibility
- callback reuse / carry-over pressure
- compact recent-act social meaning

## Guardrails preserved

- no objective hints
- no hidden beat exposure
- no frontend architecture redesign
- no generic narrator layer
- no sandbox expansion
