<!-- templify:template_id=reports:status_summary template_hash=7a453b95325094810f781786db45aa9ca86e61977c170ac6cfea572146d2ab46 -->
# documentify — Most-Recent-Next-Steps

This page uses simple language. It should help you understand the latest result and what to do next.

## Current status

- suite: `documentify`
- command: `audit`
- ok: `true`
- latest_run_id: `documentify-db558b5d3a05`
- latest_run_mode: `audit`
- latest_run_status: `ok`

## Plain summary

Documentify generated the current documentation tracks and status pages.

## Decision guidance



## Most-Recent-Next-Steps

- Read the latest documentify output and choose the narrowest next move based on the current evidence.

## Key signals

- none

## Uncertainty

- none

## Cross-suite signals

- `usabilify`: Usabilify evaluated UI and UX surfaces, connected available UI contracts, and highlighted the next usability steps in plain language.
  - next: Read the latest usabilify output and choose the narrowest next move based on the current evidence.
- `templatify`: No summary is available yet.
  - next: Read the latest templatify output and choose the narrowest next move based on the current evidence.
- `securify`: Securify did not find tracked secret-like files or embedded secret patterns, and basic security guidance is present.
  - next: Keep security surfaces stable and rerun securify after meaningful repository changes.
- `docify`: Found 8 indexed evidence hits for query "docstring" across suites ['docify']. Strongest source: generated/context_packs/docify_context_pack.json#chunk-1. Use the top-ranked items first and treat lower-confidence hits as hints.
  - next: Open generated/context_packs/docify_context_pack.json#chunk-1 first.
  - next: Use the top two hits to validate the next code or governance action.
- `contractify`: Found 8 indexed evidence hits for query "openapi health" across suites ['contractify']. Strongest source: generated/context_packs/contractify_context_pack.md#chunk-4. Use the top-ranked items first and treat lower-confidence hits as hints.
  - next: Open generated/context_packs/contractify_context_pack.md#chunk-4 first.
  - next: Use the top two hits to validate the next code or governance action.

## Governance

- none

## Warnings

- none
