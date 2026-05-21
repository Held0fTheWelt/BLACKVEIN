"""Langfuse verify source segment: langfuse_query_filters_and_assertions.

Loaded by loader.py so each refactor slice stays below the file-size gate.
"""

SOURCE = r'''
        elif trace_names:
            allowed_names = {str(name).strip() for name in trace_names if str(name).strip()}
            name_ok = str(row.get("name") or "").strip() in allowed_names
        env_ok = True
        if env_target is not None:
            # GOC-KNOWLEDGE-RUNTIME-INTEGRATION P1.4: staging environment filter so MCP
            # discovery does not silently drop staging traces. Match either the top-level
            # ``environment`` field Langfuse exposes or the metadata mirror written by
            # ``_align_langfuse_otel_resource_environment`` / world-engine adapter.
            candidates = (
                str(row.get("environment") or "").strip().lower(),
                str(meta.get("environment") or "").strip().lower(),
                str(meta.get("langfuse_environment") or "").strip().lower(),
            )
            env_ok = any(value == env_target for value in candidates if value)
        if origin_ok and canonical_ok and tier_ok and name_ok and env_ok:
            filtered.append(row)
    return filtered


def _assertions_for_mode(mode: str) -> list[tuple[str, bool, str]]:
    if mode == "test":
        return [
            ("trace_origin == pytest", True, "metadata.trace_origin must be pytest"),
            (
                "canonical_player_flow == false",
                True,
                "metadata.canonical_player_flow must be false",
            ),
            (
                "live_opening_contract_pass == 0",
                True,
                "score live_opening_contract_pass must be 0",
            ),
        ]
    return [
        ("trace_origin == live_ui", True, "metadata.trace_origin must be live_ui"),
        ("execution_tier == live", True, "metadata.execution_tier must be live"),
        (
            "canonical_player_flow == true",
            True,
            "metadata.canonical_player_flow must be true",
        ),
        (
            "selected_player_role present",
            True,
            "metadata.selected_player_role must be present",
        ),
        (
            "human_actor_id == selected_player_role",
            True,
            "metadata.human_actor_id must equal selected_player_role",
        ),
        (
            "opening_shape_contract_pass == 1",
            True,
            "score opening_shape_contract_pass must be 1",
        ),
        (
            "live_runtime_contract_pass == 1",
            True,
            "score live_runtime_contract_pass must be 1",
        ),
        (
            "live_opening_contract_pass == 1",
            True,
            "score live_opening_contract_pass must be 1",
        ),
        (
            "final_adapter != ldss_fallback",
            True,
            "metadata.final_adapter must not be ldss_fallback",
'''
