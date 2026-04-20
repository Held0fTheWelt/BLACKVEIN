"""Runtime Open World Bootstrap Tests.

WAVE 8: Comprehensive runtime behavior and persistence testing.
Tests open-world initialization: bootstrap behavior and expected defaults.

Mark: @pytest.mark.contract, @pytest.mark.unit
"""

from __future__ import annotations

import pytest

from app.runtime.manager import RuntimeManager
from app.runtime.models import RunStatus


@pytest.mark.contract
@pytest.mark.unit
def test_open_world_bootstrap_creates_persistent_instance(tmp_path):
    """Verify open world bootstrap creates persistent instance on init."""
    manager = RuntimeManager(store_root=tmp_path)

    # Find an open world template
    open_world_template = next(
        (t for t in manager.templates.values() if str(t.kind) == "open_world"),
        None
    )

    if open_world_template:
        # Verify public instance was created
        public_runs = [
            r for r in manager.instances.values()
            if r.template_id == open_world_template.id
        ]
        assert len(public_runs) > 0
        public_run = public_runs[0]
        assert public_run.persistent is True
        assert public_run.id.startswith("public-")


@pytest.mark.contract
@pytest.mark.unit
def test_open_world_starts_in_running_state(tmp_path):
    """Verify open world instances start in RUNNING state."""
    manager = RuntimeManager(store_root=tmp_path)

    open_world_template = next(
        (t for t in manager.templates.values() if str(t.kind) == "open_world"),
        None
    )

    if open_world_template:
        public_runs = [
            r for r in manager.instances.values()
            if r.template_id == open_world_template.id
        ]
        for run in public_runs:
            assert run.status == RunStatus.RUNNING


@pytest.mark.contract
@pytest.mark.unit
def test_open_world_has_initial_beat(tmp_path):
    """Verify open world has initial beat set."""
    manager = RuntimeManager(store_root=tmp_path)

    open_world_template = next(
        (t for t in manager.templates.values() if str(t.kind) == "open_world"),
        None
    )

    if open_world_template:
        public_runs = [
            r for r in manager.instances.values()
            if r.template_id == open_world_template.id
        ]
        for run in public_runs:
            assert run.beat_id is not None
            assert run.beat_id == open_world_template.initial_beat_id


@pytest.mark.contract
@pytest.mark.unit
def test_open_world_has_all_props_initialized(tmp_path):
    """Verify all props are initialized in open world."""
    manager = RuntimeManager(store_root=tmp_path)

    open_world_template = next(
        (t for t in manager.templates.values() if str(t.kind) == "open_world"),
        None
    )

    if open_world_template:
        public_runs = [
            r for r in manager.instances.values()
            if r.template_id == open_world_template.id
        ]
        for run in public_runs:
            assert len(run.props) == len(open_world_template.props)
            for prop in open_world_template.props:
                assert prop.id in run.props


@pytest.mark.contract
@pytest.mark.unit
def test_open_world_has_npc_participants(tmp_path):
    """Verify NPCs are present in open world."""
    manager = RuntimeManager(store_root=tmp_path)

    open_world_template = next(
        (t for t in manager.templates.values() if str(t.kind) == "open_world"),
        None
    )

    if open_world_template:
        npc_roles = [r for r in open_world_template.roles if str(r.mode) == "npc"]
        if npc_roles:
            public_runs = [
                r for r in manager.instances.values()
                if r.template_id == open_world_template.id
            ]
            for run in public_runs:
                npc_count = sum(
                    1 for p in run.participants.values()
                    if str(p.mode) == "npc"
                )
                assert npc_count >= len(npc_roles)
