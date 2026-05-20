# Delagecy Wave Log Integrity Audit

Date: 2026-05-20  
Scope: audit of the executed Delagecy wave reports in `'fy'-suites/delagecy/reports`  
Primary evidence: Delagecy scan/report artifacts, not git history

## Result

The wave logs were rechecked before continuing removal work.

The last active-surface report is mechanically clean:

- `active_surface_report_after_wave_next_4.md`
- scanned files: 5454
- active legacy hits: 358
- registered findings: 1103
- unregistered findings: 0
- registry status: `approved_for_removal` 1034, `removed` 69
- `delagecy check --scan-json active_surface_scan_after_wave_next_4.json` returns `ok: true`

This is not enough to continue removal safely.

Reason: the Delagecy gate proves only that removed fingerprints no longer appear
in the scan. It does not prove that the underlying behavior was actually
removed. Several entries marked `removed` are better classified as
canonicalization of still-active behavior, or as test/comment wording cleanup.
By the active rule, "legacy is not active compatibility"; active behavior may be
renamed or clarified, but that is not true legacy removal by itself.

No further removal should continue until the entries below are discussed and
reclassified or explicitly approved as real removals.

## Wave Timeline

| Step | Scan artifact | Scanned files | Hits |
| --- | --- | ---: | ---: |
| Baseline | `active_surface_scan.json` | 5349 | 989 |
| Partial removal 1 | `active_surface_scan_after_partial_removal.json` | 5348 | 800 |
| Partial removal 2 | `active_surface_scan_after_partial_removal_2.json` | 5334 | 708 |
| Partial removal 3 | `active_surface_scan_after_partial_removal_3.json` | 5334 | 672 |
| Reclassification audit | `active_surface_scan_after_reclassification_audit.json` | 5396 | 682 |
| Continued removal 1 | `active_surface_scan_after_continued_removal.json` | 5398 | 480 |
| Continued removal 2 | `active_surface_scan_after_continued_removal_2.json` | 5398 | 478 |
| Wave next 1 | `active_surface_scan_after_wave_next.json` | 5414 | 427 |
| Wave next 2 | `active_surface_scan_after_wave_next_2.json` | 5454 | 427 |
| Wave next 3 | `active_surface_scan_after_wave_next_3.json` | 5454 | 419 |
| Wave next 4 | `active_surface_scan_after_wave_next_4.json` | 5454 | 358 |

## Wave Deltas From Reports

| Transition | Removed scan hits | Added scan hits | Main observation |
| --- | ---: | ---: | --- |
| Baseline -> Partial 1 | 263 | 74 | Large mixed wave: UI/admin text, backend routes, runtime readiness, old story-runtime naming, and new registered findings. Needs semantic separation by cluster. |
| Partial 1 -> Partial 2 | 92 | 0 | Mostly world-engine story-session snapshots plus W5 player/session names. The execution plan had already flagged `world-engine/app/var/story_sessions` as a decision-required scope. |
| Partial 2 -> Partial 3 | 36 | 0 | Langfuse evaluator `legacy_trace_names` wording disappeared. Reclassification audit later says evaluator behavior was active and preserved under `alternate_trace_names`. This is canonicalization, not true removal. |
| Partial 3 -> Reclassification audit | 4 | 14 | Corrections and new registrations appeared during the reclassification pass. This is expected but shows the backlog was still moving. |
| Reclassification audit -> Continued 1 | 206 | 4 | Broad wave touching governance console, LangGraph executor, dramatic-effect gate, inspector projection, writers-room services, and tests. Contains both true residue cleanup and active behavior canonicalization. |
| Continued 1 -> Continued 2 | 24 | 22 | Mostly file moves into subpackages. This should not be counted as legacy removal without matching semantic evidence. |
| Continued 2 -> Wave next 1 | 62 | 11 | Routing/model inventory/operator wording and LangChain bridge wording changed; several changes moved service paths. Contains high-risk active-routing terminology. |
| Wave next 1 -> Wave next 2 | 8 | 8 | Service wording removed, generated recommendation JSON wording added. This is mostly scope/generation noise. |
| Wave next 2 -> Wave next 3 | 8 | 0 | Generated recommendation text cleanup. Likely low-risk config text residue. |
| Wave next 3 -> Wave next 4 | 61 | 0 | The most suspicious wave: `removed` registry entries include active adapter output branches, routing authority wording, NPC-agency aliases, MCP permission metadata, and tests. |

## Registry Status Problem

The registry currently has:

| Status | Count |
| --- | ---: |
| `approved_for_removal` | 1034 |
| `removed` | 69 |

The 69 `removed` entries are not all semantically equal. Some are likely real
text cleanup, but several preserve current behavior under a new or neutral name.
Those should not be counted as legacy removal until the retained behavior has a
documented current contract and, where relevant, the old public/input/output
surface is actually gone.

## Removed Entries Requiring Reclassification Or Discussion

### Adapter role/unstructured output

Registry entries:

- `DLG-034` to `DLG-037`
- related tests: `DLG-230` to `DLG-235`

Files:

- `backend/app/runtime/ai_adapter.py`
- `backend/tests/runtime/test_ai_adapter.py`

Current evidence:

- `request_role_structured_output` still defaults to `False`.
- `MockStoryAIAdapter` still returns the unstructured decision shape when that flag is false.
- tests still assert the false-flag behavior, now using neutral wording.

Audit classification:

- Active behavior preserved.
- Wording cleanup may be valid, but it is not a true removal of the old output branch.
- Do not count as removed unless the unstructured branch is actually retired or explicitly documented as the current canonical behavior.

### AI decision logging role fields

Registry entries:

- `DLG-038`
- related tests: `DLG-236` to `DLG-243`

Files:

- `backend/app/runtime/ai_decision_logging.py`
- `backend/tests/runtime/test_ai_decision_logging.py`

Current evidence:

- tests still cover `role_aware_decision=None`.
- role-specific fields are still expected to remain `None` in that path.

Audit classification:

- This appears to be active fallback behavior with renamed wording.
- Needs confirmation before any `removed` status is trusted.

### routing governance routing authority / old graph routing

Registry entries:

- `DLG-041`
- `DLG-048` to `DLG-051`

Files:

- `backend/app/runtime/operator_truth.py`
- `backend/app/runtime/routing_authority.py`

Current evidence:

- `story_runtime_core.RoutingPolicy.choose()` remains present as the ai_stack LangGraph routing API.
- The wording now says it is non-authoritative for Task 2A HTTP paths, but the graph routing behavior still exists.

Audit classification:

- Not true routing removal.
- The rename from legacy/compatibility terminology to adapter/non-authoritative terminology may be accurate, but it risks hiding old routing if the distinction is not explicit.
- Must be discussed before further routing removal.

### LangChain bridge aliases

Registry entry:

- `DLG-463`

File:

- `ai_stack/langchain/bridges.py`

Current evidence:

- `narrative_response` remains an active alias/copy of `narration_summary`.
- the reclassification audit already lists LangChain bridge aliases as "Still Blocked / Do Not Auto-Remove".

Audit classification:

- Active alias preserved.
- Should not be marked as true removal.

### MCP permission metadata

Registry entries:

- `DLG-527` to `DLG-529`
- related tests: `DLG-598` to `DLG-602`

File:

- `ai_stack/mcp/mcp_canonical_surface.py`

Current evidence:

- `permission_legacy` was renamed to `permission_scope`.
- `_derive_permission_legacy` was renamed to `_derive_permission_scope`.
- permission derivation still exists and appears to be active tool metadata.

Audit classification:

- Potentially valid canonicalization, but not automatically true removal.
- Need to verify whether any public client consumed `permission_legacy`.
- If old public metadata was removed, that specific surface may be removal; the internal permission behavior is retained.

### NPC-agency initiative alias

Registry entries:

- `DLG-1015` to `DLG-1019`
- related tests: `DLG-604` to `DLG-614`

File:

- `ai_stack/contracts/npc_agency_contracts.py`

Current evidence:

- canonical `npc_initiatives` is used first.
- `raw_plan.get("initiatives")` is still read as an alternate input shape.
- tests still cover old `initiatives` input, now under neutral names.

Audit classification:

- Active input alias preserved.
- This is not true removal unless the `initiatives` input is retired or explicitly declared current canonical compatibility.

### NPC-agency social pressure shift

Registry entries:

- `DLG-560` to `DLG-564`

File:

- `ai_stack/story_runtime/npc_agency/npc_agency_planner.py`

Current evidence:

- `social_pressure_shift` is preferred.
- `pressure_shift` remains an accepted alternate input.
- reason code was canonicalized to `social_pressure_shift`.

Audit classification:

- Active alternate input preserved.
- Wording cleanup/canonicalization, not removal.

### Preview delta full-copy comparison tests

Registry entries:

- `DLG-250` to `DLG-256`

File:

- `backend/tests/runtime/test_preview_delta.py`

Current evidence:

- the test still compares the bounded clone path against the old full-deepcopy semantics.
- variable/test wording was neutralized.

Audit classification:

- Test reference cleanup only.
- Not implementation removal.
- Safe as wording cleanup, but should not be counted as behavior removal.

### Generated recommendation summaries

Registry entries:

- `DLG-1096` to `DLG-1103`

Files:

- `backend/app/var/improvement/recommendations/*.json`

Current evidence:

- generated recommendation text changed from compatibility/legacy wording to non-authoritative routing wording.

Audit classification:

- Low-risk text/config cleanup if these files are generated or recommendation snapshots.
- Still should not be used as evidence that routing behavior was removed.

## Already Blocked By Earlier Audit

`removal_reclassification_audit.md` already says the following must not be
auto-removed:

- dramatic-effect gate fields such as `legacy_fallback_used`
- LangChain bridge aliases such as `narrative_response` and responder aliases
- world-engine manager `_legacy_loader`, `_legacy_sources`, and related monolith-split remnants
- model-routing registry/report terminology such as legacy adapter maps
- persisted/generated historical scan reports and registry rows

The later `removed` statuses must be interpreted against this block list. In
particular, the LangChain bridge and routing authority changes should not be
treated as completed removal without separate approval.

## Findings That Look Safer

These clusters look more likely to be safe cleanup, based on the reports:

- user-visible UI labels and hidden UI residue removed in the early waves, if active navigation still renders correctly
- obsolete backend web redirects and old browser-route references corrected during the reclassification audit
- generated recommendation text cleanup in `backend/app/var/improvement/recommendations`
- pure test/comment wording cleanup, provided it is not counted as implementation removal

These still need targeted verification before final closure, especially for UI
surfaces.

## Tooling Gap

Delagecy currently has `reported`, `blocked`, `retained`,
`approved_for_removal`, `removal_in_progress`, and `removed` style handling, but
the executed logs show a missing practical distinction:

- true removal: obsolete behavior and every exposed surface are gone
- canonicalization: active behavior remains, but old wording/name was replaced
- retained active alias: old-looking input/output remains because current clients still need it

The current `check` command can pass even when a `removed` finding was only
renamed, because the original fingerprint disappears. This is why the last
report can be green while the semantic audit is not.

## Required Next Actions Before Any Further Removal

1. Freeze additional removal waves until the 69 `removed` entries are reviewed.
2. Reclassify entries that are canonicalization or active aliases instead of true removals.
3. Add an explicit Delagecy state or tracker note for `canonicalized_active_behavior` or equivalent, so future scans do not treat renaming as deletion.
4. For each active alias or fallback, decide with the user whether it is:
   - current canonical behavior with a bad name,
   - active transitional compatibility that needs a migration plan,
   - true obsolete legacy that can be removed in a coordinated wave.
5. Only after that, continue with the next removal wave.

## Stop List For Immediate Discussion

Do not continue removal in these areas without explicit direction:

- `backend/app/runtime/ai_adapter.py`: unstructured adapter output branch
- `backend/app/runtime/ai_decision_logging.py`: `role_aware_decision=None` behavior
- `backend/app/runtime/routing_authority.py`: `RoutingPolicy.choose()` / LangGraph routing relation
- `ai_stack/langchain/bridges.py`: `narrative_response` and responder aliases
- `ai_stack/mcp/mcp_canonical_surface.py`: permission metadata public surface
- `ai_stack/contracts/npc_agency_contracts.py`: `initiatives` input alias
- `ai_stack/story_runtime/npc_agency/npc_agency_planner.py`: `pressure_shift` input alias
- `world-engine/app/story_runtime/manager/_legacy_loader.py` and `_legacy_sources`: manager monolith-split remnants

## Audit Conclusion

The reports show real progress in reducing active-surface hits from 989 to 358,
but the current removal ledger overstates semantic removal. The last wave
contains multiple cases where legacy wording disappeared while behavior stayed
active. Those must be corrected in the Delagecy registry/tracker before removal
continues, otherwise the process can hide old active compatibility under current
names and violate the ADR rule.
