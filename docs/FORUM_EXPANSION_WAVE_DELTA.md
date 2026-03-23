# Forum Expansion Wave (v0.0.30) — Delta Analysis

## Current State

### A. Forum ↔ News/Wiki Integration (Baseline)
**What exists:**
- NewsArticle.discussion_thread_id (primary discussion link)
- WikiPage.discussion_thread_id (primary discussion link)
- NewsArticleForumThread junction table (multiple related threads)
- WikiPageForumThread junction table (multiple related threads)
- relation_type field in both junction tables (default "related")
- list_related_threads_for_article() service function (existing)
- list_related_threads_for_page() service function (existing)
- API routes: news_related_threads_get/add/delete, wiki-equivalent routes
- Public visibility filtering: only public, non-private, active categories

**What is missing:**
- Automatic related-thread suggestions (tag-based, category-based, or hybrid)
- Richer contextual display on News/Wiki pages (showing both primary + related)
- Search/discovery for related-thread visibility on content pages
- Tests specifically for related-thread suggestion consistency

### B. User Profiles and Community Depth
**What exists:**
- User model with: username, email, role, role_level, is_banned, created_at, last_seen_at
- User.to_dict() serializer (basic, without activity stats)
- GET /users/<id> endpoint (basic user data)
- Role system: user, moderator, admin with role_level hierarchy
- Areas system (user_areas junction, user skill areas)

**What is missing:**
- User profile page / dedicated profile routes
- User activity summary (recent threads, recent posts, stats)
- Visible join date and contribution markers on profiles
- Bookmarks and saved threads accessible from profile context
- Profile-level stats: thread count, post count, etc.
- Badges or contribution markers (explicitly unclear if needed; may be skipped)
- Public profile visibility settings (what should non-authenticated users see)

### C. Moderation Professionalization
**What exists:**
- ForumReport model with: target_type, target_id, reported_by, reason, status ("open"), handled_by, handled_at, resolution_note
- list_reports() service function with basic filtering
- update_report_status() service function
- log_activity() for moderation actions (with before/after metadata)
- Moderation routes: report creation, status update, bulk operations implied but not comprehensive
- Admin dashboard references but no dedicated moderation queue or escalation view

**What is missing:**
- Escalation states beyond "open" → handler (no multi-stage escalation)
- Bulk report handling workflow (select multiple, take action, log all)
- Bulk thread/post moderation (lock, hide, delete multiple)
- Review queue views for moderators (escalated reports, recent actions)
- Audit/activity log with richer query/filtering for staff
- Bulk action confirmation UX (frontend)
- Escalation logic (what triggers escalation, who escalates, when resolved)

### D. Search / Performance / Stability
**What exists:**
- Forum search endpoint (hardened in v0.0.29)
- Query pagination with limit validation (1-100)
- Eager loading for author relationships (v0.0.29 improvement)
- 92 forum API tests passing
- Performance indexes on forum tables (migration 028)
- Visibility filtering (SQL-level)

**What is missing:**
- Related-thread search/discovery (surfacing related threads in results)
- Profile/activity query optimization (once implemented)
- Regression tests for related-thread behavior
- Regression tests for new profile features
- Regression tests for new moderation escalation/bulk workflows
- Index review for new queries added in this wave

## Files Expected to Change

### Models (backend/app/models/)
- forum.py: possibly add ForumReportEscalation or extend ForumReport status enum
- Possibly: new model for contribution badges (if Phase 4 includes them)

### Services (backend/app/services/)
- forum_service.py: add functions for bulk actions, auto-suggestions
- news_service.py: possibly add auto-suggest helper, richer related-thread display
- wiki_service.py: possibly add auto-suggest helper, richer related-thread display
- user_service.py: add activity stats, profile enrichment
- Possibly: new moderation_service.py or extend forum_service with escalation/review logic

### Routes (backend/app/api/v1/)
- forum_routes.py: add auto-suggest endpoint, bulk moderation endpoints, review queue
- user_routes.py: add profile endpoint, activity stats endpoint, bookmarks endpoint
- admin_routes.py or new moderation_routes.py: escalation/review endpoints
- news_routes.py: possibly update related-threads display
- wiki_routes.py: possibly update related-threads display

### Frontend (administration-tool/)
- templates/forum/: possibly bulk action UI, review queue
- templates/user/: new user profile page
- templates/moderation/: review queue, escalation dashboard
- static/js/: manage_forum.js (bulk actions), manage_moderation.js (new)

### Tests (backend/tests/)
- test_forum_api.py: add tests for auto-suggestions, bulk actions
- test_user_api.py or new test_profiles.py: profile functionality
- test_moderation_api.py: escalation logic, bulk flows
- test_news_api.py: related-thread discovery changes
- test_wiki_api.py: related-thread discovery changes

### Migrations
- Possibly new migration for: ForumReportEscalation table or status enum changes
- Possibly: user stats denormalization (if performance justifies)

## What Must NOT Be Broadly Refactored
- Auth system (JWT, sessions, permissions)
- Role model and permission checks
- Forum core (categories, threads, posts, likes)
- News/Wiki core (translations, publishing, versioning)
- Database schema (only add, don't redesign)
- Frontend framework (vanilla JS + Jinja2 only)
- API v1 structure

## Integrity, Moderation, Performance Risks

### Integrity Risks
- **Related-thread consistency**: Auto-suggest logic must not create stale or irrelevant suggestions
- **Escalation state machine**: Must prevent invalid transitions (e.g., cannot un-resolve a report)
- **Bulk action atomicity**: Bulk operations must succeed/fail as a group to avoid partial states
- **User data exposure**: Profile activity stats must respect visibility settings and permission

### Moderation Risks
- **Escalation visibility**: Only mods/admins can view escalated reports; non-staff must not see them
- **Audit trail integrity**: All bulk actions must be logged with actor, timestamp, before/after state
- **Permission bypass**: Moderators cannot access non-public categories; admin-only actions restricted

### Performance Risks
- **Auto-suggest computation**: Tag/category matching on every content view could be expensive
- **Related-thread queries**: N+1 if not using batch loading or eager loading
- **Profile activity queries**: Stats aggregation could be slow on high-volume users
- **Bulk action overhead**: Bulk delete/update on 1000+ items could lock tables or timeout

## Mitigation Strategies
- Auto-suggest results limited to small limit (e.g., 5-10)
- Eager load relationships in batch queries
- Bulk actions process in transactions; log each action
- Pagination enforced on all list endpoints
- Profile stats cached or denormalized if necessary
- All moderation queries must enforce visibility SQL-level

## Current Test Coverage
- 92 forum API tests (bookmarks, tags, search, moderation, permissions)
- Forum regression tests in test_forum_api.py
- Auth and user tests in test_api.py, test_web.py
- Missing: related-thread tests, profile tests, bulk moderation tests, escalation tests

## Gaps Summary

| Goal | Gap | Priority |
|------|-----|----------|
| A. Deeper integration | No auto-suggestions; limited contextual display | Medium |
| B. Professional moderation | No escalation states; no bulk action UX; limited audit views | High |
| C. Community profiles | No profile pages; no activity stats; unclear on badges | High |
| D. Search/perf/stability | No regression tests for new features; index gaps TBD | Medium |
