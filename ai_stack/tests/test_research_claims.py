# ai_stack/tests/test_research_claims.py
from __future__ import annotations

import pytest

from ai_stack.research.research_claims import (
    RECOGNIZED_CLAIM_TYPES,
    is_recognized_claim_type,
    is_schema_valid_claim_payload,
)


def test_is_recognized_claim_type_valid() -> None:
    for claim_type in RECOGNIZED_CLAIM_TYPES:
        assert is_recognized_claim_type(claim_type) is True


def test_is_recognized_claim_type_invalid() -> None:
    assert is_recognized_claim_type("unknown_type") is False
    assert is_recognized_claim_type(123) is False
    assert is_recognized_claim_type(None) is False
    assert is_recognized_claim_type([]) is False


def test_is_schema_valid_claim_payload_valid() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "This is a valid claim",
        "evidence_anchor_ids": ["anchor_1", "anchor_2"],
        "perspective": "narrator",
    }
    assert is_schema_valid_claim_payload(payload) is True


def test_is_schema_valid_claim_payload_missing_claim_type() -> None:
    payload = {
        "statement": "text",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_missing_statement() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_missing_evidence_anchor_ids() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_missing_perspective() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": ["a"],
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_invalid_claim_type() -> None:
    payload = {
        "claim_type": "invalid_type",
        "statement": "text",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_empty_statement() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_whitespace_only_statement() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "   \t\n  ",
        "evidence_anchor_ids": ["a"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_empty_anchor_list() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": [],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_non_list_anchors() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": "not_a_list",
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_anchor_with_empty_string() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": ["", "anchor_2"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_anchor_with_whitespace() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": ["   ", "anchor_2"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_non_string_anchor() -> None:
    payload = {
        "claim_type": "dramatic_function",
        "statement": "text",
        "evidence_anchor_ids": [123, "anchor_2"],
        "perspective": "p",
    }
    assert is_schema_valid_claim_payload(payload) is False


def test_is_schema_valid_claim_payload_all_claim_types() -> None:
    for claim_type in RECOGNIZED_CLAIM_TYPES:
        payload = {
            "claim_type": claim_type,
            "statement": "This is a valid statement",
            "evidence_anchor_ids": ["anchor_1"],
            "perspective": "reviewer",
        }
        assert is_schema_valid_claim_payload(payload) is True
