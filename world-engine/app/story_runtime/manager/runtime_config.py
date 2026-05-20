"""Runtime configuration projection.

Resolves manager runtime configuration, governed runtime status, and public truth surfaces.
"""
from __future__ import annotations

from ._deps import *

class _RuntimeConfigMixin:
    def _allow_degraded_commit_after_retries(self) -> bool:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        return bool(settings.get("allow_degraded_commit_after_retries", True))

    def _validation_execution_mode(self) -> str:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        mode = str(
            (self._governed_runtime_config or {}).get("validation_execution_mode")
            or settings.get("validation_execution_mode")
            or "schema_plus_semantic"
        ).strip().lower()
        if mode not in {"schema_only", "schema_plus_semantic", "strict_rule_engine"}:
            return "schema_plus_semantic"
        return mode

    def _opening_retry_count(self) -> int:
        settings = (
            (self._governed_runtime_config or {}).get("world_engine_settings") or {}
            if isinstance(self._governed_runtime_config, dict)
            else {}
        )
        try:
            return max(0, int(settings.get("opening_retry_attempts", 2)))
        except Exception:
            return 2

    def _story_runtime_experience_policy(self):
        """Resolve the active Story Runtime Experience policy from governed config.

        Always returns a policy — if the resolved config is missing or the
        section has not been seeded yet (first boot), canonical defaults are
        used so the runtime still packages truthfully in recap mode.
        """
        from ai_stack.story_runtime.story_runtime_experience import (
            extract_policy_from_resolved_config,
        )

        return extract_policy_from_resolved_config(self._governed_runtime_config)

    def _apply_experience_packaging(self, raw_bundle, policy):
        if not isinstance(raw_bundle, dict):
            return raw_bundle
        try:
            from ai_stack.story_runtime.story_runtime_experience_packaging import (
                package_bundle_with_policy,
            )

            return package_bundle_with_policy(raw_bundle, policy)
        except Exception:  # noqa: BLE001 — packaging must not break the turn
            return raw_bundle

    def _apply_runtime_components(self, governed_runtime_config: dict[str, Any] | None) -> None:
        components = build_governed_story_runtime_components(governed_runtime_config)
        if components is not None:
            reg, rout, adp = components
            self.registry = reg
            self.routing = rout
            self.adapters = adp
            self._governed_runtime_config = dict(governed_runtime_config or {})
            self._runtime_config_status = {
                "source": "governed_runtime_config",
                "config_version": (governed_runtime_config or {}).get("config_version"),
                "last_reload_ok": True,
                "route_count": len((governed_runtime_config or {}).get("routes") or []),
                "model_count": len((governed_runtime_config or {}).get("models") or []),
                "live_execution_blocked": False,
            }
            self.metrics.incr(
                "runtime_config_apply_success",
                source="governed_runtime_config",
                config_version=(governed_runtime_config or {}).get("config_version"),
            )
            return
        # Escape hatch removed: always fail-closed when config is invalid/missing
        reason = "resolved_config_unusable"
        if not isinstance(governed_runtime_config, dict):
            reason = "resolved_config_missing"
        elif not is_governed_resolved_config_operational(governed_runtime_config):
            reason = "resolved_config_incomplete_or_invalid"
        self._apply_blocked_runtime_components(governed_runtime_config, reason_code=reason)

    def _apply_blocked_runtime_components(
        self, governed_runtime_config: dict[str, Any] | None, *, reason_code: str
    ) -> None:
        """Fail-closed posture: no default registry, no hidden live-capable adapters."""
        self._governed_runtime_config = dict(governed_runtime_config) if isinstance(governed_runtime_config, dict) else None
        self.registry = ModelRegistry()
        self.routing = BlockedLiveStoryRoutingPolicy()
        self.adapters = {}
        self._runtime_config_status = {
            "source": "governed_config_invalid_or_missing",
            "config_version": (governed_runtime_config or {}).get("config_version")
            if isinstance(governed_runtime_config, dict)
            else None,
            "last_reload_ok": False,
            "route_count": 0,
            "model_count": 0,
            "live_execution_blocked": True,
            "live_execution_block_reason": reason_code,
        }
        self.metrics.incr(
            "runtime_config_apply_blocked",
            source="governed_config_invalid_or_missing",
            reason=reason_code,
            config_version=self._runtime_config_status.get("config_version"),
        )

    def _rebuild_turn_graph(self) -> None:
        gen_mode = None
        retrieval_cfg = None
        if isinstance(self._governed_runtime_config, dict):
            gen_mode = str(self._governed_runtime_config.get("generation_execution_mode") or "").strip() or None
            retrieval_cfg = retrieval_config_from_governed(self._governed_runtime_config)
        self.turn_graph = RuntimeTurnGraphExecutor(
            interpreter=interpret_player_input,
            routing=self.routing,
            registry=self.registry,
            adapters=self.adapters,
            retriever=self.retriever,
            assembler=self.context_assembler,
            capability_registry=self.capability_registry,
            max_self_correction_attempts=self._max_self_correction_attempts(),
            allow_degraded_commit_after_retries=self._allow_degraded_commit_after_retries(),
            generation_execution_mode=gen_mode,
            retrieval_config=retrieval_cfg,
            action_resolution_short_path_enabled=getattr(
                self, "_action_resolution_short_path_enabled", True
            ),
        )

    def _bump_authority_version(self) -> None:
        self._authority_version += 1
        self._authority_applied_at_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def reload_runtime_config(self, governed_runtime_config: dict[str, Any] | None) -> dict[str, Any]:
        configure_prompt_bundle(
            governed_runtime_config.get("prompt_store")
            if isinstance(governed_runtime_config, dict)
            else None
        )
        self._apply_runtime_components(governed_runtime_config)
        self._rebuild_turn_graph()
        self._bump_authority_version()
        return self.runtime_config_status()

    def runtime_config_status(self) -> dict[str, Any]:
        src = str(self._runtime_config_status.get("source") or "")
        governed = src in {"governed_runtime_config", "governed_runtime_config_with_injected_adapters"}
        # Publish a runtime-truth surface so operators can inspect the actual
        # runtime mode, authority source, generation mode, graph mode,
        # validator-lane posture, and prompt-template / commit / schema contract
        # versions. Loader or package state is explicitly not part of this
        # surface (see ``_compose_runtime_truth_surface``).
        truth_surface = self._compose_runtime_truth_surface(governed=governed)
        return {
            **self._runtime_config_status,
            "governed_runtime_active": governed and not bool(self._runtime_config_status.get("live_execution_blocked")),
            "legacy_default_registry_path": src == "default_registry",
            "max_self_correction_attempts": self._max_self_correction_attempts(),
            "allow_degraded_commit_after_retries": self._allow_degraded_commit_after_retries(),
            "metrics": self.metrics.summary(),
            # Authority-binding identity. Monotonically increments on every
            # successful or blocked apply so post-reload live turns can prove
            # they ran under the new authority rather than stale registry /
            # routing components.
            "authority_version": self._authority_version,
            "authority_applied_at_iso": self._authority_applied_at_iso,
            "runtime_truth_surface": truth_surface,
            # Story Runtime Experience truth surface: configured vs effective,
            # degradation markers, and packaging contract version. Operators
            # rely on this rather than the configured row to know whether the
            # requested mode is actually honored.
            "story_runtime_experience": self._story_runtime_experience_policy().to_truth_surface(),
            "session_loop_logging": self._session_loop_log_policy(),
        }

    def _session_loop_log_policy(self) -> dict[str, Any]:
        cfg = self._governed_runtime_config if isinstance(self._governed_runtime_config, dict) else {}
        settings = cfg.get("world_engine_settings") if isinstance(cfg.get("world_engine_settings"), dict) else {}
        raw = settings.get("session_loop_logging")
        source = "governed_runtime_config.world_engine_settings.session_loop_logging"
        if not isinstance(raw, dict):
            raw = settings.get("session_loop_observability")
            source = "governed_runtime_config.world_engine_settings.session_loop_observability"
        if not isinstance(raw, dict):
            raw = {}
            source = "default"

        raw_level = str(raw.get("level") or "info").strip().lower()
        level = raw_level if raw_level in SESSION_LOOP_LOG_LEVELS else "info"
        return {
            "contract": SESSION_LOOP_LOG_POLICY_VERSION,
            "source": source,
            "enabled": bool(raw.get("enabled", True)),
            "level": level,
            "include_runtime_world_summary": bool(raw.get("include_runtime_world_summary", True)),
            "include_projection_summary": bool(raw.get("include_projection_summary", True)),
            "include_diagnostic_summary": bool(raw.get("include_diagnostic_summary", True)),
        }

    @staticmethod
    def _runtime_world_summary(runtime_world: dict[str, Any]) -> dict[str, Any]:
        world = runtime_world if isinstance(runtime_world, dict) else {}
        return {
            "schema_version": world.get("schema_version"),
            "status": world.get("status"),
            "mode": world.get("mode"),
            "current_room_id": world.get("current_room_id"),
            "room_count": len(world.get("rooms") if isinstance(world.get("rooms"), dict) else {}),
            "prop_count": len(world.get("props") if isinstance(world.get("props"), dict) else {}),
            "exit_count": len(world.get("exits") if isinstance(world.get("exits"), dict) else {}),
            "actor_count": len(world.get("actors") if isinstance(world.get("actors"), dict) else {}),
            "diagnostic_summary": world.get("diagnostic_summary"),
        }

    @staticmethod
    def _runtime_projection_summary(runtime_projection: dict[str, Any]) -> dict[str, Any]:
        projection = runtime_projection if isinstance(runtime_projection, dict) else {}
        return {
            "module_id": projection.get("module_id"),
            "runtime_profile_id": projection.get("runtime_profile_id"),
            "start_scene_id": projection.get("start_scene_id"),
            "start_room_id": projection.get("start_room_id"),
            "room_count": len(projection.get("rooms") if isinstance(projection.get("rooms"), list) else []),
            "location_count": len(projection.get("locations") if isinstance(projection.get("locations"), list) else []),
            "prop_count": len(projection.get("props") if isinstance(projection.get("props"), list) else []),
            "object_count": len(projection.get("objects") if isinstance(projection.get("objects"), list) else []),
            "npc_actor_count": len(projection.get("npc_actor_ids") if isinstance(projection.get("npc_actor_ids"), list) else []),
            "has_human_actor_id": bool(str(projection.get("human_actor_id") or "").strip()),
        }


__all__ = ["_RuntimeConfigMixin"]
