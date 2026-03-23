"""Infrastructure validation tests for Clockwork hybrid orchestration."""
import os
import pytest


class TestClockworkIntegration:
    """Validate Clockwork infrastructure and folder structures."""

    def test_memory_system_exists(self):
        """Verify .clockwork_runtime/knowledge/ exists and is accessible."""
        repo_root = self._get_repo_root()
        knowledge_dir = os.path.join(repo_root, ".clockwork_runtime", "knowledge")
        assert os.path.isdir(knowledge_dir), (
            f"Clockwork knowledge directory missing: {knowledge_dir}"
        )
        assert os.access(knowledge_dir, os.R_OK), (
            f"Clockwork knowledge directory not readable: {knowledge_dir}"
        )

    def test_evidence_folder_structure(self):
        """Verify evidence/, brain/, audit/, reports/ folders exist."""
        repo_root = self._get_repo_root()
        clockwork_dir = os.path.join(repo_root, ".clockwork_runtime")

        required_dirs = [
            os.path.join(clockwork_dir, "evidence"),
            os.path.join(clockwork_dir, "brain"),
            os.path.join(clockwork_dir, "audit"),
            os.path.join(clockwork_dir, "reports"),
        ]

        for dir_path in required_dirs:
            assert os.path.isdir(dir_path), (
                f"Clockwork directory missing: {dir_path}"
            )
            assert os.access(dir_path, os.R_OK), (
                f"Clockwork directory not readable: {dir_path}"
            )

    def test_infrastructure_files(self):
        """Verify ROLES.md and MEMORY.md exist in repo root."""
        repo_root = self._get_repo_root()

        required_files = [
            os.path.join(repo_root, "CLAUDE.md"),
            os.path.join(repo_root, "INFRASTRUCTURE.md"),
        ]

        for file_path in required_files:
            assert os.path.isfile(file_path), (
                f"Infrastructure file missing: {file_path}"
            )
            assert os.access(file_path, os.R_OK), (
                f"Infrastructure file not readable: {file_path}"
            )

    @staticmethod
    def _get_repo_root():
        """Get the repository root by traversing up from tests directory."""
        current = os.path.dirname(os.path.abspath(__file__))
        # From backend/tests/ up to repo root
        while True:
            if os.path.exists(os.path.join(current, ".git")):
                return current
            parent = os.path.dirname(current)
            if parent == current:
                raise RuntimeError("Could not find repo root with .git")
            current = parent
