from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import WebSocket

from app.config import RUN_STORE_BACKEND, RUN_STORE_URL
from app.content.builtins import load_builtin_templates
from app.content.models import ExperienceKind, ExperienceTemplate, JoinPolicy, ParticipantMode, RoleTemplate
from app.runtime.engine import RuntimeEngine
from app.runtime.models import LobbySeatState, ParticipantState, PropState, PublicRunSummary, RunStatus, RuntimeInstance
from app.runtime.store import RunStore, build_run_store


class RuntimeManager:
    def __init__(
        self,
        store_root: Path,
        *,
        store_backend: str | None = None,
        store_url: str | None = None,
    ) -> None:
        self.templates: dict[str, ExperienceTemplate] = load_builtin_templates()
        self.instances: dict[str, RuntimeInstance] = {}
        self.engines: dict[str, RuntimeEngine] = {}
        self.connections: dict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.locks: dict[str, asyncio.Lock] = {}
        self.store: RunStore = build_run_store(
            root=store_root,
            backend=store_backend or RUN_STORE_BACKEND,
            url=store_url or RUN_STORE_URL or None,
        )
        self._load_persisted_instances()
        self._ensure_public_open_worlds()

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
