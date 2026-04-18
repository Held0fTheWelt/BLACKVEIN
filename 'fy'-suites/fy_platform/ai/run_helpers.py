"""Run lifecycle and artifact bundle helpers.

This module extracts mechanical responsibilities from BaseAdapter:
- Run lifecycle management (_start_run, _finish_run)
- Payload bundle writing (_write_payload_bundle)

These are pure mechanical operations that should be shared across adapters
without inheritance. This module is part of the first core-thinning wave.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fy_platform.ai.evidence_registry.registry import EvidenceRegistry
from fy_platform.ai.run_journal.journal import RunJournal
from fy_platform.ai.workspace import (
    internal_run_dir,
    target_repo_id,
    write_json,
)


class RunLifecycleHelper:
    """Mechanical helper for managing run lifecycle."""

    def __init__(self, registry: EvidenceRegistry, journal: RunJournal, root: Path) -> None:
        """Initialize run helper with registry and journal.

        Parameters
        ----------
        registry
            Evidence registry for recording runs
        journal
            Run journal for recording events
        root
            fy workspace root
        """
        self.registry = registry
        self.journal = journal
        self.root = root

    def start_run(
        self,
        suite: str,
        mode: str,
        target_repo_root: Path,
        governance: dict[str, Any] | None = None,
    ) -> tuple[str, Path, str]:
        """Create a new run, enforce governance, and write opening journal events.

        Parameters
        ----------
        suite
            Suite name
        mode
            Run mode (e.g., 'audit', 'inspect')
        target_repo_root
            Target repository path
        governance
            Optional governance status

        Returns
        -------
        tuple
            (run_id, run_dir, target_repo_id)

        Raises
        ------
        RuntimeError
            If governance gate fails
        """
        if governance and not governance.get("ok"):
            failures = governance.get("failures", [])
            raise RuntimeError(f"governance_gate_failed:{';'.join(failures)}")

        tgt_id = target_repo_id(target_repo_root)
        run = self.registry.start_run(
            suite=suite,
            mode=mode,
            target_repo_root=str(target_repo_root),
            target_repo_id=tgt_id,
        )
        run_dir = internal_run_dir(self.root, suite, run.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        self.journal.append(
            suite,
            run.run_id,
            "run_started",
            {
                "mode": mode,
                "target_repo_root": str(target_repo_root),
                "target_repo_id": tgt_id,
            },
        )

        if governance:
            self.journal.append(suite, run.run_id, "self_governance_checked", governance)

        return run.run_id, run_dir, tgt_id

    def finish_run(self, suite: str, run_id: str, status: str, summary: dict[str, Any]) -> None:
        """Write closing run journal data and mark the run complete.

        Parameters
        ----------
        suite
            Suite name
        run_id
            Run identifier
        status
            Final run status (e.g., 'ok', 'failed')
        summary
            Summary data to record
        """
        self.journal.append(suite, run_id, "run_finished", {"status": status, "summary": summary})
        self.registry.finish_run(run_id, status=status)


class PayloadBundleHelper:
    """Mechanical helper for writing artifact bundles."""

    def __init__(self, registry: EvidenceRegistry, root: Path) -> None:
        """Initialize bundle helper.

        Parameters
        ----------
        registry
            Evidence registry for recording artifacts
        root
            fy workspace root
        """
        self.registry = registry
        self.root = root

    def write_payload_bundle(
        self,
        *,
        suite: str,
        run_id: str,
        run_dir: Path,
        payload: dict[str, Any],
        summary_md: str,
        role_prefix: str,
    ) -> dict[str, str]:
        """Write a JSON/Markdown artifact pair for a run payload.

        This is one of the most important bridge points: turning an in-memory
        result into persistent, explainable run artifacts.

        Parameters
        ----------
        suite
            Suite name
        run_id
            Run identifier
        run_dir
            Run directory path
        payload
            Payload to write as JSON
        summary_md
            Markdown summary text
        role_prefix
            Artifact role prefix (e.g., 'audit', 'inspect')

        Returns
        -------
        dict
            Paths to written JSON and markdown files
        """
        json_path = run_dir / f"{role_prefix}.json"
        md_path = run_dir / f"{role_prefix}.md"

        write_json(json_path, payload)
        md_path.write_text(summary_md, encoding="utf-8")

        self.registry.record_artifact(
            suite=suite,
            run_id=run_id,
            format="json",
            role=f"{role_prefix}_json",
            path=str(json_path.relative_to(self.root)),
            payload=payload,
        )
        self.registry.record_artifact(
            suite=suite,
            run_id=run_id,
            format="md",
            role=f"{role_prefix}_md",
            path=str(md_path.relative_to(self.root)),
            payload={"markdown_preview": summary_md[:500]},
        )
        return {"json_path": str(json_path), "md_path": str(md_path)}
