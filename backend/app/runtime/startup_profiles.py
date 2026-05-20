"""routing governance — named startup profiles and deterministic expected operational facts.

These profiles classify repository-intended environments. They do not change bootstrap
behavior; they document and test the relationship between config, registry state, and
:class:`OperationalState`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from app.runtime.operational_state import OperationalState, pytest_session_active


class StartupProfile(str, Enum):
    """Explicit startup profiles used in docs, tests, and operator legibility."""

    production_default = "production_default"
    production_bootstrap_disabled = "production_bootstrap_disabled"
    testing_isolated = "testing_isolated"
    testing_bootstrap_on = "testing_bootstrap_on"


@dataclass(frozen=True, slots=True)
class StartupProfileFacts:
    """Expected relationships for a profile (documentation + gate tests)."""

    profile: StartupProfile
    routing_registry_bootstrap: bool
    expect_global_model_specs_nonempty_after_create_app: bool
    pytest_session: bool
    narrative: str


def resolve_startup_profile(
    *,
    routing_registry_bootstrap: bool,
    under_pytest: bool | None = None,
) -> StartupProfile:
    """Map config + environment to a named profile.

    ``under_pytest`` defaults to :func:`pytest_session_active`.
    """

    ut = under_pytest if under_pytest is not None else pytest_session_active()
    if ut:
        return (
            StartupProfile.testing_bootstrap_on
            if routing_registry_bootstrap
            else StartupProfile.testing_isolated
        )
    if routing_registry_bootstrap:
        return StartupProfile.production_default
    return StartupProfile.production_bootstrap_disabled


def facts_for_profile(profile: StartupProfile) -> StartupProfileFacts:
    """Return frozen expected facts for documentation parity tests."""

    if profile is StartupProfile.production_default:
        return StartupProfileFacts(
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
    if profile is StartupProfile.production_bootstrap_disabled:
        return StartupProfileFacts(
            profile=profile,
            routing_registry_bootstrap=False,
            expect_global_model_specs_nonempty_after_create_app=False,
            pytest_session=False,
            narrative=(
                "Non-test process with bootstrap explicitly false: operators disabled "
                "registry seeding; expect empty ``iter_model_specs()`` unless something "
                "else registered specs. ``OperationalState.intentionally_degraded`` "
                "when classification sees bootstrap off outside pytest."
            ),
        )
    if profile is StartupProfile.testing_isolated:
        return StartupProfileFacts(
            profile=profile,
            routing_registry_bootstrap=False,
            expect_global_model_specs_nonempty_after_create_app=False,
            pytest_session=True,
            narrative=(
                "``TestingConfig`` default: bootstrap off; empty global spec store is expected "
                "so tests do not share registry pollution. ``OperationalState.test_isolated`` "
                "when classification inputs match empty registry under pytest."
            ),
        )
    return StartupProfileFacts(
        profile=profile,
        routing_registry_bootstrap=True,
        expect_global_model_specs_nonempty_after_create_app=True,
        pytest_session=True,
        narrative=(
            "Pytest subclass with ``ROUTING_REGISTRY_BOOTSTRAP=True``: mirrors production-like "
            "registry population for HTTP/integration proofs without changing routing policy."
        ),
    )


def expected_operational_state_for_profile(
    profile: StartupProfile,
    *,
    registry_model_spec_count: int,
    canonical_surfaces_all_satisfied: bool | None,
) -> OperationalState:
    """Deterministic expected :class:`OperationalState` for gate matrices.

    Uses the same classification rules as production code via explicit fact vectors
    implied by each profile's intended use.
    """

    from app.runtime.operational_state import classify_operational_state

    facts = facts_for_profile(profile)
    return classify_operational_state(
        bootstrap_enabled=facts.routing_registry_bootstrap,
        registry_model_spec_count=registry_model_spec_count,
        canonical_surfaces_all_satisfied=canonical_surfaces_all_satisfied,
    )
