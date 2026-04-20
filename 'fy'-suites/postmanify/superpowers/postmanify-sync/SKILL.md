---
name: postmanify-sync
description: Routes agents to refresh Postman collections from OpenAPI and emit per-tag sub-suites. Triggers on postmanify, sync postman, openapi to postman, update Newman collections.
---

# Postmanify sync (router)

**Do not duplicate procedure here.** The **only** specification for when to run generators, how to review diffs, and commit expectations is:

`'fy'-suites/postmanify/postmanify-sync-task.md`

Read that file **in full** before running tooling or editing `postman/`.

**Machine commands (repo root, after `pip install -e .`):**

- `python -m postmanify.tools plan` — counts only.
- `python -m postmanify.tools generate` — writes **`postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json`**, **`postman/suites/`**, and **`postman/postmanify-manifest.json`** (override master path with `--out-master` if required).

CLI flags and paths: [`../references/CLI.md`](../references/CLI.md).
