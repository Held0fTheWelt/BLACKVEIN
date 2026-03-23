# Forum moderation workflow

Moderators and admins can use the following to triage and manage forum content.

## Moderation dashboard (`/manage/forum`)

When logged in as moderator or admin, the **Moderation dashboard** card appears at the top of the Forum management page.

- **Metrics:** Open reports count, hidden posts, locked threads, pinned threads.
- **Open reports:** Recent open reports with link to thread and quick actions (Reviewed, Resolved, Dismiss).
- **Recently handled:** Reports recently marked reviewed/resolved/dismissed.
- **Locked / Pinned / Hidden:** Expandable lists of locked threads, pinned threads, and hidden posts with links to the thread.

All dashboard data is moderator-only; endpoints require JWT with moderator or admin role.

## Key API endpoints (moderator/admin)

| Endpoint | Purpose |
|----------|--------|
| `GET /api/v1/forum/moderation/metrics` | Counts for dashboard |
| `GET /api/v1/forum/moderation/recent-reports?limit=10` | Open reports for action |
| `GET /api/v1/forum/moderation/recently-handled?limit=10` | Recently handled reports (status `reviewed` / `escalated` / `resolved` / `dismissed`) |
| `GET /api/v1/forum/moderation/locked-threads` | List locked threads |
| `GET /api/v1/forum/moderation/pinned-threads` | List pinned threads |
| `GET /api/v1/forum/moderation/hidden-posts` | List hidden posts |
| `PUT /api/v1/forum/reports/<id>` | Update report status (body: `{"status": "open"\|"reviewed"\|"escalated"\|"resolved"\|"dismissed"}`) |
| `POST /api/v1/forum/reports/bulk-status` | Bulk update status for multiple reports (body: `{"report_ids": [<int>...], "status": "reviewed"\|"escalated"\|"resolved"\|"dismissed"}`) |
| `GET /api/v1/forum/moderation/log` | Moderation/audit log for forum actions (`category=forum`), paginated |

## Bulk moderation actions

The moderation dashboard and admin tooling support a small set of safe bulk operations for staff:

- **Bulk thread status (lock/archive):**
  - Endpoint: `POST /api/v1/forum/moderation/bulk-threads/status`
  - Who: moderators/admins with rights on the affected categories.
  - Body: `{"thread_ids": [<int>...], "lock": true|false?, "archive": true|false?}`.
  - Behavior: applies lock/unlock and/or archive/unarchive to each thread the caller may moderate; skips others. All changes reuse the existing per-thread helpers (`set_thread_lock`, `set_thread_archived`, `set_thread_unarchived`).

- **Bulk post hide/unhide:**
  - Endpoint: `POST /api/v1/forum/moderation/bulk-posts/hide`
  - Who: moderators/admins with rights on the affected categories.
  - Body: `{"post_ids": [<int>...], "hidden": true|false}`.
  - Behavior: hides or unhides posts using the same rules as the single-post hide/unhide endpoints; counters and `last_post_*` are recalculated via the existing helpers.

- **Bulk report triage:**
  - Endpoint: `POST /api/v1/forum/reports/bulk-status`
  - Who: moderators/admins.
  - Body: `{"report_ids": [<int>...], "status": "reviewed"|"escalated"|"resolved"|"dismissed"}`.
  - Behavior: updates each existing report to the given status and records `handled_by` / `handled_at`. Invalid or missing IDs are skipped.

All bulk operations are logged via the central activity log (`category="forum"`) so they appear in both the admin logs and the dedicated forum moderation log.

## Thread moderation (public thread page)

On a thread page, moderators see a mod bar with:

- **Lock / Unlock** – Prevents new replies (except staff).
- **Pin / Unpin** – Pins thread at top of category list.
- **Archive / Unarchive** – Archives thread (staff-only visibility; no new posts from regular users).
- **Move…** – Move thread to another category (dropdown, then Move).
- **Merge…** – Merge the current thread into another thread (by ID or slug).

API:

- `POST /api/v1/forum/threads/<id>/lock` | `.../unlock`
- `POST /api/v1/forum/threads/<id>/pin` | `.../unpin`
- `POST /api/v1/forum/threads/<id>/archive` | `.../unarchive`
- `POST /api/v1/forum/threads/<id>/move` (body: `{"category_id": <int>}`)
- `POST /api/v1/forum/threads/<source_id>/merge` (body: `{"target_thread_id": <int>}`)

### Merge workflow

- **Who**: Moderators and admins with permission to moderate **both** the source and target thread categories.
- **What**: Move all posts and subscriptions from a source thread into a target thread, then archive the source thread so it is staff-only.
- **How (UI)**:
  - Open the source thread.
  - Click **Merge…** in the mod bar.
  - Enter the target thread **slug** or **ID**.
  - Confirm the irreversible merge prompt.
  - You are redirected to the merged target thread.
- **Safety**:
  - The source thread is marked `archived` after merge; its URL remains valid for staff but is no longer a live public discussion.
  - Reply structure is preserved because posts keep their original `parent_post_id`; only `thread_id` changes.
  - Counters (`reply_count`, `last_post_at`, `last_post_id`) are recalculated for both threads after the merge.

## Post moderation

- **Hide / Unhide** (per post): `POST /api/v1/forum/posts/<id>/hide` | `.../unhide` (moderator/admin for that category).

## Thread split (public thread page)

Moderators can split off a coherent sub-thread starting from a **top-level** post:

- **Who**: Moderators and admins for the thread’s category.
- **What**: Take one top-level post and its direct replies and move them into a new thread.
- **Limitations (by design)**:
  - You can only split from a **top-level** post (no parent). Attempts to split from a reply are rejected.
  - Only the root post and its **direct** replies move. Deeper trees are not supported in the current model.
  - The new thread is created with a moderator-provided title and lives in the original category unless a target category ID is specified (which must also be moderate‑able by the user).
- **How (UI)**:
  - On the thread page, each top-level post shows a **“Split to new thread”** action for moderators.
  - Click “Split to new thread”, confirm the prompt, and provide a new thread title.
  - The UI calls `POST /api/v1/forum/threads/<thread_id>/split` and redirects to the new thread on success.
- **API**:
  - `POST /api/v1/forum/threads/<thread_id>/split`  
    Body:
    - `root_post_id` (int, required) – ID of the top-level post to split from.
    - `title` (string, required) – title for the new thread.
    - `category_id` (int, optional) – target category; must exist and be moderate‑able by the caller.
- **Safety**:
  - Split is refused when `root_post_id` is not a top-level post, to avoid broken reply chains.
  - Only `thread_id` changes on the moved posts; reply links and IDs remain stable.
  - Counters and last‑post metadata are recomputed for both the original and new threads after split.

## Notifications and mentions

- Users receive notifications for thread replies (when subscribed) and when mentioned with `@username` in a post.
- Notification list and detail include `thread_slug` and `target_post_id` (for post targets) so the UI can link to the exact thread and post.
- `PUT /api/v1/notifications/read-all` marks all of the current user’s notifications as read.

See `postman/WorldOfShadows_API.postman_collection.json` (Forum and Moderation folders) for request examples.
