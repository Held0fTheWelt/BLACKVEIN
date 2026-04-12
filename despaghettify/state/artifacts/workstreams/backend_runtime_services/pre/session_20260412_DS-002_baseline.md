# DS-002 Pre-Artifact — Duplicate Callable Names Baseline

Generated: 2026-04-12

## C6 Baseline

- count_functions_duplicate_name_across_files: 660
- total_functions: 4404
- C6 pct: 14.99%

## Top Actionable Targets

| Function | Files | Action |
|----------|-------|--------|
| _utc_now | 25 | Extract to app/utils/time_utils.py |
| _parse_int | 7 | Extract to app/api/v1/_route_utils.py |
| _parse_date + _date_to_end_of_day | 2 each | Extract to app/services/_analytics_utils.py |
| _utc_iso | 2 | Merge into time_utils.py |
| _normalize_slug | 2 (actionable) | Consolidate news_service_create_guards → news_service |
| _cap_str | 2 | Extract to app/runtime/_string_utils.py |

## Expected Post-Reduction Estimate

Target: ≤ 625 occurrences (≥ -35)
