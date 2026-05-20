"""Small extraction helpers used by runtime intelligence projections.

The projection code reads many aspect records. Keeping these accessors together
makes the field-selection rules explicit and avoids hand-written dictionary
lookups drifting across modules.
"""

from __future__ import annotations

from typing import Any

def _first_text(values: list[Any]) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None
def _record_block(record: dict[str, Any], key: str) -> dict[str, Any]:
    block = record.get(key) if isinstance(record, dict) else {}
    return block if isinstance(block, dict) else {}
def _record_nested_value(record: dict[str, Any], key: str, nested_key: str) -> Any:
    nested = record.get(nested_key) if isinstance(record.get(nested_key), dict) else {}
    return record.get(key) or nested.get(key)
def _record_reasons(record: dict[str, Any]) -> list[str]:
    reasons = record.get("reasons") if isinstance(record, dict) else []
    return [str(reason) for reason in reasons if str(reason).strip()] if isinstance(reasons, list) else []
