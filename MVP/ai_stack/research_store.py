"""Persistent deterministic store for Research-and-Canon-Improvement MVP."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from ai_stack.research_contract import utc_now_iso


RESEARCH_STORE_SCHEMA_VERSION = "research_store_v1"

_ENTITY_BUCKETS: tuple[str, ...] = (
    "sources",
    "anchors",
    "aspects",
    "exploration_nodes",
    "exploration_edges",
    "claims",
    "issues",
    "proposals",
    "runs",
)


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": RESEARCH_STORE_SCHEMA_VERSION,
        "updated_at": utc_now_iso(),
        "counters": {},
        "sources": {},
        "anchors": {},
        "aspects": {},
        "exploration_nodes": {},
        "exploration_edges": {},
        "claims": {},
        "issues": {},
        "proposals": {},
        "runs": {},
    }


def _to_plain_dict(record: Any) -> dict[str, Any]:
    if hasattr(record, "to_dict") and callable(record.to_dict):
        value = record.to_dict()
        if isinstance(value, dict):
            return value
    if is_dataclass(record):
        value = asdict(record)
        if isinstance(value, dict):
            return value
    if isinstance(record, dict):
        return dict(record)
    raise ValueError("record_must_be_dict_or_dataclass")


def _ensure_required_fields(record: dict[str, Any], required_fields: tuple[str, ...]) -> None:
    for field in required_fields:
        value = record.get(field)
        if value is None:
            raise ValueError(f"missing_required_field:{field}")
        if isinstance(value, str) and not value.strip():
            raise ValueError(f"empty_required_field:{field}")
        if isinstance(value, list) and field.endswith("_ids") and len(value) == 0:
            raise ValueError(f"empty_required_list:{field}")
        if isinstance(value, dict) and field in {"provenance", "metadata", "budget", "outputs", "preview_patch_ref"} and len(value) == 0:
            raise ValueError(f"empty_required_object:{field}")


class ResearchStore:
    """Persistent structured store used by all research MVP phases."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self._state: dict[str, Any] = _empty_state()
        self._load()

    @classmethod
    def from_repo_root(cls, repo_root: Path) -> "ResearchStore":
        return cls(repo_root / ".wos" / "research" / "research_store.json")

    def _load(self) -> None:
        if not self.storage_path.exists():
            self._state = _empty_state()
            return
        try:
            loaded = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            raise ValueError("invalid_research_store_json")
        if not isinstance(loaded, dict):
            raise ValueError("invalid_research_store_shape")
        if loaded.get("schema_version") != RESEARCH_STORE_SCHEMA_VERSION:
            raise ValueError("unsupported_research_store_schema_version")
        state = _empty_state()
        state["updated_at"] = str(loaded.get("updated_at") or utc_now_iso())
        counters = loaded.get("counters", {})
        state["counters"] = counters if isinstance(counters, dict) else {}
        for bucket in _ENTITY_BUCKETS:
            value = loaded.get(bucket, {})
            state[bucket] = value if isinstance(value, dict) else {}
        self._state = state

    def _save(self) -> None:
        self._state["updated_at"] = utc_now_iso()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._state, ensure_ascii=True, indent=2, sort_keys=True)
        temp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=self.storage_path.parent,
                prefix=".research_store_",
                suffix=".json",
            ) as temp_file:
                temp_file.write(payload)
                temp_name = temp_file.name
            if temp_name:
                os.replace(temp_name, self.storage_path)
        except Exception:
            if temp_name:
                try:
                    Path(temp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    def next_id(self, prefix: str) -> str:
        counters = self._state["counters"]
        current = int(counters.get(prefix, 0)) + 1
        counters[prefix] = current
        self._save()
        return f"{prefix}_{current:06d}"

    def _upsert(self, bucket: str, record: Any, *, id_field: str, required_fields: tuple[str, ...]) -> dict[str, Any]:
        plain = _to_plain_dict(record)
        _ensure_required_fields(plain, required_fields)
        self._validate_record_references(bucket=bucket, record=plain)
        record_id = plain.get(id_field)
        if not isinstance(record_id, str) or not record_id.strip():
            raise ValueError(f"missing_record_id:{id_field}")
        self._state[bucket][record_id] = plain
        self._save()
        return plain

    def _validate_record_references(self, *, bucket: str, record: dict[str, Any]) -> None:
        if bucket == "anchors":
            source_id = record.get("source_id")
            if source_id not in self._state["sources"]:
                raise ValueError(f"unknown_source_reference:{source_id}")
        if bucket == "aspects":
            source_id = record.get("source_id")
            if source_id not in self._state["sources"]:
                raise ValueError(f"unknown_source_reference:{source_id}")
            for anchor_id in record.get("evidence_anchor_ids", []):
                if anchor_id not in self._state["anchors"]:
                    raise ValueError(f"unknown_anchor_reference:{anchor_id}")
        if bucket == "exploration_nodes":
            seed_aspect = record.get("seed_aspect_id")
            if seed_aspect not in self._state["aspects"]:
                raise ValueError(f"unknown_aspect_reference:{seed_aspect}")
            parent = record.get("parent_node_id")
            if parent is not None and parent not in self._state["exploration_nodes"]:
                raise ValueError(f"unknown_parent_node_reference:{parent}")
            for anchor_id in record.get("evidence_anchor_ids", []):
                if anchor_id not in self._state["anchors"]:
                    raise ValueError(f"unknown_anchor_reference:{anchor_id}")
        if bucket == "exploration_edges":
            if record.get("from_node_id") not in self._state["exploration_nodes"]:
                raise ValueError(f"unknown_from_node_reference:{record.get('from_node_id')}")
            if record.get("to_node_id") not in self._state["exploration_nodes"]:
                raise ValueError(f"unknown_to_node_reference:{record.get('to_node_id')}")
        if bucket == "claims":
            for anchor_id in record.get("evidence_anchor_ids", []):
                if anchor_id not in self._state["anchors"]:
                    raise ValueError(f"unknown_anchor_reference:{anchor_id}")
        if bucket == "issues":
            for claim_id in record.get("supporting_claim_ids", []):
                if claim_id not in self._state["claims"]:
                    raise ValueError(f"unknown_claim_reference:{claim_id}")
        if bucket == "proposals":
            for claim_id in record.get("supporting_claim_ids", []):
                if claim_id not in self._state["claims"]:
                    raise ValueError(f"unknown_claim_reference:{claim_id}")

    def _list(self, bucket: str) -> list[dict[str, Any]]:
        return [self._state[bucket][key] for key in sorted(self._state[bucket].keys())]

    def upsert_source(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "sources",
            record,
            id_field="source_id",
            required_fields=(
                "source_id",
                "work_id",
                "source_type",
                "title",
                "provenance",
                "visibility",
                "copyright_posture",
                "segment_index_status",
                "metadata",
            ),
        )

    def upsert_anchor(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "anchors",
            record,
            id_field="anchor_id",
            required_fields=(
                "anchor_id",
                "source_id",
                "segment_ref",
                "span_ref",
                "paraphrase_or_excerpt",
                "confidence",
                "notes",
            ),
        )

    def upsert_aspect(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "aspects",
            record,
            id_field="aspect_id",
            required_fields=(
                "aspect_id",
                "source_id",
                "perspective",
                "aspect_type",
                "statement",
                "evidence_anchor_ids",
                "tags",
                "status",
            ),
        )

    def upsert_exploration_node(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "exploration_nodes",
            record,
            id_field="node_id",
            required_fields=(
                "node_id",
                "seed_aspect_id",
                "perspective",
                "hypothesis",
                "rationale",
                "speculative_level",
                "evidence_anchor_ids",
                "novelty_score",
                "status",
                "outcome",
            ),
        )

    def upsert_exploration_edge(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "exploration_edges",
            record,
            id_field="edge_id",
            required_fields=("edge_id", "from_node_id", "to_node_id", "relation_type"),
        )

    def upsert_claim(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "claims",
            record,
            id_field="claim_id",
            required_fields=(
                "claim_id",
                "work_id",
                "perspective",
                "claim_type",
                "statement",
                "evidence_anchor_ids",
                "support_level",
                "contradiction_status",
                "status",
                "notes",
            ),
        )

    def upsert_issue(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "issues",
            record,
            id_field="issue_id",
            required_fields=(
                "issue_id",
                "module_id",
                "issue_type",
                "severity",
                "description",
                "supporting_claim_ids",
                "status",
            ),
        )

    def upsert_proposal(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "proposals",
            record,
            id_field="proposal_id",
            required_fields=(
                "proposal_id",
                "module_id",
                "proposal_type",
                "rationale",
                "expected_effect",
                "supporting_claim_ids",
                "preview_patch_ref",
                "status",
            ),
        )

    def upsert_run(self, record: Any) -> dict[str, Any]:
        return self._upsert(
            "runs",
            record,
            id_field="run_id",
            required_fields=(
                "run_id",
                "mode",
                "source_ids",
                "seed_question",
                "budget",
                "outputs",
                "audit_refs",
                "created_at",
            ),
        )

    def list_sources(self) -> list[dict[str, Any]]:
        return self._list("sources")

    def list_anchors(self) -> list[dict[str, Any]]:
        return self._list("anchors")

    def list_aspects(self) -> list[dict[str, Any]]:
        return self._list("aspects")

    def list_exploration_nodes(self) -> list[dict[str, Any]]:
        return self._list("exploration_nodes")

    def list_exploration_edges(self) -> list[dict[str, Any]]:
        return self._list("exploration_edges")

    def list_claims(self) -> list[dict[str, Any]]:
        return self._list("claims")

    def list_issues(self) -> list[dict[str, Any]]:
        return self._list("issues")

    def list_proposals(self) -> list[dict[str, Any]]:
        return self._list("proposals")

    def list_runs(self) -> list[dict[str, Any]]:
        return self._list("runs")

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        run = self._state["runs"].get(run_id)
        return dict(run) if isinstance(run, dict) else None

    def get_source(self, source_id: str) -> dict[str, Any] | None:
        source = self._state["sources"].get(source_id)
        return dict(source) if isinstance(source, dict) else None

    def get_claim(self, claim_id: str) -> dict[str, Any] | None:
        claim = self._state["claims"].get(claim_id)
        return dict(claim) if isinstance(claim, dict) else None
