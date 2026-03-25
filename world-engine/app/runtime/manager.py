from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.content.backend_source import RemoteContentError, load_remote_templates
from app.content.builtins import load_builtin_templates
from app.content.models import ExperienceTemplate, JoinPolicy, ParticipantMode
from app.runtime.engine import RuntimeEngine
from app.runtime.models import ParticipantState, PropState, PublicRunSummary, RunStatus, RuntimeInstance
from app.runtime.store import JsonRunStore


class RuntimeManager:
    def __init__(self, store_root: Path, content_source_url: str | None = None) -> None:
        self.templates: dict[str, ExperienceTemplate] = load_builtin_templates()
        self.content_source_url = (content_source_url or "").strip()
        if self.content_source_url:
            try:
                self.templates.update(load_remote_templates(self.content_source_url))
            except RemoteContentError:
                pass
        self.instances: dict[str, RuntimeInstance] = {}
        self.engines: dict[str, RuntimeEngine] = {}
        self.connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.locks: dict[str, asyncio.Lock] = {}
        self.store = JsonRunStore(store_root)
        self._load_persisted_instances()
        self._ensure_public_open_worlds()

    def _load_persisted_instances(self) -> None:
        for instance in self.store.load_all():
            template = self.templates.get(instance.template_id)
            if template is None:
                continue
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
        return list(self.templates.values())

    def list_runs(self) -> list[PublicRunSummary]:
        summaries: list[PublicRunSummary] = []
        for instance in sorted(self.instances.values(), key=lambda item: item.created_at):
            human_count = len([p for p in instance.participants.values() if p.mode == ParticipantMode.HUMAN])
            connected_humans = len([p for p in instance.participants.values() if p.mode == ParticipantMode.HUMAN and p.connected])
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
                    total_humans=human_count,
                    tension=instance.tension,
                    beat_id=instance.beat_id,
                    owner_player_name=instance.owner_player_name,
                )
            )
        return summaries

    def get_template(self, template_id: str) -> ExperienceTemplate:
        return self.templates[template_id]

    def create_run(
        self,
        template_id: str,
        display_name: str,
        account_id: str | None = None,
        character_id: str | None = None,
    ) -> RuntimeInstance:
        template = self.get_template(template_id)
        return self._bootstrap_instance(
            template,
            owner_display_name=display_name,
            owner_account_id=account_id,
            owner_character_id=character_id,
        )

    def _bootstrap_instance(
        self,
        template: ExperienceTemplate,
        owner_display_name: str | None,
        owner_account_id: str | None = None,
        owner_character_id: str | None = None,
        forced_run_id: str | None = None,
    ) -> RuntimeInstance:
        from app.runtime.models import LobbySeatState
        from app.content.models import ExperienceKind

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
            status=RunStatus.RUNNING if template.kind.value == "open_world" else RunStatus.LOBBY,
            persistent=template.persistent,
        )
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

        # Initialize lobby seats for GROUP_STORY templates
        if template.kind == ExperienceKind.GROUP_STORY:
            for role in template.roles:
                if role.mode == ParticipantMode.HUMAN and role.can_join:
                    instance.lobby_seats[role.id] = LobbySeatState(
                        role_id=role.id,
                        role_display_name=role.display_name,
                    )

        self.instances[instance.id] = instance
        self.engines[instance.id] = RuntimeEngine(template)
        self.locks.setdefault(instance.id, asyncio.Lock())
        self.store.save(instance)

        if owner_display_name:
            joinable_roles = [role for role in template.roles if role.mode == ParticipantMode.HUMAN and role.can_join]
            if not joinable_roles:
                raise ValueError(f"Template {template.id} has no joinable human roles")
            role = joinable_roles[0]
            participant = ParticipantState(
                display_name=owner_display_name,
                role_id=role.id,
                mode=ParticipantMode.HUMAN,
                current_room_id=role.initial_room_id,
                account_id=account_id_or_none(owner_account_id),
                character_id=owner_character_id,
                seat_owner_account_id=account_id_or_none(owner_account_id),
                seat_owner_display_name=owner_display_name,
                seat_owner=owner_account_id or owner_display_name,
            )
            instance.participants[participant.id] = participant
            instance.metadata.setdefault("seat_assignments", {})[role.id] = participant.id

            # Update lobby seat if it exists (for GROUP_STORY templates)
            if role.id in instance.lobby_seats:
                instance.lobby_seats[role.id].participant_id = participant.id
                instance.lobby_seats[role.id].occupant_display_name = owner_display_name
                instance.lobby_seats[role.id].joined_at = datetime.now(timezone.utc)

            instance.updated_at = datetime.now(timezone.utc)
            self.store.save(instance)
        return instance

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
            return existing

        if instance.join_policy == JoinPolicy.OWNER_ONLY:
            if instance.owner_account_id:
                if account_id != instance.owner_account_id:
                    raise PermissionError("This story run is private to its owner.")
            elif instance.owner_player_name and instance.owner_player_name != display_name:
                raise PermissionError("This story run is private to its owner.")

        occupied_roles = {participant.role_id for participant in instance.participants.values() if participant.mode == ParticipantMode.HUMAN}
        available_roles = [
            role for role in template.roles
            if role.mode == ParticipantMode.HUMAN and role.can_join and role.id not in occupied_roles
        ]
        if preferred_role_id:
            available_roles = [role for role in available_roles if role.id == preferred_role_id]
        if not available_roles:
            raise RuntimeError("No joinable human role is currently available.")
        role = available_roles[0]
        participant = ParticipantState(
            display_name=display_name,
            role_id=role.id,
            mode=ParticipantMode.HUMAN,
            current_room_id=role.initial_room_id,
            account_id=account_id_or_none(account_id),
            character_id=character_id,
            seat_owner_account_id=account_id_or_none(account_id),
            seat_owner_display_name=display_name,
            seat_owner=account_id or display_name,
        )
        instance.participants[participant.id] = participant
        instance.status = RunStatus.RUNNING
        instance.metadata.setdefault("seat_assignments", {})[role.id] = participant.id

        # Update lobby seat if it exists
        if role.id in instance.lobby_seats:
            instance.lobby_seats[role.id].participant_id = participant.id
            instance.lobby_seats[role.id].occupant_display_name = display_name
            instance.lobby_seats[role.id].connected = False  # Will be set to True when WebSocket connects
            instance.lobby_seats[role.id].joined_at = datetime.now(timezone.utc)

        self.store.save(instance)
        return participant

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
                    return participant
            if not account_id and participant.seat_owner_display_name == display_name:
                return participant
        return None

    def describe_run(self, run_id: str) -> dict[str, Any]:
        instance = self.instances[run_id]
        participants = []
        for participant in instance.participants.values():
            participants.append({
                "id": participant.id,
                "display_name": participant.display_name,
                "role_id": participant.role_id,
                "mode": participant.mode.value,
                "current_room_id": participant.current_room_id,
                "connected": participant.connected,
                "account_id": participant.account_id,
                "character_id": participant.character_id,
                "seat_owner_account_id": participant.seat_owner_account_id,
                "seat_owner_display_name": participant.seat_owner_display_name,
            })
        return {
            "id": instance.id,
            "template_id": instance.template_id,
            "template_title": instance.template_title,
            "kind": instance.kind.value,
            "join_policy": instance.join_policy.value,
            "status": instance.status.value,
            "beat_id": instance.beat_id,
            "tension": instance.tension,
            "persistent": instance.persistent,
            "owner_player_name": instance.owner_player_name,
            "owner_account_id": instance.owner_account_id,
            "owner_character_id": instance.owner_character_id,
            "participants": participants,
            "seat_assignments": dict(instance.metadata.get("seat_assignments", {})),
            "flags": sorted(instance.flags),
            "metadata": instance.metadata,
            "created_at": instance.created_at.isoformat() if instance.created_at else None,
            "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
        }

    def terminate_run(self, run_id: str, *, actor_display_name: str | None = None, reason: str | None = None) -> dict[str, Any]:
        instance = self.instances[run_id]
        if instance.status == RunStatus.COMPLETED:
            return self.describe_run(run_id)
        instance.status = RunStatus.COMPLETED
        instance.metadata["terminated_reason"] = reason
        instance.metadata["terminated_by"] = actor_display_name
        engine = self.engines[run_id]
        engine._append_event(
            instance,
            event_type="runtime_terminated",
            text=reason or "Runtime terminated by operator.",
            actor=actor_display_name or "operator",
            room_id=None,
            payload={"reason": reason, "terminated_by": actor_display_name},
        )
        self.store.save(instance)
        return self.describe_run(run_id)

    def get_instance(self, run_id: str) -> RuntimeInstance:
        return self.instances[run_id]

    def build_snapshot(self, run_id: str, participant_id: str):
        instance = self.instances[run_id]
        return self.engines[run_id].build_snapshot(instance, participant_id)

    async def connect(self, run_id: str, participant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[run_id][participant_id] = websocket
        instance = self.instances[run_id]
        participant = instance.participants[participant_id]
        participant.connected = True
        instance.status = RunStatus.RUNNING

        # Update lobby seat connected status if it exists
        if participant.role_id in instance.lobby_seats:
            instance.lobby_seats[participant.role_id].connected = True

        self.store.save(instance)
        await self.broadcast_snapshot(run_id)

    async def disconnect(self, run_id: str, participant_id: str) -> None:
        if run_id in self.connections:
            self.connections[run_id].pop(participant_id, None)
        if run_id in self.instances and participant_id in self.instances[run_id].participants:
            instance = self.instances[run_id]
            participant = instance.participants[participant_id]
            participant.connected = False

            # Update lobby seat connected status if it exists
            if participant.role_id in instance.lobby_seats:
                instance.lobby_seats[participant.role_id].connected = False

            self.store.save(instance)
            await self.broadcast_snapshot(run_id)

    async def process_command(self, run_id: str, participant_id: str, command: dict[str, Any]) -> None:
        lock = self.locks.setdefault(run_id, asyncio.Lock())
        async with lock:
            instance = self.instances[run_id]
            engine = self.engines[run_id]
            result = engine.apply_command(instance, participant_id, command)
            if not result.accepted:
                websocket = self.connections[run_id].get(participant_id)
                if websocket:
                    await websocket.send_json({"type": "command_rejected", "reason": result.reason})
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
