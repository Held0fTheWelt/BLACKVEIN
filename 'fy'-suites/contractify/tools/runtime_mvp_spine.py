from __future__ import annotations

from pathlib import Path

from contractify.tools.models import ConflictFinding, ContractRecord, ProjectionRecord, RelationEdge
from contractify.tools.runtime_mvp_spine_path_helpers import (
    PRECEDENCE_RULES,
    _adr0001,
    _adr0002,
    _adr0003,
    _existing,
    _make_review_conflict,
    _one_of,
    _path_target_id,
)
from contractify.tools.runtime_mvp_spine_record_builders import _contract, _projection


def build_runtime_mvp_spine(
    repo: Path,
) -> tuple[list[ContractRecord], list[ProjectionRecord], list[RelationEdge], list[ConflictFinding], dict[str, list[str]]]:
    """Build the curated runtime/MVP spine for the current repository."""
    from contractify.tools.runtime_mvp_spine_contracts_a import extend_authority_and_slice_contracts_a
    from contractify.tools.runtime_mvp_spine_contracts_b import extend_slice_contracts_b
    from contractify.tools.runtime_mvp_spine_contracts_c import extend_evidence_contracts_c
    from contractify.tools.runtime_mvp_spine_contracts_d import extend_evidence_contracts_d
    from contractify.tools.runtime_mvp_spine_projections import build_projection_records
    from contractify.tools.runtime_mvp_spine_relations import build_relation_edges
    from contractify.tools.runtime_mvp_spine_review import build_unresolved_and_families
    from contractify.tools.runtime_mvp_spine_support import SpineHelpers

    repo = repo.resolve()
    contracts: list[ContractRecord] = []
    path_to_id: dict[str, str] = {}

    def add(rec: ContractRecord) -> None:
        if not (repo / rec.anchor_location).is_file():
            return
        contracts.append(rec)
        path_to_id[rec.anchor_location] = rec.id

    helpers = SpineHelpers(
        contract=_contract,
        projection=_projection,
        existing=_existing,
        one_of=_one_of,
        adr0001=_adr0001,
        adr0002=_adr0002,
        adr0003=_adr0003,
        path_target_id=_path_target_id,
        make_review_conflict=_make_review_conflict,
    )
    extend_authority_and_slice_contracts_a(repo, add, helpers)
    extend_slice_contracts_b(repo, add, helpers)
    extend_evidence_contracts_c(repo, add, helpers)
    extend_evidence_contracts_d(repo, add, helpers)
    projections = build_projection_records(repo, path_to_id, helpers)
    relations = build_relation_edges()
    unresolved, families = build_unresolved_and_families(repo, helpers)
    return contracts, projections, relations, unresolved, families
