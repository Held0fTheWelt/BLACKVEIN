# Despaghettify Audit

- total_python_files: 341
- file_spikes: 27
- function_spikes: 60
- global_category: `low`
- transition_profile: `core_transition`

## Wave plan

- `extract_function` → `contractify/tools/adr_governance.py` (high)
- `extract_function` → `contractify/tools/canonical_graph.py` (high)
- `split_file` → `contractify/tools/discovery.py` (high)
- `extract_function` → `contractify/tools/discovery.py` (high)
- `extract_function` → `contractify/tools/relations.py` (high)
- `split_file` → `despaghettify/tools/hub_cli.py` (high)
- `extract_function` → `despaghettify/tools/hub_cli.py` (high)
- `split_file` → `despaghettify/tools/spaghetti_setup_audit.py` (high)
- `extract_function` → `despaghettify/tools/spaghetti_setup_audit.py` (high)
- `extract_function` → `diagnosta/tools/analysis.py` (high)
- `extract_function` → `docify/tools/canonical_graph.py` (high)
- `extract_function` → `docify/tools/canonical_graph.py` (high)
- `split_file` → `docify/tools/python_docstring_synthesize.py` (high)
- `split_file` → `docify/tools/python_documentation_audit.py` (high)
- `extract_function` → `docify/tools/python_documentation_audit.py` (high)
- `split_file` → `docify/tools/python_inline_explain.py` (high)
- `split_by_concern` → `fy_platform/ai/adapter_cli_helper.py` (high)
- `split_by_concern` → `fy_platform/ai/adapter_commands.py` (high)
- `split_by_concern` → `fy_platform/ai/base_adapter.py` (high)
- `split_by_concern` → `fy_platform/ai/final_product_catalog_data.py` (high)

## Ownership hotspots

- `fy_platform/ai/adr_reflection.py` → `core_transition_spike` (low)
- `fy_platform/ai/adapter_commands.py` → `core_transition_spike` (low)
- `fy_platform/ai/evidence_registry/registry.py` → `core_transition_spike` (medium)
- `fy_platform/ai/semantic_index/index_manager.py` → `core_transition_spike` (low)
- `fy_platform/ai/adapter_cli_helper.py` → `mixed_responsibility_module` (high)
- `fy_platform/ai/adapter_commands.py` → `mixed_responsibility_module` (high)
- `fy_platform/ai/base_adapter.py` → `mixed_responsibility_module` (high)
- `fy_platform/ai/contracts.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/evidence_registry/registry.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/final_product.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/final_product_capability.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/final_product_catalog_data.py` → `mixed_responsibility_module` (high)
- `fy_platform/ai/final_product_catalog_render.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/final_product_schema_catalog.py` → `mixed_responsibility_module` (high)
- `fy_platform/ai/model_router/recording.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/model_router/router.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/production_readiness_render.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/run_lifecycle.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/schemas/__init__.py` → `mixed_responsibility_module` (medium)
- `fy_platform/ai/schemas/common.py` → `mixed_responsibility_module` (medium)

## Refattening guard

- ok: `false`
- violation_count: `10`
