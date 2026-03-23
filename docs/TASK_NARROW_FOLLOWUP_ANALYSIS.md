# PHASE 1: FREEZE DELTA SCOPE

## Current State Analysis

### What Already Exists:

✅ **Forum-side suggestion logic:**
- `suggest_related_threads_by_tags()` in forum_service.py (Phase 2 of v0.0.30)
- Tag-based ranking with tag overlap count and recency
- Excludes deleted/hidden threads, respects visibility

✅ **News-side suggestion logic:**
- `get_suggested_threads_for_article()` in news_service.py (Phase 2 of v0.0.30)
- Category-based suggestions (articles suggest threads from same category)
- Filters for public categories only
- Returns enriched dict with thread data

✅ **Wiki-side suggestion logic:**
- `get_suggested_threads_for_wiki_page()` in wiki_service.py (Phase 2 of v0.0.30)
- Category-based suggestions (wiki suggests threads from same category)
- Filters for public categories
- Returns enriched dict

✅ **Discussion links:**
- NewsArticle.discussion_thread_id (primary)
- WikiPage.discussion_thread_id (primary)
- NewsArticleForumThread junction table (manual related)
- WikiPageForumThread junction table (manual related)
- Both support relation_type field

✅ **Manual related-thread management:**
- API endpoints for add/list/delete related threads
- Tested and working

### What's Missing (Gaps for this Task):

❌ **Frontend rendering of suggestions:**
- News/Wiki public pages don't surface auto-suggestions yet
- Admin templates don't show suggestion candidates
- No UI distinction between linked vs suggested threads

❌ **Endpoint exposure:**
- Suggestion functions exist but aren't exposed as dedicated endpoints
- News/Wiki API doesn't include suggestions in responses

❌ **Administration UI:**
- No admin interface to view suggestions
- No way to promote suggestions to manual links

## Files That Will Change

**Backend (New/Modified):**
1. `backend/app/api/v1/news_routes.py` - Add suggestion endpoint
2. `backend/app/api/v1/wiki_routes.py` - Add suggestion endpoint
3. `backend/app/models/news_article.py` - Verify discussion_thread_id exists
4. `backend/app/models/wiki_page.py` - Verify discussion_thread_id exists

**Frontend (New/Modified):**
1. `administration-tool/templates/news/edit.html` - Show suggestions
2. `administration-tool/templates/wiki/edit.html` - Show suggestions
3. `administration-tool/static/manage_news.js` - Handle suggestions
4. `administration-tool/static/manage_wiki.js` - Handle suggestions
5. `administration-tool/templates/news/public.html` - Display suggestions
6. `administration-tool/templates/wiki/public.html` - Display suggestions

**Tests:**
1. `backend/tests/test_news_api.py` - Add suggestion endpoint tests
2. `backend/tests/test_wiki_api.py` - Add suggestion endpoint tests

**Docs:**
1. `docs/changelog.md` - Phase update entry
2. `postman/WorldOfShadows_API.postman_collection.json` - New endpoints

## Suggestion Strategy (Already Chosen in v0.0.30)

**News articles suggest forum threads by:**
1. Primary: Threads in same category
2. Secondary: Recent activity (last_post_at DESC)
3. Filters: Public categories, non-hidden/deleted threads
4. Limit: 5-10 threads max
5. Excludes: Primary discussion link, manually linked threads

**Wiki pages suggest forum threads by:**
1. Primary: Threads in same category
2. Secondary: Recent activity
3. Filters: Public categories, non-hidden/deleted threads
4. Limit: 5-10 threads max
5. Excludes: Primary discussion link, manually linked threads

## What Must NOT Be Refactored

- Forum core (categories, threads, posts, tags, bookmarks)
- News/Wiki publishing system
- Discussion link structure
- Manual related-thread management
- Auth/permissions
- Moderation system

## Safe Constraints

✅ No API changes required (endpoints already exist)
✅ No data migration needed (fields already present)
✅ No permission leaks (uses existing visibility filters)
✅ Deterministic ranking (category → recent activity → ID)
✅ Explainable suggestions (can tell user why suggested)

## Risk Assessment

**Low risk** - Building on existing Phase 2 work (v0.0.30)
- Suggestion functions already tested
- Discussion links already working
- No new schema changes
- Only missing: frontend surface and admin UI

## Recommendation

This is a **surface layer implementation** - the hard work is done. Just need to:
1. Expose suggestions via API endpoints (already have functions)
2. Add admin UI to show/manage suggestions  
3. Add public display of suggestions
4. Add tests for endpoint/UI
5. Update docs

**Effort: Medium (2-4 hours)**
**Risk: Low**
**Quality: High (reusing proven Phase 2 work)**

