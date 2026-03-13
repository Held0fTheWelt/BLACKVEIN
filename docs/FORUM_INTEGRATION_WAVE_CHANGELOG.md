# Forum Integration Wave Changelog

## v0.0.27 — Forum Integration Wave (2026-03-13)

This entry documents changes confirmed in the codebase as of 2026-03-13.

### Added

- **`GET /api/v1/forum/tags`** — List all forum tags (moderator/admin only). Supports `q` (label/slug search), `page`, and `limit` query params. Returns `items` (each with `id`, `slug`, `label`, `thread_count`, `created_at`), `total`, `page`, `per_page`.
- **`DELETE /api/v1/forum/tags/<id>`** — Delete a forum tag by ID (admin only). Returns 404 if the tag does not exist and 409 if the tag is currently associated with one or more threads. Returns 200 on success.
- **`bookmarked_by_me` and `tags` fields on thread list** — `GET /api/v1/forum/categories/<slug>/threads` now includes `bookmarked_by_me` (bool, false for anonymous users) and `tags` (array of tag label strings) on each thread object. These are batch-loaded per page to avoid N+1 queries.
- **`total` and `per_page` fields on thread list response** — The thread list response now returns `total` (count of all visible threads in the category after per-user visibility filtering), `page`, and `per_page` in addition to `items`.

### Changed

- **Thread list pagination strategy** — `GET /api/v1/forum/categories/<slug>/threads` loads up to 1000 threads from the database, applies per-user visibility rules in Python, then slices the result to the requested page. This is a known limitation: categories with more than 1000 non-deleted threads will not show threads beyond that position. A SQL-level pagination rewrite is deferred to a future phase.

### Performance

- **Migration 026** — Indexes on `forum_reports(status, created_at)` and `forum_threads(category_id, is_pinned, last_post_at)` support moderation dashboard queries and thread listing.

### Not Implemented (documented for clarity)

The following items were listed in the integration wave plan but are **not present** in the codebase as of this release:

- `resolution_note` field on `ForumReport` — no migration, no model column, not serialized.
- Pagination (`page`, `limit`) and `target_type` filtering on `GET /api/v1/forum/reports` — the endpoint only supports a `status` filter and returns all matching reports in a single list.
- Migrations 027 and 028 referenced in the delta plan do not exist.
