# Forum module (0.0.27)

## Boundaries and entities

- **Module scope:** Discussion forum for the community (and staff) with categories, threads, posts, likes, and moderation.
- **Backend:** Own models, services, and API routes under `app.models.forum_*`, `app.services.forum_service`, `app.api.v1.forum_routes`.
- **Frontend:** Public pages under `administration-tool/templates/forum/` and admin/moderation under `administration-tool/templates/manage/forum_*` with JS in `administration-tool/static/`.

Entities:

- `forum_categories`: top-level grouping of threads.
- `forum_threads`: discussion topics inside a category.
- `forum_posts`: individual messages in a thread (flat or shallow replies via `parent_post_id`).
- `forum_post_likes`: per-user likes on posts.
- `forum_reports`: user reports on threads or posts. Includes `resolution_note TEXT` (nullable) for moderator remarks.
- `forum_thread_subscriptions`: user follows on threads (triggers notifications on new replies).
- `forum_thread_bookmarks`: user-saved threads (visible only to the bookmarking user).
- `forum_tags`: normalized tag slugs with human-readable labels.
- `forum_thread_tags`: many-to-many link between threads and tags.

## Roles and behavior

Roles reuse existing system roles:

- **Public (anonymous):**
  - View public categories, threads, and visible posts (no posting/liking).
- **Authenticated user (role=user/qa/moderator/admin):**
  - View all non-private categories plus any private categories where `required_role` <= own role.
  - Create threads in categories that are active, not private beyond their role, and not restricted to staff.
  - Create posts in open, unlocked threads within accessible categories.
  - Edit own posts (time-window or status based; initial policy: always allowed until post is hidden/deleted).
  - Soft-delete own posts if they are not already moderated (status becomes `deleted` and `deleted_at` set).
  - Like/unlike visible posts in unlocked threads.
  - Report threads/posts.
- **Moderator (role=moderator):**
  - All authenticated user capabilities.
  - Hide/unhide posts (including bulk hide/unhide via `POST /forum/moderation/bulk-posts/hide`).
  - Lock/unlock threads (including bulk lock/unlock via `POST /forum/moderation/bulk-threads/status`).
  - Pin/unpin, archive/unarchive, move threads between categories.
  - Merge threads (`POST /forum/threads/<source>/merge`).
  - Split threads from a top-level post (`POST /forum/threads/<id>/split`).
  - Review and update `forum_reports` (statuses: `open`, `reviewed`, `escalated`, `resolved`, `dismissed`), with optional `resolution_note`.
  - Bulk update report status (`POST /forum/reports/bulk-status`) with optional `resolution_note`.
  - View moderation metrics, recent open reports, recently handled reports, locked threads, pinned threads, hidden posts via the Moderation Dashboard endpoints.
  - View moderation log (`GET /forum/moderation/log`) backed by activity logs filtered to `category=forum`.
  - Set tags on any thread.
  - Soft-delete/hide inappropriate content.
- **Admin (role=admin):**
  - Full forum control.
  - Create/edit/delete categories.
  - Configure `is_active`, `is_private`, `required_role`.
  - Access all private/staff categories.
  - All moderator actions across all categories.

Role-level (`role_level`) and areas are respected where they already apply to admin actions (e.g. category management screens behind appropriate features).

## Soft-delete and status

- Threads:
  - Fields: `status` (`open`, `locked`, `archived`, `hidden`, `deleted`), `deleted_at`.
  - Normal user deletion: soft-delete own threads where allowed (status `deleted`, `deleted_at` set, content hidden from public lists).
  - Moderation hides: set `status=hidden` without removing from DB.
  - Locked threads cannot receive new posts from regular users.
- Posts:
  - Fields: `status` (`visible`, `edited`, `hidden`, `deleted`), `deleted_at`.
  - Soft-delete: own deletion or moderator deletion sets `deleted_at` and `status=deleted`; content hidden from normal views.
  - Hidden: moderator hide sets `status=hidden` (e.g. for temporary removals).
  - Edited posts track `edited_at` and `edited_by`.

No hard-deletes for threads/posts in normal flows; only admins may have specific hard-delete endpoints if later required.

## Slugs and routing

- Categories:
  - `slug` unique; stable identifier for `/forum/categories/<slug>` both API and frontend.
- Threads:
  - `slug` unique across all threads; used for `/forum/threads/<slug>` (public) and `/api/v1/forum/threads/<slug>` (API).
  - Generated from title with collision handling by appending `-<short-id>` when needed.

Posts are referenced by numeric ID in API routes (no public slug).

## Pagination and search

- Pagination:
  - Category thread lists: `page`, `limit` query params (default sensible values; hard max per_page).
  - Thread post lists: same pagination parameters.
  - Stable ordering:
    - Threads: primarily by `is_pinned` desc, then `last_post_at` desc, then `created_at` desc.
    - Posts: by `created_at` asc (oldest first); moderation can affect visibility but not order.
- Search:
  - Endpoint `/api/v1/forum/search`:
    - Searches thread titles (and optionally post content) for a text query.
    - Returns paginated results with basic metadata.
  - Exact matching strategy kept simple (ILIKE `%query%` or equivalent).

## Moderation rules

- Only moderators/admins may:
  - Lock/unlock, pin/unpin, archive/unarchive, move threads.
  - Merge and split threads.
  - Hide/unhide posts (individually or in bulk).
  - Change report statuses and add a `resolution_note`.
  - Access full report lists (`GET /forum/reports?page&limit&status&target_type`).
  - Access the moderation dashboard and moderation log.
- Regular users may:
  - File reports on threads or posts they can see.
  - Not see internal report handling details.
- Reports:
  - `target_type`: `thread` or `post`.
  - `status`: `open` (new), `reviewed` (seen but not resolved), `escalated` (requires senior attention), `resolved` (action taken), `dismissed` (no action needed).
  - `resolution_note`: optional free-text stored by the moderator when updating status. Returned in all `to_dict()` outputs.
  - List endpoint supports pagination (`page`, `limit`) and filters (`status`, `target_type`). Response envelope: `{ items, total, page, limit }`.

Moderation and admin actions are logged via the activity log service (`category="forum"`). The moderation log endpoint exposes these entries to moderators and admins with text, status, and date filters.

## API contracts (high-level)

Public/community (JWT optional):

- `GET /api/v1/forum/categories` → list visible categories.
- `GET /api/v1/forum/categories/<slug>` → category detail (+ `thread_count`).
- `GET /api/v1/forum/categories/<slug>/threads?page&limit` → paginated threads. Response: `{ items, total, page, per_page }`. Thread objects include `author_username`, `bookmarked_by_me` (bool), and `tags` (array of label strings). Moderators/admins see hidden/archived threads via SQL-level filter.
- `GET /api/v1/forum/threads/<slug>` → thread detail, including `subscribed_by_me` flag and `tags` array (when tags exist).
- `GET /api/v1/forum/threads/<id>/posts?page&limit&include_hidden&include_deleted` → paginated posts. Each post includes `liked_by_me` flag when authenticated.
- `GET /api/v1/forum/search?q&page&limit&category&status&tag&include_content` → search threads (and optionally post content).

Authenticated (JWT required):

- Thread CRUD: `POST /api/v1/forum/categories/<slug>/threads`, `PUT /api/v1/forum/threads/<id>`, `DELETE /api/v1/forum/threads/<id>`.
- Post CRUD: `POST /api/v1/forum/threads/<id>/posts`, `PUT /api/v1/forum/posts/<id>`, `DELETE /api/v1/forum/posts/<id>`.
- Likes: `POST/DELETE /api/v1/forum/posts/<id>/like`.
- Subscriptions: `POST/DELETE /api/v1/forum/threads/<id>/subscribe`.
- Bookmarks: `POST/DELETE /api/v1/forum/threads/<id>/bookmark`, `GET /api/v1/forum/bookmarks?page&limit`.
- Tags: `PUT /api/v1/forum/threads/<id>/tags` (body `{ "tags": [...] }`). Author, moderator, or admin only.
- Reports: `POST /api/v1/forum/reports` (body `{ target_type, target_id, reason }`).

Moderator/admin:

- Thread moderation: lock/unlock, pin/unpin, archive/unarchive, move, merge, split, hide thread.
- Bulk thread operations: `POST /api/v1/forum/moderation/bulk-threads/status` (body `{ thread_ids, lock?, archive? }`).
- Post moderation: `POST /api/v1/forum/posts/<id>/hide`, `POST /api/v1/forum/posts/<id>/unhide`.
- Bulk post operations: `POST /api/v1/forum/moderation/bulk-posts/hide` (body `{ post_ids, hidden }`).
- Reports: `GET /api/v1/forum/reports?page&limit&status&target_type` → `{ items, total, page, limit }`. Each item includes `resolution_note`.
- Report update: `PUT /api/v1/forum/reports/<id>` (body `{ status, resolution_note? }`).
- Bulk report update: `POST /api/v1/forum/reports/bulk-status` (body `{ report_ids, status, resolution_note? }`).
- Tags: `GET /api/v1/forum/tags` (list all with thread counts; supports `q`, `page`, `limit`).
- Moderation dashboard: metrics, recent open reports, recently handled reports, locked threads, pinned threads, hidden posts.
- Moderation log: `GET /api/v1/forum/moderation/log?page&limit&q&status&date_from&date_to` → `{ items, total, page, limit }`.
- Category admin: `POST /api/v1/forum/admin/categories`, `PUT /api/v1/forum/admin/categories/<id>`, `DELETE /api/v1/forum/admin/categories/<id>`.

Admin only:

- `DELETE /api/v1/forum/tags/<id>` — delete unused tag (409 if in use by any thread).

All endpoints follow existing API conventions: JSON bodies, error structures `{"error": "..."}`, and pagination fields (`items`, `total`, `page`, `per_page` or `limit` depending on endpoint).

## Tag management

Tags are created implicitly when set on threads. Tag slugs are normalized from labels. The `GET /api/v1/forum/tags` endpoint returns each tag's `id`, `slug`, `label`, `thread_count`, and `created_at`. Tags cannot be deleted while any thread associations exist (409 Conflict).

## Thread list `bookmarked_by_me` and `tags` fields

Added in v0.0.27. The category thread list endpoint batch-loads bookmark state and tags for the current page. Anonymous requests always receive `bookmarked_by_me: false`. Tags are an array of label strings. SQL-level visibility filtering replaces the earlier Python-side THREAD_FETCH_CAP approach.

## Performance indexes (as of 0.0.27)

| Index name | Table | Columns | Purpose |
|---|---|---|---|
| `ix_forum_posts_status` | `forum_posts` | `status` | Post visibility filtering |
| `ix_forum_posts_thread_status` | `forum_posts` | `thread_id, status` | Thread detail post lists |
| `ix_forum_threads_status` | `forum_threads` | `status` | Thread listing visibility filter |
| `ix_notifications_user_is_read` | `notifications` | `user_id, is_read` | Unread notification queries |

Earlier migrations (026) added indexes on `forum_reports(status, created_at)` and
`forum_threads(category_id, is_pinned, last_post_at)`. Indexes for bookmarks and tags were
added in migration 025.

