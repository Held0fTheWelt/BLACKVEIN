# fy v2 Core-Thinning Followpass Wave 2 Report

## Executive judgment

This followpass targeted the remaining shared-core consolidation points that still behaved like cross-cutting hubs after the earlier wave set.

The goal of this pass was not to broaden architecture again.
It was to reduce the next layer of shared-core concentration while preserving compatibility and test stability.

## Wave targets

The pass focused on four shared-core areas:

1. `fy_platform/ai/schemas/common.py`
2. `fy_platform/ai/workspace.py`
3. `fy_platform/ai/model_router/router.py`
4. `fy_platform/surfaces/platform_dispatch.py`

These files were still acting as broad aggregation surfaces even though the more dominant core spikes had already been reduced in the earlier followpass.

## Implemented reductions

### Wave E — schema hub split

`fy_platform/ai/schemas/common.py` was reduced from a broad mixed schema hub into a thin compatibility export layer.

New supporting modules:

- `fy_platform/ai/schemas/common_records.py`
- `fy_platform/ai/schemas/common_runtime.py`
- `fy_platform/ai/schemas/common_utils.py`

Result:

- `common.py`: **275 -> 32 lines**

### Wave F — workspace hub split

`fy_platform/ai/workspace.py` was reduced from a mixed hashing / IO / layout / docs surface into a thin public workspace facade.

New supporting modules:

- `fy_platform/ai/workspace_hashing.py`
- `fy_platform/ai/workspace_io.py`
- `fy_platform/ai/workspace_layout.py`
- `fy_platform/ai/workspace_docs.py`

Result:

- `workspace.py`: **210 -> 40 lines**

### Wave G — model router split

`fy_platform/ai/model_router/router.py` was reduced by extracting static policy construction and governed-route recording.

New supporting modules:

- `fy_platform/ai/model_router/policies.py`
- `fy_platform/ai/model_router/recording.py`

Result:

- `router.py`: **190 -> 88 lines**

### Wave H — platform dispatch split

`fy_platform/surfaces/platform_dispatch.py` was reduced by extracting payload-specialization helpers and emit logic.

New supporting modules:

- `fy_platform/surfaces/platform_dispatch_payloads.py`
- `fy_platform/surfaces/platform_dispatch_emit.py`

Result:

- `platform_dispatch.py`: **185 -> 150 lines**

## Hardening and compatibility notes

- Existing import surfaces remain compatible.
- `fy_platform/ai/schemas/common.py` still exports the expected public names.
- `fy_platform/ai/workspace.py` still exports the expected workspace helper names.
- The special `govern` exit-code contract was preserved after the dispatch split.
- New structural regression tests were added to keep the newly reduced files from silently regrowing.

## Test result

- `83 passed`

## Remaining shared-core picture

The most problematic early shared-core spikes are no longer concentrated in the same central hub files.
The remaining larger files are now more often domain-specific or intentionally grouped helper modules rather than broad cross-cutting platform hubs.

That is materially stronger than the pre-pass state.
