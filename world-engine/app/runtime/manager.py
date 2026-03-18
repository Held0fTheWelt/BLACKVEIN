from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.content.builtins import load_builtin_templates
from app.content.models import ExperienceTemplate, JoinPolicy, ParticipantMode
from app.runtime.engine import RuntimeEngine
from app.runtime.models import ParticipantState, PropState, PublicRunSummary, RunStatus, RuntimeInstance
from app.runtime.store import JsonRunStore, RunStore


class RuntimeManager:
    def __init__(self, store_root: Path, store: RunStore | None = None) -> None:
        self.templates: dict[str, ExperienceTemplate] = load_builtin_templates()
        self.instances: dict[str, RuntimeInstance] = {}
        self.engines: dict[str, RuntimeEngine] = {}
        self.connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.run_locks: dict[str, asyncio.Lock] = {}
        self.store = store or JsonRunStore(store_root)
        self._load_persisted_instances()
        self._ensure_public_open_worlds()

    def _get_run_lock(self, run_id: str) -> asyncio.Lock:
        lock = self.run_locks.get(run_id)
        if lock is None:
            lock = asyncio.Lock()
            self.run_locks[run_id] = lock
        return lock

    def _load_persisted_instances(self) -> None:
        for instance in self.store.load_all():
            template = self.templates.get(instance.template_id)
            if template is None:
                continue
            self.instances[instance.id] = instance
            self.engines[instance.id] = RuntimeEngine(template)
            self._get_run_lock(instance.id)

    def _ensure_public_open_worlds(self) -> None:
        for template in self.templates.values():
            if template.persistent and template.join_policy == JoinPolicy.PUBLIC:
                existing = next((run for run in self.instances.values() if run.template_id == template.id), None)
                if existing is None:
                    self._bootstrap_instance(
                        template,
                        owner_account_id=None,
                        owner_display_name=None,
                        forced_run_id=f"public-{template.id}",
                    )

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
                    owner_display_name=instance.owner_display_name,
                )
            )
        return summaries

    def get_template(self, template_id: str) -> ExperienceTemplate:
        return self.templates[template_id]

    def create_run(
        self,
        template_id: str,
        account_id: str,
        display_name: str,
        character_id: str | None = None,
    ) -> RuntimeInstance:
        template = self.get_template(template_id)
        return self._bootstrap_instance(
            template,
            owner_account_id=account_id,
            owner_display_name=display_name,
            owner_character_id=character_id,
        )

    def _bootstrap_instance(
        self,
        template: ExperienceTemplate,
        owner_account_id: str | None,
        owner_display_name: str | None,
        owner_character_id: str | None = None,
        forced_run_id: str | None = None,
    ) -> RuntimeInstance:
        instance = RuntimeInstance(
            id=forced_run_id or uuid4().hex,
            template_id=template.id,
            template_title=template.title,
            kind=template.kind,
            join_policy=template.join_policy,
            owner_account_id=owner_account_id,
            owner_display_name=owner_display_name,
            beat_id=template.initial_beat_id,
            status=RunStatus.RUNNING if template.kind.value == "open_world" else RunStatus.LOBBY,
            persistent=template.persistent,
        )
        for role in template.roles:
            if role.mode == ParticipantMode.NPC:
                npc = ParticipantState(
                    account_id=f"npc:{template.id}:{role.id}",
                    display_name=role.display_name,
                    role_id=role.id,
                    mode=role.mode,
                    current_room_id=role.initial_room_id,
                    connected=True,
                    seat_owner_account_id=f"npc:{template.id}:{role.id}",
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
        self._get_run_lock(instance.id)
        self.store.save(instance)

        if owner_account_id and owner_display_name:
            joinable_roles = [role for role in template.roles if role.mode == ParticipantMode.HUMAN and role.can_join]
            if not joinable_roles:
                raise ValueError(f"Template {template.id} has no joinable human roles")
            role = joinable_roles[0]
            participant = ParticipantState(
                account_id=owner_account_id,
                display_name=owner_display_name,
                character_id=owner_character_id,
                role_id=role.id,
                mode=ParticipantMode.HUMAN,
                current_room_id=role.initial_room_id,
                seat_owner_account_id=owner_account_id,
            )
            instance.participants[participant.id] = participant
            instance.metadata.setdefault("seat_assignments", {})[role.id] = participant.id
            instance.updated_at = datetime.now(timezone.utc)
            self.store.save(instance)
        return instance

    def find_or_join_run(
        self,
        run_id: str,
        account_id: str,
        display_name: str,
        character_id: str | None = None,
        preferred_role_id: str | None = None,
    ) -> ParticipantState:
        instance = self.instances[run_id]
        template = self.templates[instance.template_id]

        for participant in instance.participants.values():
            if participant.mode == ParticipantMode.HUMAN and participant.seat_owner_account_id == account_id:
                if character_id and not participant.character_id:
                    participant.character_id = character_id
                    self.store.save(instance)
                return participant

        if instance.join_policy == JoinPolicy.OWNER_ONLY and instance.owner_account_id != account_id:
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
            account_id=account_id,
            display_name=display_name,
            character_id=character_id,
            role_id=role.id,
            mode=ParticipantMode.HUMAN,
            current_room_id=role.initial_room_id,
            seat_owner_account_id=account_id,
        )
        instance.participants[participant.id] = participant
        instance.status = RunStatus.RUNNING
        instance.metadata.setdefault("seat_assignments", {})[role.id] = participant.id
        self.store.save(instance)
        return participant

    def get_instance(self, run_id: str) -> RuntimeInstance:
        return self.instances[run_id]

    def build_snapshot(self, run_id: str, participant_id: str):
        instance = self.instances[run_id]
        return self.engines[run_id].build_snapshot(instance, participant_id)

    def visible_transcript(self, run_id: str, participant_id: str):
        instance = self.instances[run_id]
        engine = self.engines[run_id]
        viewer = instance.participants[participant_id]
        return engine.visibility.visible_transcript(instance, viewer, tail=500)

    async def connect(self, run_id: str, participant_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._get_run_lock(run_id):
            self.connections[run_id][participant_id] = websocket
            self.instances[run_id].participants[participant_id].connected = True
            self.instances[run_id].status = RunStatus.RUNNING
            self.store.save(self.instances[run_id])
        await self.broadcast_snapshot(run_id)

    async def disconnect(self, run_id: str, participant_id: str) -> None:
        async with self._get_run_lock(run_id):
            if run_id in self.connections:
                self.connections[run_id].pop(participant_id, None)
            if run_id in self.instances and participant_id in self.instances[run_id].participants:
                self.instances[run_id].participants[participant_id].connected = False
                self.store.save(self.instances[run_id])
        await self.broadcast_snapshot(run_id)

    async def process_command(self, run_id: str, participant_id: str, command: dict[str, Any]) -> None:
        async with self._get_run_lock(run_id):
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
        self.store.save(instance)
