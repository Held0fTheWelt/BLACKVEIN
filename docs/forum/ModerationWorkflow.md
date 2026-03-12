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
| `GET /api/v1/forum/moderation/recently-handled?limit=10` | Recently handled reports |
| `GET /api/v1/forum/moderation/locked-threads` | List locked threads |
| `GET /api/v1/forum/moderation/pinned-threads` | List pinned threads |
| `GET /api/v1/forum/moderation/hidden-posts` | List hidden posts |
| `PUT /api/v1/forum/reports/<id>` | Update report status (body: `{"status": "open"\|"reviewed"\|"resolved"\|"dismissed"}`) |

## Thread moderation (public thread page)

On a thread page, moderators see a mod bar with:

- **Lock / Unlock** – Prevents new replies (except staff).
- **Pin / Unpin** – Pins thread at top of category list.
- **Archive / Unarchive** – Archives thread (staff-only visibility; no new posts from regular users).
- **Move…** – Move thread to another category (dropdown, then Move).

API:

- `POST /api/v1/forum/threads/<id>/lock` | `.../unlock`
- `POST /api/v1/forum/threads/<id>/pin` | `.../unpin`
- `POST /api/v1/forum/threads/<id>/archive` | `.../unarchive`
- `POST /api/v1/forum/threads/<id>/move` (body: `{"category_id": <int>}`)

## Post moderation

- **Hide / Unhide** (per post): `POST /api/v1/forum/posts/<id>/hide` | `.../unhide` (moderator/admin for that category).

## Notifications and mentions

- Users receive notifications for thread replies (when subscribed) and when mentioned with `@username` in a post.
- Notification list and detail include `thread_slug` and `target_post_id` (for post targets) so the UI can link to the exact thread and post.
- `PUT /api/v1/notifications/read-all` marks all of the current user’s notifications as read.

See `postman/WorldOfShadows_API.postman_collection.json` (Forum and Moderation folders) for request examples.
