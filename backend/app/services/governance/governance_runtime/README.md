# Governance Runtime Service

This directory contains the source slices loaded by
`backend/app/services/governance/governance_runtime_service.py`.

The public import path stays stable because routes, CLI commands, runtime
helpers, and tests import `app.services.governance.governance_runtime_service`.
The loader executes these ordered slices into that module namespace, so existing
monkeypatches of module globals such as `urlopen` and `httpx` keep working.

Keep every service slice below 100 lines and name new slices by the governance
capability they own: bootstrap, provider contracts, model routing, readiness,
runtime snapshots, scope settings, usage, budgets, audit, or operational
activity.
