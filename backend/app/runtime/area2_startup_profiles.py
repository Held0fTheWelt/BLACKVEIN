"""Area 2 — named startup profiles and deterministic expected operational facts.

These profiles classify repository-intended environments. They do not change bootstrap
behavior; they document and test the relationship between config, registry state, and
:class:`Area2OperationalState`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.runtime.area2_operational_state import Area2OperationalState, pytest_session_active


class Area2StartupProfile(str, Enum):
    """Explicit startup profiles used in docs, tests, and operator legibility."""

    production_default = "production_default"
    production_bootstrap_disabled = "production_bootstrap_disabled"
    testing_isolated = "testing_isolated"
    testing_bootstrap_on = "testing_bootstrap_on"


@dataclass(frozen=True, slots=True)
class Area2StartupProfileFacts:
    """Expected relationships for a profile (documentation + gate tests)."""

    profile: Area2StartupProfile
    routing_registry_bootstrap: bool
    expect_global_model_specs_nonempty_after_create_app: bool
    pytest_session: bool
    narrative: str


def resolve_startup_profile(
    *,
    routing_registry_bootstrap: bool,
    under_pytest: bool | None = None,
) -> Area2StartupProfile:
    """Map config + environment to a named profile.

    ``under_pytest`` defaults to :func:`pytest_session_active`.
    """

    ut = under_pytest if under_pytest is not None else pytest_session_active()
    if ut:
        return (
            Area2StartupProfile.testing_bootstrap_on
            if routing_registry_bootstrap
            else Area2StartupProfile.testing_isolated
        )
    if routing_registry_bootstrap:
        return Area2StartupProfile.production_default
    return Area2StartupProfile.production_bootstrap_disabled


def facts_for_profile(profile: Area2StartupProfile) -> Area2StartupProfileFacts:
    """Return frozen expected facts for documentation parity tests."""

    if profile is Area2StartupProfile.production_default:
        return Area2StartupProfileFacts(
            profile=profile,
            routing_registry_bootstrap=True,
            expect_global_model_specs_nonempty_after_create_app=True,
            pytest_session=False,
            narrative=(
                "Flask ``Config`` default: ``ROUTING_REGISTRY_BOOTSTRAP`` is true; "
                "``create_app`` registers MockStoryAIAdapter + spec so "
                "``iter_model_specs()`` is non-empty in normal non-test processes."
            ),
        )
    if profile is Area2StartupProfile.production_bootstrap_disabled:
        return Area2StartupProfileFacts(
            profile=profile,
            routing_registry_bootstrap=False,
            expect_global_model_specs_nonempty_after_create_app=False,
            pytest_session=False,
            narrative=(
                "Non-test process with bootstrap explicitly false: operators disabled "
                "registry seeding; expect empty ``iter_model_specs()`` unless something "
                "else registered specs. ``Area2OperationalState.intentionally_degraded`` "
                "when classification sees bootstrap off outside pytest."
            ),
        )
    if profile is Area2StartupProfile.testing_isolated:
        return Area2StartupProfileFacts(
            profile=profile,
            routing_registry_bootstrap=False,
            expect_global_model_specs_nonempty_after_create_app=False,
            pytest_session=True,
            narrative=(
                "``TestingConfig`` default: bootstrap off; empty global spec store is expected "
                "so tests do not share registry pollution. ``Area2OperationalState.test_isolated`` "
                "when classification inputs match empty registry under pytest."
            ),
        )
    return Area2StartupProfileFacts(
        profile=profile,
        routing_registry_bootstrap=True,
        expect_global_model_specs_nonempty_after_create_app=True,
        pytest_session=True,
        narrative=(
            "Pytest subclass with ``ROUTING_REGISTRY_BOOTSTRAP=True``: mirrors production-like "
            "registry population for HTTP/integration proofs without changing routing policy."
        ),
    )


def expected_area2_operational_state_for_profile(
    profile: Area2StartupProfile,
    *,
    registry_model_spec_count: int,
    canonical_surfaces_all_satisfied: bool | None,
) -> Area2OperationalState:
    """Deterministic expected :class:`Area2OperationalState` for gate matrices.

    Uses the same classification rules as production code via explicit fact vectors
    implied by each profile's intended use.
    """

    from app.runtime.area2_operational_state import classify_area2_operational_state

    facts = facts_for_profile(profile)
    return classify_area2_operational_state(
        bootstrap_enabled=facts.routing_registry_bootstrap,
        registry_model_spec_count=registry_model_spec_count,
        canonical_surfaces_all_satisfied=canonical_surfaces_all_satisfied,
    )
