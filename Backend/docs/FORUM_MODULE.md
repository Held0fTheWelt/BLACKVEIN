# Forum module (0.0.19)

## Boundaries and entities

- **Module scope:** Discussion forum for the community (and staff) with categories, threads, posts, likes, and moderation.
- **Backend:** Own models, services, and API routes under `app.models.forum_*`, `app.services.forum_service`, `app.api.v1.forum_routes`.
- **Frontend:** Public pages under `administration-tool/templates/forum/` and admin/moderation under `administration-tool/templates/manage/forum_*` with JS in `administration-tool/static/`.

Entities:

- `forum_categories`: top-level grouping of threads.
- `forum_threads`: discussion topics inside a category.
- `forum_posts`: individual messages in a thread (flat or shallow replies via `parent_post_id`).
- `forum_post_likes`: per-user likes on posts.
- `forum_reports`: user reports on threads or posts.
- `forum_thread_subscriptions` (optional): user follows on threads (for future notifications).

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
  - Hide/unhide posts.
  - Lock/unlock threads.
  - Pin/unpin threads.
  - Review and update `forum_reports` for accessible categories.
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
  - Lock/unlock, pin/unpin threads.
  - Hide/unhide posts.
  - Change report statuses (`open`, `reviewed`, `resolved`, `dismissed`).
  - Access full report lists and details.
- Regular users may:
  - File reports on threads or posts they can see.
  - Not see internal report handling details.
- Reports:
  - `target_type`: `thread` or `post`.
  - `status`: `open` (new), `reviewed` (seen but not resolved), `resolved` (action taken), `dismissed` (no action needed).

Moderation and admin actions should be logged via the existing activity log service where appropriate (e.g. category changes, locks, hides).

## API contracts (high-level)

Public/community:

- `GET /api/v1/forum/categories` → list visible categories.
- `GET /api/v1/forum/categories/<slug>` → category detail (+ limited stats).
- `GET /api/v1/forum/categories/<slug>/threads` → paginated threads in category.
- `GET /api/v1/forum/threads/<slug>` → thread detail.
- `GET /api/v1/forum/threads/<id>/posts` → paginated posts for thread.
- `GET /api/v1/forum/search` → search threads (and optionally posts).

Authenticated:

- Thread CRUD: `POST/PUT/DELETE /api/v1/forum/threads[...]` with permission checks.
- Post CRUD: `POST/PUT/DELETE /api/v1/forum/posts[...]` with permission checks.
- Likes: `POST/DELETE /api/v1/forum/posts/<id>/like`.
- Reports: `POST /api/v1/forum/reports`.

Moderator/admin:

- Thread moderation: lock/unlock, pin/unpin.
- Post moderation: hide/unhide.
- Reports: list + update status.
- Category admin: create/edit/delete categories.

All endpoints will follow existing API conventions: JSON bodies, error structures with `{"error": "..."} ` or typed issues, and pagination fields (`items`, `total`, `page`, `per_page`).

