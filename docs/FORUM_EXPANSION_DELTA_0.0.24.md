# Forum expansion wave – delta note (0.0.24)

Internal planning. Backend path: `backend/`. Frontend path: `administration-tool/`. Remote-first default unchanged.

## What already exists

- **Forum API (forum_routes.py):** Categories, threads, posts, likes, reports, subscriptions; lock/unlock, pin/unpin, feature/unfeature, hide/unhide post; GET/PUT reports list/detail/status; GET `/forum/moderation/metrics` (open_reports, hidden_posts, locked_threads); GET `/forum/moderation/recent-reports` (open only, limit).
- **Forum service (forum_service.py):** Full CRUD for categories, threads, posts; hide_thread/unhide_thread, set_thread_lock, set_thread_pinned, set_thread_featured; hide/unhide post; recalc_thread_counters; list_reports(status), update_report_status; create_notifications_for_thread_reply (subscribers, exclude author). No move_thread, merge_threads, split_posts, archive/unarchive yet. Thread status: open, locked, hidden, deleted (no "archived" yet).
- **Models:** ForumCategory, ForumThread, ForumPost, ForumPostLike, ForumReport, ForumThreadSubscription; Notification (event_type, target_type, target_id, message, is_read, read_at). No mention storage.
- **Notifications API:** GET `/api/v1/notifications` (page, limit, unread_only); PATCH/PUT `/api/v1/notifications/<id>/read`. List adds thread_slug for forum_thread targets; forum_post targets get thread_slug = None (gap: should resolve via post.thread).
- **Manage forum UI (manage/forum.html + manage_forum.js):** Categories card (list, create, edit, delete); Reports card (filter by status, list, refresh). No dedicated moderation dashboard view (open reports summary, recently moderated, filtered hidden/locked/pinned lists).
- **Public forum:** index, category, thread; forum.js has initNotifications (list, pagination, mark-read per item, link to thread). No mark-all-read; no post anchor in link.
- **Tests:** test_forum_api.py (30 tests): categories, threads, posts, likes, reports, subscribe, lock/pin/hide, search, permissions. No tests for moderation metrics/recent-reports, move/archive, mentions, mark-all-read.
- **Postman:** Collection has forum endpoints; may lack moderation/metrics and any new endpoints from this wave.

## What is incomplete for this wave

- Moderation dashboard: no single staff view with open reports + recently moderated + filters (hidden posts, locked threads, pinned threads, recently reported).
- Notification center: thread_slug for forum_post targets; optional mark-all-read; link to post anchor when target is post.
- Advanced thread actions: move thread to another category; archive/unarchive (add status or reuse hidden); merge/split only if feasible without scope creep.
- Mentions: no @username parsing, no mention storage, no mention notifications, no safe rendering in UI.

## What will be added (this wave)

1. **Moderation dashboard:** New view in administration-tool (e.g. /manage/forum with dashboard section or dedicated /manage/forum/moderation) using existing metrics + recent-reports; optional backend list endpoints for “hidden posts”, “locked threads”, “pinned threads” if needed for filtered views; moderator quick actions (link to thread, set report status).
2. **Notification center polishing:** Backend: ensure thread_slug (and optional target_post_id for anchor) in notifications list for forum_post. Optional POST/PUT mark-all-read. Frontend: clear read/unread state, optional “Mark all read”, link to thread#post-<id> when applicable.
3. **Advanced thread moderation:** Backend: move thread to category (service + route); archive/unarchive thread (status or flag); UI controls for move/archive. Merge/split only if clean implementation; otherwise document as future.
4. **Mentions:** Parse @username in post content on create/update; validate against User; store (e.g. Notification with event_type mention or separate mention table); create notification for mentioned user; exclude self; sanitize/escape mention display in forum UI.
5. **Tests:** Moderation dashboard endpoints; move thread; archive/unarchive; notifications (thread_slug for post); mark-read/mark-all-read; mentions and mention notifications.
6. **Postman + docs:** New/modified requests; short moderator workflow doc; changelog 0.0.24 filled.

## Files expected to change

- **backend:** app/api/v1/forum_routes.py (move, archive/unarchive, optional mark-all-read, notification list thread_slug for post); app/services/forum_service.py (move_thread, set_thread_archived, mention parsing/notification); app/models/ (optional: mention table or reuse Notification); migrations if new fields/tables.
- **administration-tool:** templates/manage/forum.html (dashboard section or new template); static/manage_forum.js (dashboard UI, filters, quick actions); templates/forum/notifications.html, static/forum.js (mark-all-read, link to post, read state).
- **administration-tool (forum thread):** Post form / display for safe mention rendering.
- **backend tests:** test_forum_api.py (move, archive, moderation lists if any); test notifications (mark-all-read, thread_slug for post); mention tests.
- **Postman:** WorldOfShadows_API.postman_collection.json.
- **docs:** New or updated moderator/forum doc; CHANGELOG 0.0.24.

## What must not be broadly refactored

- Existing forum permission model (moderator/admin per category).
- Existing report status flow (open, reviewed, resolved, dismissed).
- News/wiki/discussion links.
- Auth (JWT, session) or backend/frontend split.
