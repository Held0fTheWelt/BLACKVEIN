"""Langfuse verify source segment: handler_builder_projection_start.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        ),
        (
            "quality_class not in [degraded, failed]",
            True,
            "metadata.quality_class must not be degraded/failed",
        ),
    ]


def build_langfuse_verify_mcp_handlers() -> dict[str, Callable[..., dict[str, Any]]]:
    config = Config()
    repo_root = Path(config.repo_root)

    def run_projection_tests(arguments: dict[str, Any]) -> dict[str, Any]:
        python_executable = sys.executable
        extra_pytest_args: list[str] = []
        if arguments.get("extra_pytest_args") and isinstance(arguments["extra_pytest_args"], list):
            extra_pytest_args = [str(x) for x in arguments["extra_pytest_args"] if str(x).strip()]
        evidence_metadata = {
            "evidence_scope": "local_pytest",
            "proof_level": "local_only",
            "live_or_staging_evidence": False,
            "governance_adr": "ADR-0039",
        }

        def _tail(raw: str) -> str:
            return "\n".join((raw or "").splitlines()[-40:])

        def _run_pytest_subprocess(
            *,
            cmd: list[str],
            cwd: Path,
            pythonpath_parts: list[str],
        ) -> dict[str, Any]:
            env = dict(os.environ)
            existing_py_path = str(env.get("PYTHONPATH") or "").strip()
            py_path_parts = [x for x in pythonpath_parts if str(x).strip()]
            if existing_py_path:
                py_path_parts.append(existing_py_path)
            env["PYTHONPATH"] = os.pathsep.join(py_path_parts)
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            return {
                **evidence_metadata,
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "command": cmd,
                "cwd": str(cwd),
                "pythonpath": env.get("PYTHONPATH", ""),
                "stdout_tail": _tail(proc.stdout),
                "stderr_tail": _tail(proc.stderr),
            }

        world_engine_path = repo_root / "world-engine"
        world_engine_cwd = world_engine_path
        world_engine_py_path = [str(world_engine_path), str(repo_root)]
        world_engine_preflight_env = dict(os.environ)
        existing_preflight_path = str(world_engine_preflight_env.get("PYTHONPATH") or "").strip()
        if existing_preflight_path:
            world_engine_preflight_env["PYTHONPATH"] = os.pathsep.join(
                [*world_engine_py_path, existing_preflight_path]
            )
        else:
            world_engine_preflight_env["PYTHONPATH"] = os.pathsep.join(world_engine_py_path)
        preflight_cmd = [
            python_executable,
'''
