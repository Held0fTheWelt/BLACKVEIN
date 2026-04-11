# Publishing and module activation

## Canonical content

- Authored modules live under `content/modules/<module_id>/` as YAML and related assets.
- The **backend** loads modules and runs the **compiler** to produce **runtime**, **retrieval**, and **review** projections.

Technical detail (for engineers): [`docs/technical/content/writers-room-and-publishing-flow.md`](../technical/content/writers-room-and-publishing-flow.md) and [`docs/dev/architecture/content-modules-and-compiler-pipeline.md`](../dev/architecture/content-modules-and-compiler-pipeline.md).

## God of Carnage

GoC treats **module YAML as primary**; builtins must not silently override YAML. Contract: [`docs/VERTICAL_SLICE_CONTRACT_GOC.md`](../VERTICAL_SLICE_CONTRACT_GOC.md).

## Writers’ Room and governance

Writers’ Room workflows produce **recommendations** and **review bundles**; **publishing** authority remains with backend/admin governance—not with raw model output. See the technical writers’ room page above for stage names and API entry points.

## Operational notes

- After changing module files in production, follow your release process to **reload** or **redeploy** services that cache projections.
- RAG corpora may need refresh when documentation or content fingerprints change (see [`docs/technical/ai/RAG.md`](../technical/ai/RAG.md)).

## Related

- [Diagnostics and auditing](diagnostics-and-auditing.md)
- [Security and compliance overview](security-and-compliance-overview.md)
