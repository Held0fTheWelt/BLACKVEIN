from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MVP = ROOT / "MVP"
BUNDLE = ROOT / "docs" / "MVPs" / "MVP_World_Of_Shadows_Canonical_Implementation_Bundle"


def classify(path: Path):
    rel = path.relative_to(ROOT).as_posix()
    s = rel
    ext = path.suffix.lower().lstrip(".") or "none"
    unique = "no"
    destination = "n/a"
    section = "n/a"
    merge_target = "n/a"
    omission = "n/a"

    if "/.pytest_cache/" in s or "/.egg-info/" in s or s.endswith("/CACHEDIR.TAG") or s.endswith("/.gitignore"):
        role = "cache or build metadata"
        status = "OMIT_WITH_JUSTIFICATION"
        omission = "Non-canonical cache/build artifact."
    elif "/'fy'-suites/.fydata/" in s or ("/'fy'-suites/" in s and "/generated/" in s):
        role = "generated governance artifact"
        status = "OMIT_WITH_JUSTIFICATION"
        omission = "Generated run artifact, retained in history only."
    elif s.startswith("MVP/docs/"):
        role = "documentation source material"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        destination = "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/"
        section = "canonical docs sections"
        merge_target = "canonical MVP bundle docs"
    elif "/tests/" in s or s.endswith("pytest.ini") or "conftest.py" in s:
        role = "test artifact"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        if s.startswith("MVP/backend/"):
            destination = "backend/tests/"
        elif s.startswith("MVP/world-engine/"):
            destination = "world-engine/tests/"
        elif s.startswith("MVP/frontend/"):
            destination = "frontend/tests/"
        elif s.startswith("MVP/administration-tool/"):
            destination = "administration-tool/tests/"
        else:
            destination = "tests/"
        section = "test integration"
        merge_target = "domain test suites"
    elif s.startswith("MVP/backend/"):
        role = "backend runtime/config"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        destination = "backend/"
        section = "backend integration"
        merge_target = "backend active implementation"
    elif s.startswith("MVP/world-engine/"):
        role = "world-engine runtime/config"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        destination = "world-engine/"
        section = "world-engine integration"
        merge_target = "world-engine active implementation"
    elif s.startswith("MVP/ai_stack/"):
        role = "ai_stack runtime/config"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        destination = "ai_stack/"
        section = "ai_stack integration"
        merge_target = "ai_stack active implementation"
    elif s.startswith("MVP/frontend/"):
        role = "frontend runtime/config"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        destination = "frontend/"
        section = "frontend integration"
        merge_target = "frontend active implementation"
    elif s.startswith("MVP/administration-tool/"):
        role = "administration-tool runtime/config"
        status = "MERGE_INTO_SECTION"
        unique = "yes"
        destination = "administration-tool/"
        section = "administration-tool integration"
        merge_target = "administration-tool active implementation"
    elif "/var/" in s or "/runtime_data/" in s or "/evidence/" in s:
        role = "runtime/generated data"
        status = "PRESERVE_AS_REFERENCE"
        destination = "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/open_tasks_and_follow_on_work.md"
        section = "evidence references"
        merge_target = "reference appendix"
    else:
        role = "auxiliary source"
        status = "PRESERVE_AS_REFERENCE"
        destination = "docs/MVPs/MVP_World_Of_Shadows_Canonical_Implementation_Bundle/open_tasks_and_follow_on_work.md"
        section = "reference appendix"
        merge_target = "follow-on references"

    return rel, ext, role, status, unique, destination, section, merge_target, omission


def write_md(path: Path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    files = sorted([p for p in MVP.rglob("*") if p.is_file()])
    inventory = [
        "# mvp_source_inventory",
        "",
        f"Total source files: {len(files)}",
        "",
        "| source path | file type | topic / intent | unique substance | overlap notes | recommended disposition |",
        "|---|---|---|---|---|---|",
    ]
    mapping = [
        "# source_to_destination_mapping_table",
        "",
        f"Total source files: {len(files)}",
        "",
        "| source path | file type | topic / content role | classification | unique substance present | destination file | destination section | merge target or reference target if not direct migration | omission justification if omitted | verification status |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for p in files:
        rel, ext, role, status, unique, destination, section, merge_target, omission = classify(p)
        overlap = "Reviewed against active paths during reconciliation phase."
        inventory.append(
            f"| `{rel}` | `{ext}` | {role} | {unique} | {overlap} | `{status}` |"
        )
        mapping.append(
            f"| `{rel}` | `{ext}` | {role} | `{status}` | {unique} | `{destination}` | {section} | {merge_target} | {omission} | `pending` |"
        )

    write_md(BUNDLE / "mvp_source_inventory.md", inventory)
    write_md(BUNDLE / "source_to_destination_mapping_table.md", mapping)

    reconciliation = [
        "# reconciliation_report",
        "",
        "Status: intake baseline created. Detailed file-level reconciliation decisions will be appended during integrate-runtime-assets.",
        "",
        "| reconciliation ID | source file | active destination file | existing state | missing elements | conflicts | chosen merge strategy | must remain unchanged | status |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    write_md(BUNDLE / "reconciliation_report.md", reconciliation)

    conflicts = [
        "# integration_conflict_register",
        "",
        "| conflict ID | affected source files | affected active destination files | conflict type | chosen resolution | justification | validation status |",
        "|---|---|---|---|---|---|---|",
    ]
    write_md(BUNDLE / "integration_conflict_register.md", conflicts)

    matrix = [
        "# domain_validation_matrix",
        "",
        "| destination domain | migrated source inputs | affected destination paths | required validation commands | expected evidence type | resulting status |",
        "|---|---|---|---|---|---|",
        "| backend | pending | `backend/` | pending | unit/integration/smoke | pending |",
        "| world-engine | pending | `world-engine/` | pending | unit/integration/smoke | pending |",
        "| ai_stack | pending | `ai_stack/` | pending | unit/integration/smoke | pending |",
        "| frontend | pending | `frontend/` | pending | unit/integration/smoke | pending |",
        "| administration-tool | pending | `administration-tool/` | pending | unit/integration/smoke | pending |",
        "| canonical docs | pending | `docs/`, `docs/MVPs/` | pending | doc consistency/navigation | pending |",
    ]
    write_md(BUNDLE / "domain_validation_matrix.md", matrix)

    print(f"baseline files written for {len(files)} MVP source files")


if __name__ == "__main__":
    main()
