# Patch notes — documentify + docify quality uplift

This patch does two targeted things:

1. **Documentify easy docs**
   - upgrades the simple output into a real **What / Why / How** style easy document
   - allows and uses **Mermaid** where a small visual improves orientation
   - keeps the output grounded in the actual repository surface

2. **Docify code explanation quality**
   - adds a real `inline-explain` command
   - generates denser, more contextual inline explanations for Python functions
   - is intended to support files like `fy_platform/ai/base_adapter.py` at a much higher readability level

This patch is designed as a changed-files patch set for another runner to integrate into the current `fy-suites` repository.
