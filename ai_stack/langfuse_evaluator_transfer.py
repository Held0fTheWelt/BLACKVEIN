"""Transfer bundle helpers for bootstrapping WoS judges into local Langfuse.

The canonical judge definitions live in ``langfuse_evaluator_catalog``. This
module reshapes them for a local Langfuse project without making API calls or
moving secrets. Langfuse's stable documented setup path for LLM-as-a-Judge is
the UI, so the bundle is an import/runbook artifact rather than an automatic
write to a local instance.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ai_stack.langfuse_evaluator_catalog import (
    GATE_OVERRIDE_WARNING,
    LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
    ORDERED_CATEGORICAL_EVALUATORS,
    TURN_JUDGE_OPTIONAL_METADATA_HINT,
    evaluator_spec_to_public_dict,
)

TRANSFER_BUNDLE_SCHEMA_VERSION = "wos_langfuse_judge_transfer_bundle.v1"


def _local_observation_filters(filters: dict[str, Any], *, environment: str) -> dict[str, Any]:
    out = dict(filters)
    out["Environment"] = [environment]
    return out


def _local_metadata_filters(filters: dict[str, Any], *, environment: str) -> dict[str, Any]:
    out = dict(filters)
    out.update(
        {
            "environment": environment,
            "evidence_scope": "local_langfuse",
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
        }
    )
    return out


def build_local_langfuse_judge_transfer_bundle(
    *,
    environment: str = "local",
    include_prompts: bool = True,
) -> dict[str, Any]:
    """Return a local-only transfer bundle for all canonical categorical judges."""
    env = str(environment or "local").strip() or "local"
    judges: list[dict[str, Any]] = []
    for index, spec in enumerate(ORDERED_CATEGORICAL_EVALUATORS, start=1):
        public = evaluator_spec_to_public_dict(spec, include_prompts=include_prompts)
        observation_filters = _local_observation_filters(
            spec.langfuse_observation_filters,
            environment=env,
        )
        metadata_filters = _local_metadata_filters(
            spec.trace_metadata_filters,
            environment=env,
        )
        ui_steps = {
            "create_via": "Langfuse UI -> Evaluators -> + Set up Evaluator -> LLM-as-a-Judge",
            "target": "Observations",
            "observation_filters": observation_filters,
            "trace_metadata_filters": metadata_filters,
            "score_type": spec.score_type,
            "categories": list(spec.categories),
            "default_variable_mapping": {
                "input": "{{input}}",
                "output": "{{output}}",
                "metadata": "{{metadata}}",
            },
            "provider_key_location": "Langfuse UI -> Project Settings -> LLM Connections",
        }
        if spec.scope == "turn_generation":
            ui_steps["optional_trace_metadata_hint"] = TURN_JUDGE_OPTIONAL_METADATA_HINT
        judges.append(
            {
                **public,
                "order": index,
                "local_only": True,
                "live_or_staging_evidence": False,
                "langfuse_ui_bootstrap": ui_steps,
                "operator_transfer_note": (
                    "Create this evaluator in the local Langfuse UI using the prompt, "
                    "categories, and filters in this object. Scores are qualitative "
                    "local diagnostics only."
                ),
            }
        )

    return {
        "schema_version": TRANSFER_BUNDLE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "transfer_mode": "ui_bootstrap_bundle",
        "api_write_supported": False,
        "api_write_note": (
            "This repository intentionally does not auto-write Langfuse evaluator "
            "definitions. Current documented Langfuse LLM-as-a-Judge setup is UI-first; "
            "provider keys must stay in Langfuse project settings."
        ),
        "target": {
            "environment": env,
            "evidence_scope": "local_langfuse",
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
        },
        "canonical_definition_source": LLM_AS_A_JUDGE_DOC_RELATIVE_PATH,
        "gate_override_warning": GATE_OVERRIDE_WARNING,
        "judge_count": len(judges),
        "judges": judges,
    }


def render_local_langfuse_judge_transfer_markdown(bundle: dict[str, Any]) -> str:
    """Render a compact operator runbook for the JSON transfer bundle."""
    target = bundle.get("target") if isinstance(bundle.get("target"), dict) else {}
    judges = bundle.get("judges") if isinstance(bundle.get("judges"), list) else []
    lines = [
        "# Local Langfuse Judge Transfer Bundle",
        "",
        f"- Schema: `{bundle.get('schema_version')}`",
        f"- Environment: `{target.get('environment', 'local')}`",
        f"- Evidence scope: `{target.get('evidence_scope', 'local_langfuse')}`",
        f"- Proof level: `{target.get('proof_level', 'local_only')}`",
        f"- Live/staging evidence: `{target.get('live_or_staging_evidence', False)}`",
        f"- Judge count: `{len(judges)}`",
        "",
        "## Bootstrap Steps",
        "",
        "1. Start local Langfuse with `python docker-up.py up`.",
        "2. Open `http://localhost:3000` and create/open the local project.",
        "3. Add judge provider credentials in Project Settings -> LLM Connections.",
        "4. For each judge below, create an LLM-as-a-Judge evaluator targeting Observations.",
        "5. Use the JSON bundle for the exact prompt, categories, and local filters.",
        "",
        "Local judge scores are qualitative diagnostics only; they do not change Commit, Readiness, or `validation_outcome`.",
        "",
        "## Judges",
        "",
    ]
    for judge in judges:
        ui = judge.get("langfuse_ui_bootstrap") if isinstance(judge.get("langfuse_ui_bootstrap"), dict) else {}
        filters = ui.get("observation_filters") if isinstance(ui.get("observation_filters"), dict) else {}
        lines.extend(
            [
                f"### {judge.get('order')}. `{judge.get('name')}`",
                "",
                f"- Scope: `{judge.get('scope')}`",
                f"- Categories: `{', '.join(str(c) for c in judge.get('categories', []))}`",
                f"- Observation name: `{', '.join(filters.get('Name', []))}`",
                f"- Trace name: `{', '.join(filters.get('Trace Name', []))}`",
                f"- Environment filter: `{', '.join(filters.get('Environment', []))}`",
                f"- Repair card: `{judge.get('repair_card')}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"
