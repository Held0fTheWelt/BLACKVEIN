"""Langfuse verify source segment: handler_projection_preflight.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
            "-c",
            "import app.story_runtime; print('import_ok=app.story_runtime')",
        ]
        preflight = subprocess.run(
            preflight_cmd,
            cwd=str(world_engine_cwd),
            env=world_engine_preflight_env,
            text=True,
            capture_output=True,
            check=False,
        )
        if preflight.returncode != 0:
            world_engine_result = {
                **evidence_metadata,
                "ok": False,
                "returncode": preflight.returncode,
                "command": preflight_cmd,
                "cwd": str(world_engine_cwd),
                "pythonpath": world_engine_preflight_env.get("PYTHONPATH", ""),
                "stdout_tail": _tail(preflight.stdout),
                "stderr_tail": _tail(preflight.stderr),
            }
            ai_stack_result = {
                **evidence_metadata,
                "ok": False,
                "returncode": None,
                "command": [
                    python_executable,
                    "-m",
                    "pytest",
                    "ai_stack/tests/test_actor_lane_absence_governance.py",
                    "-q",
                    *extra_pytest_args,
                ],
                "cwd": str(repo_root),
                "pythonpath": "",
                "stdout_tail": "",
                "stderr_tail": "skipped_due_to_world_engine_preflight_failure",
            }
            return {
                **evidence_metadata,
                "ok": False,
                "world_engine": world_engine_result,
                "ai_stack": ai_stack_result,
            }

        world_engine_result = _run_pytest_subprocess(
            cmd=[
                python_executable,
                "-m",
                "pytest",
                "tests/test_trace_middleware.py",
                "-q",
                *extra_pytest_args,
            ],
            cwd=world_engine_cwd,
            pythonpath_parts=world_engine_py_path,
        )
        ai_stack_result = _run_pytest_subprocess(
            cmd=[
                python_executable,
                "-m",
                "pytest",
                "ai_stack/tests/test_actor_lane_absence_governance.py",
                "-q",
                *extra_pytest_args,
            ],
            cwd=repo_root,
            pythonpath_parts=[str(repo_root)],
        )
        return {
            **evidence_metadata,
'''
