<!-- templify:template_id=reports:workspace_release_readiness template_hash=c823d2fceb637ff645dddc216354ccfe069bf58e693812533a3f90769473809c -->
# fy Workspace Release Readiness

- ok: `false`
- generated_at: `2026-05-18T13:34:18.232726+00:00`
- core_ready: `12`
- core_blocked: `1`

## Core Suites

- `coda` ready=`false` latest_run=`none`
  - blocking: `missing:state`
  - blocking: `no_successful_run_recorded`
- `contractify` ready=`true` latest_run=`contractify-c2470d746432`
  - next: Read the latest contractify output and choose the narrowest next move based on the current evidence.
- `despaghettify` ready=`true` latest_run=`despaghettify-722989bbcc30`
  - next: Read the latest despaghettify output and choose the narrowest next move based on the current evidence.
- `diagnosta` ready=`true` latest_run=`diagnosta-a16db438b53a`
- `docify` ready=`true` latest_run=`docify-5ff205bff250`
  - next: Open tools/tests/test_python_docstring_synthesize.py#chunk-1 first.
  - next: Use the top two hits to validate the next code or governance action.
- `documentify` ready=`true` latest_run=`documentify-7fc258544374`
  - next: Read the latest documentify output and choose the narrowest next move based on the current evidence.
- `metrify` ready=`true` latest_run=`metrify-c8fb95fd55d3`
- `mvpify` ready=`true` latest_run=`mvpify-1b990e1ed455`
- `observifyfy` ready=`true` latest_run=`observifyfy-0f7996516de6`
- `securify` ready=`true` latest_run=`securify-9311350210be`
  - next: Keep security surfaces stable and rerun securify after meaningful repository changes.
- `templatify` ready=`true` latest_run=`templatify-d0e8dc9c54e2`
  - next: Read the latest templatify output and choose the narrowest next move based on the current evidence.
- `testify` ready=`true` latest_run=`testify-399409292cb9`
  - next: Read the latest testify output and choose the narrowest next move based on the current evidence.
- `usabilify` ready=`true` latest_run=`usabilify-1435848b1055`
  - next: Review the highest-traffic templates and static assets for navigation, state clarity, and error recovery.

## Optional Suites

- `dockerify` ready=`true` latest_run=`dockerify-13a5c99ab9ce`
- `postmanify` ready=`true` latest_run=`postmanify-8b19e58f06b7`

