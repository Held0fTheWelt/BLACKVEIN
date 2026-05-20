"""Documentation readiness checks for Capability Matrix governance."""

from __future__ import annotations

from pathlib import Path
import re

from ai_stack.story_runtime.runtime_aspect_ledger import ASPECT_KEYS


REPO_ROOT = Path(__file__).resolve().parents[1]
MVP_DOCS = REPO_ROOT / "docs" / "MVPs"

MATRIX_DOC = MVP_DOCS / "capability_matrix_status_and_adr_relations.md"
VERIFICATION_LOG = MVP_DOCS / "capability_matrix_verification_log.md"
LIVE_GATES_DOC = MVP_DOCS / "capability_matrix_live_claim_gates.md"

MATRIX_DOCS = (MATRIX_DOC, VERIFICATION_LOG, LIVE_GATES_DOC)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _local_markdown_links(text: str) -> list[str]:
    links: list[str] = []
    for raw in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = raw.strip()
        if not target or target.startswith(("#", "http://", "https://", "mailto:")):
            continue
        links.append(target.split("#", 1)[0])
    return links


def test_capability_matrix_docs_are_split_by_purpose() -> None:
    for path in MATRIX_DOCS:
        assert path.exists(), f"Missing Capability Matrix doc: {path.relative_to(REPO_ROOT)}"

    matrix = _read(MATRIX_DOC)
    verification = _read(VERIFICATION_LOG)
    gates = _read(LIVE_GATES_DOC)

    assert "not a wishlist" in matrix
    assert "capability_matrix_verification_log.md" in matrix
    assert "capability_matrix_live_claim_gates.md" in matrix
    assert "## Local verification snapshot" not in matrix
    assert "## Local verification snapshot" in verification
    assert "Do not treat local PASS output as live-provider proof" in verification
    assert "`target_state` -> `partial`" in gates
    assert "`partial` -> `implemented`" in gates
    assert "`implemented` -> live claim gate" in gates


def test_capability_matrix_docs_keep_pi_labels_legacy_only() -> None:
    matrix = _read(MATRIX_DOC)
    gates = _read(LIVE_GATES_DOC)

    assert "Pi / Π labels are historical capability-map vocabulary" in gates
    assert "runtime branch keys" in gates
    assert "Langfuse score names" in gates
    assert "MCP payload keys" in gates
    assert "tests that explicitly verify no active Pi / Π control flow exists" in gates
    assert "Π labels are **index only**" in matrix


def test_runtime_aspect_ledger_terms_are_documented_in_matrix() -> None:
    matrix = _read(MATRIX_DOC)

    for aspect in ASPECT_KEYS:
        assert f"`{aspect}`" in matrix or aspect in matrix, f"RuntimeAspectLedger aspect missing from matrix: {aspect}"

    assert "Capability -> RuntimeAspectLedger field/aspect -> tests -> ADR -> Langfuse/MCP score" in matrix
    assert "Aspects required for commit/readiness gates" in matrix


def test_capability_matrix_doc_links_resolve() -> None:
    missing: list[str] = []
    for doc in MATRIX_DOCS:
        for target in _local_markdown_links(_read(doc)):
            candidate = (doc.parent / target).resolve()
            if not candidate.exists():
                missing.append(f"{doc.relative_to(REPO_ROOT)} -> {target}")

    assert not missing, "Broken Capability Matrix doc links:\n" + "\n".join(missing)
