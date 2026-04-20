# Apply patch — documentify + docify quality uplift

## Intent

This patch is meant to be merged into the current `fy-suites` repository by another runner.

It has two goals:

1. make **documentify** generate an easy-entry doc in a readable **What / Why / How** style and allow Mermaid-based lightweight visuals
2. make **docify** capable of producing denser contextual inline explanations that can reach the quality expected for files like `fy_platform/ai/base_adapter.py`

## What to integrate

- overwrite the changed files listed in `CHANGED_FILES.txt`
- keep repository structure unchanged
- run the targeted tests after integration

## Minimum validation

```bash
PYTHONPATH=. pytest -q   documentify/tools/tests/test_document_builder.py   docify/tools/tests/test_python_inline_explain.py   docify/tools/tests/test_hub_cli.py
```

## Expected result

- documentify simple docs read like human-facing easy docs, not only terse summaries
- documentify can use Mermaid when it improves orientation
- docify exposes `inline-explain`
- docify can generate block-level contextual inline explanations
- the included `docify/examples/base_adapter_docified_example.py` shows the intended explanation density and style
