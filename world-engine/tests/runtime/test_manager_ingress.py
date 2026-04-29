"""RuntimeManager ingress: structured results and metadata diagnostics."""

from __future__ import annotations

import pytest

from app.runtime.command_resolution import REJECTION_MISSING_INPUT, REJECTION_NO_INTERPRETABLE_INTENT
from app.runtime.manager import RuntimeManager


@pytest.mark.asyncio
async def test_explicit_command_path_unchanged(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="a1", display_name="P1")
    human = next(p for p in run.participants.values() if p.account_id == "a1")
    ingress = manager.resolve_player_message(run.id, human.id, {"action": "say", "text": "Hello."})
    assert ingress.command == {"action": "say", "text": "Hello."}
    assert ingress.rejection_code is None
    assert ingress.diagnostics.input_source == "explicit_payload"
    assert ingress.diagnostics.resolved_action == "say"
    meta = ingress.diagnostics.as_metadata_dict()
    assert "parser_version" in meta
    assert "candidate_summaries" in meta


@pytest.mark.asyncio
async def test_natural_language_rejection_metadata_schema(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="a1", display_name="P1")
    human = next(p for p in run.participants.values() if p.account_id == "a1")
    ingress = manager.resolve_player_message(run.id, human.id, {"player_input": "Fine."})
    assert ingress.command is None
    assert ingress.rejection_code == REJECTION_NO_INTERPRETABLE_INTENT
    d = ingress.diagnostics.as_metadata_dict()
    assert d["rejection_code"] == REJECTION_NO_INTERPRETABLE_INTENT
    assert d["resolved_action"] is None
    assert d["engine_rejection_reason"] is None
    assert d["actor_participant_id"] == human.id
    assert isinstance(d["candidate_summaries"], list)


@pytest.mark.asyncio
async def test_input_text_empty_rejection(tmp_path):
    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="a1", display_name="P1")
    human = next(p for p in run.participants.values() if p.account_id == "a1")
    ingress = manager.resolve_player_message(run.id, human.id, {"action": "input_text", "text": "   "})
    assert ingress.command is None
    assert ingress.rejection_code == REJECTION_MISSING_INPUT


@pytest.mark.asyncio
async def test_process_command_sets_same_metadata_shape_on_engine_reject(tmp_path):
    from unittest.mock import AsyncMock, MagicMock

    manager = RuntimeManager(store_root=tmp_path)
    run = manager.create_run("god_of_carnage_solo", account_id="a1", display_name="P1")
    human = next(p for p in run.participants.values() if p.account_id == "a1")

    ws = MagicMock()
    ws.send_json = AsyncMock()
    manager.connections.setdefault(run.id, {})[human.id] = ws

    await manager.process_command(run.id, human.id, {"action": "say", "text": ""})
    inst = manager.get_instance(run.id)
    meta = inst.metadata.get("last_input_interpretation")
    assert meta is not None
    assert "parser_version" in meta
    assert "candidate_summaries" in meta
    assert meta.get("engine_rejection_reason") is not None
