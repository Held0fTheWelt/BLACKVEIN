# DS-006 Task 1: Writers Room Packaging Stage Analysis

**File:** `backend/app/services/writers_room_pipeline_packaging_stage.py` (354 LOC)

**Session:** April 12, 2026

**Objective:** Identify natural sub-stages for extraction to reduce cognitive load and improve testability.

---

## File Structure Overview

### Imports & Constants (1-18 LOC)
- Standard library imports: `dataclass`, `typing`, `uuid`
- Internal imports: artifact builder, context preview, manifest utilities
- Clean dependency footprint (3 external files)

### Data Structure (20-33 LOC)
- **WritersRoomPackagingStageResult** (14 LOC)
  - Frozen dataclass containing 11 fields
  - Represents the complete output envelope
  - Key fields: issues, recommendation_artifacts, review_bundle, proposal_package, patch_candidates, variant_candidates, review_summary, langchain_documents

### Main Function (35-353 LOC)
- **run_writers_room_packaging_stage()** (318 LOC)
  - Single monolithic function handling all packaging logic
  - 13 workflow stage markers via `_append_workflow_stage()` calls
  - 6+ artifact builders creating linked records
  - Multiple nested loops and conditional transformations

---

## Identified Sub-Stages (with Evidence-Based LOC)

### Sub-Stage 1: Issue Extraction (Lines 70-95) — ~26 LOC
**Responsibility:** Extract canon alignment issues from retrieval results

**Functions/Logic:**
- Issue artifact building loop (lines 71-95)
- 3-issue cap from source_rows
- Severity/confidence/evidence mapping
- Direct sources: source_rows, evidence_tag, module_id

**Dependencies:** `build_writers_room_artifact_record()`, source_rows
**Output:** issues list

**Candidate for Extraction:** YES
- Isolated loop with clear input/output contract
- Reusable pattern (builds from source_rows)
- Single concern: map retrieval rows to issue artifacts

---

### Sub-Stage 2: Recommendation Bundling (Lines 101-130) — ~30 LOC
**Responsibility:** Aggregate recommendations from structured output and generation content

**Functions/Logic:**
- Recommendation text aggregation (lines 101-111)
- 3 base recommendations + structured items + generation excerpt
- Artifact building loop (lines 116-130)
- Confidence/evidence refs applied per recommendation

**Dependencies:** `build_writers_room_artifact_record()`, structured output, generation content
**Output:** recommendation_artifacts list

**Candidate for Extraction:** YES
- Self-contained text aggregation logic
- Clear loop pattern with artifact building
- Separate concern from issues/review packaging

---

### Sub-Stage 3: Review Packaging (Lines 132-169) — ~38 LOC
**Responsibility:** Invoke review bundle tool and prepare langchain retrieval preview

**Functions/Logic:**
- Review bundle invocation (lines 132-141)
- Artifact metadata stamping (lines 142-157)
- Langchain document extraction (lines 160-169)
- Bundle ID resolution and preview path extraction

**Dependencies:** review_bundle_tool, `_langchain_preview_documents_from_context_pack()`, retrieval_inner
**Output:** review_bundle, langchain_documents, langchain_preview_paths

**Candidate for Extraction:** YES
- Clear tool invocation boundary
- Separate retrieval preview pipeline
- Governance envelope wrapping

---

### Sub-Stage 4: Proposal Finalization (Lines 171-338) — ~168 LOC
**Responsibility:** Assemble final proposal package with candidates and summary

**Functions/Logic:**
- Retrieval hit count normalization (lines 171-178) — ~8 LOC
- Proposal package assembly (lines 180-226) — ~47 LOC
  - Metadata stamping
  - Issue/recommendation/evidence aggregation
  - Governance readiness checklist
  - Retrieval digest metadata

- Comment bundle creation (lines 227-256) — ~30 LOC
  - Root artifact + loop through issues
  - Maps severity and evidence to comment items

- Patch candidate generation (lines 258-289) — ~32 LOC
  - 2-patch cap from source_rows
  - Confidence mapping from severity
  - Evidence tier propagation

- Variant candidate generation (lines 290-310) — ~21 LOC
  - 3-variant cap from recommendation_artifacts
  - Confidence splitting based on structured output presence

- Review summary assembly (lines 311-338) — ~28 LOC
  - Metadata stamping
  - Counters, evidence tier, bundle references
  - Review checkpoint checklist

**Dependencies:** proposal_id, evidence_paths, retrieval_trace, preflight_trace, structured, bundle_id
**Output:** proposal_package, comment_bundle, patch_candidates, variant_candidates, review_summary

**Candidate for Extraction:** PARTIAL
- Large sub-stage with 5 distinct concerns (>50 LOC each should be split)
- Recommend breaking into: patch/variant candidates (extractable) and proposal/summary assembly (keep together)

---

## Helper Extraction Candidates (Utilities)

### 1. Artifact Record Builder with Evidence Refs (High Priority)
**Pattern Location:** Lines 53-61, 73-80, 120-126, 149-156, 238-244, 261-268, 292-299, 311-318

**Frequency:** 8 calls across different artifact classes (analysis_artifact, proposal_artifact, candidate_authored_artifact)

**Commonality:** All follow pattern:
```python
build_writers_room_artifact_record(
    artifact_id=<computed_id>,
    artifact_class=<class>,
    source_module_id=module_id,
    evidence_refs=[filtered_paths],
    proposal_scope=<scope>,
    approval_state="pending_review",
)
```

**Extraction Benefit:** Reduce boilerplate, ensure consistent artifact stamping, enable standardized evidence path filtering

**Estimated LOC Reduction:** 15-20 LOC (shared evidence filtering, ID generation patterns)

---

### 2. Confidence Mapping Function (Medium Priority)
**Pattern Location:** Lines 257, 279-281, 306-307

**Pattern:**
```python
_severity_confidence = {"high": 0.9, "medium": 0.7, "low": 0.4}
# Used in multiple contexts with conditional lookups
```

**Extraction Benefit:** Centralize confidence calculation rules, make testable independently, enable A/B testing different confidence models

**Estimated LOC Reduction:** 3-5 LOC

---

### 3. Evidence Path Filtering and Capping (Medium Priority)
**Pattern Location:** Lines 113-114, 153, 184, 200-201, 231, 315

**Pattern:** Consistent `[p for p in evidence_paths if p][:N]` across 6+ locations

**Extraction Benefit:** Single source of truth for evidence path validation, cap enforcement, consistent slicing logic

**Estimated LOC Reduction:** 5-8 LOC

---

## Dependency Graph

```
run_writers_room_packaging_stage()
├─ Issue Extraction
│  └─ build_writers_room_artifact_record()
├─ Recommendation Bundling
│  └─ build_writers_room_artifact_record()
├─ Review Packaging
│  ├─ review_bundle_tool.invoke()
│  ├─ build_writers_room_artifact_record()
│  └─ _langchain_preview_documents_from_context_pack()
└─ Proposal Finalization
   ├─ Patch Candidate Generation
   │  └─ build_writers_room_artifact_record()
   ├─ Variant Candidate Generation
   │  └─ build_writers_room_artifact_record()
   ├─ Comment Bundle Assembly
   │  └─ build_writers_room_artifact_record()
   └─ Review Summary Assembly
      └─ build_writers_room_artifact_record()
```

**Coupling Points:**
- All sub-stages write to result fields (issues → proposal_package)
- Issue/recommendation artifacts referenced in proposal assembly
- Evidence paths shared across all sub-stages
- Metadata (module_id, evidence_tag) threaded through all stages

---

## LOC Breakdown Summary

| Component | LOC | Extractable | Notes |
|-----------|-----|------------|-------|
| Imports & Constants | 18 | No | Shared dependencies |
| WritersRoomPackagingStageResult | 14 | No | Core data structure |
| **Issue Extraction** | 26 | **YES** | Clean loop, isolated |
| **Recommendation Bundling** | 30 | **YES** | Text aggregation + artifact loop |
| **Review Packaging** | 38 | **YES** | Tool invocation + preview pipeline |
| **Patch Candidates** | 32 | **YES** | Isolatable sub-concern of Finalization |
| **Variant Candidates** | 21 | **YES** | Isolatable sub-concern of Finalization |
| **Comment Bundle** | 30 | **YES** | Iterates over issues, could extract |
| **Proposal Assembly** | 47 | PARTIAL | Mix of data aggregation + checklist |
| **Review Summary** | 28 | PARTIAL | Could extract with summary builder |
| **Helper Utilities** | ~50 | **YES** | Scattered boilerplate consolidation |
| **Total (consolidated functions)** | 354 | — | Current monolithic function |

---

## Task 2 Extraction Plan

### Phase 1: Extract Sub-Stage Functions
1. **extract_writers_room_issues()** — 26 LOC
   - Input: source_rows, module_id, evidence_tag
   - Output: issues list
   - Dependencies: build_writers_room_artifact_record()

2. **extract_writers_room_recommendations()** — 30 LOC
   - Input: structured, generation, proposal_id, module_id, evidence_refs
   - Output: recommendation_artifacts list
   - Dependencies: build_writers_room_artifact_record()

3. **prepare_writers_room_review_bundle()** — 38 LOC
   - Input: review_bundle_tool, module_id, recommendation_artifacts, source_rows, retrieval_inner
   - Output: (review_bundle, langchain_documents, langchain_preview_paths)
   - Dependencies: review_bundle_tool, _langchain_preview_documents_from_context_pack()

4. **generate_writers_room_patch_candidates()** — 32 LOC
   - Input: source_rows, module_id, issues, evidence_tag, bundle_id
   - Output: patch_candidates list
   - Dependencies: build_writers_room_artifact_record(), confidence_mapping()

5. **generate_writers_room_variant_candidates()** — 21 LOC
   - Input: recommendation_artifacts, module_id, structured, evidence_refs
   - Output: variant_candidates list
   - Dependencies: build_writers_room_artifact_record()

6. **assemble_writers_room_comment_bundle()** — 30 LOC
   - Input: issues, comment_bundle_id, module_id, evidence_paths
   - Output: comment_bundle dict
   - Dependencies: build_writers_room_artifact_record()

### Phase 2: Helper Utilities
1. **_build_artifact_with_evidence()** — Wrapper around build_writers_room_artifact_record() with evidence path filtering
2. **_map_severity_to_confidence()** — Centralized confidence mapping function
3. **_filter_and_cap_evidence_paths()** — Consistent evidence path validation

### Estimated LOC Reduction
- Current main function: 318 LOC
- After extraction: ~100-120 LOC (orchestration + variable setup)
- Extracted sub-functions: ~208 LOC (in separate module)
- Helper utilities: ~15 LOC (consolidation)
- **Net impact:** Improved readability via separation of concerns; no total line reduction (extraction preserves LOC but improves testability)

---

## Backwards Compatibility Notes

- WritersRoomPackagingStageResult dataclass will remain unchanged
- run_writers_room_packaging_stage() signature will remain unchanged
- Internal function extraction requires only internal refactoring
- No public API changes required
- All external dependencies (review_bundle_tool, build_writers_room_artifact_record) remain in same import locations

---

## Notes for Task 2 Implementation

1. **Issue Extraction:** Most straightforward to extract; minimal external state dependency
2. **Recommendation Bundling:** Straightforward; requires only proposal_id prefix logic
3. **Review Packaging:** Requires careful handling of tool invocation; consider retry logic
4. **Candidate Generation:** Can extract separately, but patch/variant candidates share severity→confidence logic
5. **Comment Bundle:** Depends on issues being available first; extract last in ordering
6. **Helpers:** Implement first to unblock other extractions; validate artifact record builder wrapper
