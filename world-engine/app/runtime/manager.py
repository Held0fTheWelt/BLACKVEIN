from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.config import BACKEND_CONTENT_FEED_URL, BACKEND_CONTENT_SYNC_ENABLED, BACKEND_CONTENT_SYNC_INTERVAL_SECONDS, BACKEND_CONTENT_TIMEOUT_SECONDS, RUN_STORE_BACKEND, RUN_STORE_URL
from app.content.backend_loader import BackendContentLoadError, load_published_templates
from app.content.builtins import load_builtin_templates
from app.content.models import ExperienceKind, ExperienceTemplate, JoinPolicy, ParticipantMode, RoleTemplate
from app.runtime.command_resolution import (
    LastInputInterpretationRecord,
    PlayerMessageIngressResult,
    diagnostics_explicit,
    diagnostics_from_plan,
    diagnostics_missing_input,
    merge_engine_outcome,
    resolve_plan_to_command,
)
from app.runtime.engine import RuntimeEngine
from app.runtime.input_interpreter import interpret_runtime_input
from app.runtime.models import LobbySeatState, ParticipantState, PropState, PublicRunSummary, RunStatus, RuntimeInstance
from app.runtime.store import RunStore, build_run_store


class RuntimeManager:
    def __init__(
        self,
        store_root: Path,
        *,
        store_backend: str | None = None,
        store_url: str | None = None,
        governed_runtime_config: dict[str, Any] | None = None,
    ) -> None:
        self.templates: dict[str, ExperienceTemplate] = load_builtin_templates()
        self.template_sources: dict[str, str] = {template_id: "builtin" for template_id in self.templates}
        self.backend_content_feed_url = BACKEND_CONTENT_FEED_URL
        self.backend_content_sync_enabled = BACKEND_CONTENT_SYNC_ENABLED
        self.backend_content_timeout_seconds = BACKEND_CONTENT_TIMEOUT_SECONDS
        self.backend_content_sync_interval = timedelta(seconds=BACKEND_CONTENT_SYNC_INTERVAL_SECONDS)
        if governed_runtime_config:
            world_engine_settings = governed_runtime_config.get("world_engine_settings") or {}
            backend_settings = governed_runtime_config.get("backend_settings") or {}
            self.backend_content_sync_enabled = bool(world_engine_settings.get("content_sync_enabled", self.backend_content_sync_enabled))
            self.backend_content_sync_interval = timedelta(
                seconds=float(world_engine_settings.get("content_sync_interval", self.backend_content_sync_interval.total_seconds()))
            )
            self.backend_content_timeout_seconds = float(
                world_engine_settings.get("content_timeout_seconds", self.backend_content_timeout_seconds)
            )
            governed_feed = backend_settings.get("content_feed_url")
            if isinstance(governed_feed, str) and governed_feed.strip():
                self.backend_content_feed_url = governed_feed.strip()
        self._last_backend_content_sync_at: datetime | None = None
        self.instances: dict[str, RuntimeInstance] = {}
        self.engines: dict[str, RuntimeEngine] = {}
        self.connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.locks: dict[str, asyncio.Lock] = {}
        self.store: RunStore = build_run_store(
            root=store_root,
            backend=store_backend or RUN_STORE_BACKEND,
            url=store_url or RUN_STORE_URL or None,
        )
        self.sync_templates(force=True)
        self._load_persisted_instances()
        self._ensure_public_open_worlds()

    def sync_templates(self, *, force: bool = False) -> None:
        if not self.backend_content_sync_enabled or not self.backend_content_feed_url:
            return
        now = datetime.now(timezone.utc)
        if not force and self._last_backend_content_sync_at is not None:
            if now - self._last_backend_content_sync_at < self.backend_content_sync_interval:
                return
        try:
            remote_templates = load_published_templates(self.backend_content_feed_url, timeout=self.backend_content_timeout_seconds)
        except BackendContentLoadError:
            self._last_backend_content_sync_at = now
            return
        if remote_templates:
            for template_id, template in remote_templates.items():
                self.templates[template_id] = template
                self.template_sources[template_id] = "backend_published"
        self._last_backend_content_sync_at = now

    def _load_persisted_instances(self) -> None:
        for instance in self.store.load_all():
            template = self.templates.get(instance.template_id)
            if template is None:
                continue
            self._normalize_instance(instance, template)
            self.instances[instance.id] = instance
            self.engines[instance.id] = RuntimeEngine(template)
            self.locks.setdefault(instance.id, asyncio.Lock())

    def _ensure_public_open_worlds(self) -> None:
        for template in self.templates.values():
            if template.persistent and template.join_policy == JoinPolicy.PUBLIC:
                existing = next((run for run in self.instances.values() if run.template_id == template.id), None)
                if existing is None:
                    self._bootstrap_instance(template, owner_display_name=None, forced_run_id=f"public-{template.id}")

    def list_templates(self) -> list[ExperienceTemplate]:
        self.sync_templates()
        return list(self.templates.values())

    def list_runs(self) -> list[PublicRunSummary]:
        summaries: list[PublicRunSummary] = []
        for instance in sorted(self.instances.values(), key=lambda item: item.created_at):
            human_participants = [p for p in instance.participants.values() if p.mode == ParticipantMode.HUMAN]
            connected_humans = len([p for p in human_participants if p.connected])
            total_humans = len(human_participants)
            seats = list(instance.lobby_seats.values())
            summaries.append(
                PublicRunSummary(
                    id=instance.id,
                    template_id=instance.template_id,
                    template_title=instance.template_title,
                    kind=instance.kind,
                    join_policy=instance.join_policy,
                    persistent=instance.persistent,
                    status=instance.status,
                    connected_humans=connected_humans,
                    total_humans=total_humans,
                    open_human_seats=len([seat for seat in seats if seat.participant_id is None]),
                    ready_human_seats=len([seat for seat in seats if seat.ready]),
                    tension=instance.tension,
                    beat_id=instance.beat_id,
                    owner_player_name=instance.owner_player_name,
                )
            )
        return summaries

    def get_template(self, template_id: str) -> ExperienceTemplate:
        self.sync_templates()
        return self.templates[template_id]

    def create_run(
        self,
        template_id: str,
        display_name: str,
        account_id: str | None = None,
        character_id: str | None = None,
        preferred_role_id: str | None = None,
    ) -> RuntimeInstance:
        template = self.get_template(template_id)
        return self._bootstrap_instance(
            template,
            owner_display_name=display_name,
            owner_account_id=account_id,
            owner_character_id=character_id,
            preferred_role_id=preferred_role_id,
        )

    def _bootstrap_instance(
        self,
        template: ExperienceTemplate,
        owner_display_name: str | None,
        owner_account_id: str | None = None,
        owner_character_id: str | None = None,
        forced_run_id: str | None = None,
        preferred_role_id: str | None = None,
    ) -> RuntimeInstance:
        instance = RuntimeInstance(
            id=forced_run_id or uuid4().hex,
            template_id=template.id,
            template_title=template.title,
            kind=template.kind,
            join_policy=template.join_policy,
            owner_player_name=owner_display_name,
            owner_account_id=owner_account_id,
            owner_character_id=owner_character_id,
            beat_id=template.initial_beat_id,
            status=self._initial_status_for(template),
            persistent=template.persistent,
        )
        instance.metadata.setdefault("store_backend", self.store.backend_name)
        instance.metadata.setdefault("min_humans_to_start", template.min_humans_to_start)
        self._initialize_lobby_seats(instance, template)

        for role in template.roles:
            if role.mode == ParticipantMode.NPC:
                npc = ParticipantState(
                    display_name=role.display_name,
                    role_id=role.id,
                    mode=role.mode,
                    current_room_id=role.initial_room_id,
                    connected=True,
                )
                instance.participants[npc.id] = npc
        for prop in template.props:
            room_id = next(room.id for room in template.rooms if prop.id in room.prop_ids)
            instance.props[prop.id] = PropState(
                id=prop.id,
                name=prop.name,
                description=prop.description,
                room_id=room_id,
                state=prop.initial_state,
            )
        self.instances[instance.id] = instance
        self.engines[instance.id] = RuntimeEngine(template)
        self.locks.setdefault(instance.id, asyncio.Lock())
        self.store.save(instance)

        if owner_display_name:
            joinable_roles = [role for role in template.roles if role.mode == ParticipantMode.HUMAN and role.can_join]
            if not joinable_roles:
                raise ValueError(f"Template {template.id} has no joinable human roles")
            if preferred_role_id:
                role = next((r for r in joinable_roles if r.id == preferred_role_id), None)
                if role is None:
                    raise ValueError(
                        f"Preferred role {preferred_role_id!r} is not a joinable human role in template {template.id!r}."
                    )
            else:
                role = joinable_roles[0]
            participant = self._attach_human_participant(
                instance,
                role,
                display_name=owner_display_name,
                account_id=account_id_or_none(owner_account_id),
                character_id=owner_character_id,
                set_owner=True,
            )
            if template.kind == ExperienceKind.SOLO_STORY:
                instance.status = RunStatus.RUNNING
                instance.lobby_seats[participant.role_id].ready = True
            instance.updated_at = datetime.now(timezone.utc)
            self.store.save(instance)
        return instance

    def _initialize_lobby_seats(self, instance: RuntimeInstance, template: ExperienceTemplate) -> None:
        instance.lobby_seats = {
            role.id: LobbySeatState(role_id=role.id, role_display_name=role.display_name)
            for role in template.roles
            if role.mode == ParticipantMode.HUMAN and role.can_join
        }

    def _normalize_instance(self, instance: RuntimeInstance, template: ExperienceTemplate) -> None:
        if not instance.lobby_seats:
            self._initialize_lobby_seats(instance, template)
        for role in template.roles:
            if role.mode != ParticipantMode.HUMAN or not role.can_join:
                continue
            instance.lobby_seats.setdefault(role.id, LobbySeatState(role_id=role.id, role_display_name=role.display_name))
        for participant in instance.participants.values():
            if participant.mode != ParticipantMode.HUMAN:
                continue
            seat = instance.lobby_seats.get(participant.role_id)
            if seat is None:
                continue
            seat.participant_id = participant.id
            seat.occupant_display_name = participant.display_name
            seat.connected = participant.connected
            seat.joined_at = participant.joined_at
            if participant.account_id and not seat.reserved_for_account_id:
                seat.reserved_for_account_id = participant.account_id
            if not seat.reserved_for_display_name:
                seat.reserved_for_display_name = participant.display_name
        instance.metadata.setdefault("store_backend", self.store.backend_name)
        instance.metadata.setdefault("min_humans_to_start", template.min_humans_to_start)

    def _initial_status_for(self, template: ExperienceTemplate) -> RunStatus:
        if template.kind == ExperienceKind.OPEN_WORLD:
            return RunStatus.RUNNING
        if template.kind == ExperienceKind.GROUP_STORY:
            return RunStatus.LOBBY
        return RunStatus.LOBBY

    def _attach_human_participant(
        self,
        instance: RuntimeInstance,
        role: RoleTemplate,
        *,
        display_name: str,
        account_id: str | None,
        character_id: str | None,
        set_owner: bool = False,
    ) -> ParticipantState:
        participant = ParticipantState(
            display_name=display_name,
            role_id=role.id,
            mode=ParticipantMode.HUMAN,
            current_room_id=role.initial_room_id,
            account_id=account_id,
            character_id=character_id,
            seat_owner_account_id=account_id,
            seat_owner_display_name=display_name,
            seat_owner=account_id or display_name,
        )
        instance.participants[participant.id] = participant
        seat = instance.lobby_seats[role.id]
        seat.participant_id = participant.id
        seat.occupant_display_name = display_name
        seat.reserved_for_account_id = account_id
        seat.reserved_for_display_name = display_name
        seat.connected = False
        seat.ready = instance.kind == ExperienceKind.SOLO_STORY
        seat.joined_at = participant.joined_at
        instance.metadata.setdefault("seat_assignments", {})[role.id] = participant.id
        if set_owner and account_id:
            instance.owner_account_id = account_id
        if set_owner:
            instance.owner_player_name = display_name
        return participant

    def find_or_join_run(
        self,
        run_id: str,
        display_name: str,
        account_id: str | None = None,
        character_id: str | None = None,
        preferred_role_id: str | None = None,
    ) -> ParticipantState:
        instance = self.instances[run_id]
        template = self.templates[instance.template_id]

        existing = self._find_existing_human_participant(instance, account_id=account_id, character_id=character_id, display_name=display_name)
        if existing is not None:
            self._sync_seat_from_participant(instance, existing)
            self.store.save(instance)
            return existing

        if instance.join_policy == JoinPolicy.OWNER_ONLY:
            if instance.owner_account_id:
                if account_id != instance.owner_account_id:
                    raise PermissionError("This story run is private to its owner.")
            elif instance.owner_player_name and instance.owner_player_name != display_name:
                raise PermissionError("This story run is private to its owner.")

        role = self._resolve_join_role(instance, template, account_id=account_id, display_name=display_name, preferred_role_id=preferred_role_id)
        if role is None:
            raise RuntimeError("No joinable human seat is currently available.")

        participant = self._attach_human_participant(
            instance,
            role,
            display_name=display_name,
            account_id=account_id_or_none(account_id),
            character_id=character_id,
        )
        if template.kind != ExperienceKind.GROUP_STORY:
            instance.status = RunStatus.RUNNING
        self.store.save(instance)
        return participant

    def _resolve_join_role(
        self,
        instance: RuntimeInstance,
        template: ExperienceTemplate,
        *,
        account_id: str | None,
        display_name: str,
        preferred_role_id: str | None,
    ) -> RoleTemplate | None:
        joinable_roles = {
            role.id: role
            for role in template.roles
            if role.mode == ParticipantMode.HUMAN and role.can_join
        }
        if preferred_role_id:
            seat = instance.lobby_seats.get(preferred_role_id)
            role = joinable_roles.get(preferred_role_id)
            if seat and role and self._seat_can_be_claimed(seat, account_id=account_id, display_name=display_name):
                return role
            return None

        for role_id, role in joinable_roles.items():
            seat = instance.lobby_seats[role_id]
            if self._seat_can_be_claimed(seat, account_id=account_id, display_name=display_name):
                return role
        return None

    def _seat_can_be_claimed(self, seat: LobbySeatState, *, account_id: str | None, display_name: str) -> bool:
        if seat.participant_id is None:
            return True
        if account_id and seat.reserved_for_account_id == account_id:
            return True
        if not account_id and seat.reserved_for_display_name == display_name:
            return True
        return False

    def _find_existing_human_participant(
        self,
        instance: RuntimeInstance,
        account_id: str | None,
        character_id: str | None,
        display_name: str,
    ) -> ParticipantState | None:
        for participant in instance.participants.values():
            if participant.mode != ParticipantMode.HUMAN:
                continue
            if account_id and participant.account_id == account_id:
                if character_id is None or participant.character_id == character_id:
                    if display_name and participant.display_name != display_name:
                        participant.display_name = display_name
                        if participant.role_id in instance.lobby_seats:
                            instance.lobby_seats[participant.role_id].occupant_display_name = display_name
                            instance.lobby_seats[participant.role_id].reserved_for_display_name = display_name
                    return participant
            if not account_id and participant.seat_owner_display_name == display_name:
                return participant
        return None

    def _sync_seat_from_participant(self, instance: RuntimeInstance, participant: ParticipantState) -> None:
        seat = instance.lobby_seats.get(participant.role_id)
        if seat is None:
            return
        seat.participant_id = participant.id
        seat.occupant_display_name = participant.display_name
        seat.connected = participant.connected
        seat.joined_at = participant.joined_at
        if participant.account_id:
            seat.reserved_for_account_id = participant.account_id
        seat.reserved_for_display_name = participant.display_name

    def get_instance(self, run_id: str) -> RuntimeInstance:
        return self.instances[run_id]

    def build_snapshot(self, run_id: str, participant_id: str):
        instance = self.instances[run_id]
        return self.engines[run_id].build_snapshot(instance, participant_id)

    def get_run_details(self, run_id: str) -> dict[str, Any]:
        instance = self.instances[run_id]
        template = self.templates[instance.template_id]
        return {
            "run": instance.model_dump(mode="json"),
            "template_source": self.template_sources.get(instance.template_id, "builtin"),
            "template": {
                "id": template.id,
                "title": template.title,
                "kind": template.kind.value,
                "join_policy": template.join_policy.value,
                "min_humans_to_start": template.min_humans_to_start,
            },
            "store": self.store.describe(),
            "lobby": self.engines[run_id].build_lobby_payload(instance),
        }

    def terminate_run(
        self,
        run_id: str,
        *,
        actor_display_name: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        instance = self.instances.pop(run_id, None)
        self.engines.pop(run_id, None)
        self.connections.pop(run_id, None)
        self.locks.pop(run_id, None)
        if instance is None:
            raise KeyError(run_id)
        self.store.delete(run_id)
        return {
            "run_id": run_id,
            "terminated": True,
            "template_id": instance.template_id,
            "actor_display_name": (actor_display_name or "").strip(),
            "reason": (reason or "").strip(),
        }

    async def connect(self, run_id: str, participant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[run_id][participant_id] = websocket
        participant = self.instances[run_id].participants[participant_id]
        participant.connected = True
        self._sync_seat_from_participant(self.instances[run_id], participant)
        if self.instances[run_id].kind != ExperienceKind.GROUP_STORY or self.instances[run_id].status != RunStatus.LOBBY:
            self.instances[run_id].status = RunStatus.RUNNING
        self.store.save(self.instances[run_id])
        await self.broadcast_snapshot(run_id)

    async def disconnect(self, run_id: str, participant_id: str) -> None:
        if run_id in self.connections:
            self.connections[run_id].pop(participant_id, None)
        if run_id in self.instances and participant_id in self.instances[run_id].participants:
            participant = self.instances[run_id].participants[participant_id]
            participant.connected = False
            self._sync_seat_from_participant(self.instances[run_id], participant)
            self.store.save(self.instances[run_id])
            await self.broadcast_snapshot(run_id)

    @staticmethod
    def _map_explicit_command(raw_text: str) -> dict[str, Any] | None:
        stripped = raw_text.strip()
        if not stripped.startswith(("/", "!")):
            return None
        parts = stripped[1:].split()
        if not parts:
            return None
        name = parts[0].lower()
        args = parts[1:]
        if name in {"move", "go", "goto"} and args:
            return {"action": "move", "target_room_id": args[0]}
        if name in {"say", "speak"} and args:
            return {"action": "say", "text": " ".join(args)}
        if name in {"emote", "me"} and args:
            return {"action": "emote", "text": " ".join(args)}
        if name in {"inspect", "look", "examine"} and args:
            return {"action": "inspect", "target_id": args[0]}
        if name in {"ready"}:
            return {"action": "set_ready", "ready": True}
        if name in {"unready"}:
            return {"action": "set_ready", "ready": False}
        if name in {"start", "start_run"}:
            return {"action": "start_run"}
        return None

    def _interpretation_context(self, run_id: str, participant_id: str) -> dict[str, Any]:
        instance = self.instances[run_id]
        engine = self.engines[run_id]
        actor = instance.participants[participant_id]
        room = engine.rooms[actor.current_room_id]
        visible_targets = [actor.current_room_id, *room.prop_ids]
        available_actions = engine.available_actions(instance, actor)
        reachable_rooms = [
            {"id": ex.target_room_id, "name": engine.rooms[ex.target_room_id].name} for ex in room.exits
        ]
        return {
            "available_actions": available_actions,
            "visible_targets": visible_targets,
            "reachable_rooms": reachable_rooms,
        }

    def resolve_player_message(self, run_id: str, participant_id: str, payload: dict[str, Any]) -> PlayerMessageIngressResult:
        """Normalize and interpret incoming player payloads into at most one explicit command plus diagnostics."""
        action = payload.get("action")

        if isinstance(action, str) and action.strip().lower() == "input_text":
            text_val = payload.get("text")
            if not isinstance(text_val, str) or not text_val.strip():
                diag = diagnostics_missing_input(actor_participant_id=participant_id)
                diag.input_source = "input_text_payload"
                diag.rejection_reason = "Field input_text.text must be a non-empty string."
                return PlayerMessageIngressResult(
                    command=None,
                    rejection_code=diag.rejection_code,
                    rejection_reason=diag.rejection_reason,
                    diagnostics=diag,
                )
            text = text_val.strip()
            ctx = self._interpretation_context(run_id, participant_id)
            plan = interpret_runtime_input(
                text,
                available_actions=ctx["available_actions"],
                visible_targets=ctx["visible_targets"],
                reachable_rooms=ctx["reachable_rooms"],
            )
            cmd, rcode, rreason = resolve_plan_to_command(plan)
            resolved = cmd["action"] if cmd else None
            diag = diagnostics_from_plan(
                plan,
                actor_participant_id=participant_id,
                input_source="input_text_payload",
                rejection_code=rcode,
                rejection_reason=rreason,
                resolved_action=resolved,
            )
            return PlayerMessageIngressResult(
                command=cmd,
                rejection_code=rcode,
                rejection_reason=rreason,
                diagnostics=diag,
            )

        if isinstance(action, str) and action.strip():
            act = action.strip()
            diag = diagnostics_explicit(
                actor_participant_id=participant_id,
                input_source="explicit_payload",
                resolved_action=act,
                rationale="Structured command with explicit action field.",
            )
            return PlayerMessageIngressResult(command=dict(payload), diagnostics=diag)

        raw_input = payload.get("player_input")
        if raw_input is None:
            raw_input = payload.get("input")
        if not isinstance(raw_input, str) or not raw_input.strip():
            diag = diagnostics_missing_input(actor_participant_id=participant_id)
            return PlayerMessageIngressResult(
                command=None,
                rejection_code=diag.rejection_code,
                rejection_reason=diag.rejection_reason,
                diagnostics=diag,
            )

        text = raw_input.strip()
        slash_cmd = self._map_explicit_command(text)
        if slash_cmd is not None:
            act = str(slash_cmd.get("action", ""))
            diag = diagnostics_explicit(
                actor_participant_id=participant_id,
                input_source="slash_in_text",
                resolved_action=act,
                rationale="Slash or bang command parsed from free-text field.",
            )
            return PlayerMessageIngressResult(command=slash_cmd, diagnostics=diag)

        ctx = self._interpretation_context(run_id, participant_id)
        plan = interpret_runtime_input(
            text,
            available_actions=ctx["available_actions"],
            visible_targets=ctx["visible_targets"],
            reachable_rooms=ctx["reachable_rooms"],
        )
        cmd, rcode, rreason = resolve_plan_to_command(plan)
        resolved = cmd["action"] if cmd else None
        diag = diagnostics_from_plan(
            plan,
            actor_participant_id=participant_id,
            input_source="natural_language",
            rejection_code=rcode,
            rejection_reason=rreason,
            resolved_action=resolved,
        )
        return PlayerMessageIngressResult(
            command=cmd,
            rejection_code=rcode,
            rejection_reason=rreason,
            diagnostics=diag,
        )

    async def process_command(self, run_id: str, participant_id: str, command: dict[str, Any]) -> None:
        ingress = self.resolve_player_message(run_id, participant_id, command)
        instance = self.instances[run_id]

        def _apply_metadata(diag: LastInputInterpretationRecord) -> None:
            instance.metadata["last_input_interpretation"] = diag.as_metadata_dict()

        _apply_metadata(ingress.diagnostics)

        if ingress.command is None:
            self.store.save(instance)
            websocket = self.connections[run_id].get(participant_id)
            if websocket:
                msg: dict[str, Any] = {
                    "type": "command_rejected",
                    "reason": ingress.rejection_reason or "Command rejected.",
                }
                if ingress.rejection_code:
                    msg["code"] = ingress.rejection_code
                await websocket.send_json(msg)
            return

        lock = self.locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            instance = self.instances[run_id]
            engine = self.engines[run_id]
            result = engine.apply_command(instance, participant_id, ingress.command)
            final_diag = merge_engine_outcome(
                ingress.diagnostics,
                actor_participant_id=participant_id,
                engine_accepted=result.accepted,
                engine_reason=result.reason,
            )
            instance.metadata["last_input_interpretation"] = final_diag.as_metadata_dict()
            if not result.accepted:
                self.store.save(instance)
                websocket = self.connections[run_id].get(participant_id)
                if websocket:
                    await websocket.send_json(
                        {
                            "type": "command_rejected",
                            "reason": result.reason or "Command rejected.",
                            "code": "engine_rejected",
                        }
                    )
                return
            engine.run_npc_cycle(instance, participant_id)
            self.store.save(instance)
        await self.broadcast_snapshot(run_id)

    async def broadcast_snapshot(self, run_id: str) -> None:
        if run_id not in self.connections:
            return
        instance = self.instances[run_id]
        engine = self.engines[run_id]
        for participant_id, websocket in list(self.connections[run_id].items()):
            if participant_id not in instance.participants:
                continue
            snapshot = engine.build_snapshot(instance, participant_id)
            try:
                await websocket.send_json({"type": "snapshot", "data": snapshot.model_dump(mode="json")})
            except Exception:
                self.connections[run_id].pop(participant_id, None)



def account_id_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    return str(value)
