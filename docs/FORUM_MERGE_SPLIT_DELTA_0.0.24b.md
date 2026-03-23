Forum merge/split wave – delta note (0.0.24b)
================================================

Backend path: `backend/`. Frontend path: `administration-tool/`. Remote-first backend default (PythonAnywhere) remains unchanged.

What already exists
-------------------

- **Models:** `ForumCategory`, `ForumThread`, `ForumPost`, `ForumReport`, `ForumThreadSubscription`, `Notification`.
  - Threads: `status` (`open`, `locked`, `hidden`, `archived`, `deleted`), `reply_count`, `last_post_at`, `last_post_id`, `category_id`, `author_id`.
  - Posts: `thread_id`, `parent_post_id` (single-level replies enforced), `status` (`visible`, `edited`, `hidden`, `deleted`).
  - Reports: `target_type` (`thread`/`post`), `target_id` (no FK), `status` (`open`, `reviewed`, `resolved`, `dismissed`).
  - Subscriptions: per-thread subscriptions; notifications for thread replies and mentions.
- **Service layer (`forum_service.py`):**
  - Permissions: `user_can_view_thread/post`, `user_can_post_in_thread`, `user_can_moderate_category`, etc.
  - Threads: create, update title, soft delete, hide/unhide, lock/unlock, pin/unpin, feature/unfeature, archive/unarchive, move to another category (`move_thread`).
  - Posts: list (with `include_hidden`/`include_deleted` flags for staff), create (validates parent within same thread, shallow replies only), update content, soft delete, hide/unhide, recalc counters (`recalc_thread_counters`).
  - Notifications: `create_notifications_for_thread_reply` (subscribers, `event_type="thread_reply"`); mention notifications on create/update (`event_type="mention"`, `target_type="forum_post"`).
- **Routes (`forum_routes.py`):**
  - Full public/community forum API (categories, threads, posts, likes, reports, subscriptions, search).
  - Moderation: lock/unlock, pin/unpin, feature/unfeature, hide/unhide post, reports list/detail/update, moderation metrics + recent-reports + recently-handled + locked/pinned/hidden lists, move, archive/unarchive.
  - Notifications: `GET /api/v1/notifications` (page/limit/unread_only), `PATCH/PUT /notifications/<id>/read`, `POST/PUT /notifications/read-all` (mark-all-read). Notification payloads include `thread_slug` and `target_post_id` where applicable.
- **Frontend (public `forum.js` + templates):**
  - Public forum pages (index, category, thread) consuming API only.
  - Thread page: mod bar for lock/pin/archive/move; post list with `id="post-<id>"`, safe content rendering + `@username` highlighting.
  - Notifications page: list with read/unread styling, per-item mark-as-read, mark-all-read, links to thread and `#post-<id>` when available.
- **Frontend (manage):**
  - `/manage/forum` template and `manage_forum.js` with categories CRUD, reports list with status filter and actions, moderation dashboard (metrics, recent reports, recently handled, locked/pinned threads, hidden posts).
- **Tests (`test_forum_api.py`):**
  - 38 tests: coverage for category visibility, thread/post CRUD, likes, reports, moderation actions, counters, search, subscriptions, notifications (reply + mention, mark-read, mark-all-read, payload fields), move, archive/unarchive, moderation dashboard endpoints.
- **Postman:**
  - Forum folder with public + moderation endpoints (including move, archive/unarchive, moderation metrics/lists).
  - Notifications folder (list, mark read, mark all read).
- **Docs/Changelog:**
  - `CHANGELOG.md` 0.0.24 describes moderation dashboard, advanced moderation, notifications, mentions, tests, and Postman truthfully.
  - `docs/forum/ModerationWorkflow.md` documents moderation dashboard and core thread/post actions; no mention of merge/split yet.

What is missing for this wave
-----------------------------

- **Thread merge:**
  - No backend operation to merge one thread into another.
  - No helper to move posts from a source thread into a target thread and recalc counters for both.
  - No strategy yet for how to treat the source thread after merge (archived/redirect vs. soft-deleted).
  - No moderation route or UI control for “Merge thread”.
- **Thread split:**
  - No backend operation to split selected posts into a new thread.
  - No strategy defined for handling `parent_post_id` when splitting (reply trees that span old/new threads).
  - No moderation route or UI control for “Split thread”.
- **Notification polish for this wave:**
  - Functional and reasonably polished already (thread_slug + target_post_id, mention vs thread_reply, mark-read/all-read).
  - Remaining polish is mostly around clearer event-type presentation and text (e.g. distinguishing mention vs reply in UI) and optional filtering, not correctness.
- **Moderation comfort:**
  - Dashboard exists but has only basic filters (status for reports, fixed limit values).
  - Thread UI exposes lock/pin/archive/move but not merge/split controls or explicit merged/split state.

Files expected to change
------------------------

- **Backend:**
  - `backend/app/services/forum_service.py` – thread merge helper(s), split helper(s), safe counter updates for source/target threads, and constrained handling of `parent_post_id` during split.
  - `backend/app/api/v1/forum_routes.py` – new moderator/admin routes for merge and split (JWT-protected, category-aware permissions, activity logging).
  - Potential small adjustments in notifications or reports if merge/split semantics require marking a thread as merged/archived.
- **Frontend (public forum):**
  - `administration-tool/templates/forum/thread.html` and `administration-tool/static/forum.js` – moderator controls and flows for merge/split on the thread page, confirmation dialogs, clear labels.
- **Frontend (manage):**
  - Optional refinements in `manage_forum.js` / `manage/forum.html` for moderation comfort (e.g. additional filters or quick links), but no redesign.
- **Tests:**
  - `backend/tests/test_forum_api.py` – new tests for merge and split behavior, metadata correctness after merge/split, and permission checks.
- **Postman:**
  - `postman/WorldOfShadows_API.postman_collection.json` – add merge/split requests and, if needed, updated notification/moderation examples.
- **Docs/Changelog:**
  - `docs/forum/ModerationWorkflow.md` – extend with merge/split workflows and constraints.
  - `CHANGELOG.md` – new 0.0.25 (or next) entry for this wave.

Must not be broadly refactored
------------------------------

- Permission model (moderator/admin per category, JWT checks).
- Thread/post visibility semantics (`status`, `is_locked`, `is_pinned`, archived/hidden staff-only behavior).
- Baseline notifications and moderation dashboard; only targeted changes where needed for merge/split and UX polish.
- Existing forum flows (create/update/delete/hide/move/archive threads and posts) unless correctness for merge/split demands a local adjustment.

Data integrity risks for merge/split
------------------------------------

- **Lost posts:** Merge/split operations must move posts only by updating `thread_id` via controlled helpers, ideally within a transaction; partial moves must not be committed.
- **Reply structure (`parent_post_id`):** Splitting arbitrary posts risks breaking reply trees if parents/children end up in different threads. Safe split strategy likely: split from a given post and include all its descendants (subtree), or restrict split to posts without children. The implementation must choose a constrained strategy and document limitations.
- **Counters and metadata:** `reply_count`, `last_post_at`, `last_post_id` must be recalculated for both source and target threads after merge/split to avoid stale metadata and broken ordering.
- **Reports and notifications:** `ForumReport.target_type/id` and `Notification.target_type/id` are id-based references. Since merge/split does not change primary keys, these references remain valid, but merging/splitting threads changes context (thread/category of a post). Any features that assume a fixed thread/category for a post must account for this.
- **Subscriptions:** `ForumThreadSubscription` is per-thread. Merge may need to consolidate subscriptions from both threads into the target thread to avoid “lost” followers. Split should likely keep subscriptions on the original thread only (or document a simple rule) to avoid unexpected subscription explosions.
- **Slugs and URLs:** After merge, the target thread’s slug becomes canonical. The source thread should not be reused blindly; marking it as archived/merged (or soft-deleted) is safer so old URLs do not silently point at an unrelated discussion in the future.

These constraints will guide implementation choices in later phases: prefer a constrained, well-documented merge/split behavior over a superficially flexible but fragile design.

