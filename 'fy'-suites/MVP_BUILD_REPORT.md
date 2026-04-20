# fy-suite Built MVP Report

This package contains a working built MVP for the autark fy suite workspace.

## Implemented in this MVP

- shared internal evidence registry backed by SQLite
- shared internal semantic index backed by SQLite
- shared run journal with JSONL event streams
- shared model router policy
- shared context pack generation
- generic suite adapter CLI (`fy-suite`)
- complete adapters for:
  - contractify
  - testify
  - documentify
  - docify
  - despaghettify
  - dockerify
  - postmanify
- lifecycle support for:
  - init
  - inspect
  - audit
  - explain
  - prepare-context-pack
  - compare-runs
  - clean
  - reset
  - triage
  - prepare-fix

## Autarky model

All internal state is kept inside the fy workspace under `.fydata/` and suite-owned folders.
The adapters work outward against a target repository path.

## Validation

The built MVP includes adapter and platform tests.

Validated in this build:
- `fy_platform/tests/test_ai_registry.py`
- `fy_platform/tests/test_ai_suite_cli.py`
- `contractify/adapter/tests/test_contractify_adapter.py`
- `testify/adapter/tests/test_testify_adapter.py`
- `documentify/adapter/tests/test_documentify_adapter.py`
- `docify/adapter/tests/test_docify_adapter.py`
- `despaghettify/adapter/tests/test_despaghettify_adapter.py`
- `dockerify/adapter/tests/test_dockerify_adapter.py`
- `postmanify/adapter/tests/test_postmanify_adapter.py`

Result for the built MVP validation slice:
- **10 passed**

## Example usage

```bash
fy-suite contractify init --target-repo /path/to/target-repo
fy-suite contractify audit --target-repo /path/to/target-repo
fy-suite contractify explain
fy-suite contractify prepare-context-pack --query "openapi drift"

fy-suite documentify audit --target-repo /path/to/target-repo
fy-suite despaghettify audit --target-repo /path/to/target-repo
fy-suite postmanify audit --target-repo /path/to/target-repo
```


## Next-stage expansion

- Added contractify consolidate mode with safe apply / user-input split.
- Added testify ADR reflection guard.
- Added root requirements files (normal/dev/test).

