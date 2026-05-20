"""ADR-0041 feature-flag resolution for ledger projections.

The runtime ledger records which experimental authority paths were enabled when
it built a projection. Each resolver accepts an optional environment mapping so
unit tests and diagnostics can ask the same question deterministically.
"""

from __future__ import annotations

import os
from typing import Any

from .constants import (
    ADR0041_PLAN_PROJECTION_ENABLED_ENV,
    ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV,
    ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV,
    ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV,
    ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV,
)

def resolve_adr0041_scoped_co_authority_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve the explicit ADR-0041 scoped co-authority feature flag.

    Default ``False`` (fail closed): no co-authority decision payload is emitted.
    Enabling this flag still does not mutate validation, readiness, or commit state.
    """
    warnings: list[str] = []
    raw = env_value if env_value is not None else os.environ.get(ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV)
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_SCOPED_CO_AUTHORITY_ENABLED_ENV}={raw!r}; "
        "ADR-0041 scoped co-authority decision disabled."
    )
    return False, tuple(warnings)
def resolve_adr0041_readiness_co_authority_preview_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve explicit readiness co-authority preview flag.

    Default ``False`` (fail closed): no readiness policy preview payload is emitted.
    """
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_READINESS_CO_AUTHORITY_PREVIEW_ENABLED_ENV}={raw!r}; "
        "ADR-0041 readiness co-authority preview disabled."
    )
    return False, tuple(warnings)
def resolve_adr0041_scoped_readiness_enforcement_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve explicit scoped readiness enforcement pilot flag (fail closed)."""
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_SCOPED_READINESS_ENFORCEMENT_ENABLED_ENV}={raw!r}; "
        "ADR-0041 scoped readiness enforcement disabled."
    )
    return False, tuple(warnings)
def resolve_adr0041_scoped_readiness_aggregation_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve scoped readiness aggregation pilot flag (fail closed)."""
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_SCOPED_READINESS_AGGREGATION_ENABLED_ENV}={raw!r}; "
        "ADR-0041 scoped readiness aggregation disabled."
    )
    return False, tuple(warnings)
def resolve_adr0041_runtime_readiness_consumer_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve ADR-0041 runtime readiness consumer flag (fail closed).

    When disabled, final session readiness fields must match legacy/seam evaluation
    with no silent ADR-0041 overlay.
    """
    warnings: list[str] = []
    raw = (
        env_value
        if env_value is not None
        else os.environ.get(ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV)
    )
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_RUNTIME_READINESS_CONSUMER_ENABLED_ENV}={raw!r}; "
        "ADR-0041 runtime readiness consumer disabled."
    )
    return False, tuple(warnings)
def resolve_adr0041_plan_projection_enabled(
    *,
    env_value: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Resolve optional ADR-0041 plan-aware sibling projection under runtime_intelligence_projection.

    Default ``False`` (fail closed): sibling omitted; validator_dispatch_report unchanged.
    Explicit truthy env enables sibling-only evidence (still projection-only; no execution).
    """
    warnings: list[str] = []
    raw = env_value if env_value is not None else os.environ.get(ADR0041_PLAN_PROJECTION_ENABLED_ENV)
    text = str(raw or "").strip().lower()
    if text in {"", "0", "false", "no", "off"}:
        return False, tuple(warnings)
    if text in {"1", "true", "yes", "on"}:
        return True, tuple(warnings)
    warnings.append(
        f"Unsupported {ADR0041_PLAN_PROJECTION_ENABLED_ENV}={raw!r}; "
        "ADR-0041 plan projection sibling disabled."
    )
    return False, tuple(warnings)
