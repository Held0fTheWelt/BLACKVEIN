# Changelog

All notable changes to the World of Shadows project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).


# Version Description

- Version 0.0: Foundation, Web-Api with backend and administration-tool to administrate the system

**Current repository paths:** Docs and README use `backend/` and `administration-tool/`. Older entries may mention `Backend/` or `Frontend/` as they were at release time. The administration-tool default for `BACKEND_API_URL` is now remote-first (PythonAnywhere); local is for override/troubleshooting only (see README).
- Version 0.1: Integration of a content framework to organize role playing game
- Version 0.2: Integration of Game Rules and Game System
- Version 0.3: Integration of dynamic evolving content with rules and drafts


---

## [0.0.27] - 2026-03-13

### Added

- **Forum tag management endpoints:** `GET /api/v1/forum/tags` (moderator/admin, paginated, searchable) lists all tags with thread counts. `DELETE /api/v1/forum/tags/<id>` (admin only) deletes unused tags; returns 409 if the tag has thread associations.
- **Thread list enhancements:** `GET /api/v1/forum/categories/<slug>/threads` now returns `bookmarked_by_me` (bool) and `tags` (array of label strings) per thread, and includes `total` in the response envelope. Tags and bookmark state are batch-loaded per page.

### Changed

- **Postman collection:** Added `Forum > Tags` folder with `List Tags (Moderator+)` and `Delete Tag (Admin only)` requests including response examples. Updated `List Category Threads` with a response example showing `bookmarked_by_me`, `tags`, and `total`. Corrected `List Reports (Moderator+)` URL to remove non-functional `page`/`limit` params and added an accurate response example.
- **`backend/docs/FORUM_MODULE.md`:** Updated to document all endpoints added since v0.0.19 including bookmarks, subscriptions, tags, bulk moderation, merges, splits, and search filters.

### Known limitations

- `GET /api/v1/forum/reports` does not support `page`, `limit`, or `target_type` filtering. It supports `status` only and returns all matching reports in a single list.
- Thread list visibility filtering runs in Python over up to 1000 threads per category; categories with more than 1000 non-deleted threads may not surface all content at higher page offsets.

---

## [0.0.26] - 2026-03-12

### Added

- **News/Wiki–forum integration:** News detail responses now include a `related_threads` array (safe subset of public forum threads). New endpoints `GET /api/v1/news/<id>/related-threads`, `POST /api/v1/news/<id>/related-threads` and `DELETE /api/v1/news/<id>/related-threads/<thread_id>` allow moderators/admins to attach explicit related threads to articles. Wiki public responses include `related_threads` as well, with admin endpoints `GET/POST/DELETE /api/v1/wiki/<id>/related-threads` to manage them. All related-thread lists are restricted to threads in public categories and exclude deleted threads.
- **Bookmarks / saved threads:** New `ForumThreadBookmark` model and endpoints `POST /api/v1/forum/threads/<id>/bookmark`, `DELETE /api/v1/forum/threads/<id>/bookmark`, and `GET /api/v1/forum/bookmarks` let authenticated users save threads and list their bookmarks. Bookmarked thread lists include author, category, and tags and respect existing visibility rules.
- **Thread tags:** New `ForumTag` and `ForumThreadTag` models support normalized thread tags. Threads expose a `tags` array in `GET /api/v1/forum/threads/<slug>` and bookmarks. Moderators/admins or thread authors can set tags via `PUT /api/v1/forum/threads/<id>/tags` (body `{"tags": [...]}`); tags are normalized to slug form and reused across threads. Forum search gains a `tag` filter parameter.
- **Forum search filters and content search:** `GET /api/v1/forum/search` now supports filters for `category` (slug), `status`, and `tag`, plus an `include_content=1` flag to include post content in the search. Empty queries with no filters return an empty result (to avoid unbounded scans); ordering is stable via pinned + `last_post_at` + id. Overly long search terms are truncated and post-content search only runs for queries of length ≥ 3.
- **Bulk moderation actions:** Safe bulk operations for moderators/admins: `POST /api/v1/forum/moderation/bulk-threads/status` (lock/unlock and/or archive/unarchive multiple threads by id) and `POST /api/v1/forum/moderation/bulk-posts/hide` (hide/unhide multiple posts). Both reuse the existing per-item helpers and only affect threads/posts in categories the caller may moderate.
- **Report workflow enhancements:** `ForumReport.status` now accepts `escalated` in addition to `open`, `reviewed`, `resolved`, and `dismissed`. New endpoint `POST /api/v1/forum/reports/bulk-status` allows moderators/admins to move multiple reports to `reviewed`/`escalated`/`resolved`/`dismissed` in one operation. The moderation dashboard’s "recently handled" view includes escalated reports as a handled state.
- **Forum moderation log:** Dedicated moderator/admin-visible log for forum actions at `GET /api/v1/forum/moderation/log`, backed by the existing activity log (`category="forum"`). Supports text, status, and date filters and is used to audit merge/split, bulk actions, report updates, and other forum moderation events.
- **Indexes for moderation and search:** Added indexes on `forum_reports(status, created_at)` and `forum_threads(category_id, is_pinned, last_post_at)` to support moderation dashboards and thread listings/search. Earlier waves added indexes for discussion-related tables, bookmarks, and tags.

### Changed

- **Forum search behavior:** Empty or trivial search requests without filters now return no results instead of scanning all threads. Post-content search is limited to reasonable query lengths and combined with title-based search, keeping queries index-friendly.
- **Moderation docs and Postman:** `docs/forum/ModerationWorkflow.md` now documents escalation, bulk actions, and the forum moderation log. `postman/WorldOfShadows_API.postman_collection.json` has been extended with examples for related threads (News/Wiki), bookmarks, tags, bulk moderation operations, and the moderation log so staff can exercise the new APIs directly.

---

## [0.0.25] - 2026-03-12

### Added

- **Thread merge:** Moderators/admins can merge one thread into another via `POST /api/v1/forum/threads/<source_id>/merge` (body `{"target_thread_id": <int>}`). All posts and subscriptions from the source thread move into the target; the source thread is archived (staff-only) and both threads have `reply_count`, `last_post_at`, and `last_post_id` recalculated. Public thread UI exposes a **Merge…** action in the moderator bar.
- **Thread split (constrained):** Moderators/admins can split a thread starting from a **top-level** post via `POST /api/v1/forum/threads/<id>/split` (body `{"root_post_id": <int>, "title": "<string>", "category_id": <int?>}`). The root post and its direct replies move into a new thread; deeper reply trees and non-top-level roots are rejected by design to avoid broken reply chains. Both the original and new threads recalculate counters and last-post metadata after the move. Public thread UI adds a **Split to new thread** action on top-level posts for moderators.
- **Split tests:** `backend/tests/test_forum_api.py` now includes focused tests for split success (new thread creation and post movement), permission enforcement for non-moderators, and the “top-level only” constraint when choosing a root post.
- **Postman merge/split coverage:** `postman/WorldOfShadows_API.postman_collection.json` extends the Forum → Threads folder with **Merge Thread (Moderator+)** and **Split Thread (Moderator+)** requests using the existing `{{baseUrl}}`/JWT conventions.
- **Moderation docs for merge/split:** `docs/forum/ModerationWorkflow.md` documents the merge and split workflows, required roles, API endpoints, and the intentional limitations of the current split strategy.

---

## [0.0.24] - 2026-03-12

### Added

- **Moderation dashboard (admin UI):** New dashboard card on `/manage/forum` for moderator/admin: metrics (open reports, hidden posts, locked threads, pinned threads), open reports list with quick status actions, recently handled reports, and expandable lists for locked threads, pinned threads, and hidden posts. Backend: `GET /forum/moderation/recently-handled`, `locked-threads`, `pinned-threads`, `hidden-posts`; metrics response includes `pinned_threads`; report list responses enriched with `thread_slug` and `target_title` for linking.
- **Notification center polishing:** Notifications list returns `thread_slug` and `target_post_id` for `forum_post` targets so links can point to the specific post. `PUT /api/v1/notifications/read-all` marks all current user's notifications as read. Frontend: "Mark all as read" button, thread links use `#post-<id>` when applicable; thread page posts have `id="post-<id>"` for anchor navigation.
- **Advanced thread moderation:** Move thread to another category: `POST /forum/threads/<id>/move` (body `category_id`). Archive/unarchive: `POST /forum/threads/<id>/archive` and `.../unarchive` (thread status `archived` / `open`). Service: `move_thread`, `set_thread_archived`, `set_thread_unarchived`. Public thread page mod bar: Archive/Unarchive and Move (category dropdown).
- **Mentions (@username):** Post content can include `@username`; on create/update the backend extracts mentions, resolves usernames to users, and creates a `mention` notification for each (excluding author and banned users, no duplicates). Notifications list and thread links support mention targets. Frontend: post body and edit flow render content with `.forum-mention` styling for @username.
- **Tests:** Moderation metrics (pinned_threads), recently-handled reports, locked/pinned/hidden lists; move thread; archive/unarchive; notifications mark-all-read; notifications `thread_slug`/`target_post_id` for forum_post; mention creates notification. Forum test count: 38.
- **Postman:** New requests: Get Recently Handled Reports, Get Locked Threads, Get Pinned Threads, Get Hidden Posts; Move Thread, Archive Thread, Unarchive Thread. Notifications Mark All Read already present.

---

## [0.0.23] - 2026-03-12

### Added

- **Discussion-link integration (News):** Public news API and list/detail responses now include `discussion_thread_id` and `discussion_thread_slug` when a thread is linked. Management UI (`/manage/news`) supports view/set/clear of linked discussion thread (thread ID input, Link/Unlink). Public news detail page shows "Discuss this article" when a thread is linked.
- **Discussion-link integration (Wiki):** Public wiki page API (`GET /api/v1/wiki/<slug>`) includes `discussion_thread_id` and `discussion_thread_slug` when linked. Wiki admin `_page_to_dict` includes discussion fields. Management UI (`/manage/wiki`) supports view/set/clear of linked thread. Public wiki page shows "Discuss this page" when linked.
- **Notifications (functional):** On forum post create, notifications are created for all thread subscribers except the author (`create_notifications_for_thread_reply` in forum_service). Thread detail API returns `subscribed_by_me`. PATCH/PUT `/api/v1/notifications/<id>/read` to mark one as read. Notifications list response includes `thread_slug` for forum_thread targets so the UI can link to the thread.
- **Subscribe/notification UI:** Forum thread page shows Subscribe/Unsubscribe button when logged in. New page `/forum/notifications` lists user notifications with links to threads and "Mark as read"; linked from forum index.

### Changed

- **Docs/path consistency:** README and changelog use `backend/` and `administration-tool/` consistently. README states remote-first default (PythonAnywhere) for BACKEND_API_URL and local troubleshooting override.
- **News discussion permission:** `current_user_can_write_news()` is called with no arguments in news link/unlink routes (permissions define it as no-arg).

### Tests

- **Focused tests:** News discussion link/unlink and public response; wiki public discussion link when linked/not linked; forum subscribe/unsubscribe flow; notification creation on reply for subscribers; notifications list and mark-read. New file `backend/tests/test_wiki_public.py`.

---

## [0.0.22] - 2026-03-12

### Added

- **Forum MVP strengthened:** 27 passing tests cover category visibility, thread/post creation, permissions, like/unlike, reports, moderation actions (lock/unlock, pin/unpin, hide/unhide), counter consistency, and search behavior.
- **News management DX hardened:** Local development documentation and refined article management flow.
- **Discussion integration:** Added `discussion_thread_id` field to NewsArticle and WikiPage models. New endpoints: POST/DELETE `/api/v1/news/<id>/discussion-thread` and `/api/v1/wiki/<id>/discussion-thread` to link/unlink discussion threads with news and wiki content.
- **Subscription foundation:** New endpoint GET `/api/v1/forum/threads/<id>/subscribers` (moderator/admin only) to list thread subscribers.
- **Moderation metrics:** Lightweight endpoints GET `/api/v1/forum/moderation/metrics` and GET `/api/v1/forum/moderation/recent-reports` for moderation dashboard.
- **Notification foundation:** Basic Notification model with `event_type`, `target_type/id`, `is_read` tracking. Endpoint GET `/api/v1/notifications` for user to list their notifications (paginated, can filter unread only).
- **Postman collection:** Updated with all new endpoints (discussion links, subscriptions, moderation, notifications).

---

## [0.0.21] - 2026-03-12

### Added

- **Postman collection:** Updated `postman/WorldOfShadows_API.postman_collection.json` with forum module endpoints (categories, threads, posts, likes, reports).

---

## [0.0.20] - 2026-03-12

### Added

- **Forum QA repairs & expanded tests:** Comprehensive test framework for forum module with 27 tests covering category visibility, thread/post creation, permissions, like/unlike functionality, report submissions, moderation actions (lock/unlock, pin/unpin, hide/unhide), own post editing/deletion, counter consistency, parent post validation, and search behavior. Tests verify role-based access control, soft-delete semantics, and permission enforcement.
- **Forum API enrichment:** Fixed API responses to include `author_username` field consistently across all forum endpoints (category thread listings, thread creation/update, post creation, post listings, search results). Enriched like/unlike endpoints to return `liked_by_me` flag and updated post counts.
- **Forum moderation verification:** Confirmed full moderation UI implementation in both public (`/forum/threads/<slug>`) and management (`/manage/forum`) areas: lock/unlock, pin/unpin, hide/unhide for posts, category CRUD (admin-only), and report status management (open/reviewed/resolved/dismissed).

### Changed

- **Test coverage strategy:** Forum module now has dedicated test suite in `backend/tests/test_forum_api.py` with 27 comprehensive tests. Global repository coverage remains at pytest.ini gate of 85%; forum-specific tests demonstrate correct functionality independent of full repo coverage, allowing incremental improvements to broader test suite without blocking forum QA.

### Fixed

- **API serialization:** Author usernames now included in all thread responses (list, create, update, search) and post responses (list, create), enabling consistent user attribution in forum UI without additional API calls.
- **Test consistency:** Fixed test fixture patterns for proper SQLAlchemy session handling (category_id must be set before thread add, thread_id before post add) to prevent constraint violations.

---

## [0.0.19] - 2026-03-12

### Added

- **Forum architecture contracts:** Documented forum module boundaries, entities (categories, threads, posts, likes, reports, subscriptions), role behavior (public, user, moderator, admin), soft-delete semantics, slug strategy, pagination/search expectations, moderation rules, and high-level API contracts in `Backend/docs/FORUM_MODULE.md` to guide the implementation.
- **Forum schema and migrations:** Added persistent tables for `forum_categories`, `forum_threads`, `forum_posts`, `forum_post_likes`, `forum_reports`, and `forum_thread_subscriptions` via Alembic migration `021_forum_models`, with SQLite-safe, idempotent behavior and optional foreign key for `forum_threads.last_post_id`.
- **Forum service layer:** Implemented `forum_service` with role/permission helpers (access/create/post/edit/like/moderate), thread/post operations (create, update, soft-delete, hide/unhide, lock/unlock, pin/unpin, featured), reply/view/like counters, report CRUD helpers, and subscription helpers as the backend foundation for forum APIs and UI.
- **Forum API (v1):** Added `/api/v1/forum/*` endpoints for public category/thread/post listing and search, authenticated thread/post CRUD, likes, subscriptions, and reports, plus moderator/admin actions for locking/pinning/featuring/hiding content and full report/category management, all wired to the forum service and existing activity log and JWT/role enforcement.
- **Forum public frontend (Phase 3):** Public forum pages under `/forum`: categories list, category thread list with pagination and “New thread” modal, thread detail with paginated posts and reply form. Uses `FrontendConfig.apiFetch` and optional `ManageAuth.apiFetchWithAuth` for authenticated reads/writes; login hint and link to Manage login when not logged in. Nav link “Forum” in main header; forum styles and view-count increment on thread GET in backend.
- **Forum moderation/admin frontend (Phase 4):** Management UI under `/manage/forum` with a **Categories** card (lists categories via API, admin-only create/update/delete wired to `/api/v1/forum/admin/categories[...]`) and a **Reports** card (lists forum reports and allows moderators/admins to set status to open/reviewed/resolved/dismissed via `/api/v1/forum/reports[...]`). New feature flag `manage.forum` in `feature_registry` controls nav visibility; all actions use `ManageAuth.apiFetchWithAuth` and respect backend role checks (moderator/admin) and activity logging.
- **Forum critical fixes & tests:** Hardened thread listing so hidden/archived/private threads do not leak in category lists; tightened like permissions to require actual post visibility; added parent_post_id validation (existence, same-thread, depth, status); ensured reply counters and last-post metadata stay consistent after hide/unhide/delete; introduced `tests/test_forum_api.py` covering visibility, parent validation, like restrictions, and counter behavior.
- **Forum public UI (Phase C):** Like/Unlike buttons per post with `liked_by_me` and `author_username` in API; report modal (POST reports) on thread page; edit/delete own posts (PUT/DELETE) with inline edit; clearer empty/error states; `apiPut`/`apiDelete` and report form in `forum.js`; backend adds `author_username` and `liked_by_me` to thread and post responses; `current_user_is_moderator()` in permissions.
- **Forum moderation/admin UI (Phase D):** Lock/Unlock and Pin/Unpin on public thread page for moderators/admins; Hide/Unhide per post with `include_hidden` for mods; manage/forum shows category CRUD only for admins (moderators see only Reports); report review actions already present in manage UI.
- **Forum search & hardening (Phase E):** Public forum search on index page: form and results with pagination calling `GET /api/v1/forum/search`; search respects visibility (no leakage); CSS for search, mod bar, and hidden badge.

---

## [0.0.18] - 2026-03-12

### Added

- **Versioned data export/import:** Structured JSON export format with `metadata` (format_version, application_version, schema_revision, exported_at, scope, tables, generator, checksum) and `data.tables` for rows. Supports full database, single-table, and row-level exports.
- **Export/import services:** `app.services.data_export_service` and `app.services.data_import_service` implement export logic, metadata generation, import validation, schema/version checks, and deterministic all-or-nothing import execution.
- **Data-tool CLI:** `data-tool/data_tool.py` provides `inspect`, `validate`, and `transform` commands for export payloads. Validates metadata and data structure, optionally compares against a provided current schema revision, and can write sanitized copies for supported formats.
- **Admin data API:** `POST /api/v1/data/export`, `POST /api/v1/data/import/preflight`, `POST /api/v1/data/import/execute`. Export requires admin + feature `manage.data_export`; preflight requires admin + `manage.data_import`; execute requires **SuperAdmin** + `manage.data_import`. All endpoints enforce role/role_level/area-based permissions server-side.
- **Admin frontend UI:** New **Data** page under Manage (`/manage/data`) with export (scope/table/rows) and import (preflight + execute) flows wired to the real API; nav entry visible only when the user has `manage.data_export` in `allowed_features`.
- **Tests:** `tests/test_data_api.py` covering auth protection, export metadata, table validation, metadata/format/schema validation, SuperAdmin requirement, and primary-key collision handling. Full backend suite (203 tests) passes with the new features.
- **Docs & Postman:** `Backend/docs/DATA_EXPORT_IMPORT.md` documents format, metadata, validation, collision strategy, data-tool usage, and security model; Postman collection extended with a **Data Export/Import** folder (Export Full/Table/Rows, Import Preflight/Execute).

### Collision / import strategy

- **Primary key collisions:** For single-column PK tables, existing rows with the same primary keys are detected during preflight with `PRIMARY_KEY_CONFLICT`. Policy: **fail on conflict** – imports do not upsert or skip; they abort without any changes if conflicts exist.
- **Unsupported versions:** Payloads with `metadata.format_version` != 1 are rejected; schema mismatches are reported via `SCHEMA_MISMATCH` and should be resolved with the data-tool once transformation rules exist.

---

## [0.0.17] - 2026-03-12

### Added

- **Area-based access control:** Access to admin/dashboard features now depends on **Role**, **RoleLevel**, and **RoleAreas**. A user may use a feature only if role permits, role_level hierarchy permits, and (when the feature has area assignments) the user has the "all" area or at least one assigned area for that feature.
- **Area model:** Persistent `areas` table (id, name, slug, description, is_system, timestamps). Default areas seeded: `all`, `community`, `website content`, `rules and system`, `ai integration`, `game`, `wiki`. **`all`** is the special wildcard (global access). Areas manageable by admins; system areas protected where appropriate.
- **User–area relation:** Many-to-many via `user_areas`. Users can be assigned one or many areas; "all" grants access to all area-scoped features. API exposes `area_ids` and `areas` on user; admin can assign/remove user areas (subject to hierarchy: target must have lower role_level).
- **Feature/view–area mapping:** Table `feature_areas` (feature_id, area_id). Central registry in `feature_registry.py` with stable feature IDs (e.g. `manage.news`, `manage.users`, `manage.areas`, `manage.feature_areas`). Empty mapping = feature is global; otherwise only users with "all" or one of the assigned areas can access (in addition to role/level).
- **API:** `GET/POST /api/v1/areas`, `GET/PUT/DELETE /api/v1/areas/<id>`; `GET/PUT /api/v1/users/<id>/areas` (body: `area_ids`); `GET /api/v1/feature-areas`, `GET/PUT /api/v1/feature-areas/<feature_id>`. All admin-only; user areas enforce hierarchy. Auth/me includes `allowed_features` and `area_ids`/`areas`.
- **Admin frontend:** **Areas** page (list, create, edit, delete); **Feature access** page (list features, edit area assignment per feature); **Users** form: Areas multi-select and "Save areas". Nav links (News, Users, Roles, Areas, Feature access, Wiki, Slogans) shown/hidden by `allowed_features`.
- **Backend enforcement:** `require_feature(feature_id)` and `user_can_access_feature(user, feature_id)`; area and user-area and feature-area routes protected; user management requires feature `manage.users` and hierarchy.
- **Tests:** `test_areas_api.py` (areas CRUD, user areas GET/PUT, feature-areas list/put, auth/me allowed_features); conftest calls `ensure_areas_seeded()`; `test_home_returns_200` fixed for current landing content (WORLD OF SHADOWS / BLACKVEIN).
- **Docs:** `Backend/docs/AREA_ACCESS_CONTROL.md` (area model, defaults, "all", user/feature areas, API, frontend, hierarchy); `ROLE_HIERARCHY.md` updated with reference to area-based access.
- **Postman:** Collection variables `area_id`; folders **Areas** (List, Get, Create, Update, User Areas Get/Put) and **Feature Areas** (List, Get, Put).

### Changed

- **Permissions:** Role + RoleLevel + RoleAreas; centralized in `feature_registry` and `permissions`. No frontend-only checks for security; backend enforces feature and hierarchy on all admin actions.
- **Migrations:** 019 adds `areas` and `user_areas` and seeds default areas; 020 adds `feature_areas`. Seed/init-db runs `ensure_areas_seeded()`.

---

## [0.0.16] - 2026-03-12

### Added

- **Role QA:** New role `qa` added; seeded with default_role_level 5. Users can be assigned the QA role.
- **RoleLevel on users:** Users have a persistent `role_level` (integer). Stored in DB (migration 017), exposed in user API and dashboards. Used for strict hierarchy.
- **SuperAdmin:** Admin with `role_level >= 100` is SuperAdmin (semantic label only). Only SuperAdmin may increase their own role_level. All users start at role_level 0; create the initial SuperAdmin with `flask seed-dev-user --username admin --password Admin123 --superadmin` or `flask seed-admin-user`.
- **Role model extended:** Roles support optional `description` and `default_role_level` (metadata only; user role_level is not set from this). Seed sets defaults for roles; user authority (role_level) is always 0 except when created by seed.
- **Hierarchy enforcement (backend):** Admins may only edit/ban/unban/delete users with **strictly lower** role_level. Admins may not assign a role whose default_role_level is >= their own. Non-SuperAdmin cannot set own role_level; SuperAdmin may set own role_level only to >= 100. All enforced in user_routes and permissions.
- **Admin role management (frontend):** New **Roles** page under Manage: list roles, create, edit (name, description, default_role_level), delete. Role dropdown in Users is loaded from API (includes QA).
- **User management (frontend):** Users table shows **Level** (role_level). User form has **Role level** field; Save/Ban/Unban/Delete disabled when target has equal or higher role_level. Clear message when editing is forbidden.
- **Tests:** Hierarchy tests: admin cannot edit equal/higher level; cannot delete/ban higher; non-SuperAdmin cannot raise own level; SuperAdmin may raise own level. User list includes role_level. Fixtures: super_admin_user (level 100), admin_user_same_level (50).
- **CLI:** `flask set-user-role-level --username <name>` (bzw. `python -m flask set-user-role-level --username <name>`) setzt für einen bestehenden User das `role_level` (Standard 100 = SuperAdmin). Option `--role-level` für anderen Wert. Kein DEV_SECRETS_OK nötig; nützlich um bestehende Admins zu SuperAdmins zu machen.

### Changed

- **API:** User list/detail include `role_id` and `role_level`. PUT `/api/v1/users/<id>` accepts optional `role_level` (subject to hierarchy). Role create/update accept `description`, `default_role_level`.
- **Permissions:** `admin_may_edit_target`, `admin_may_assign_role_level`, `admin_may_assign_role_with_level`; `current_user_role_level`, `current_user_is_super_admin`. ALLOWED_ROLES includes `qa`.
- **Migrations:** 017 adds `roles.description`, `roles.default_role_level`, `users.role_level`; seeds QA. 018 sets all users’ `role_level` to 0 (authority is per-user; only seed creates SuperAdmin).

---

## [0.0.15] - 2026-03-11

### Added

- **User data: Created and Last seen:** User API and dashboards now expose `created_at` and `last_seen_at` (ISO 8601). `User.to_dict()` includes both; list and detail endpoints return them.
- **Backend dashboard – User Settings:** Profile section shows read-only **Created** and **Last seen** (UTC) for the current user.
- **Frontend manage users:** Users table has **Created** and **Last seen** columns; user detail form shows **Created** and **Last seen** (locale-formatted).
- **Landing teaser slogans with rotation:** Slogans with placement `landing.teaser.primary` are shown on both Backend and Frontend landing pages in the hero subtitle (replacing the static “Where power is automated…” / “A dark foundation…” text). When multiple slogans exist and rotation is enabled in Site Settings, they alternate at the configured interval.
- **Public site APIs:** `GET /api/v1/site/slogans?placement=&lang=` returns all slogans for a placement (for rotation); `GET /api/v1/site/settings` returns read-only `slogan_rotation_interval_seconds` and `slogan_rotation_enabled`. Both are public (no auth).
- **Postman:** Site collection extended with **Site Slogans (list for placement)** and **Site Settings (public)** requests.
- **Tests:** `test_slogans.py` extended with tests for `site/slogans` (public, requires placement, response structure, create-then-list, deactivate-excluded, multiple slogans) and `site/settings` (public, rotation fields).

### Changed

- **API:** `GET /api/v1/users` and `GET /api/v1/users/<id>` responses now include `created_at` and `last_seen_at`.
- **Landing pages:** Backend `home.html` and Frontend `index.html` load teaser slogans via the new slogans API and optional rotation (interval and enabled from site settings).

---

## [0.0.14] - 2026-03-11

### Fixed (frontend only)

- **Management frontend script order:** Page-specific scripts (users, news, wiki, slogans, login, dashboard) were included inside `{% block content %}`, so they ran before `manage_auth.js`. As a result, `ManageAuth` was undefined and pages failed silently. All page scripts are now in `{% block extra_scripts %}` so they run after the shared auth bootstrap.
- **Management page initialization:** Page modules no longer bail out at parse time with `if (!api) return`. They initialize on `DOMContentLoaded` (or immediately if already loaded), resolve `ManageAuth.apiFetchWithAuth` at init time, and set an `apiRef` used by all handlers. If auth is missing, the module logs to the console and shows an inline “Auth not loaded. Refresh the page.” message instead of failing silently.
- **Users page search:** Search input now triggers list reload on Enter in addition to the Apply button.
- **Frontend API config (historical):** At 0.0.14 the default `BACKEND_API_URL` was set to `http://127.0.0.1:5000` for local development. **Current default is remote-first** (PythonAnywhere); set `BACKEND_API_URL` for deployment or use it to override for local troubleshooting (see README).

### Changed (frontend only)

- **Management UI states:** Loading, empty, and error states are surfaced; failed requests show messages in the UI; save/action buttons disable during in-flight requests where applicable.
- **Management hover/focus styling:** Nav links, table rows, tabs, and wiki page links use subtle hover (background/color) and distinct `focus-visible` outlines for accessibility. No layout jump or heavy outline on hover.

### Added (frontend only)

- **Regression documentation:** `docs/frontend/ManagementFrontend.md` describes required script order (config → main.js → manage_auth.js → extra_scripts) and a manual verification checklist for the management area.

---

## [0.0.13] - 2026-03-11

### Added

- **Real dashboard metrics:** Admin Metrics view uses only real user data. Active Users = users with `last_seen_at` in the last 15 minutes; Registered, Verified, Banned totals from DB. Active Users Over Time and User Growth charts from `GET /dashboard/api/metrics?range=24h|7d|30d|12m` with hourly/daily/monthly bucketing. Chart scales derived from actual data maxima. Fake revenue, sessions, and conversion metrics removed.
- **User activity tracking:** `last_seen_at` on User (migration 014), updated on web login and on JWT API requests (throttled to at most once per 5 minutes). `created_at` added for user growth series.
- **Slogan system:** Slogans are a managed content type with CRUD API (`/api/v1/slogans`, moderator+). Placement resolution via `GET /api/v1/site/slogan?placement=&lang=` (public). Categories and placement keys for landing hero/teaser, promo, ad slots. Active/validity/pinned/priority rules; language fallback to default.
- **Slogan management UI:** Frontend `/manage/slogans` for list, create, edit, delete, activate/deactivate. Landing teaser slogan is loaded dynamically from the API; fallback to static text when none or on error.
- **Site Management:** Admin dashboard section “Site Management” with slogan rotation settings: `slogan_rotation_interval_seconds` and `slogan_rotation_enabled` (persisted in `site_settings` table, migration 016).

### Changed

- **Dashboard Metrics UI:** Metric cards are Active Users (last 15 min), Registered Users, Verified Users, Banned Users. Revenue Trend replaced by Active Users Over Time; User Growth shows cumulative registered users. Range selector 24h / 7d / 30d / 12m. Threshold-alert panel for fake metrics removed.

---

## [0.0.12] - 2026-03-11

### Added

- **Wiki HTML sanitization:** Server-side allowlist sanitization (bleach) for all wiki markdown-rendered HTML. Script tags, event handlers, and `javascript:` URLs are removed. Public wiki API, legacy wiki GET, and backend `/wiki` route use sanitized output. Manage wiki preview uses DOMPurify only; when DOMPurify is unavailable, preview shows raw text (textContent) and never injects unsanitized HTML (weak regex fallback removed).
- **Dedicated password change endpoint:** `PUT /api/v1/users/<id>/password` (self only) with body `current_password` and `new_password`. Current password is required and validated before any change.
- **Security headers:** Backend and frontend set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and `Content-Security-Policy`. Optional `Strict-Transport-Security` when `ENFORCE_HTTPS` is set (backend).
- **CSP hardening:** Backend and frontend CSP include `object-src 'none'`. Frontend `connect-src` explicitly allows the backend API origin (derived from `BACKEND_API_URL`) so split frontend/backend setups (e.g. frontend :5001, backend :5000) can communicate. Regression test asserts backend CSP contains `object-src 'none'`.
- **CSV formula injection hardening:** Activity log CSV export uses `csv_safe_cell()` so cells starting with `=`, `+`, `-`, or `@` are prefixed and treated as text in spreadsheets.
- **Wiki slug uniqueness:** Unique constraint and service validation so slug is unique per language across all wiki pages. Migration 013. Duplicate slug in the same language returns a clear error.
- **Translation outdated handling:** When source (default-language) news article or wiki translation content is updated, other-language translations are marked outdated and `source_version` is set. Wiki: `upsert_wiki_page_translation` update path now sets `source_version` on the edited translation and marks all other languages for that page outdated (deterministic, regression-tested).
- **Regression tests:** `tests/test_security_and_correctness.py` for wiki sanitizer, password change (including missing current_password), generic user update rejecting password fields, news slug detail, CSV formula neutralization, security headers, wiki slug uniqueness, translation outdated marking, wiki update marking other translations outdated, verification/reset email not logging tokens or URLs. `tests/test_config.py`: secret-key required when not TESTING (including empty SECRET_KEY).

### Changed

- **Password not in generic user update:** Generic `PUT /api/v1/users/<id>` rejects requests that include `password` or `current_password` with 400 and a message to use `PUT /api/v1/users/<id>/password`. Password changes only via that dedicated endpoint (self, with current password).
- **Activation and reset links not logged:** In dev/TESTING mail fallback, verification and password-reset flows log that a link was sent but do not log the URL or token.
- **Frontend secret:** Frontend requires `SECRET_KEY` unless `FLASK_ENV=development` or `DEV_SECRETS_OK` is set; then a one-off random key is used and a warning is printed.

### Fixed

- **News detail by slug:** `get_news_by_slug` was missing from news route imports; `GET /api/v1/news/<slug>?lang=` now works; invalid slug returns 404.

---

## [0.0.11] - 2026-03-11

### Added

- **Documentation:** `docs/architecture/MultilingualArchitecture.md` – supported languages (de, en), default and fallback, translation statuses, roles, backend–n8n contract, public vs editorial routes.
- **User:** Field `preferred_language` (migration 010). Config `SUPPORTED_LANGUAGES`, `DEFAULT_LANGUAGE`. Module `app/i18n.py` for language validation and status constants.
- **News (new model):** Tables `news_articles` and `news_article_translations` (title, slug, summary, content, translation_status, etc.). Migration 011 with data migration from `news`, then drop of `news`. Public list/detail support `?lang=` and fallback; detail by id or slug.
- **Wiki (new model):** Tables `wiki_pages` and `wiki_page_translations` (key, slug, content_markdown, translation_status). Migration 012; seed from `Backend/content/wiki.md`. Backend `/wiki` serves from DB with file fallback. Public `GET /api/v1/wiki/<slug>?lang=`.
- **API – auth/users:** `GET /api/v1/auth/me` and user update expose `preferred_language`. `GET /api/v1/languages` (supported + default), `PUT /api/v1/users/<id>/preferences` (preferred_language). User update validates preferred_language.
- **API – news editorial:** `GET/PUT /api/v1/news/<id>/translations`, `GET/PUT .../translations/<lang>`, `POST .../submit-review`, `.../approve`, `.../publish`, `POST .../translations/auto-translate`. List with `include_drafts=1` returns `translation_statuses` and `default_language` per article.
- **API – wiki editorial:** `GET/POST/PUT /api/v1/wiki-admin/pages`, `GET/PUT .../pages/<id>/translations/<lang>`, `POST .../submit-review`, `.../approve`, `.../publish`, `POST .../translations/auto-translate`. Legacy `GET/PUT /api/v1/wiki` (file) unchanged.
- **n8n:** Config `N8N_WEBHOOK_URL`, `N8N_WEBHOOK_SECRET`, `N8N_SERVICE_TOKEN`. On auto-translate (News/Wiki), backend POSTs webhook events `news.translation.requested` / `wiki.translation.requested` (article_id/page_id, target_language, source_language). Optional HMAC-SHA256 in `X-Webhook-Signature`. `app/n8n_trigger.py` for signing and sending.
- **n8n service auth:** Header `X-Service-Key` accepted on GET/PUT for news and wiki translations (alongside JWT). Service writes forced to `machine_draft`. Decorator `require_editor_or_n8n_service`. `docs/n8n/README.md` for setup, payloads, signature, idempotency.
- **Audit:** `log_activity` for translation actions submit-review, approve, publish (news and wiki).
- **Frontend – UI i18n:** `Frontend/translations/de.json` and `en.json`. Language resolution: `?lang=` → session → Accept-Language → default `de`. Context: `current_lang`, `t`, `frontend_config.currentLanguage`. Base template: nav, footer, skip-link, language switcher (DE/EN). News/wiki and manage use `t` for labels.
- **Frontend – public wiki:** Routes `/wiki` and `/wiki/<slug>`. Template `wiki_public.html` fetches `GET /api/v1/wiki/<slug>?lang=` and renders content.
- **Frontend – manage news (multilingual):** List with DE/EN status columns (badges); filters search, category, status, language, sort, direction. Editor: shared category/cover; language tabs (DE/EN) with title, slug, summary, content; Save, Request review, Approve, Publish translation, Publish article, Unpublish, Auto-translate, Delete. New article creates default-language translation.
- **Frontend – manage wiki (multilingual):** Page list, New page, select page loads translations. Language tabs DE/EN with markdown editor and preview; Save, Request review, Approve, Publish translation, Auto-translate.
- **Frontend – user admin:** Users table column Lang (`preferred_language`). Edit form: Preferred language (— default — / de / en); save via PUT. No password or hash fields.

### Changed

- **News:** Replaced single `news` table with `news_articles` + `news_article_translations`; public API uses `?lang=` and fallback.
- **Wiki:** Content from DB (`wiki_pages` + `wiki_page_translations`) with file fallback; public wiki API by slug and language.
- **Validation:** Language codes validated via `normalize_language` in routes and services; translation upserts one row per entity+language (no duplicates).

---

## [0.0.10] - 2026-03-11

### Added

- **Management area (Frontend):** Protected editorial and admin area at `/manage` (login at `/manage/login`). JWT-based auth: login form calls backend `POST /api/v1/auth/login`; token stored in `sessionStorage`; central `ManageAuth.apiFetchWithAuth()` attaches `Authorization: Bearer <token>` and redirects to login on 401. Current user bootstrapped via `GET /api/v1/auth/me`; username and role shown in header; logout clears token. Role-based nav: Users link visible only to admin.
- **News management UI:** `/manage/news` – list with pagination, search, category and published/draft filters, sort; row selection; create/edit form (title, slug, summary, content, category, cover_image, is_published); publish, unpublish, delete with confirmation; uses existing news API (list with `include_drafts=1` for staff, get/create/update/delete/publish/unpublish).
- **User administration UI:** `/manage/users` (admin only) – table with pagination and search; select row for detail panel; edit username, email, role (no password fields); ban (optional reason), unban, delete with confirmation. Uses `GET/PUT/DELETE /api/v1/users`, `PATCH .../role`, `POST .../ban`, `POST .../unban`.
- **Wiki editing:** Backend `GET /api/v1/wiki` and `PUT /api/v1/wiki` (moderator or admin). Read returns `{ content, html }` from `Backend/content/wiki.md`; write updates the file with optional activity logging. Frontend `/manage/wiki` – load source, textarea editor, client-side preview (marked.js), save; unsaved-changes handling. Public wiki view (`Backend /wiki`) unchanged.
- **Docs:** Management routes, frontend auth (sessionStorage, apiFetchWithAuth, /auth/me), and wiki API described in `docs/runbook.md` and `README.md` where relevant.

---

## [0.0.9] - 2026-03-11

Release 0.0.9 focuses on the new role and access-control model (user/moderator/admin), admin-only user management and bans, moderator/admin news permissions, blocked-user UX, and updated Postman and test coverage.

### Added

- **Wiki page:** Dedicated view at `/wiki`, reachable via the "Wiki" button in the header. Content is loaded from the Markdown file `Backend/content/wiki.md` and rendered to HTML with the Python `markdown` library (extension "extra"); if the file is missing, "Coming soon" is shown. New stylesheet `app/static/wiki.css` for wiki prose; template `wiki.html` extends `base.html`. Dependency `markdown>=3.5,<4` in `requirements.txt`. Test: `test_wiki_returns_200` in `test_web.py`.
- **Startup mode log:** On backend startup, a single line is always logged indicating the current mode: `Running BLACKVEIN Backend [mode: TESTING]`, `[mode: NORMAL (MAIL_ENABLED=1)]`, or `[mode: DEV (MAIL_ENABLED=0)]` (`app/__init__.py`).

### Changed

- **Email verification (dev):** When `MAIL_ENABLED=0` or `TESTING=True`, the activation link is logged at WARNING level on register/resend ("DEV email verification mode (...). Activation URL for 'user': ...") so it appears in the same terminal as HTTP logs (`app/services/mail_service.py`).

---

## [0.0.8] - 2025-03-10

### Added

- **User CRUD API:** Full CRUD for users at `/api/v1/users`: `GET /api/v1/users` (list, admin only, paginated with `page`, `limit`, `q`), `GET /api/v1/users/<id>` (single user, admin or self), `PUT /api/v1/users/<id>` (update, admin or self; body: optional `username`, `email`, `password`, `current_password`, `role` admin only), `DELETE /api/v1/users/<id>` (admin only). Service layer: `get_user_by_id`, `list_users`, `update_user`, `delete_user` in `user_service.py`; permissions `get_current_user()` and `current_user_is_admin()` in `app.auth.permissions`. On delete: user's news keep `author_id=None`; reset and verification tokens are removed.
- **User model:** `to_dict(include_email=False)` extended; auth responses (login, me) include `email` for the current user when requested.
- **BackendApi.md:** Section **4. Users (CRUD)** with all endpoints, query/body parameters and response formats; section 5 (General) renumbered.
- **Postman:** "Users" folder in the collection: Users List (admin), Users Get (self), Users Update (self), Users Get (404), Users Delete (admin, uses `target_user_id`). Variable `target_user_id` in collection and environments; Users List sets it to another user for Delete. `postman/README.md` and collection description updated for users and admin usage.
- **Runbook:** All commands documented in **two forms** (short `flask` / Python form `python -m flask`) and for **PowerShell** as well as **Bash/Terminal**. Table "Further useful commands" (migrations, stamp, seed-dev-user, seed-news, pytest). API flow with curl examples for Bash and PowerShell. Troubleshooting: `&&` in PowerShell, `flask` not found ? `python -m flask`.

### Changed

- **Config:** `MAIL_USE_TLS` default changed from `True` to `False` (local SMTP without TLS).
- **Auth API:** Login and Me responses include `email` for the logged-in user.

---

## [0.0.7] - 2025-03-10

### Added

- **Email verification on registration:** New users must verify their email before they can log in (web session and API JWT). After registration (web and API), a time-limited activation token is created and a verification email is sent (or only logged in dev when MAIL_ENABLED is off). Activation URL: `/activate/<token>`; validity configurable via `EMAIL_VERIFICATION_TTL_HOURS` (default 24).
- **User model:** Column `email_verified_at` (nullable DateTime); migration `005_add_email_verified_at`.
- **EmailVerificationToken:** New model and table `email_verification_tokens` (token_hash, user_id, created_at, expires_at, used_at, invalidated_at, purpose, sent_to_email); migration `006_email_verification_tokens`. Token creation as with password reset (secrets.token_urlsafe(32), SHA-256 hash).
- **Service layer:** `create_email_verification_token`, `invalidate_existing_verification_tokens`, `get_valid_verification_token`, `verify_email_with_token` in `user_service.py`. `send_verification_email` in `mail_service.py` (uses `APP_PUBLIC_BASE_URL` or url_for for activation link; when MAIL_ENABLED=False or TESTING, only logs).
- **Web registration:** After successful registration, redirect to `/register/pending` with instructions to check email; token is created and verification email sent.
- **New web routes:** `GET /register/pending`, `GET /activate/<token>`, `GET/POST /resend-verification` (generic success message, no user enumeration; existing tokens invalidated). Templates: `register_pending.html`, `resend_verification.html`.
- **Login enforcement:** Web login and `require_web_login`: users with email but no `email_verified_at` cannot log in (session not set or cleared, flash message). API `POST /auth/login`: for unverified email returns 403 with `{"error": "Email not verified."}`.
- **Config:** `MAIL_ENABLED`, `MAIL_USE_SSL`, `APP_PUBLIC_BASE_URL`, `EMAIL_VERIFICATION_TTL_HOURS` in `app/config.py`. Existing mail config (MAIL_SERVER, MAIL_PORT, etc.) unchanged.
- **Tests:** `test_register_post_success_redirects_to_pending`, `test_register_pending_get_returns_200`, `test_activate_valid_token_redirects_to_login`, `test_login_blocked_for_unverified_user`, `test_resend_verification_get_returns_200`, `test_login_unverified_email_returns_403`. Fixture `test_user_with_email` sets `email_verified_at` so reset/login tests keep working. Audit doc `Backend/docs/PHASE1_AUDIT_0.0.7.md`.
- **Postman:** Full test environment and test suite: two environments ("World of Shadows ? Local", "World of Shadows ? Test") with `baseUrl`, `apiPath`, `username`, `password`, `email`, `access_token`, `user_id`, `news_id`, `register_username`, `register_email`, `register_password`. Collection with test scripts for all requests: Auth (Register, Login, Login invalid, Me, Me no token), System (Health, Test Protected), News (List, Detail, Detail 404). Assertions for status codes and response body; Login sets token and `user_id`, News List sets `news_id`. `postman/README.md` with instructions (import, variables, Collection Runner).

### Changed

- **Registration (web):** Redirect after success changed from login to `/register/pending`.
- **Registration (API):** After `create_user`, verification tokens are created and email sent; login remains blocked with 403 until verification.

---

## [0.0.6] - 2025-03-10

### Added

- **Developer workflow and documentation:** `docker-compose.yml` updated for the Frontend/Backend split: two services, `backend` (build from Backend/, port 8000, Gunicorn) and `frontend` (build from Frontend/, port 5001). Backend sets `CORS_ORIGINS=http://localhost:5001,http://127.0.0.1:5001`; frontend sets `BACKEND_API_URL=http://localhost:8000` so the browser can call the API. `Frontend/requirements.txt` (Flask) and `Frontend/Dockerfile` added for the compose build. `README.md` rewritten: repository structure (Backend + Frontend), prerequisites, env vars (with table), **run workflow** (backend: `cd Backend`, `pip install -r requirements.txt`, `flask init-db`, `flask db upgrade`, optional `flask seed-dev-user` / `flask seed-news`, `python run.py` or `flask run`; frontend: `cd Frontend`, `pip install -r requirements.txt`, `python frontend_app.py`), **migrations** (`flask db upgrade` / `flask db revision` from Backend/), **tests** (`pytest` from Backend/), **Docker** (`docker compose up --build`, backend 8000, frontend 5001), and links to `docs/development/LocalDevelopment.md`, architecture, runbook, security, Backend tests README. No vague docs; commands and structure match the current repo.
- **Backend tests for news API and split:** New `Backend/tests/test_news_api.py` (19 tests): news list JSON shape and item fields; news detail JSON and 404 for missing/draft; search (q), sort (sort/direction), pagination (page/limit), category filter; published-only visibility (list excludes drafts, detail returns 404 for draft); anonymous write (POST/PUT/DELETE without token ? 401); authenticated user with role=user (POST/PUT ? 403); editor (role=editor) write (POST 201, PUT 200, publish 200, DELETE 200). Fixtures in `conftest.py`: `editor_user`, `editor_headers`, `sample_news` (two published, one draft). `Backend/tests/README.md` updated. News detail route fixed to handle timezone-naive `published_at` from SQLite (compare with UTC when needed). All 64 Backend tests pass; test paths remain under `Backend/tests/`.
- **Frontend?backend connectivity:** Backend API base URL is centralized: Frontend reads it only from `BACKEND_API_URL` (env) ? Flask `inject_config()` ? `window.__FRONTEND_CONFIG__.backendApiUrl`. `main.js` is loaded in `base.html` and exposes `FrontendConfig.getApiBaseUrl()` and `FrontendConfig.apiFetch(pathOrUrl, opts)`. `apiFetch` builds the full URL from the base + path, sends `Accept: application/json`, and returns a Promise that resolves with parsed JSON or rejects with an error message string (network, 4xx/5xx, or invalid JSON). News list and detail use `FrontendConfig` and `apiFetch` for all backend calls. CORS: when Frontend and Backend run on different origins (e.g. Frontend :5001, Backend :5000), set `CORS_ORIGINS=http://127.0.0.1:5001,http://localhost:5001` so the browser allows API requests; documented in `.env.example`. `docs/development/LocalDevelopment.md` describes default URLs (Backend 5000, Frontend 5001), startup flow, how Frontend and Backend talk (single API URL source, apiFetch, CORS), and optional seed commands.
- **Seed/example news:** `flask seed-news` (requires `DEV_SECRETS_OK=1`) creates a small set of example news entries for development and validation. Themes: project announcement, backend/frontend split (development), news system live (features), World of Blackveign (lore), API and CORS setup (technical), and one draft (Upcoming Events). Categories: Announcements, Development, Features, Lore, Technical. Five published and one draft so list/detail, search, sort, and category filter can be tested. Author is set from the first user if any. Skips slugs that already exist. Data is loaded by running the CLI once after `flask init-db` (and optionally `flask seed-dev-user`).
- **Frontend news detail page:** `Frontend/templates/news_detail.html` and `Frontend/static/news.js` (loadDetail) implement the public article view. Page is directly addressable at `/news/<id>`; JS fetches `GET /api/v1/news/<id>` and renders title, date (published_at/created_at), summary (if present), full content, author and category in meta line, and back link to news list. No placeholder content; loading and error states only. Document title updates to "Article title ? World of Shadows" when the article loads. Styling: `.news-detail-content .summary`, `.back-link-top`/`.back-link-bottom`, focus-visible on back link.
- **Frontend news list page:** `Frontend/templates/news.html` and `Frontend/static/news.js` implement the public news list with backend API consumption only (no DB). List shows title, summary, published date, category, and link to detail. Controls: search (q), sort (published_at, created_at, updated_at, title), direction (asc/desc), category filter, Apply button; Enter in search/category triggers apply. Pagination: Previous/Next and "Page X of Y (total)"; hidden when a single page. States: loading, empty ("No news yet"), error. Styling in `styles.css`: `.news-controls`, `.news-input`, `.news-select`, `.news-item-summary`, `.news-item-meta`, `.news-pagination`; WoS design tokens. Entry point: `NewsApp.initList()`.
- **Public frontend base and homepage:** `Frontend/templates/base.html` is the common public layout with semantic header (nav: News, Wiki, Community, Log in, Register, Dashboard), skip-link for accessibility, main content area, and footer. `Frontend/templates/index.html` is the public homepage with hero (Blackveign tagline, Get started / Sign in / News CTAs) and an "Explore" card grid linking to News, Log in, Register, and Dashboard. All auth/dashboard links point to the backend (`BACKEND_API_URL`). `Frontend/static/styles.css` includes World of Shadows design tokens (void/violet, Inter, JetBrains Mono), header/nav/footer styles, hero and card grid, focus-visible for keyboard users, and styles shared with news pages. `Frontend/static/main.js` exposes `FrontendConfig.getApiBaseUrl()` for API consumption. No server-side DB; frontend is static/JS-driven and production-oriented.
- **Permission groundwork for news write:** User model has a `role` column (`user`, `editor`, `admin`). Only `editor` and `admin` may call the protected news write API (POST/PUT/DELETE/publish/unpublish); others receive 403 Forbidden. Helper `current_user_can_write_news()` in `app.auth.permissions` and `User.can_write_news()` centralise the check; news write routes use the helper after `@jwt_required()`. Migration `004_add_user_role` adds `role` with server default `editor` for existing users; new registrations get `user`; `flask seed-dev-user` creates users with `editor` so dev can write news.
- **News service layer:** `Backend/app/services/news_service.py` with `list_news` (published_only, search, sort, order, page, per_page, category), `get_news_by_id`, `get_news_by_slug`, `create_news`, `update_news`, `delete_news`, `publish_news`, `unpublish_news`. Filtering, sorting, pagination, and slug validation live in the service; route handlers stay thin. Exported from `app.services`.
- **Public news API:** `GET /api/v1/news` (list) and `GET /api/v1/news/<id>` (detail). List supports query params: `q` (search), `sort`, `direction`, `page`, `limit`, `category`. Only published news is returned; drafts/unpublished return 404 on detail. Response: list `{ "items", "total", "page", "per_page" }`, detail single news object. Uses news service; rate limit 60/min.
- **Protected news write API:** `POST /api/v1/news`, `PUT /api/v1/news/<id>`, `DELETE /api/v1/news/<id>`, `POST /api/v1/news/<id>/publish`, `POST /api/v1/news/<id>/unpublish`. All require `Authorization: Bearer <JWT>` and editor/admin role; 401 without or invalid token, 403 for forbidden. Author for create set from JWT identity. Handlers delegate to news_service; rate limit 30/min per write endpoint.

---

## [0.0.5] - 2025-03-10

### Added

- **Architecture audit:** Implementation note `docs/architecture/FrontendBackendRestructure.md` defining the target Backend/Frontend split. World of Shadows is to be restructured into `Backend/` (app, instance, migrations, tests, run.py, API, auth, dashboard) and `Frontend/` (frontend_app.py, public templates, static, API consumption). MasterBlogAPI used only as reference for separation and API-first content delivery; existing auth and branding preserved. Real news system will be implemented in Backend (model + API) with frontend consuming JSON; no file moves in this audit step.
- **Backend/Frontend restructure:** Repository split into `Backend/` and `Frontend/`. Backend now contains `app/`, `migrations/`, `tests/`, `run.py`, `requirements.txt`, `requirements-dev.txt`, `Dockerfile`, `pytest.ini`, `.dockerignore`; run and test from `Backend/` with `FLASK_APP=run:app`. New `Frontend/` has `frontend_app.py`, `templates/`, `static/` (placeholder only). Root keeps `README.md`, `CHANGELOG.md`, `docker-compose.yml`, `docs/`, `.env.example`. Docker build context is `Backend/`; compose mounts `Backend/instance`. No news system yet; structure only.
- **Frontend application:** Lightweight Flask public frontend in `Frontend/`: `frontend_app.py` with home (`/`), news list (`/news`), news detail (`/news/<id>`); templates `base.html`, `index.html`, `news.html`, `news_detail.html`; static `styles.css`, `main.js`, `news.js`. Config via `BACKEND_API_URL` (default `http://127.0.0.1:5000`) for login/wiki/community links and for JS to call backend API. No database; news data will be loaded by JS from backend API (graceful empty/404 until news API exists). Styling aligned with World of Shadows (void/violet, Inter, JetBrains Mono). Run from `Frontend/` with `python frontend_app.py` (port 5001).
- **News model:** `Backend/app/models/news.py` with id, title, slug (unique), summary, content, author_id (FK users), is_published, published_at, created_at, updated_at, cover_image, category; migration `003_news` adds `news` table.

### Changed

- **Routing responsibility split:** Backend serves only auth and internal flows (login, register, forgot/reset-password, dashboard, game-menu, wiki/community placeholders). When `FRONTEND_URL` is set, backend redirects `GET /` and `GET /news` to the frontend so the public home and news are served only by the frontend; logout redirects to frontend home. Backend keeps legacy `home.html`/`news.html` when `FRONTEND_URL` is unset (e.g. tests, backend-only deployment). No duplicate public news; config documented in `.env.example` and `docs/architecture/FrontendBackendRestructure.md`.
- **Backend stabilization (post-move):** When running from `Backend/`, config now also loads `.env` from repo root so a single `.env` at project root works. Documented that the database instance path is `Backend/instance` when run from Backend. Imports, migration path, pytest discovery, and Docker/startup unchanged and verified; all 45 tests pass from `Backend/`.
- **Config:** Single `TestingConfig`; removed duplicate. `FRONTEND_URL` (optional) for redirecting public home/news to frontend.

### Security

- **Open redirect:** Login no longer redirects to external URLs. `is_safe_redirect()` in `app/web/auth.py` allows only path-only URLs (no scheme, no netloc). `next` query param is ignored when unsafe; fallback to dashboard.

---

## [0.0.4] - 2025-03-10

### Added

- **Landing page:** Aetheris-style hero (eyebrow, title, subtitle, CTAs), benefits grid, scrolling ticker, features section, void footer, fixed command dock. Design tokens (void, violet, mono/display fonts, transitions) and Google Fonts (Inter, JetBrains Mono). `landing.js`: hero cursor shear, feature reveal on scroll, benefit counters, smooth scroll for dock links, preload with IntersectionObserver; reduced-motion respected.
- **Dashboard:** Two-column layout (sidebar left, content right). Sidebar sections: User (User Settings), Admin (Overview, Metrics, Logs). User Settings: form for name and email with "Save Changes" (client-side confirmation). Metrics view: metric cards, revenue/user charts (Chart.js), threshold config with localStorage and breach alerts. Logs view: filterable activity table, CSV export. Overview: short description of sections. Content area fills available height with internal scroll.
- **Header navigation:** "Log in" removed. New nav links: News, Wiki, Community (each with placeholder page). When logged in: "Enter Game" between News and Wiki, linking to protected `/game-menu` (Game Menu placeholder page).
- **Base template:** Optional blocks for layout variants: `html_class`, `body_class`, `extra_head`, `site_header`, `site_main`, `flash_messages`, `content`, `site_footer`, `extra_scripts`. Header and footer kept by default; landing overrides only `site_main`.

### Changed

- **Config / styles:** Extended `:root` with violet/void tokens and font variables. Landing and dashboard CSS appended; responsive breakpoints for hero, benefits, features, dock and dashboard grid.

---

## [0.0.3] - 2025-03-10

### Security

- **Secrets:** Removed hardcoded fallback secrets from production config. `SECRET_KEY` and `JWT_SECRET_KEY` must be set in the environment. App raises at startup if `SECRET_KEY` is missing (unless testing or `DEV_SECRETS_OK=1`).
- **Dev-only fallback:** Added `DevelopmentConfig` and `DEV_SECRETS_OK` env var. When set, dev fallback secrets are used and `flask seed-dev-user` is allowed. Not for production.
- **Default user seeding removed:** `flask init-db` only creates tables; it no longer creates an admin/admin user. Use `flask seed-dev-user` with `DEV_SECRETS_OK=1` for local dev only.
- **Logout:** Web logout is POST only. Logout link replaced with a form and CSRF token to reduce abuse.
- **CSRF:** Web forms (login, logout) protected with CSRF. API blueprint exempt; API remains JWT-based.
- **CORS:** Origins are configurable via `CORS_ORIGINS` (comma-separated). No CORS when unset (same-origin only).
- **Session cookies:** `SESSION_COOKIE_HTTPONLY` and `SESSION_COOKIE_SAMESITE` set explicitly; `SESSION_COOKIE_SECURE` when `PREFER_HTTPS=1`.

### Added

- **Web auth:** Protected route `/dashboard`; central `require_web_login` decorator in `app/web/auth.py`. Anonymous access to `/dashboard` redirects to `/login`.
- **Login flow:** If already logged in, GET `/login` redirects to dashboard. Optional `next` query param for redirect-after-login.
- **Dashboard template:** `app/web/templates/dashboard.html`.
- **CLI:** `flask seed-dev-user` to create a default admin user when `DEV_SECRETS_OK=1`.
- **Documentation:** `README.md` (purpose, structure, setup, env, web/API usage). `docs/runbook.md` (local workflow, example API flow). `docs/security.md` (auth model, CSRF, CORS, cookies, dev-only behavior).

### Changed

- **Config:** `SECRET_KEY`, `JWT_SECRET_KEY` from env only in base config. Added `CORS_ORIGINS`, explicit session cookie settings. `DevelopmentConfig` and `TestingConfig` separated.
- **Startup:** Debug mode driven by `FLASK_DEBUG` instead of `FLASK_ENV`.
- **API:** User lookup uses `db.session.get(User, id)` (SQLAlchemy 2.x) instead of `User.query.get(id)`.
- **Web health:** Docstring aligned: returns JSON status.
- **.env.example:** Updated with required vars, `CORS_ORIGINS`, `FLASK_DEBUG`, `DEV_SECRETS_OK`.

### Removed

- **Default admin from init-db:** No automatic admin/admin creation.
- **Empty layer:** Removed unused `app/repositories/` package.

### Documentation

- README.md: project purpose, scope, structure, setup, environment table, web/API usage, limitations, links to runbook and security.
- docs/runbook.md: one-time setup, start server, web flow, API curl examples, health checks, troubleshooting.
- docs/security.md: session vs JWT auth, CSRF scope, secrets and dev fallback, default users, CORS, session cookies, rate limiting.

---

## [0.0.2] - 2025-03-10

### Added

- **Test suite:** Pytest tests for web and API (19 tests), in-memory DB config, pytest.ini, pytest and pytest-cov in requirements.
- **Planning docs:** Milestone list and execution prompts for staged rebuild (no code changes).

---

## [0.0.1] - 2025-03-10

### Added

- **Server foundation**
  - Flask application factory (`app/__init__.py`) with config loading from environment.
  - Central config (`app/config.py`) for `SECRET_KEY`, database URI, JWT, session cookies, and rate limiting.
  - Extensions module (`app/extensions.py`): SQLAlchemy, Flask-JWT-Extended, Flask-Limiter, Flask-CORS.
  - Single entrypoint `run.py`; no separate backend/frontend apps.

- **Database**
  - SQLite as default database (configurable via `DATABASE_URI`).
  - User model (`app/models/user.py`): `id`, `username`, `password_hash`.
  - CLI command `flask init-db` to create tables and optionally seed a default admin user.

- **Web (server-rendered)**
  - Blueprint `web`: routes for `/`, `/health`, `/login`, `/logout`.
  - Session-based authentication for browser users.
  - Templates: `base.html`, `home.html`, `login.html`, `404.html`, `500.html`.
  - Static assets: `app/static/style.css` (World of Shadows theme).

- **API (REST v1)**
  - Versioned API under `/api/v1`.
  - **Auth:** `POST /api/v1/auth/register`, `POST /api/v1/auth/login` (returns JWT), `GET /api/v1/auth/me` (protected).
  - **System:** `GET /api/v1/health`, `GET /api/v1/test/protected` (protected).
  - JWT authentication for API; CORS and rate limiting enabled.
  - Consistent JSON error responses for 401 and 429.

- **Tooling and docs:** requirements.txt, .env.example, Postman collection for API testing.

### Technical notes

- No movie or blog domain logic; foundation only.
- Code and identifiers in English.
- `.gitignore` updated (instance/, *.db, .env, __pycache__, etc.).
- Server foundation: Flask app factory, config, extensions (db, jwt, limiter, CORS), single entrypoint run.py.
- Database: SQLite default, User model, flask init-db.
- Web: Blueprint with home, health, login, logout; session auth; templates and static.
- API: /api/v1 health, auth (register, login, me), protected test route; JWT and rate limiting.
- Tooling and docs: requirements.txt, .env.example, Postman collection for API testing.
