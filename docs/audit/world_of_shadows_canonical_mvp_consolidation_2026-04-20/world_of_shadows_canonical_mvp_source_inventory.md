# World of Shadows canonical MVP source inventory

## Inventory principle

This inventory covers the audited source artifacts that materially informed the canonical reconstruction.
It is grouped by meaningful source layers rather than by every single file in the repository.

## Audited source inventory

| Artifact | Type | Classification | Why used | Outcome |
|---|---|---|---|---|
| world_of_shadows_mvp_v24_f_line_closed_FULL_MVP_DIRECTORY.zip | supplied archive | canonical candidate, implementation evidence, audit evidence, ADR / architecture authority, historical but still content-bearing | Primary evidence-rich superset archive with the broad MVP tree, current docs, governance ledgers, proof reports, and more complete code/test surfaces. | Chosen as primary reconstruction base. |
| world_of_shadows_mvp_v24_lean_finishable.zip | supplied archive | partial MVP fragment, historical packaging claim, duplicate / near duplicate | Secondary comparison artifact for omissions, narrowing decisions, and wording drift. | Used as comparison source only; not sufficient alone as canonical MVP. |
| mvp/docs/* and mvp/reference_scaffold/* | historical MVP core | canonical candidate, historical but still content-bearing | Carries the broad system target, constitutional laws, memory/emotion/consciousness layers, writers-room platform, implementation protocol, and executable scaffold. | Preserved as enduring target-state layer. |
| docs/start-here/*, docs/technical/*, docs/admin/*, docs/user/* | current repo documentation | canonical candidate, implementation-adjacent documentation | Best source for current service boundaries, runtime authority, player/admin surfaces, AI stack, publishing flow, and active slice semantics. | Used as main current-state narrative layer. |
| GoC contract family | slice contract family | ADR / architecture authority, canonical candidate | Normative contract family for the God of Carnage slice. | Folded into the canonical GoC experience and authority docs; originals retained as deep anchors. |
| docs/audit/* | closure cockpit baseline | audit evidence | Defines Level A vs Level B closure posture and gate summary. | Used to set runtime-proof judgment honestly. |
| validation/V24_* | validation reports | implementation evidence, audit evidence | Provides wave-by-wave and system-surface proof, especially shell loop, publish/runtime activation, GoC A-F behavior, and quick-suite closure. | Used as primary proof corpus. |
| governance/V24_*_LEDGER.md | governance ledger family | ADR / architecture authority, audit evidence | Carries anti-drift rules around source preservation, backend retirement, API projection governance, and Writers’ Room/RAG overlap. | Pulled into canonical governance and residue statements. |
| content/modules/god_of_carnage/* | authored content | implementation evidence, canonical candidate | Primary authored source for the active slice. | Preserved as canonical authored source. |
| owner components and tests | code and tests | implementation evidence | Repository reality used to judge implemented vs partial vs target-only status. | Cross-checked against documentation and validation reports. |
| backend/docs/UI_USABILITY.md and docs/ROADMAP_MVP_ENGINE_AND_UI.md | UI expectation sources | historical but still content-bearing, partial MVP fragment | Carry player-facing UI/UX requirements that were not fully pulled into a canonical doc. | Integrated directly into the new canonical UI/UX document. |

## Archive comparison conclusion

- The **FULL** archive was the evidence-rich superset and primary reconstruction base.
- The **LEAN** archive was useful as a packaging-claim comparator, but it was not complete enough to serve as the canonical MVP on its own.
- The broad historical `mvp/` tree remained materially relevant and could not be discarded without losing World of Shadows system truth.
