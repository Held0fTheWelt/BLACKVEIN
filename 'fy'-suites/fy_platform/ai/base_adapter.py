"""Shared base adapter for all fy suite adapters.

This module defines :class:`BaseSuiteAdapter`, the common runtime surface that all
suite-specific adapters build on top of. The class provides three major kinds of
behavior:

1. **Workspace bootstrapping**
   It resolves the fy workspace root, ensures the required internal directory
   layout exists, and wires together the shared platform services
   (registry, journal, semantic index, context packs, and model router).

2. **Common lifecycle commands**
   It implements the generic suite lifecycle used throughout the fy platform,
   including ``init``, ``inspect``, ``explain``, ``prepare_context_pack``,
   ``compare_runs``, ``clean``, ``reset``, ``triage``, ``prepare_fix``,
   ``self_audit``, ``release_readiness``, and ``production_readiness``.

3. **Run orchestration helpers**
   It provides internal helpers for starting and finishing runs, writing
   artifact bundles, attaching suite status pages, and enforcing governance
   gates before outward work begins.

The class is intentionally conservative:

- internal state always stays inside the fy workspace,
- outward work is explicit,
- risky automatic action is avoided,
- and every suite inherits the same operational baseline.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from fy_platform.ai.context_packs.service import ContextPackService
from fy_platform.ai.cross_suite_intelligence import collect_cross_suite_signals
from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.model_router.router import ModelRouter
from fy_platform.ai.policy.suite_quality_policy import (
    evaluate_suite_quality,
    evaluate_workspace_quality,
)
from fy_platform.ai.production_readiness import workspace_production_readiness
from fy_platform.ai.release_readiness import suite_release_readiness
from fy_platform.ai.run_journal.journal import RunJournal
from fy_platform.ai.run_helpers import RunLifecycleHelper, PayloadBundleHelper
from fy_platform.ai.semantic_index.index_manager import SemanticIndex
from fy_platform.ai.status_page import build_status_payload, write_status_page
from fy_platform.ai.workspace import (
    binding_path,
    ensure_workspace_layout,
    suite_hub_dir,
    target_repo_id,
    utc_now,
    workspace_root,
    write_json,
)


class BaseSuiteAdapter(ABC):
    """Common base class for all fy suite adapters.

    Every suite adapter inherits the same internal services and lifecycle
    surface from this class. Concrete suites only need to add their
    suite-specific audit logic and, where relevant, stronger implementations
    for fix preparation or consolidation.

    Parameters
    ----------
    suite:
        Canonical suite name, for example ``"contractify"`` or ``"documentify"``.
        It is used to scope internal storage, runs, generated artifacts, and
        status pages.
    root:
        Optional path to a fy workspace root. If omitted, the shared workspace
        resolution logic is used.

    Notes
    -----
    The constructor performs real initialization work:
    - resolves the fy workspace root,
    - ensures the workspace layout exists,
    - constructs shared platform services,
    - and guarantees suite-local working directories exist.
    """

    def __init__(self, suite: str, root: Path | None = None) -> None:
        """Initialize the adapter and its shared platform services.

        The initialization is intentionally eager rather than lazy. This keeps
        all suite adapters operationally consistent and avoids half-initialized
        objects that only fail later during a command invocation.
        """
        self.suite = suite
        self.root = workspace_root(root)

        # Build the minimum fy workspace structure before any shared service
        # tries to touch local state, registry files, or generated outputs.
        ensure_workspace_layout(self.root)

        # Shared platform services live at the workspace level and are reused by
        # all suite adapters so that every suite sees the same evidence, runs,
        # search index, and routing policy.
        self.registry = EvidenceRegistry(self.root)
        self.journal = RunJournal(self.root)
        self.index = SemanticIndex(self.root)
        self.context_packs = ContextPackService(self.root)
        self.router = ModelRouter()

        # Each suite owns a hub directory inside the autark fy workspace.
        # The hub collects reports, local state, and generated artifacts while
        # keeping those files out of the outward target repository.
        self.hub_dir = suite_hub_dir(self.root, suite)
        self.hub_dir.mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "reports").mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "state").mkdir(parents=True, exist_ok=True)
        (self.hub_dir / "generated").mkdir(parents=True, exist_ok=True)

        # Initialize mechanical helpers (extracted from base adapter for thinning)
        self._run_lifecycle = RunLifecycleHelper(self.registry, self.journal, self.root)
        self._bundle_helper = PayloadBundleHelper(self.registry, self.root)

    def _cross_suite(self, query: str | None = None) -> dict[str, Any]:
        """Collect cross-suite signals relevant to the current suite.

        Parameters
        ----------
        query:
            Optional query string used to bias the cross-suite signal collection
            toward the current problem or explanation request.

        Returns
        -------
        dict[str, Any]
            Cross-suite hints and related signals that can enrich status pages,
            explanations, and next-step recommendations.
        """
        return collect_cross_suite_signals(self.root, self.suite, query=query)

    def _attach_status_page(
        self,
        command: str,
        payload: dict[str, Any],
        latest_run: dict[str, Any] | None = None,
        governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Attach a persisted status page to a command payload.

        This helper enriches the outgoing payload with:
        - the latest run information,
        - governance context,
        - cross-suite signals,
        - and a generated status page written into the suite workspace.
        """
        latest = latest_run if latest_run is not None else self.registry.latest_run(self.suite)
        gov = governance if governance is not None else payload.get("governance")

        # If the payload does not already contain cross-suite context, attach a
        # lightweight signal bundle so the status page is not isolated from the
        # rest of the workspace.
        payload.setdefault(
            "cross_suite",
            self._cross_suite(payload.get("query") or payload.get("summary") or ""),
        )

        status = build_status_payload(
            suite=self.suite,
            command=command,
            payload=payload,
            latest_run=latest,
            governance=gov,
        )
        payload.update(write_status_page(self.root, self.suite, status))
        return payload

    def self_governance_status(self) -> dict[str, Any]:
        """Evaluate workspace-level and suite-level governance health."""
        workspace = evaluate_workspace_quality(self.root)
        suite = evaluate_suite_quality(self.root, self.suite)
        ok = bool(workspace["ok"] and suite["ok"])
        failures = [f"workspace:{item}" for item in workspace["missing"]] + [
            f"suite:{item}" for item in suite["missing"]
        ]
        warnings = list(workspace["warnings"]) + list(suite["warnings"])
        return {
            "ok": ok,
            "suite": self.suite,
            "failures": failures,
            "warnings": warnings,
            "workspace": workspace,
            "suite_check": suite,
        }

    def init(self, target_repo_root: str | None = None) -> dict[str, Any]:
        """Initialize the suite and optionally bind it to a target repository."""
        ensure_workspace_layout(self.root)
        target = Path(target_repo_root).resolve() if target_repo_root else None
        governance = self.self_governance_status()

        if target_repo_root and (not target or not target.exists() or not target.is_dir()):
            payload = {
                "ok": False,
                "suite": self.suite,
                "reason": "target_repo_not_found",
                "target_repo_root": target_repo_root,
                "governance": governance,
            }
            return self._attach_status_page("init", payload, governance=governance)

        # Initialization is intentionally blocked if the internal workspace is
        # not healthy enough. This keeps suites from binding outward work while
        # their own internal foundations are already broken.
        if not governance["ok"]:
            payload = {
                "ok": False,
                "suite": self.suite,
                "reason": "governance_gate_failed:init",
                "governance": governance,
            }
            return self._attach_status_page("init", payload, governance=governance)

        binding = {
            "suite": self.suite,
            "workspace_root": str(self.root),
            "target_repo_root": str(target) if target else None,
            "target_repo_id": target_repo_id(target) if target else None,
            "bound_at": utc_now(),
        }
        write_json(binding_path(self.root, self.suite), binding)

        payload = {
            "ok": True,
            "suite": self.suite,
            "binding": binding,
            "governance": governance,
            "warnings": governance["warnings"],
            "summary": (
                f"{self.suite} is initialized and bound for outward work. "
                "Internal state stays in the fy workspace."
            ),
        }
        return self._attach_status_page("init", payload, governance=governance)

    def inspect(self, query: str | None = None) -> dict[str, Any]:
        """Inspect the latest suite state and optionally retrieve query context."""
        latest = self.registry.latest_run(self.suite)
        governance = self.self_governance_status()
        route = self.router.route(
            "summarize",
            evidence_strength="moderate",
            audience="developer",
            reproducibility="strict",
        )

        out = {
            "ok": True,
            "suite": self.suite,
            "latest_run": latest,
            "governance": governance,
            "warnings": governance["warnings"],
            "route": route.__dict__,
            "summary": (
                f"{self.suite} is ready for inspection. Read the latest summary "
                "first and then only open detailed artifacts where you still "
                "need proof."
            ),
            "uncertainty": [],
        }

        if query:
            pack = self.index.build_context_pack(query, suite_scope=[self.suite], audience="developer")
            out.update(
                {
                    "query": query,
                    "hit_count": len(pack.hits),
                    "summary": pack.summary,
                    "artifact_paths": pack.artifact_paths,
                    "evidence_confidence": pack.evidence_confidence,
                    "priorities": pack.priorities,
                    "next_steps": pack.next_steps,
                    "uncertainty": pack.uncertainty,
                }
            )

        return self._attach_status_page("inspect", out, governance=governance)

    @abstractmethod
    def audit(self, target_repo_root: str) -> dict:
        """Run the suite-specific audit against a target repository."""
        raise NotImplementedError

    def explain(self, audience: str = "developer") -> dict[str, Any]:
        """Explain the most recent run in audience-appropriate language."""
        latest = self.registry.latest_run(self.suite)
        governance = self.self_governance_status()

        if not latest:
            payload = {"ok": False, "reason": "no_runs", "suite": self.suite, "governance": governance}
            return self._attach_status_page("explain", payload, governance=governance)

        artifacts = self.registry.artifacts_for_run(latest["run_id"])
        journal_summary = self.journal.summarize(self.suite, latest["run_id"])
        route = self.router.route("explain", audience=audience, evidence_strength="moderate")

        base = f"Suite {self.suite} last ran in mode {latest['mode']} with status {latest['status']}."
        if artifacts:
            base += f" Produced {len(artifacts)} artifacts."

        if audience == "manager":
            summary = (
                f"{self.suite} has a fresh result. Start with the simple summary "
                "and only open deeper artifacts where the summary still feels incomplete."
            )
        elif audience == "operator":
            summary = base + " Review the journal and generated artifacts before outward application."
        else:
            summary = base + " Start with the top artifacts and validate the next action against the latest evidence."

        payload = {
            "ok": True,
            "suite": self.suite,
            "run_id": latest["run_id"],
            "summary": summary,
            "artifacts": artifacts,
            "journal_summary": journal_summary,
            "governance": governance,
            "warnings": governance["warnings"],
            "route": route.__dict__,
        }
        return self._attach_status_page("explain", payload, latest_run=latest, governance=governance)

    def prepare_context_pack(self, query: str, audience: str = "developer") -> dict[str, Any]:
        """Build a fresh context pack for the suite and the current query.

        The function does more than run a search once. It first refreshes the
        relevant index scopes, then builds a context pack from the newest suite
        artifacts and the most recent bound outward repository state.
        """
        latest = self.registry.latest_run(self.suite)

        # Step 1: if the latest run points at a bound target repository, refresh
        # the target scope so the context pack does not rely on stale indexed
        # evidence from a previous target snapshot.
        if latest and latest.get("target_repo_root"):
            target = Path(latest["target_repo_root"])
            if target.is_dir():
                # Clear the older target-scope view first so the next indexing
                # pass becomes the authoritative search surface for this target.
                self.index.clear_scope(self.suite, "target", latest.get("target_repo_id"))
                self.index.index_directory(
                    suite=self.suite,
                    directory=target,
                    scope="target",
                    target_repo_id=latest.get("target_repo_id"),
                )

        # Step 2: re-index suite-owned artifacts as a separate scope. This makes
        # sure the pack can also pull in the newest reports, generated summaries,
        # context packs, and status surfaces produced inside the fy workspace.
        self.index.clear_scope(self.suite, "suite")
        self.index.index_directory(suite=self.suite, directory=self.hub_dir, scope="suite")

        # Step 3: prepare the output directory inside the suite-owned generated
        # area. Context packs remain internal first and only become outward
        # material if someone explicitly exports or applies them later.
        out_dir = self.hub_dir / "generated" / "context_packs"
        out_dir.mkdir(parents=True, exist_ok=True)

        # Step 4: route the task through the model router so the pack is built
        # under a strict, reproducible profile rather than an ad-hoc mode.
        route = self.router.route(
            "prepare_context_pack",
            audience=audience,
            evidence_strength="moderate",
            reproducibility="strict",
        )

        # Step 5: build and persist the pack. The payload already contains the
        # retrieved evidence, summary, priorities, and next-step suggestions.
        payload = self.context_packs.build_and_write(
            suite=self.suite,
            query=query,
            suite_scope=[self.suite],
            audience=audience,
            out_dir=out_dir,
        )
        payload.update(
            {
                "ok": True,
                "suite": self.suite,
                "query": query,
                "audience": audience,
                "route": route.__dict__,
            }
        )

        # Step 6: attach a status page so the freshly built pack is reflected in
        # the suite's simple-language status surfaces as well.
        return self._attach_status_page("prepare-context-pack", payload, latest_run=latest)

    def compare_runs(self, left_run_id: str, right_run_id: str) -> dict[str, Any]:
        """Compare two historical runs of the same suite."""
        delta = self.registry.compare_runs(left_run_id, right_run_id)
        if not delta:
            return self._attach_status_page(
                "compare-runs",
                {"ok": False, "reason": "run_not_found", "suite": self.suite},
            )

        warnings: list[str] = []
        if delta.target_repo_changed or delta.target_repo_id_changed:
            warnings.append("target_repo_changed_between_runs")
        if delta.mode_changed:
            warnings.append("mode_changed_between_runs")

        route = self.router.route("compare", evidence_strength="moderate")
        payload = {
            "ok": True,
            "suite": self.suite,
            **delta.__dict__,
            "warnings": warnings,
            "route": route.__dict__,
            "summary": (
                f"Compared {left_run_id} with {right_run_id}. Focus first on "
                "changed artifacts, review-state changes, and any target or "
                "mode differences."
            ),
        }
        return self._attach_status_page("compare-runs", payload)

    def clean(self, mode: str = "standard") -> dict[str, Any]:
        """Remove transient suite data without destroying canonical workspace state."""
        removed = []
        cache_dir = self.root / ".fydata" / "cache"
        if cache_dir.is_dir():
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            removed.append(str(cache_dir.relative_to(self.root)))

        if mode in {"aggressive", "generated"}:
            gen_dir = self.hub_dir / "generated"
            if gen_dir.is_dir():
                shutil.rmtree(gen_dir)
                gen_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(gen_dir.relative_to(self.root)))

        if mode == "aggressive":
            run_dir = self.root / ".fydata" / "runs" / self.suite
            if run_dir.is_dir():
                shutil.rmtree(run_dir)
                run_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(run_dir.relative_to(self.root)))

        payload = {"ok": True, "suite": self.suite, "mode": mode, "removed": removed}
        return self._attach_status_page("clean", payload)

    def reset(self, mode: str = "soft") -> dict[str, Any]:
        """Reset suite state to a cleaner baseline."""
        removed = []

        if mode in {"soft", "hard"}:
            state_dir = self.hub_dir / "state"
            if state_dir.is_dir():
                shutil.rmtree(state_dir)
                state_dir.mkdir(parents=True, exist_ok=True)
                removed.append(str(state_dir.relative_to(self.root)))

        if mode in {"hard", "reindex-reset"}:
            index_db = self.root / ".fydata" / "index" / "semantic_index.db"
            if index_db.exists():
                index_db.unlink()
                removed.append(str(index_db.relative_to(self.root)))
                self.index = SemanticIndex(self.root)

        if mode == "hard":
            bind = binding_path(self.root, self.suite)
            if bind.exists():
                bind.unlink()
                removed.append(str(bind.relative_to(self.root)))

        payload = {"ok": True, "suite": self.suite, "mode": mode, "removed": removed}
        return self._attach_status_page("reset", payload)

    def triage(self, query: str | None = None) -> dict[str, Any]:
        """Rank likely problem areas before a user takes action."""
        route = self.router.route(
            "triage",
            ambiguity="high" if query else "low",
            evidence_strength="weak" if not query else "moderate",
        )
        latest = self.registry.latest_run(self.suite)
        hints = []
        if latest:
            artifacts = self.registry.artifacts_for_run(latest["run_id"])
            hints = [item["path"] for item in artifacts[:5]]

        payload = {
            "ok": True,
            "suite": self.suite,
            "route": route.__dict__,
            "query": query or "",
            "latest_hints": hints,
            "summary": (
                "Triage is for ranking problems before action. It should help "
                "you decide what to inspect next, not silently fix risky issues."
            ),
            "decision": {
                "lane": "likely_but_review" if query else "abstain",
                "recommended_action": "Use triage to rank evidence first. Do not treat it as proof on its own.",
                "uncertainty_flags": ["query_missing"] if not query else [],
            },
            "uncertainty": ["query_missing"] if not query else [],
        }
        return self._attach_status_page("triage", payload)

    def prepare_fix(self, finding_ids: list[str]) -> dict[str, Any]:
        """Prepare an advisory-only fix plan for explicit findings."""
        route = self.router.route(
            "prepare_fix",
            ambiguity="high" if not finding_ids else "low",
            evidence_strength="weak" if not finding_ids else "moderate",
        )
        decision_lane = "abstain" if not finding_ids else "likely_but_review"
        payload = {
            "ok": True,
            "suite": self.suite,
            "route": route.__dict__,
            "finding_ids": finding_ids,
            "advisory_only": True,
            "decision": {
                "lane": decision_lane,
                "recommended_action": "Prepare the fix plan, then review it before any outward application.",
                "uncertainty_flags": ["no_finding_ids"] if not finding_ids else [],
            },
            "uncertainty": ["no_finding_ids"] if not finding_ids else [],
        }
        return self._attach_status_page("prepare-fix", payload)

    def self_audit(self) -> dict[str, Any]:
        """Audit whether the suite itself is internally healthy."""
        governance = self.self_governance_status()
        latest = self.registry.latest_run(self.suite)
        latest_artifacts = self.registry.artifacts_for_run(latest["run_id"]) if latest else []
        payload = {
            "ok": governance["ok"],
            "suite": self.suite,
            "summary": (
                "Self-audit checks whether this suite is internally well "
                "formed, documented, and ready for outward work."
            ),
            "governance": governance,
            "latest_run": latest,
            "latest_artifact_count": len(latest_artifacts),
            "warnings": governance["warnings"],
            "blocking_reasons": governance["failures"],
        }
        return self._attach_status_page("self-audit", payload, latest_run=latest, governance=governance)

    def release_readiness(self) -> dict[str, Any]:
        """Return MVP release readiness for the suite."""
        payload = suite_release_readiness(self.root, self.suite)
        payload.update(
            {
                "ok": payload["ready"],
                "summary": (
                    "Release readiness tells you if this suite is ready to "
                    "participate in an MVP release from the current workspace state."
                ),
            }
        )
        return self._attach_status_page("release-readiness", payload, latest_run=payload.get("latest_run"))

    def production_readiness(self) -> dict[str, Any]:
        """Return stricter production-readiness information for the suite."""
        workspace_payload = workspace_production_readiness(self.root)
        suite_payload = suite_release_readiness(self.root, self.suite)
        payload = {
            "ok": bool(workspace_payload.get("ok") and suite_payload.get("ready")),
            "suite": self.suite,
            "summary": (
                "Production readiness is stricter than MVP release readiness. "
                "It checks persistence, compatibility, recovery, observability, "
                "security, and release-management evidence."
            ),
            "workspace_production": {
                "ok": workspace_payload.get("ok"),
                "workspace_production_md_path": workspace_payload.get("workspace_production_md_path"),
                "top_next_steps": workspace_payload.get("top_next_steps", []),
            },
            "suite_release": suite_payload,
            "warnings": list(suite_payload.get("warnings", [])),
        }
        return self._attach_status_page(
            "production-readiness",
            payload,
            latest_run=suite_payload.get("latest_run"),
        )

    def import_bundle(self, bundle_path: str, *, legacy: bool = False) -> dict[str, Any]:
        """Default import entry point for suites without bundle import support.

        Suites that support importing current or legacy bundles should override this
        method. The base implementation keeps unsupported import work explicit.
        """
        payload = {
            'ok': False,
            'suite': self.suite,
            'reason': 'import_not_supported',
            'bundle_path': bundle_path,
            'legacy': legacy,
        }
        return self._attach_status_page('legacy-import' if legacy else 'import', payload)

    def consolidate(
        self,
        target_repo_root: str,
        *,
        apply_safe: bool = False,
        instruction: str | None = None,
    ) -> dict[str, Any]:
        """Default consolidation entry point for suites without support."""
        payload = {
            "ok": False,
            "suite": self.suite,
            "reason": "consolidate_not_supported",
            "apply_safe": apply_safe,
            "instruction": instruction or "",
        }
        return self._attach_status_page("consolidate", payload)

    def _start_run(self, mode: str, target_repo_root: Path) -> tuple[str, Path, str]:
        """Create a new run, enforce governance, and write opening journal events.

        This method delegates to RunLifecycleHelper (extracted mechanical responsibility).
        """
        governance = self.self_governance_status()
        return self._run_lifecycle.start_run(
            suite=self.suite,
            mode=mode,
            target_repo_root=target_repo_root,
            governance=governance,
        )

    def _finish_run(self, run_id: str, status: str, summary: dict[str, Any]) -> None:
        """Write closing run journal data and mark the run complete.

        This method delegates to RunLifecycleHelper (extracted mechanical responsibility).
        """
        self._run_lifecycle.finish_run(self.suite, run_id, status, summary)

    def _write_payload_bundle(
        self,
        *,
        run_id: str,
        run_dir: Path,
        payload: dict[str, Any],
        summary_md: str,
        role_prefix: str,
    ) -> dict[str, str]:
        """Write a JSON/Markdown artifact pair for a run payload.

        This is one of the most important bridge points: turning an in-memory
        result into persistent, explainable run artifacts.

        This method delegates to PayloadBundleHelper (extracted mechanical responsibility).
        """
        return self._bundle_helper.write_payload_bundle(
            suite=self.suite,
            run_id=run_id,
            run_dir=run_dir,
            payload=payload,
            summary_md=summary_md,
            role_prefix=role_prefix,
        )
