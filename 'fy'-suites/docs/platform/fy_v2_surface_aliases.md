<!-- templify:template_id=reports:surface_aliases template_hash=84dd1a933d53644e6a82127a018d482caa56684132cf2e39cc24b823c05e7cd8 -->
# fy Surface Alias Map

- entry_count: `9`

## Lenses

- `governance`: contract, security, release, production
- `quality`: quality, structure
- `knowledge`: docs, code_docs
- `platform`: context_pack, mvp, report, governor_status, surface_aliases, packaging_prep

## Legacy alias entries

- `contractify` → `fy analyze --mode contract` [governance, C2]
- `despag-check` → `fy analyze --mode structure` [quality, C2]
- `despaghettify` → `fy analyze --mode structure` [quality, C2]
- `docify` → `fy analyze --mode code_docs` [knowledge, C2]
- `documentify` → `fy analyze --mode docs` [knowledge, C2]
- `metrify` → `fy metrics --mode report` [platform, C2]
- `mvpify` → `fy import --mode mvp` [platform, C2]
- `securify` → `fy analyze --mode security` [governance, C2]
- `testify` → `fy analyze --mode quality` [quality, C2]

## Explicit exceptions

- dockerify remains suite-first until provider/runtime packaging converges.
- postmanify remains suite-first until API projection governance is explicitly collapsed.
- observifyfy stays internal-first and is not yet exposed as a platform mode.
- usabilify remains indirectly represented through the knowledge lens until its collapse surface is implemented.
