# Validation appendix

## Commands run in this post-repair re-audit

### Structural inspection
- package structural inventory of the repaired repository bundle
- targeted grep/search across docs entrypoints, active route docs, mirrors, and support-surface code
- selected markdown relative-link check across root/docs/MVP entry surfaces and active route files

### Fresh test commands

1. world-engine focused replay
```bash
cd /mnt/data/wos_post_reaudit_repo/MVP_repaired_2026-04-21/world-engine
PYTHONPATH=. pytest -q tests/test_backend_content_feed.py tests/test_story_runtime_shell_readout.py tests/test_runtime_manager.py
```
Result: `41 passed, 1 warning in 0.39s`

2. ai_stack focused replay
```bash
cd /mnt/data/wos_post_reaudit_repo/MVP_repaired_2026-04-21/ai_stack
PYTHONPATH=..:. pytest -q tests/test_mcp_canonical_surface.py
```
Result: `5 passed in 0.55s`

3. frontend replay attempt
```bash
cd /mnt/data/wos_post_reaudit_repo/MVP_repaired_2026-04-21/frontend
PYTHONPATH=. pytest -q tests/test_routes_extended.py
```
Result: blocked with `ModuleNotFoundError: No module named 'flask'`

### Link check summary
Selected root/docs/MVP entry files and all active-route markdown files were checked for relative markdown targets.
Result: `0 missing relative targets`.
