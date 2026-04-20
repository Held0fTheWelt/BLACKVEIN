"""Tests for W2.0.4 RuntimeEventLog."""

import pytest
from app.runtime.event_log import RuntimeEventLog
from app.runtime.runtime_models import EventLogEntry


class TestRuntimeEventLogConstruction:
    """Tests for RuntimeEventLog initialization and state."""

    def test_init_with_session_id_only(self):
        """Constructor with session_id only, counter starts at 0."""
        log = RuntimeEventLog(session_id="session_123")
        assert log._session_id == "session_123"
        assert log._turn_number is None
        assert log._counter == 0
        assert len(log._entries) == 0

    def test_init_with_turn_number(self):
        """Constructor with turn_number stores it correctly."""
        log = RuntimeEventLog(session_id="session_123", turn_number=5)
        assert log._turn_number == 5

    def test_count_starts_at_zero(self):
        """count property returns 0 on new instance."""
        log = RuntimeEventLog(session_id="session_123")
        assert log.count == 0


class TestRuntimeEventLogLog:
    """Tests for the .log() method."""

    def test_log_creates_entry(self):
        """log() returns an EventLogEntry."""
        log = RuntimeEventLog(session_id="session_123")
        entry = log.log("test_event", "Test summary")
        assert isinstance(entry, EventLogEntry)

    def test_log_assigns_order_index_zero_first(self):
        """First log() call gets order_index=0."""
        log = RuntimeEventLog(session_id="session_123")
        entry = log.log("first", "First event")
        assert entry.order_index == 0

    def test_log_increments_order_index(self):
        """Successive log() calls increment order_index."""
        log = RuntimeEventLog(session_id="session_123")
        entry1 = log.log("first", "First")
        entry2 = log.log("second", "Second")
        entry3 = log.log("third", "Third")
        assert entry1.order_index == 0
        assert entry2.order_index == 1
        assert entry3.order_index == 2

    def test_log_injects_session_id(self):
        """Every entry receives the session_id from constructor."""
        log = RuntimeEventLog(session_id="session_abc")
        entry = log.log("test", "Test")
        assert entry.session_id == "session_abc"

    def test_log_injects_turn_number(self):
        """Every entry receives the turn_number from constructor."""
        log = RuntimeEventLog(session_id="session_123", turn_number=3)
        entry = log.log("test", "Test")
        assert entry.turn_number == 3

    def test_log_none_turn_number_on_session_log(self):
        """Session-level log (no turn_number) produces entries with turn_number=None."""
        log = RuntimeEventLog(session_id="session_123", turn_number=None)
        entry = log.log("test", "Test")
        assert entry.turn_number is None

    def test_log_empty_payload_default(self):
        """Omitting payload gives empty dict."""
        log = RuntimeEventLog(session_id="session_123")
        entry = log.log("test", "Test")
        assert entry.payload == {}

    def test_log_with_payload(self):
        """Payload dict is stored correctly."""
        log = RuntimeEventLog(session_id="session_123")
        payload = {"key": "value", "count": 42}
        entry = log.log("test", "Test", payload=payload)
        assert entry.payload == payload

    def test_log_increments_count(self):
        """count property reflects number of calls."""
        log = RuntimeEventLog(session_id="session_123")
        assert log.count == 0
        log.log("first", "First")
        assert log.count == 1
        log.log("second", "Second")
        assert log.count == 2

    def test_log_entry_has_occurred_at(self):
        """Every entry has occurred_at timestamp set."""
        log = RuntimeEventLog(session_id="session_123")
        entry = log.log("test", "Test")
        assert entry.occurred_at is not None


class TestRuntimeEventLogFlush:
    """Tests for the .flush() method."""

    def test_flush_returns_entries_in_order(self):
        """flush() returns entries in call order."""
        log = RuntimeEventLog(session_id="session_123")
        log.log("first", "First")
        log.log("second", "Second")
        log.log("third", "Third")
        entries = log.flush()
        assert len(entries) == 3
        assert entries[0].event_type == "first"
        assert entries[1].event_type == "second"
        assert entries[2].event_type == "third"

    def test_flush_resets_counter(self):
        """After flush, counter resets to 0."""
        log = RuntimeEventLog(session_id="session_123")
        log.log("first", "First")
        log.flush()
        entry = log.log("next", "Next after flush")
        assert entry.order_index == 0

    def test_flush_resets_entries(self):
        """After flush, entries list is empty."""
        log = RuntimeEventLog(session_id="session_123")
        log.log("first", "First")
        log.flush()
        assert log.count == 0

    def test_flush_on_empty_returns_empty_list(self):
        """flush() on empty log returns empty list."""
        log = RuntimeEventLog(session_id="session_123")
        entries = log.flush()
        assert entries == []

    def test_flush_twice_returns_empty_on_second(self):
        """Calling flush twice: first returns entries, second returns empty."""
        log = RuntimeEventLog(session_id="session_123")
        log.log("first", "First")
        entries1 = log.flush()
        entries2 = log.flush()
        assert len(entries1) == 1
        assert entries2 == []


class TestRuntimeEventLogIsolation:
    """Tests for independence between instances."""

    def test_two_instances_are_independent(self):
        """Two RuntimeEventLog instances do not share state."""
        log1 = RuntimeEventLog(session_id="session_1")
        log2 = RuntimeEventLog(session_id="session_2")

        log1.log("event_1", "In log 1")
        log1.log("event_2", "In log 1")

        log2.log("event_a", "In log 2")

        entries1 = log1.flush()
        entries2 = log2.flush()

        assert len(entries1) == 2
        assert len(entries2) == 1
        assert entries1[0].session_id == "session_1"
        assert entries2[0].session_id == "session_2"
