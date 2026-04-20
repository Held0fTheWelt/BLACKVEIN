from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

# Python 3.10 compatibility: UTC was added in Python 3.11
UTC = timezone.utc

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from wos_mvp.enums import AssertionMode, AuthorityLevel, DomainType, ReviewStatus
from wos_mvp.records import MemoryEntry, PartitionKey, TemporalValidityWindow

@pytest.fixture()
def partition_key() -> PartitionKey:
    return PartitionKey(world_id="wos", module_id="vera", session_id="s1")

@pytest.fixture()
def base_entry(partition_key: PartitionKey) -> MemoryEntry:
    now = datetime.now(UTC)
    return MemoryEntry(
        record_id="r1",
        partition_key=partition_key,
        domain_type=DomainType.CANONICAL_TRUTH,
        assertion_mode=AssertionMode.CANONICAL_ASSERTION,
        authority_level=AuthorityLevel.CONFIRMED,
        review_status=ReviewStatus.CONFIRMED,
        carrier_scope="session",
        entity_id="vera_chen",
        field_name="money_trail",
        slot_key="vera_chen::canonical::money_trail::scene_1::session",
        content="Money trail points to Vera Chen.",
        normalized_value="money trail points to vera chen",
        source_lineage=["commit:1"],
        temporal_validity=TemporalValidityWindow(1, 10),
        created_at=now,
        last_accessed=now,
        task_tags={"investigation", "money_trail"},
        metadata={"fresh": True},
    )
