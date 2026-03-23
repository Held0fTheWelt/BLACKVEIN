Forum merge/split wave – delta note (0.0.25)
============================================

Backend path: `backend/`. Frontend path: `administration-tool/`. Remote-first backend default (PythonAnywhere) remains unchanged.

What already exists
-------------------

- **Models:** `ForumCategory`, `ForumThread`, `ForumPost`, `ForumReport`, `ForumThreadSubscription`, `Notification`.
  - Threads: `status` (`open`, `locked`, `hidden`, `archived`, `deleted`), `reply_count`, `last_post_at`, `last_post_id`, `category_id`, `author_id`.
  - Posts: `thread_id`, `parent_post_id` (single-level replies enforced), `status` (`visible`, `edited`, `hidden`, `deleted`).
- **Service layer (`forum_service.py`):**
  - Permissions: `user_can_view_thread/post`, `user_can_post_in_thread`, `user_can_moderate_category`, etc.
  - Thread moderation: hide/unhide, lock/unlock, pin/unpin, feature/unfeature, move between categories (`move_thread`), archive/unarchive (`set_thread_archived` / `set_thread_unarchived`), recalc counters (`recalc_thread_counters`).
  - Merge: `merge_threads(source, target)` moves all posts from source into target, merges subscriptions without duplicates, archives the source thread, and recalculates counters for both threads.
  - Split: `split_thread_from_post(source_thread, root_post, new_title, new_category=None)` creates a new thread and moves the root post plus its direct replies into it, then recalculates counters for both threads.
  - Notifications: `create_notifications_for_thread_reply` for subscribers; mention notifications on create/update.
- **Routes (`forum_routes.py`):**
  - Full forum API plus moderation endpoints from 0.0.24.
  - Merge: `POST /api/v1/forum/threads/<source_thread_id>/merge` (JWT, moderator/admin per category, body `{"target_thread_id": <int>}`) calling `merge_threads`.
  - Split: `POST /api/v1/forum/threads/<thread_id>/split` (JWT, moderator/admin per category, body `{"root_post_id": <int>, "title": "<str>", "category_id": <int?>}`) calling `split_thread_from_post`.
  - Notifications: `GET /api/v1/notifications`, `PATCH/PUT /api/v1/notifications/<id>/read`, `POST/PUT /api/v1/notifications/read-all` with `thread_slug` and `target_post_id` for forum_post targets.
- **Frontend (public `forum.js` + templates):**
  - Thread page shows moderator bar with Lock/Unlock, Pin/Unpin, Archive/Unarchive, Move…, and **Merge…** actions.
  - Per-post moderation on thread page: Hide/Unhide; for top-level posts moderators also get **“Split to new thread”** calling the split endpoint.
  - Notifications page links to `/forum/threads/<slug>#post-<id>` where `target_post_id` is present and supports mark-all-read.
- **Frontend (manage):**
  - `/manage/forum` moderation dashboard card: metrics, open reports with quick status actions, recently handled reports, locked/pinned threads lists, hidden posts list.
- **Tests (`backend/tests/test_forum_api.py`):**
  - Merge: tests for moving posts and counters, permission enforcement, and subscription merge behavior.
  - Notifications: tests for mark-all-read, `thread_slug`/`target_post_id` for forum_post, and mention notifications.
  - Moderation dashboard: metrics and lists endpoints.

What is missing for this wave
-----------------------------

- **Split tests:** There are currently no dedicated API tests exercising the `/forum/threads/<id>/split` route and the `split_thread_from_post` helper.
- **Postman coverage:** The Postman collection has forum folders and moderation actions (lock/pin/move/archive) but no explicit requests for merge or split.
- **Docs:** `docs/forum/ModerationWorkflow.md` documents lock/pin/archive/move and post hide/unhide, but not merge or split workflows or their constraints.
- **Changelog:** `CHANGELOG.md` 0.0.24 describes moderation dashboard, notification polish, advanced moderation, and mentions, but there is no entry yet for the merge/split wave (0.0.25).
- **Merged-state visibility:** Archived threads are implied by `status == "archived"` and archive/unarchive actions but there is no explicit “archived/merged” visual hint on the public thread page beyond general behavior.

Files that will change
----------------------

- **Tests:** `backend/tests/test_forum_api.py` – add focused tests for the split endpoint, permissions, data movement, and metadata correctness.
- **Postman:** `postman/WorldOfShadows_API.postman_collection.json` – extend the existing Forum folder with merge and split requests using the current variable/URL conventions.
- **Docs:** `docs/forum/ModerationWorkflow.md` – extend to cover merge and split workflows, roles, and limitations.
- **Changelog:** `CHANGELOG.md` – add a new 0.0.25 entry describing merge, split (with limitations), tests, and Postman/doc updates.
- **Optional UI improvement (if kept in scope):** `administration-tool/static/forum.js` and possibly `administration-tool/templates/forum/thread.html` for a small, staff-focused “archived/merged” hint on archived threads.

Must not be refactored
-----------------------

- Core auth and role system (User roles, role levels, area-based feature access).
- Overall backend/frontend split (`backend/` Flask API, `administration-tool/` Flask+Jinja+JS).
- Existing moderation and notification semantics that are already covered by tests (lock/pin/archive/move, hide/unhide, notification read flows).
- Remote-first default for `BACKEND_API_URL` and PythonAnywhere as initial target; local overrides remain for troubleshooting only.

Merged-state visibility feasibility
-----------------------------------

- The current model already exposes `thread.status` and exposes archived threads via API (with staff-only visibility). A small, moderator-facing hint on the thread header (e.g. showing when a thread is archived/locked and possibly clarifying that archived threads may be the result of a merge) can be added **without** new schema and without altering existing moderation behavior.
- No redirect or aliasing system exists for merged source threads; this pass will **not** add redirects. Any merged-state hint must therefore stay descriptive (status-based) rather than URL-remapping.

