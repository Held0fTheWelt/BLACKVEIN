# AI Stack Release Readiness Checklist

NOTE: placeholder file created automatically on 2026-04-17. Fill with executable checks before production rollout.

Minimum items (examples):

- Trace continuity: `X-WoS-Trace-Id` propagation across backend → world-engine → LangGraph.
- Operator/audit fields present on `AIDecisionLog` and runtime rollups.
- Smoke tests: `pytest -q` green for backend and world-engine profiles.
- Security audit: resolved high/critical findings (see `../SECURITY-AUDIT-2026-03-15.md`).
- Deployment config: `PLAY_SERVICE_*` and trace sampling configured.
- Automated gate checks: gate G1..G11 summaries present in `docs/audit/gate_summary_matrix.md`.

Replace this file with the project-maintained checklist and add runnable commands.
