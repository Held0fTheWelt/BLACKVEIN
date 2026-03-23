Technical hardening delta plan – Phase 1 (0.0.27+)
==================================================

Backend path: `backend/`. Frontend path: `administration-tool/`. Remote-first backend default (PythonAnywhere) remains unchanged.

What already exists
-------------------

**Models and schema:**
- **Forum core** (`forum.py`): `ForumCategory` (with hierarchy support via `parent_id`, `required_role`, `is_private`), `ForumThread` (with `status`, `reply_count`, `last_post_at`, `last_post_id`, `view_count`, `is_pinned`, `is_locked`, `is_featured`, soft-delete via `deleted_at`), `ForumPost` (with `status`, `parent_post_id` single-level reply model, edit tracking via `edited_at`/`edited_by`, soft-delete via `deleted_at`), `ForumPostLike` (with unique constraint per post+user), `ForumReport` (target_type/target_id dual pattern, with resolution metadata), `ForumThreadSubscription` (unique per thread+user), `ForumThreadBookmark` (unique per thread+user), `ForumTag` (normalized by slug), `ForumThreadTag` (many-to-many link).
- **News/Wiki integration** (`news_article.py`, `wiki_page.py`): Each supports multiple translations with language fallback. News articles can link to a discussion thread via `discussion_thread_id`. Both support related forum threads via junction tables (`NewsArticleForumThread`, `WikiPageForumThread`).
- **Notifications** (`Notification` model): Supports `event_type` (mention, thread_reply), `target_type` (forum_post, forum_thread), `target_id`, `is_read` flag.

**Service layer (`forum_service.py`):**
- **Permission helpers** (`user_can_view_thread`, `user_can_view_post`, `user_can_post_in_thread`, `user_can_like_post`, `user_can_edit_post`, `user_can_soft_delete_post`, `user_can_access_category`, `user_can_create_thread`, `user_can_moderate_category`, `user_can_manage_categories`, etc.): Implement role-based access control with category-level `required_role` and `is_private` checks. Handle inactive categories (admin-only).
- **Category CRUD** (`create_category`, `update_category`, `delete_category`, `get_category_by_slug_for_user`, `list_categories_for_user`): Support parent categories via `parent_id`.
- **Thread lifecycle** (`create_thread`, `update_thread`, `soft_delete_thread`, `hide_thread`/`unhide_thread`, `set_thread_lock`, `set_thread_pinned`, `set_thread_featured`, `set_thread_archived`/`set_thread_unarchived`, `move_thread`, `increment_thread_view`, `recalc_thread_counters`): Support thread status transitions and counter recalculation.
- **Advanced thread operations** (`merge_threads`, `split_thread_from_post`): Merge moves posts and merges subscriptions; split enforces single-level reply constraint (only top-level posts can split).
- **Post CRUD** (`create_post`, `update_post`, `soft_delete_post`, `hide_post`/`unhide_post`, `like_post`/`unlike_post`): Support edit tracking, nested replies with depth constraint, and like counters.
- **Reports** (`create_report`, `list_reports`, `list_reports_for_target`, `update_report_status`): Support status workflow (open, reviewed, escalated, resolved, dismissed).
- **Subscriptions and bookmarks** (`subscribe_thread`, `unsubscribe_thread`, `bookmark_thread`, `unbookmark_thread`, `list_bookmarked_threads`): Track user interest.
- **Tags** (`get_or_create_tags`, `set_thread_tags`, `list_tags_for_thread`, `list_tags_for_threads`, `list_all_tags`, `tag_thread_count`, `batch_tag_thread_counts`, `delete_tag`): Normalized by slug, support batch operations.
- **Notifications** (`create_notifications_for_thread_reply`, `_create_mention_notifications_for_post`, `_mention_usernames_from_content`): Create notifications for subscribers and @-mentions.

**API routes (`forum_routes.py`):**
- **Public/community endpoints:** Categories list, category detail, threads in category (paginated, with tag/bookmark metadata batch-loaded), thread detail (single and list posts), search (title + content with filters), post detail, post likes, tag list with search.
- **Authenticated endpoints:** Create thread/post, like/unlike, subscribe/unsubscribe, bookmark/unbookmark.
- **Moderation endpoints:** Hide/unhide/soft-delete thread/post, lock/unlock, pin/unpin, feature/unfeature, archive/unarchive, move, merge, split, manage reports.
- **Admin endpoints:** Category CRUD, report management.
- **Pagination:** Consistently implemented via `page`/`limit` query params, capped at 100 items per page, with SQL-level `offset()`/`limit()`.
- **Search:** Title search with optional content search, category/status/tag filters, with 200-char limit on search term to prevent runaway LIKE patterns.
- **Batch operations:** `list_tags_for_threads`, `bookmarked_thread_ids_for_user`, `batch_tag_thread_counts` to reduce N+1 queries.

**News/Wiki services** (`news_service.py`, `wiki_service.py`):
- Support language fallback via `_effective_language`, `_get_effective_translation`, `list_related_threads_for_article`, `list_related_threads_for_page`.

**Tests** (`backend/tests/test_forum_*.py`):
- Permission tests (400+ assertions across test_forum_service.py, test_forum_api.py).
- Pagination/list tests (category/thread/post/report/tag listing).
- Search tests (text search, status/category/tag filters, content search, visibility filtering, deleted/hidden thread behavior).
- Notification tests (thread reply, mentions, mark-all-read).
- Tag tests (create, link, batch operations, usage counting, deletion with usage check).
- Merge/split tests (post movement, counter recalculation, subscription handling).
- Moderation flow tests (moderation dashboard, activity logs, report resolution).

**Migrations:**
- `021_forum_models.py` (core forum tables with initial indexes).
- `022_wiki_news_discussion_thread_id.py` (discussion thread links).
- `024_news_wiki_related_forum_threads.py` (related thread junction tables).
- `025_forum_bookmarks_and_tags.py` (bookmark and tag tables).
- `026_forum_moderation_indexes.py` (moderation-specific indexes).
- `027_forum_report_resolution_note.py` (report resolution tracking).
- `028_forum_performance_indexes.py` (status indexes on forum_posts, forum_threads, notifications).

**Postman collection:**
- Forum folder with endpoints for categories, threads, posts, likes, search, reports, tags, subscriptions, bookmarks, merge, split.
- Moderation folder with hide/unhide/lock/unlock/pin/unpin/archive/unarchive/move/merge/split requests.
- Activity log folder.

What is technically weak
------------------------

**Query performance and N+1 risks:**
1. **Author relationships unpaginated:** Thread and post list endpoints call `.author.username` in the loop after pagination without explicit eager loading (SQLAlchemy lazy loading). This causes N+1 queries for author usernames on large page sizes.
2. **Category relationships on filtered threads:** `list_bookmarked_threads` joins `ForumCategory` but does not eager-load the category before serialization. The `.to_dict()` call doesn't include category details, but the join is present—potential missed opportunity for eager loading.
3. **Post detail endpoint:** Reading a single post and accessing `post.author`, `post.thread`, `post.editor`, and `post.parent_post` all trigger separate queries if not eager-loaded.
4. **Tag batch-loading:** `list_tags_for_threads` is called separately from thread listing. If thread detail page also loads tags per-post, there could be nested N+1 patterns.
5. **Subscription/bookmark enumeration:** `ForumThreadSubscription.query.filter_by(thread_id=source.id).all()` in `merge_threads` loads all subscriber rows into memory before deduplication. Large subscriber lists (1000+) could cause memory bloat.

**Index gaps:**
1. **Category lookup on thread listing:** `ForumThread.query.filter_by(category_id=...)` does not explicitly have a composite index. Migration 028 adds status indexes but not `(category_id, status)`.
2. **Post ordering by created_at:** `list_posts_for_thread` orders by `created_at.asc()` but has no index hint for `(thread_id, created_at)`.
3. **Notification user + is_read:** Migration 028 adds `(user_id, is_read)` index, but no composite index for filtering by event_type + user_id.
4. **Report filtering:** `list_reports` filters by `status` and `target_type` but there is no composite `(status, created_at)` or `(target_type, target_id)` index for bulk moderation queries.

**Edge cases and constraints:**
1. **View count increments without transaction safeguard:** `increment_thread_view` increments `view_count` with a plain `commit()`. Under high concurrency, reads before increment could lose updates (race condition).
2. **Reply count synchronization fragility:** `recalc_thread_counters` recalculates from all non-hidden/non-deleted posts, but the calculation excludes the root post (treats first post as index 0, replies start from 1). If a post is hidden/deleted after counter recalc, the count may drift until next manual recalc.
3. **Search LIKE pattern escaping:** The forum search builds LIKE patterns with `f"%{q_raw}%"` without escaping SQL wildcard characters (`%`, `_`). A search for `test_foo%` would not search literally for that string.
4. **Thread status inconsistency:** `thread.is_locked` boolean and `thread.status` string can drift. `set_thread_lock(locked=True)` sets both `is_locked=True` and `status="locked"`, but other code paths may only set `status` without syncing `is_locked`.
5. **Deleted post visibility in search:** Search results exclude deleted threads but may include posts from deleted/hidden posts within matching threads if content search is enabled. No guard in the post content subquery.
6. **Tag slug collision with normalization:** `_normalize_tag_value` can normalize different inputs to the same slug (e.g., "foo bar" and "foo-bar" both become "foo-bar"). The function does not enforce uniqueness per input; duplicate normalized tags could be created if not careful.
7. **Split thread deep-reply constraint:** `split_thread_from_post` enforces that only top-level posts can split. Correct. However, if a reply to the root post exists and the root post is deleted, the orphaned reply remains in the source thread—not addressed.

**Validation gaps:**
1. **Title/content length enforcement:** No maximum length checks on thread titles (255 char column) or post content (Text column). Content can be arbitrarily large.
2. **Slug collision handling:** `_ensure_unique_thread_slug` appends a numeric suffix (e.g., `my-thread-2`), but does not prevent collisions with manually-set slugs if a user creates `my-thread-2` directly.
3. **Category parent cycle detection:** `move_thread` checks target category exists but does not validate that parent_id on categories does not form a cycle.
4. **Report reason truncation:** `create_report` accepts a reason string with no max length (512 char column, but input validation does not enforce it).
5. **Like count underflow:** `unlike_post` uses `max(0, ...)` to prevent negative like counts, but `like_count` could still underflow if concurrent deletes race.

**Response inconsistencies:**
1. **Pagination format variation:** Most endpoints return `{items, total, page, per_page}`, but some return `{items, total}` without page metadata.
2. **Error response shapes:** Some endpoints return `{"error": "..."}`, others return `{"message": "..."}`, others return detailed validation errors.
3. **Null handling in to_dict():** Models check if datetime is not None before `.isoformat()`, but some endpoints may serialize `null` inconsistently (e.g., missing `author_username` vs. present with `None`).
4. **Thread author in list vs. detail:** Thread list includes `author_username`, but thread detail does not explicitly include author metadata in all response paths.
5. **Tag object shape:** Tags in thread responses are `{slug, label}`, but the `ForumTag.to_dict()` method does not exist—serialization is inline in the routes.

**Test coverage gaps:**
1. **Search edge cases:** No tests for:
   - Search with wildcard-like characters (`%`, `_`) in the query.
   - Search with very long query strings (200+ chars, should truncate).
   - Search with combined filters (all of category, status, tag at once).
   - Search including content from hidden/deleted posts within matching threads.
2. **Permission interaction tests:** No tests for:
   - User with `required_role=MODERATOR` trying to access/post in `required_role=ADMIN` category.
   - Private category with explicit `required_role` (both flags set).
   - Mixing private + required_role flags.
3. **Notification N+1 risks:** Tests for mention notifications but no tests for 100+ mentions in a single post or 1000+ thread subscribers in a merge.
4. **Pagination boundary tests:** No tests for:
   - Requesting page 0, negative page, or page > max_pages.
   - Requesting limit > 100 (should cap).
   - Empty result sets on various pages.
5. **Counter consistency under concurrent operations:** No tests for:
   - Concurrent post creation / deletion and counter sync.
   - Concurrent like/unlike and counter stability.
   - Concurrent merge and counter recalc.
6. **Tag usage and lifecycle:** No tests for:
   - Bulk tag deletion and validation of usage count.
   - Renaming a tag (slug collision).
   - Tag query with special characters or very long labels.

**Logging and monitoring gaps:**
1. **No structured logging for:** Report status changes, thread moderation actions (lock/pin/merge/split), subscription/bookmark changes, post deletions/hides.
2. **No audit trail:** Moderation actions are logged via `log_activity`, but the activity_log_service does not have dedicated fields for bulk operations (e.g., merge moves 50 posts but only one log entry).
3. **No slow-query detection:** Large search result sets or paginated queries near max results have no instrumentation.

What is inconsistent
---------------------

**Field naming across entities:**
- Models use snake_case (e.g., `created_at`, `deleted_at`, `parent_post_id`).
- Response payloads mirror this (e.g., `author_id`, `author_username` inline).
- But some responses use inconsistent naming (e.g., `thread_id` vs. `id` for thread in different contexts).

**Status field semantics:**
- `ForumThread.status` can be `open`, `locked`, `hidden`, `archived`, `deleted`. Some transitions are implicit (e.g., `set_thread_lock` sets `status="locked"`).
- `ForumPost.status` can be `visible`, `edited`, `hidden`, `deleted`. The `edited` status is set by `update_post` but never explicitly checked in permission logic.
- No explicit state machine validation; transitions are implicit in each function.

**Datetime handling:**
- All models use `datetime(timezone=True)` columns.
- Serialization uses `.isoformat()`.
- Timezone awareness is good, but there's inconsistency in whether `default=_utc_now` is called in the model or passed at insert time.

**Permission model:**
- Some permission checks are in `forum_service.py` (role-based, category-based).
- Some are in the route handlers (e.g., `current_user_is_admin()` decorator check).
- Some are in custom middleware (`get_current_user`).
- Inconsistent pattern makes it hard to audit who can do what.

**Error handling:**
- Some endpoints return 400 for input validation errors; others return 422.
- Some service functions return `(None, error_message)` tuples; others raise exceptions.
- Inconsistency makes error handling unpredictable for clients.

What queries are likely expensive or fragile
---------------------------------------------

**High-risk queries:**

1. **`list_bookmarked_threads` with large user bookmark counts:**
   ```python
   q = (
       ForumThread.query.join(ForumThreadBookmark, ...)
       .filter(ForumThreadBookmark.user_id == user.id)
       .filter(ForumThread.deleted_at.is_(None))
   )
   q = q.join(ForumCategory, ...)
   q = q.filter(ForumCategory.is_active.is_(True))
   # ... then .order_by(...).offset(...).limit(...)
   ```
   - Joins `ForumCategory` for each bookmark. If a user has 500 bookmarks, this could scan a large result set before pagination.
   - No index on `(user_id)` for `ForumThreadBookmark`. Migration 025 creates the table but migration 028 does not add a performance index.

2. **`create_notifications_for_thread_reply` with 1000+ subscribers:**
   ```python
   subs = ForumThreadSubscription.query.filter_by(thread_id=thread.id).all()
   for sub in subs:
       n = Notification(...)
       db.session.add(n)
   db.session.commit()
   ```
   - Loads all subscribers into memory. Adding 1000 rows in a loop could be slow.
   - No batch insert optimization.

3. **`merge_threads` subscription deduplication:**
   ```python
   source_subs = ForumThreadSubscription.query.filter_by(thread_id=source.id).all()
   existing_target_user_ids = {
       s.user_id for s in ForumThreadSubscription.query.filter_by(thread_id=target.id).all()
   }
   for sub in source_subs:
       if sub.user_id not in existing_target_user_ids:
           new_sub = ForumThreadSubscription(...)
   ```
   - Loads both source and target subscriptions fully. For threads with 500+ subscribers, this is memory-inefficient.
   - Could use a set-based SQL subquery instead.

4. **`forum_search` with `include_content=true` and large thread counts:**
   ```python
   if include_content and like_pattern and len(q_raw) >= 3:
       sub = (
           ForumPost.query.with_entities(ForumPost.thread_id)
           .filter(ForumPost.content.ilike(like_pattern))
           .subquery()
       )
       q = q.filter(
           db.or_(
               ForumThread.title.ilike(like_pattern),
               ForumThread.id.in_(sub),
           )
       )
   ```
   - Content search scans all posts without restriction to non-deleted/non-hidden. No subquery filtering by post status.
   - The `in_(sub)` on large thread counts could be slow.

5. **`list_posts_for_thread` with large post counts:**
   ```python
   q = q.order_by(ForumPost.created_at.asc())
   items = q.offset(offset).limit(per_page).all()
   ```
   - Orders by `created_at` without an index. If thread has 10,000 posts, sorting before pagination is expensive.
   - No pagination direction hint (ascending vs. descending); always oldest first.

6. **Thread detail with tag/bookmark batch-load:**
   - Route does `list_tags_for_threads([t.id])` and `bookmarked_thread_ids_for_user(user_id, [t.id])` for a single thread. Overkill; could just call single-thread helpers.

**Fragile patterns:**

1. **`recalc_thread_counters` called multiple times in merge:**
   - Called for both source and target threads after merge. If merge is interrupted, counters may be stale.
   - No transactional guarantee.

2. **`increment_thread_view` non-atomic:**
   - Reads `view_count`, increments, writes. Under concurrency, updates can be lost.
   - Should use SQL `UPDATE ... SET view_count = view_count + 1`.

3. **Slug uniqueness without collision detection in update:**
   - `update_thread` can change title, which could indirectly affect slug. But the function does not regenerate or validate slug uniqueness.

4. **Post parent validation only checks existence:**
   - `create_post` validates `parent_post_id` belongs to the same thread, but does not check if the parent is visible/deleted. A reply to a deleted post would be allowed if the post still exists in the DB.

What regressions are currently under-tested
--------------------------------------------

**Forum-specific test gaps:**

1. **Thread visibility with mixed status combinations:**
   - No test for: deleted thread with hidden posts (moderator trying to read deleted thread).
   - No test for: archived thread with locked status (both flags set).
   - No test for: inactive category with private flag (layered access control).

2. **Post reply depth enforcement:**
   - Test `create_post` with `parent_post_id` but no test for:
     - Replying to a reply (depth > 1, should fail).
     - Replying to a deleted/hidden post (should fail).
     - Replying to a post in a different thread (should fail but only checked at service level, not route).

3. **Search visibility filtering:**
   - Test for deleted/hidden thread exclusion, but no test for:
     - Hidden posts within a visible thread (content search should not include them).
     - Private category exclusion in search.
     - Deleted posts in content search (subquery includes all posts).

4. **Report resolution workflow:**
   - Tests for `update_report_status`, but no tests for:
     - Resolving a report on a deleted thread/post.
     - Changing report status multiple times (state machine transitions).
     - Concurrent report updates (race condition on handled_at).

5. **Subscription and bookmark edge cases:**
   - Test subscribe/unsubscribe, but no test for:
     - Bulk subscribe (1000+ threads, pagination).
     - Subscribe to a deleted thread (should fail or be noop).
     - Bookmark a thread in a private category (permission check missing at subscription level).

6. **Tag lifecycle edge cases:**
   - Test create/link/delete, but no test for:
     - Updating a tag label (rename).
     - Tag slug collision after normalization.
     - Bulk tag assignment to a thread (400+ tags, memory).
     - Deleting a tag with 100+ thread associations (count check efficiency).

7. **Merge/split under edge conditions:**
   - Test basic merge/split, but no test for:
     - Merging threads with 100+ posts (performance).
     - Splitting a thread with only 1 post (should result in empty source).
     - Merging a thread into itself (should fail).
     - Merging an archived thread (should it be allowed?).

8. **Concurrency and race conditions:**
   - No tests for:
     - Two users liking the same post simultaneously (like_count increment race).
     - Two merges on the same source thread (undefined behavior).
     - Thread delete while a post is being created (foreign key constraint check timing).
     - Recalc counters during concurrent post edits.

**News/Wiki test gaps:**

1. **Discussion thread integration:**
   - News/wiki can link a forum thread. Tests do not cover:
     - Linking a deleted forum thread (should be hidden in the response).
     - Unlinking a thread via soft-delete (deletion of the junction record vs. the thread).
     - Related threads fetch with private/inactive categories (should be filtered).

2. **Notification integration with news/wiki:**
   - Forum mentions generate notifications. No test for:
     - Mentions in a news/wiki article pointing to a forum thread.
     - Duplicate mention notifications in a single post.

What files are expected to change
----------------------------------

**Phase 1 (Delta plan consolidation):**
- `docs/TECHNICAL_HARDENING_DELTA.md` (this file) – finalize delta plan.

**Phase 2 (Search hardening):**
- `backend/app/api/v1/forum_routes.py` – refactor `forum_search` to escape LIKE patterns, add content search filtering by post status, add validation for search term length.
- `backend/tests/test_forum_routes_extended.py` or new test file – add search edge case tests (wildcard escaping, status filtering, deleted post content).
- `backend/app/services/forum_service.py` – if search is moved to service layer.

**Phase 3 (Query review and index hardening):**
- `backend/migrations/versions/029_*.py` – add missing indexes: `(category_id, status)` on `forum_threads`, `(thread_id, created_at)` on `forum_posts`, `(target_type, target_id)` on `forum_reports`, `(user_id)` on `forum_thread_bookmarks`.
- `backend/app/services/forum_service.py` – refactor `list_bookmarked_threads` to eager-load categories; refactor `merge_threads` subscription dedup to use SQL set operations; refactor `create_notifications_for_thread_reply` to use batch insert; optimize author/editor lazy loading in routes via eager loading or selective serialization.
- `backend/app/api/v1/forum_routes.py` – add explicit eager loading hints (`joinedload`, `contains_eager`) for post author/editor; refactor thread detail to avoid N+1 on tag/bookmark lookups.
- `backend/tests/test_forum_service.py` – add performance regression tests for large subscriber/tag counts (mock or scale tests).

**Phase 4 (Regression expansion):**
- `backend/tests/test_forum_api.py` – expand coverage for:
  - Thread status inconsistencies (is_locked vs. status).
  - Post reply depth enforcement at route level.
  - Report status transitions and invalid states.
  - Deleted/hidden post visibility in thread detail.
  - Mixed category access control (private + required_role).
- `backend/tests/test_forum_service.py` – add concurrency/race condition tests.

**Phase 5 (Moderation-flow regression coverage):**
- `backend/tests/test_forum_api.py` – add moderation-specific tests:
  - Hide/unhide thread/post visibility in search.
  - Archive/unarchive with counter recalc.
  - Merge with 100+ subscribers.
  - Split with 100+ posts.
  - Report workflow state machine (all transitions).
- `backend/app/services/activity_log_service.py` or new logging integration – add structured logging for moderation actions if not present.

**Phase 6 (API consistency pass):**
- `backend/app/api/v1/forum_routes.py` – standardize error response shapes, standardize pagination metadata, ensure all list endpoints return consistent format.
- `backend/app/models/forum.py` – add `to_dict()` methods for all models (ForumTag, ForumReport, etc.) if not present; standardize serialization.

**Phase 7 (Postman, docs, changelog, and final verification):**
- `postman/WorldOfShadows_API.postman_collection.json` – ensure all hardened endpoints are documented with correct variable/environment usage.
- `docs/forum/ModerationWorkflow.md` – document constraints (reply depth, merge/split conditions, visibility rules).
- `docs/forum/SearchHardening.md` – new document explaining search behavior (LIKE escaping, content filtering, status handling).
- `docs/forum/PerformanceConsiderations.md` – new document explaining N+1 risks, pagination strategies, batch operations.
- `CHANGELOG.md` – add 0.0.27+ entries describing phases, fixes, and performance improvements.

Must not be broadly refactored
------------------------------

- **Core auth and role system** (User roles, role rank levels, area-based feature access).
- **Overall backend/frontend split** (`backend/` Flask API, `administration-tool/` Flask+Jinja+JS).
- **Existing moderation and notification semantics** already covered by tests (lock/pin/archive/move, hide/unhide, notification read flows).
- **Remote-first default** for `BACKEND_API_URL` and PythonAnywhere as initial target.
- **Soft-delete pattern** (use `deleted_at`/`status` flags, not hard deletes).
- **Permission model** (defer to refactor until later; focus on filling test gaps and documenting constraints).
- **Search implementation** (keep LIKE-based; do not switch to Elasticsearch unless required later).
- **Notification architecture** (keep in-DB; do not move to queue system unless required later).

Summary of weak points to address across phases
-----------------------------------------------

**Performance risks (Phase 2–3):**
1. Author N+1 on thread/post lists – add eager loading.
2. Tag batch-load called on single items – optimize route-level calls.
3. Large subscriber/tag bulk operations – use batch inserts, set-based SQL.
4. Expensive searches with content filter – add post status filtering, truncation guards.
5. Missing indexes – add composite indexes for common filter combos.
6. View count race condition – use atomic SQL increment.

**Edge cases (Phase 4–5):**
1. Post reply depth enforcement only in service, not documented in API.
2. Search LIKE escaping missing – escape `%` and `_`.
3. Thread status/is_locked inconsistency – validate state transitions.
4. Deleted post visibility in search content – filter by status in subquery.
5. Subscription/bookmark validation missing – enforce category access check.
6. Large concurrent merge/split – add transactional safeguards.

**Consistency (Phase 6):**
1. Error response shapes – standardize to `{message, code, details}` or similar.
2. Pagination format – ensure all list endpoints return `{items, total, page, per_page}`.
3. Null handling – be explicit about when fields are omitted vs. null.
4. Status field semantics – document state machine in code comments.

**Documentation (Phase 7):**
1. Postman collection – add all hardened endpoints.
2. Moderation workflow docs – include constraints, permissions, edge cases.
3. Search behavior doc – explain LIKE escaping, filtering, truncation.
4. Performance considerations – explain N+1 patterns, batch operations, indexes.
5. Changelog – document all phases, fixes, and improvements.

