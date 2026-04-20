"""Frozen roadmap §6.9 experience-acceptance scenario set (G9).

Single non-substitutable ordering: six scenarios exactly as in docs/ROADMAP_MVP_GoC.md §6.9.
Templates and validators should align with these ids — do not introduce parallel scenario vocab.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class G9RoadmapScenario:
    """One required G9 acceptance scenario."""

    scenario_id: str
    roadmap_label: str
    failure_oriented: bool
    default_trace_hint: str | None = None


# Order is normative; do not reorder, drop, or merge scenarios.
G9_ROADMAP_SCENARIOS: tuple[G9RoadmapScenario, ...] = (
    G9RoadmapScenario(
        scenario_id="goc_roadmap_s1_direct_provocation",
        roadmap_label="Direct provocation",
        failure_oriented=False,
    ),
    G9RoadmapScenario(
        scenario_id="goc_roadmap_s2_deflection_brevity",
        roadmap_label="Deflection / brevity",
        failure_oriented=False,
    ),
    G9RoadmapScenario(
        scenario_id="goc_roadmap_s3_pressure_escalation",
        roadmap_label="Pressure escalation",
        failure_oriented=False,
    ),
    G9RoadmapScenario(
        scenario_id="goc_roadmap_s4_misinterpretation_correction",
        roadmap_label="Misinterpretation / correction",
        failure_oriented=False,
    ),
    G9RoadmapScenario(
        scenario_id="goc_roadmap_s5_primary_failure_fallback",
        roadmap_label="Primary model failure + fallback",
        failure_oriented=True,
    ),
    G9RoadmapScenario(
        scenario_id="goc_roadmap_s6_retrieval_heavy",
        roadmap_label="Retrieval-heavy context",
        failure_oriented=False,
        default_trace_hint="trace-roadmap-s6-retrieval-heavy",
    ),
)

ROADMAP_SCENARIO_IDS: tuple[str, ...] = tuple(s.scenario_id for s in G9_ROADMAP_SCENARIOS)
ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY = "goc_roadmap_s6_retrieval_heavy"


def expected_failure_oriented_by_id() -> dict[str, bool]:
    return {s.scenario_id: s.failure_oriented for s in G9_ROADMAP_SCENARIOS}
