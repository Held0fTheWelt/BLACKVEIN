# Committed report fixtures (hermetic tree)

These JSON files are **full-fidelity** `discover` / `audit` payloads produced from the same synthetic repository layout as [`../../tools/minimal_repo.py`](../../tools/minimal_repo.py) (used by hermetic **pytest**).

- **`discover.hermetic-fixture.json`** — output aligned with `build_discover_payload()` / `contractify discover`.
- **`audit.hermetic-fixture.json`** — output aligned with `run_audit()` / `contractify audit`.

They use a **fixed** `generated_at` timestamp so reviewers can diff intentional schema changes.

## Regenerate

From the **repository root** (after `pip install -e .`):

```bash
python -m contractify.tools.freeze_committed_reports
```

Ephemeral machine exports from a real monorepo checkout still belong under [`../`](../) (sibling `*.json` remain gitignored at `reports/*.json` depth only — see root [`.gitignore`](../../../.gitignore)).
