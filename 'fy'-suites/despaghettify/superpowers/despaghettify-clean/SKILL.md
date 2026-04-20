---
name: despaghettify-clean
description: Routes agents to the Despaghettify artefact wipe — workstreams pre/post, autonomous_loop session state, optional spaghetti_check_last.json, optional ephemeral cleanup. Triggers on spaghetti clean, wipe despaghettify artefacts, hub clean before reset.
---

# Despaghettify clean (router)

**Do not duplicate danger notices or PowerShell steps here.** The **only** specification for irreversibility, slug list, wipe/recreate layout, and optional ephemeral cleanup is:

`despaghettify/spaghetti-clean-task.md`

Read that file **in full** and execute it. This task **deletes governance evidence** under `artifacts/workstreams/**` and **autonomous macro-loop state** under `artifacts/autonomous_loop/`; do not run if those files are the sole copy of required closure proof.

Binding index: `despaghettify/state/WORKSTREAM_INDEX.md`.
