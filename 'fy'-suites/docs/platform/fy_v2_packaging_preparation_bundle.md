<!-- templify:template_id=reports:packaging_preparation_bundle template_hash=e210e8b1f8a99a9459b13a6a38d8ac2c43bc8d237003560379c8c0ed15258d9c -->
# fy Packaging Preparation Bundle

## Target layout

- fy_platform/core/* for workspace, hashing, IO, and backup primitives.
- fy_platform/runtime/* for mode dispatch, lane runtime, compatibility routing, and transition stabilization.
- fy_platform/ir/* for models, IDs, catalog persistence, relations, and serializers.
- fy_platform/providers/* for provider contracts, governor, cache, execution, and adapters.
- fy_platform/surfaces/* for platform shell, legacy aliases, lens registry, alias maps, and public shell docs.
- fy_platform/services/* for domain services separated from platform runtime concerns.
- fy_platform/compatibility/* for bounded carry-over shells during collapse.

## Migration notes

- Keep fy_platform/ai as a compatibility shell during the staged move into core/runtime/ir/providers/surfaces.
- Prefer extraction over file moves when preserving import stability for runner-driven implementation passes.
- Do not remove legacy suite CLIs until surface aliases are documented and the platform shell covers the same outward action.
- Use despaghettify core-transition waves to decide extraction order for shared hotspots.

## Compatibility impact matrix

- `contractify` → `fy analyze --mode contract` [compatibility-wrapper-retained, C2]
- `despag-check` → `fy analyze --mode structure` [compatibility-wrapper-retained, C2]
- `despaghettify` → `fy analyze --mode structure` [compatibility-wrapper-retained, C2]
- `docify` → `fy analyze --mode code_docs` [compatibility-wrapper-retained, C2]
- `documentify` → `fy analyze --mode docs` [compatibility-wrapper-retained, C2]
- `metrify` → `fy metrics --mode report` [compatibility-wrapper-retained, C2]
- `mvpify` → `fy import --mode mvp` [compatibility-wrapper-retained, C2]
- `securify` → `fy analyze --mode security` [compatibility-wrapper-retained, C2]
- `testify` → `fy analyze --mode quality` [compatibility-wrapper-retained, C2]

## Package freeze checklist

- Platform shell covers primary public entry points.
- Lane runtime persists real execution records for active platform modes.
- IR seed objects are written by real runtime paths.
- Governor boundary blocks or records every routed provider decision.
- Surface alias map is complete or explicitly excepted.
- Packaging impact reviewed for every still-public suite CLI.
