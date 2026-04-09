#!/usr/bin/env python3
"""Capture structured G9 Level-A evidence from real graph.run() outputs.

Aligned with pytest anchors:
  test_goc_runtime_breadth_continuity_diagnostics: s1, s2, s3
  ai_stack.goc_s4_misinterpretation_scenario: s4 (misinterpretation / correction chain)
  test_goc_multi_turn_experience_quality: s5 (primary-failure / fallback / degraded explanation)
  test_goc_retrieval_heavy_scenario: s6

S4 (Roadmap §6.9 scenario 4) uses the canonical three-turn chain in
``ai_stack/goc_s4_misinterpretation_scenario.py`` (pronominal misroute in phase_3,
player correction naming Veronique, sustained host-focused beat).

This script still writes one JSON file per roadmap scenario (S1–S6) when run
without mode flags. For audit bundles whose *purpose* is S4 closure only, pass
``--evidence-run-scope s4_closure_partial`` so ``run_metadata.json`` cannot be
read as a full six-scenario G9 threshold / matrix run.

For S5-only targeted remediation bundles, pass ``--evidence-run-scope
s5_targeted_partial``: writes only ``run_metadata.json``,
``scenario_goc_roadmap_s5_primary_failure_fallback.json``, and
``pytest_s5_anchor.txt`` (pytest witness); not a full six-scenario capture.

Usage (repo root, PYTHONPATH=repo root, ai_stack deps installed):
  python scripts/g9_level_a_evidence_capture.py OUT_DIR
    [--evidence-run-scope s4_closure_partial|s5_targeted_partial]
    [--evidence-run-note "..."]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from story_runtime_core import RoutingPolicy, interpret_player_input  # noqa: E402
from story_runtime_core.adapters import BaseModelAdapter, ModelCallResult  # noqa: E402
from story_runtime_core.model_registry import build_default_registry  # noqa: E402

from ai_stack.goc_turn_seams import build_roadmap_dramatic_turn_record  # noqa: E402
from ai_stack.goc_yaml_authority import cached_goc_yaml_title, clear_goc_yaml_slice_cache, load_goc_canonical_module_yaml  # noqa: E402
from ai_stack.langgraph_runtime import RuntimeTurnGraphExecutor  # noqa: E402
from ai_stack.rag import ContextPackAssembler, ContextRetriever, RagIngestionPipeline  # noqa: E402
from ai_stack.goc_g9_roadmap_scenarios import ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY  # noqa: E402
from ai_stack.goc_s4_misinterpretation_scenario import (  # noqa: E402
    ROADMAP_S4_PYTEST_NODE,
    TRACE_S4_T1,
    TRACE_S4_T2,
    TRACE_S4_T3,
    assess_roadmap_s4_evidence,
    run_roadmap_s4_misinterpretation_chain,
)

HOST_OK = {"template_id": "god_of_carnage_solo", "title": "God of Carnage"}
EVALUATOR_ID_DEFAULT = "single_evaluator_g9_level_a_repo_audit"
DEFAULT_EVIDENCE_RUN_SCOPE = "g9_level_a_capture_all_script_scenarios"
DEFAULT_EVIDENCE_RUN_NOTE = (
    "Capture script replays S1–S6 fixtures into JSON; scope does not imply a single "
    "pytest command covered all scenarios unless documented separately."
)
S4_PARTIAL_DEFAULT_NOTE = (
    "Partial S4-focused evidence capture (see evidence_run_scope). Not a full six-scenario "
    "G9 experience matrix or threshold validation run."
)
S5_PARTIAL_DEFAULT_NOTE = (
    "S5-targeted partial improvement run (primary model failure + graph mock fallback recovery). "
    "Not a full six-scenario G9 Level A matrix or threshold validation run."
)
S5_PYTEST_NODE = (
    "ai_stack/tests/test_goc_multi_turn_experience_quality.py::test_experience_multiturn_primary_failure_fallback_and_degraded_explained"
)


def _git_meta(repo: Path) -> dict[str, Any]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "git_commit": (head.stdout or "").strip() or None,
        "git_porcelain_lines": len([ln for ln in (porcelain.stdout or "").splitlines() if ln.strip()]),
        "working_tree_dirty": bool((porcelain.stdout or "").strip()),
    }


def write_run_metadata(
    out_dir: Path,
    *,
    audit_run_id: str,
    evaluator_id: str,
    evidence_run_scope: str | None = None,
    evidence_run_note: str | None = None,
) -> None:
    gm = _git_meta(REPO_ROOT)
    doc: dict[str, Any] = {
        "audit_run_id": audit_run_id,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_commit_or_worktree": {
            "commit": gm["git_commit"],
            "working_tree_dirty": gm["working_tree_dirty"],
            "porcelain_line_count": gm["git_porcelain_lines"],
        },
        "python_version": sys.version.split()[0],
        "active_environment_path": sys.prefix,
        "evaluator_id": evaluator_id,
        "repo_root": str(REPO_ROOT),
    }
    if evidence_run_scope:
        doc["evidence_run_scope"] = evidence_run_scope
    if evidence_run_note:
        doc["evidence_run_note"] = evidence_run_note
    (out_dir / "run_metadata.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")


class JsonAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def __init__(self, narrative: str) -> None:
        self._narrative = narrative

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        payload = {
            "narrative_response": self._narrative,
            "proposed_scene_id": None,
            "intent_summary": "g9_evidence_capture",
        }
        return ModelCallResult(
            content=json.dumps(payload),
            success=True,
            metadata={"adapter": self.adapter_name},
        )


class ErrorAdapter(BaseModelAdapter):
    adapter_name = "openai"

    def generate(self, prompt: str, *, timeout_seconds: float = 10.0, retrieval_context: str | None = None) -> ModelCallResult:
        return ModelCallResult(
            content="",
            success=False,
            metadata={"adapter": self.adapter_name, "error": "simulated_generation_failure"},
        )


def _executor(tmp_path: Path, **adapters: BaseModelAdapter) -> RuntimeTurnGraphExecutor:
    content_file = tmp_path / "content" / "god_of_carnage.md"
    content_file.parent.mkdir(parents=True, exist_ok=True)
    content_file.write_text("God of Carnage G9 evidence capture corpus.", encoding="utf-8")
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    openai = adapters["openai"]
    mock_ad = adapters.get("mock", openai)
    merged = {"mock": mock_ad, "openai": openai, "ollama": openai}
    return RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters=merged,
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )


def _summarize_result(result: dict[str, Any]) -> dict[str, Any]:
    dr = (result.get("graph_diagnostics") or {}).get("dramatic_review") or {}
    routing = result.get("routing") or {}
    vis = result.get("visible_output_bundle") or {}
    narr = vis.get("gm_narration")
    narr_excerpt: Any = narr
    if isinstance(narr, list):
        narr_excerpt = narr[:12]
    return {
        "trace_id": result.get("graph_diagnostics", {}).get("repro_metadata", {}).get("trace_id")
        if isinstance(result.get("graph_diagnostics"), dict)
        else None,
        "session_id": result.get("graph_diagnostics", {}).get("repro_metadata", {}).get("session_id")
        if isinstance(result.get("graph_diagnostics"), dict)
        else None,
        "player_input": result.get("player_input"),
        "current_scene_id": result.get("current_scene_id"),
        "selected_scene_function": result.get("selected_scene_function"),
        "pacing_mode": result.get("pacing_mode"),
        "interpreted_move": result.get("interpreted_move"),
        "continuity_impacts": result.get("continuity_impacts"),
        "prior_dramatic_signature_used": result.get("prior_dramatic_signature"),
        "visible_output_bundle": {"gm_narration": narr_excerpt},
        "routing": {
            "route_reason_code": routing.get("route_reason_code"),
            "policy_id_used": routing.get("policy_id_used"),
            "fallback_chain": routing.get("fallback_chain"),
            "fallback_stage_reached": routing.get("fallback_stage_reached"),
        },
        "validation_outcome": result.get("validation_outcome"),
        "dramatic_review": {
            "dramatic_quality_status": dr.get("dramatic_quality_status"),
            "run_classification": dr.get("run_classification"),
            "dramatic_signature": dr.get("dramatic_signature"),
            "pattern_repetition_risk": dr.get("pattern_repetition_risk"),
            "pattern_repetition_note": dr.get("pattern_repetition_note"),
            "multi_pressure_chosen": dr.get("multi_pressure_chosen"),
        },
        "retrieval": {
            "hit_count": (result.get("retrieval") or {}).get("hit_count"),
            "status": (result.get("retrieval") or {}).get("status"),
            "retrieval_governance_summary": (result.get("retrieval") or {}).get("retrieval_governance_summary"),
        },
        "weak_run_explanation": result.get("weak_run_explanation"),
        "silence_brevity_decision": result.get("silence_brevity_decision"),
        "scene_assessment_excerpt": _scene_excerpt(result.get("scene_assessment")),
    }


def _scene_excerpt(sa: Any) -> dict[str, Any]:
    if not isinstance(sa, dict):
        return {}
    mpr = sa.get("multi_pressure_resolution")
    return {
        "guidance_phase_key": sa.get("guidance_phase_key"),
        "canonical_setting": sa.get("canonical_setting"),
        "multi_pressure_resolution": mpr if isinstance(mpr, dict) else None,
    }


def _dramatic_turn_excerpt(result: dict[str, Any]) -> dict[str, Any]:
    try:
        dtr = build_roadmap_dramatic_turn_record(result)
    except Exception as e:  # pragma: no cover
        return {"error": str(e)}
    tb = dtr.get("turn_basis") or {}
    rr = dtr.get("routing_record") or {}
    ret = dtr.get("retrieval_record") or {}
    return {
        "turn_id": tb.get("turn_id"),
        "routing_record": {
            "route_reason_code": rr.get("route_reason_code"),
            "fallback_stage_reached": rr.get("fallback_stage_reached"),
        },
        "retrieval_record": {
            "authored_truth_refs": ret.get("authored_truth_refs"),
            "derived_artifact_refs": ret.get("derived_artifact_refs"),
            "retrieval_visibility_class": ret.get("retrieval_visibility_class"),
        },
    }


@dataclass
class TurnStep:
    current_scene_id: str
    player_input: str
    adapter: BaseModelAdapter
    trace_id: str
    graph_fallback_adapter: BaseModelAdapter | None = None


def _run_chain(
    tmp_path: Path, *, session_id: str, steps: list[TurnStep]
) -> list[dict[str, Any]]:
    prior_continuity: list[dict[str, Any]] = []
    prior_signature: dict[str, str] | None = None
    results: list[dict[str, Any]] = []
    for step in steps:
        ex_kw: dict[str, BaseModelAdapter] = {"openai": step.adapter}
        if step.graph_fallback_adapter is not None:
            ex_kw["mock"] = step.graph_fallback_adapter
        graph = _executor(tmp_path, **ex_kw)
        result = graph.run(
            session_id=session_id,
            module_id="god_of_carnage",
            current_scene_id=step.current_scene_id,
            player_input=step.player_input,
            trace_id=step.trace_id,
            host_experience_template=HOST_OK,
            prior_continuity_impacts=list(prior_continuity),
            prior_dramatic_signature=dict(prior_signature) if prior_signature else None,
        )
        results.append(result)
        impacts = result.get("continuity_impacts")
        if isinstance(impacts, list) and impacts:
            prior_continuity.extend(x for x in impacts if isinstance(x, dict))
            prior_continuity = prior_continuity[-4:]
        dr = ((result.get("graph_diagnostics") or {}).get("dramatic_review") or {})
        sig = dr.get("dramatic_signature") if isinstance(dr.get("dramatic_signature"), dict) else {}
        if sig:
            intent = ((result.get("interpreted_move") or {}).get("player_intent") or "")
            prior_signature = {**{k: str(v) for k, v in sig.items()}, "player_intent": str(intent)}
        else:
            prior_signature = {"player_intent": f"step_{len(results)}"}
    return results


def capture_s6_retrieval_heavy(tmp_path: Path) -> dict[str, Any]:
    load_goc_canonical_module_yaml()
    content_dir = tmp_path / "content"
    content_dir.mkdir(parents=True)
    for i in range(10):
        (content_dir / f"goc_segment_{i:02d}.md").write_text(
            "God of Carnage dinner-table escalation and retrieval segment "
            f"{i}: Veronique, Michel, Annette, Alain — moral injury and civility.\n",
            encoding="utf-8",
        )
    corpus = RagIngestionPipeline().build_corpus(tmp_path)
    registry = build_default_registry()
    routing = RoutingPolicy(registry)
    adapter = JsonAdapter(
        "The table goes quiet; retrieved notes on prior insults shape how the host answers you."
    )
    merged = {"mock": adapter, "openai": adapter, "ollama": adapter}
    graph = RuntimeTurnGraphExecutor(
        interpreter=interpret_player_input,
        routing=routing,
        registry=registry,
        adapters=merged,
        retriever=ContextRetriever(corpus),
        assembler=ContextPackAssembler(),
    )
    result = graph.run(
        session_id=f"s-{ROADMAP_SCENARIO_ID_RETRIEVAL_HEAVY}",
        module_id="god_of_carnage",
        current_scene_id="living_room",
        player_input="Explain what everyone at this table already knows from the written record about the incident.",
        trace_id="trace-roadmap-s6-retrieval-heavy",
        host_experience_template=HOST_OK,
    )
    return {
        "scenario_id": "goc_roadmap_s6_retrieval_heavy",
        "automated_trace_anchor": "trace-roadmap-s6-retrieval-heavy",
        "pytest_anchor": "test_roadmap_scenario_retrieval_heavy_governance_visible",
        "summary": _summarize_result(result),
        "dramatic_turn_record_excerpt": _dramatic_turn_excerpt(result),
        "model_narrative_fixture": json.loads(
            (result.get("generation") or {}).get("structured_output") or "{}"
        ).get("narrative_response")
        if isinstance((result.get("generation") or {}).get("structured_output"), str)
        else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="G9 Level-A evidence capture")
    parser.add_argument("out_dir", type=Path, help="Evidence directory (e.g. tests/reports/evidence/<run_id>)")
    parser.add_argument("--audit-run-id", default="", help="Defaults to out_dir name")
    parser.add_argument("--evaluator-id", default=EVALUATOR_ID_DEFAULT)
    parser.add_argument(
        "--evidence-run-scope",
        default=DEFAULT_EVIDENCE_RUN_SCOPE,
        help="run_metadata.evidence_run_scope (s4_closure_partial | s5_targeted_partial for partial bundles)",
    )
    parser.add_argument(
        "--evidence-run-note",
        default="",
        help="run_metadata.evidence_run_note (optional; default depends on scope)",
    )
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    audit_run_id = args.audit_run_id or out_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    note = (args.evidence_run_note or "").strip()
    if not note:
        if args.evidence_run_scope == "s4_closure_partial":
            note = S4_PARTIAL_DEFAULT_NOTE
        elif args.evidence_run_scope == "s5_targeted_partial":
            note = S5_PARTIAL_DEFAULT_NOTE
        else:
            note = DEFAULT_EVIDENCE_RUN_NOTE

    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    load_goc_canonical_module_yaml()

    write_run_metadata(
        out_dir,
        audit_run_id=audit_run_id,
        evaluator_id=args.evaluator_id,
        evidence_run_scope=args.evidence_run_scope,
        evidence_run_note=note,
    )

    import tempfile

    def _write_s5_only(base: Path) -> None:
        steps_c = [
            TurnStep(
                "courtesy",
                "Why do you think this happened?",
                JsonAdapter("Annette asks why and demands a reason, pressing you to explain what truly happened."),
                "trace-p3-c1",
            ),
            TurnStep(
                "living_room",
                "I am angry and want to fight now.",
                JsonAdapter(
                    "The atmosphere thickens with a sense of mood and something shifts while everyone feels the moment hang."
                ),
                "trace-p3-c2",
            ),
            TurnStep(
                "living_room",
                "I blame you for what happened.",
                ErrorAdapter(),
                "trace-p3-c3",
                graph_fallback_adapter=JsonAdapter(
                    "Annette meets your blame head-on: she refuses to carry the fault alone, snaps that the table "
                    "will not scapegoat her tonight, and forces the accusation back into the open air where everyone "
                    "must answer for what they did."
                ),
            ),
        ]
        chain_c = _run_chain(base, session_id="s-p3-c", steps=steps_c)
        r5 = chain_c[2]
        doc5: dict[str, Any] = {
            "scenario_id": "goc_roadmap_s5_primary_failure_fallback",
            "failure_oriented": True,
            "automated_trace_anchor": "trace-p3-c3",
            "pytest_anchor": "test_experience_multiturn_primary_failure_fallback_and_degraded_explained",
            "pytest_anchor_node": S5_PYTEST_NODE,
            "prior_turns_trace_ids": ["trace-p3-c1", "trace-p3-c2"],
            "failure_turn": _summarize_result(r5),
            "dramatic_turn_record_excerpt": _dramatic_turn_excerpt(r5),
        }
        if args.evidence_run_scope == "s5_targeted_partial":
            doc5["evidence_run_scope"] = args.evidence_run_scope
            doc5["partial_run_disclaimer"] = note
        (out_dir / "scenario_goc_roadmap_s5_primary_failure_fallback.json").write_text(
            json.dumps(doc5, indent=2), encoding="utf-8"
        )

    if args.evidence_run_scope == "s5_targeted_partial":
        with tempfile.TemporaryDirectory() as td:
            _write_s5_only(Path(td))
        env = os.environ.copy()
        env["PYTHONPATH"] = str(REPO_ROOT)
        witness_path = out_dir / "pytest_s5_anchor.txt"
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                S5_PYTEST_NODE,
                "-q",
                "--tb=short",
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        witness_body = (proc.stdout or "") + "\n" + (proc.stderr or "") + f"\nexit_code={proc.returncode}\n"
        witness_path.write_text(witness_body, encoding="utf-8")
        if proc.returncode != 0:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "pytest_s5_witness_failed",
                        "exit_code": proc.returncode,
                        "witness": str(witness_path),
                    },
                    indent=2,
                ),
                file=sys.stderr,
            )
            return 1
        print(
            json.dumps(
                {
                    "ok": True,
                    "out_dir": str(out_dir),
                    "audit_run_id": audit_run_id,
                    "evidence_run_scope": args.evidence_run_scope,
                },
                indent=2,
            )
        )
        return 0

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        # S1
        n1 = (
            "Michel's voice rises sharply; he accuses you of insulting his judgment and slams his hand "
            "on the table, furious that you would attack him here."
        )
        g1 = _executor(base, openai=JsonAdapter(n1))
        r1 = g1.run(
            session_id="s-p2-escalate",
            module_id="god_of_carnage",
            current_scene_id="living_room",
            player_input="I am so angry I want to fight and shout at Michel now.",
            trace_id="trace-p2-escalate",
            host_experience_template=HOST_OK,
        )
        doc1 = {
            "scenario_id": "goc_roadmap_s1_direct_provocation",
            "automated_trace_anchor": "trace-p2-escalate",
            "pytest_anchor": "test_scenario_standard_escalation_non_preview",
            "summary": _summarize_result(r1),
            "dramatic_turn_record_excerpt": _dramatic_turn_excerpt(r1),
        }
        (out_dir / "scenario_goc_roadmap_s1_direct_provocation.json").write_text(
            json.dumps(doc1, indent=2), encoding="utf-8"
        )

        # S2
        n2 = "You stay silent at the table; you say nothing aloud while others watch you hold still and quiet."
        g2 = _executor(base, openai=JsonAdapter(n2))
        r2 = g2.run(
            session_id="s-p2-thin",
            module_id="god_of_carnage",
            current_scene_id="living_room",
            player_input="thin edge silent say nothing",
            trace_id="trace-p2-thin",
            host_experience_template=HOST_OK,
        )
        doc2 = {
            "scenario_id": "goc_roadmap_s2_deflection_brevity",
            "automated_trace_anchor": "trace-p2-thin",
            "pytest_anchor": "test_scenario_thin_edge_silence_non_preview",
            "summary": _summarize_result(r2),
            "dramatic_turn_record_excerpt": _dramatic_turn_excerpt(r2),
        }
        (out_dir / "scenario_goc_roadmap_s2_deflection_brevity.json").write_text(
            json.dumps(doc2, indent=2), encoding="utf-8"
        )

        # S3
        n3 = (
            "I'm sorry you hid this from us; you must reveal the truth now and admit what you knew about "
            "the incident so we can face the fact together."
        )
        g3 = _executor(base, openai=JsonAdapter(n3))
        r3 = g3.run(
            session_id="s-p2-multi",
            module_id="god_of_carnage",
            current_scene_id="living_room",
            player_input="I'm sorry but you must reveal the truth now multi pressure",
            trace_id="trace-p2-multi",
            host_experience_template=HOST_OK,
        )
        doc3 = {
            "scenario_id": "goc_roadmap_s3_pressure_escalation",
            "automated_trace_anchor": "trace-p2-multi",
            "pytest_anchor": "test_scenario_multi_pressure_non_preview",
            "summary": _summarize_result(r3),
            "dramatic_turn_record_excerpt": _dramatic_turn_excerpt(r3),
        }
        (out_dir / "scenario_goc_roadmap_s3_pressure_escalation.json").write_text(
            json.dumps(doc3, indent=2), encoding="utf-8"
        )

        # S4 — canonical misinterpretation / correction chain (see goc_s4_misinterpretation_scenario)
        cached_goc_yaml_title.cache_clear()
        clear_goc_yaml_slice_cache()
        chain = run_roadmap_s4_misinterpretation_chain(base)
        s4_assessment = assess_roadmap_s4_evidence(chain)
        doc4 = {
            "scenario_id": "goc_roadmap_s4_misinterpretation_correction",
            "evidence_run_scope": args.evidence_run_scope,
            "partial_run_disclaimer": note if args.evidence_run_scope == "s4_closure_partial" else None,
            "automated_trace_anchor": f"{TRACE_S4_T1} | {TRACE_S4_T2} | {TRACE_S4_T3}",
            "pytest_anchor": ROADMAP_S4_PYTEST_NODE,
            "pytest_anchor_module": "ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py",
            "roadmap_s4_evidence": s4_assessment,
            "turns": [_summarize_result(x) for x in chain],
            "dramatic_turn_record_excerpts": [_dramatic_turn_excerpt(x) for x in chain],
        }
        (out_dir / "scenario_goc_roadmap_s4_misinterpretation_correction.json").write_text(
            json.dumps(doc4, indent=2), encoding="utf-8"
        )

        # S5 — run_c, third turn (primary openai fails; graph fallback_model uses mock adapter)
        _write_s5_only(base)

    # S6 separate tmp — different corpus layout
    with tempfile.TemporaryDirectory() as td6:
        doc6 = capture_s6_retrieval_heavy(Path(td6))
        (out_dir / "scenario_goc_roadmap_s6_retrieval_heavy.json").write_text(
            json.dumps(doc6, indent=2), encoding="utf-8"
        )

    cached_goc_yaml_title.cache_clear()
    clear_goc_yaml_slice_cache()
    print(
        json.dumps(
            {
                "ok": True,
                "out_dir": str(out_dir),
                "audit_run_id": audit_run_id,
                "evidence_run_scope": args.evidence_run_scope,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
