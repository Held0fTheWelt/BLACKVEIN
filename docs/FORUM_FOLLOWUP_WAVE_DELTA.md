# Forum Follow-up Wave — Delta Scope (Phase 1)

**Date:** 2026-03-14
**Mission:** Implement bookmarks UX, tag editing UX, reactions decision (truthful defer), tests, Postman/docs updates.

## Current State (What Exists)

### Models & Database
- **ForumThreadBookmark** — user/thread link; unique constraint
- **ForumTag** — slug + label; created_at
- **ForumThreadTag** — many-to-many thread/tag link; unique constraint
- **ForumPostLike** — user like on post; unique constraint (post_id, user_id)
- No ForumPostReaction model exists

### Backend APIs (Fully Functional)

**Bookmarks:**
- `POST /api/v1/forum/threads/<id>/bookmark` — Create bookmark; 409 if exists (idempotent), 404 if thread not found
- `DELETE /api/v1/forum/threads/<id>/bookmark` — Remove bookmark
- `GET /api/v1/forum/bookmarks?page=1&limit=20` — List bookmarked threads for current user; returns thread objects with `tags` array + `bookmarked_by_me` flag

**Tags:**
- `GET /api/v1/forum/tags?page=1&limit=50&q=search` — List all tags (moderator+); paginated, with search
- `DELETE /api/v1/forum/tags/<id>` — Delete tag (admin only); 409 if tag still in use
- `PUT /api/v1/forum/threads/<id>/tags` — Set tags for thread (moderator/admin OR thread author); body: `{"tags": ["tag1", "tag2"]}`; returns `{"tags": [{slug, label}, ...]}`

**Thread List/Detail:**
- `GET /api/v1/forum/categories/<slug>/threads` — Includes `tags` array and `bookmarked_by_me` flag per thread
- `GET /api/v1/forum/threads/<id>` — Thread detail; serializes tags

**Likes:**
- `POST /api/v1/forum/posts/<id>/like` — Like post (idempotent)
- `DELETE /api/v1/forum/posts/<id>/like` — Unlike post
- Post object includes `like_count` and `liked_by_me` flag

### Frontend UI (Partially Implemented)

**Bookmarks:**
- Bookmark toggle button on thread list and thread detail page (★ icon, filled when bookmarked)
- Button calls `POST /forum/threads/{id}/bookmark` and `DELETE /forum/threads/{id}/bookmark`
- No dedicated "Saved Threads" page or route

**Tags:**
- Admin tag management UI in `administration-tool/manage_forum.js` (`initTags()`) — list, search, delete (only when thread_count=0)
- No user-facing thread-level tag edit UI on thread detail page
- Thread detail shows tags as read-only labels

**Likes:**
- Like button on posts (with count)
- Works via POST/DELETE `/forum/posts/{id}/like`

### Tests

**Existing tests cover:**
- `test_thread_bookmark_create_and_list` — bookmark add/list
- `test_bookmarked_by_me_in_thread_list` — flag in thread list
- `test_bookmarked_by_me_false_for_anonymous` — anonymous users see `false`
- `test_bookmark_removal` — delete bookmark
- `test_bookmark_unbookmark_route` — route behavior
- `test_bookmarks_list_route` — pagination
- Tag tests: list, search, delete, permissions, thread-level tagging

### Postman Collection

- `/forum/threads/{id}/bookmark` (POST, DELETE)
- `/forum/bookmarks` (GET with page/limit)
- `/forum/tags` (GET with page/limit/q)
- `/forum/tags/{id}` (DELETE)
- `/forum/threads/{id}/tags` (PUT with body)
- All documented with examples

### Docs

- `FORUM_COMMUNITY_FEATURES.md` — Describes bookmarks and tags at API level
- No user-facing documentation for "Saved Threads" page
- No user-facing documentation for tag editing workflow

---

## Exact Remaining Gaps

1. **Saved Threads / Bookmarks UX:**
   - ❌ No dedicated user-facing page at a real route (e.g., `/forum/saved` or `/bookmarks`)
   - ✓ API exists but needs UI wrapper
   - ✓ Pagination already supported in backend

2. **Tag Editing UX:**
   - ❌ No thread-detail tag edit UI for moderators/authors
   - ✓ API exists (`PUT /forum/threads/{id}/tags`) but only admin has UI access
   - ✓ Permissions already enforced (moderator/admin OR thread author)
   - ❌ No inline tag editor on user-facing thread page

3. **Reactions:**
   - ❌ No model, no API, no UI
   - ✓ Likes system exists (ForumPostLike) — stable, with UI buttons
   - ❌ Would require new model + rework of like_count + notification changes
   - ⚠️ **NOT cleanly feasible in this narrow pass** (would destabilize interaction system)

---

## Files That Will Change

### Backend
- `backend/app/api/v1/forum_routes.py` — No changes expected (APIs complete); may refine serializers if needed

### Frontend (administration-tool)
- `administration-tool/frontend_app.py` — Add `/forum/saved` or `/bookmarks` route
- `administration-tool/templates/forum/saved_threads.html` — New template
- `administration-tool/static/forum.js` — Add saved threads page load logic, add inline tag editor to thread detail
- `administration-tool/templates/forum/thread.html` — Add tag edit UI (inline editor for moderator/author)

### Tests
- `backend/tests/test_forum_api.py` or new file — Add tests for saved threads list retrieval, tag editing behavior (permission enforcement)

### Postman & Docs
- `postman/WorldOfShadows_API.postman_collection.json` — No new endpoints; may clarify existing ones
- `docs/FORUM_COMMUNITY_FEATURES.md` — Add saved threads usage section
- `docs/CHANGELOG.md` — Add entry for this follow-up pass
- New file: `docs/FORUM_REACTIONS_DEFER.md` — Truthful note on why reactions were explicitly deferred

---

## What Must NOT Be Refactored

- Forum notification system (subscriptions, mentions) — out of scope
- Post moderation system — out of scope
- Report/escalation system — out of scope
- Like system itself — keep intact; reactions are separate consideration
- Existing tag admin UI (`manage_forum.js`) — do not break
- Category/thread visibility filtering — do not change

---

## Reactions Decision: OPTION B (Explicitly Defer)

**Rationale:**
- Reactions would require introducing a new `ForumPostReaction` model (or replacing `ForumPostLike`)
- Current like_count is tightly tied to ForumPostLike; reactions would require rethinking how interaction metrics work
- Would need:
  - New model design (emoji/type + count logic)
  - Changes to post serialization
  - UI for reaction picker
  - Notification behavior updates (do reactions trigger notifications?)
  - Full test coverage for multi-reaction edge cases
  - Potential migration complexity

**Decision:**
- ✓ Keep ForumPostLike + like button intact (no destabilization)
- ✗ Do NOT add half-built reactions
- ✓ Add truthful defer note in docs explaining reactions were intentionally deferred as out-of-scope for this pass
- ✓ Ensure changelog does not claim reactions exist or are coming soon

---

## Phase 1 Conclusion

- **Remaining gaps confirmed:** Saved threads page, tag edit UX, explicit reactions defer
- **Files to change:** `frontend_app.py`, 2 new/modified forum templates, `forum.js`, 1 test file, Postman, 2 docs files
- **Reactions status:** Explicitly deferred; likes remain intact; truthful documentation required
- **Current commit:** (to be noted after Phase 1 completion)
