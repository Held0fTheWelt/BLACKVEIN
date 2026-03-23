## Forum–Product Integration Delta 0.0.26

### 1. Existing State (Relevant to This Wave)

- **Forum core**
  - `backend/app/models/forum.py`: ForumCategory, ForumThread, ForumPost, ForumPostLike, ForumReport, ForumThreadSubscription with reply/like counters, status fields, soft-delete flags, and basic report/subscription models.
  - `backend/app/services/forum_service.py`: Category/thread/post CRUD, visibility helpers, reply counter recalculation, likes, subscriptions, mention notifications, report helpers, and notification creation.
  - `backend/app/api/v1/forum_routes.py`: Public category/thread/post listing and detail, search endpoint (`GET /api/v1/forum/search`), authenticated thread/post CRUD, likes, reports, subscriptions, notifications, and moderation actions (lock, pin, move, archive, merge, split, hide/unhide).
  - `administration-tool/static/forum.js`: Public forum UI (category + thread list, thread view, replies, likes, reports, moderation controls, split/merge UI, notifications).

- **News**
  - `backend/app/models/news_article.py`: `discussion_thread_id` FK to `forum_threads.id` (nullable, indexed).
  - `backend/app/services/news_service.py`:
    - Public list/detail helpers include `discussion_thread_id` and `discussion_thread_slug` when linked thread exists and is not deleted.
    - Full-text-ish search over title/summary/content via `NewsArticleTranslation`.
  - `backend/app/api/v1/news_routes.py`:
    - Public list: `GET /api/v1/news` with `q`, `category`, `lang`, pagination and sort.
    - Public detail: `GET /api/v1/news/<id_or_slug>` with language handling and publication gates.
    - Admin CRUD and translation endpoints for articles.
    - Discussion linking admin endpoints:
      - `POST /api/v1/news/<int:article_id>/discussion-thread` to link existing forum thread by id.
      - `DELETE /api/v1/news/<int:article_id>/discussion-thread` to unlink.
  - `administration-tool/templates/news.html` + `static/news.js`:
    - Public news list with search, category filter, stable pagination.
  - `administration-tool/templates/news_detail.html` + `static/news.js`:
    - Public news detail renders title/meta/content from `/api/v1/news/<id>`.
    - Currently no explicit news → forum discussion entrypoint in UI.

- **Wiki**
  - `backend/app/models/wiki_page.py`: `discussion_thread_id` FK to `forum_threads.id` (nullable, indexed).
  - `backend/app/services/wiki_service.py`: Page and translation lookup (`get_wiki_page_by_slug`, `get_effective_wiki_translation`).
  - `backend/app/api/v1/wiki_routes.py`:
    - `GET /api/v1/wiki/<slug>` returns title, slug, content_markdown, sanitized HTML, language_code and:
      - `discussion_thread_id` / `discussion_thread_slug` when linked thread exists and is not deleted; otherwise both null.
  - `backend/app/api/v1/wiki_admin_routes.py`:
    - Wiki admin CRUD and translation endpoints.
    - Discussion linking admin endpoints:
      - `POST /api/v1/wiki/<int:page_id>/discussion-thread` to link existing forum thread by id.
      - `DELETE /api/v1/wiki/<int:page_id>/discussion-thread` to unlink.
    - `_page_to_dict` exposes `discussion_thread_id` and derived `discussion_thread_slug` for admin UI.
  - `administration-tool/templates/wiki_public.html`:
    - Public wiki page fetches `/api/v1/wiki/<slug>?lang=…`.
    - If `discussion_thread_slug` is present, renders a “Discuss this page” link to `/forum/threads/<slug>`.

- **Discussion links (News/Wiki ↔ Forum)**
  - Data model fields and link/unlink admin endpoints exist for both NewsArticle and WikiPage.
  - Public wiki JSON already exposes `discussion_thread_id` and `discussion_thread_slug`; public news service does the same at dict level.
  - Tests:
    - `backend/tests/test_news_api.py`: Coverage for linking/unlinking discussion threads and public detail behavior.
    - `backend/tests/test_wiki_public.py`: Coverage for wiki discussion thread exposure in public API.

- **Subscriptions / notifications / mentions / likes**
  - `backend/app/models/forum.py` + `backend/app/models/notification.py`: Foundations for ForumThreadSubscription, Notification, and ForumPostLike.
  - `backend/app/services/forum_service.py`:
    - Subscriptions: `subscribe_thread`, `unsubscribe_thread`, `create_notifications_for_thread_reply`.
    - Mentions: `_create_mention_notifications_for_post` based on `@username` patterns.
    - Likes: `like_post`, `unlike_post` with `ForumPost.like_count`.
  - `backend/app/api/v1/forum_routes.py`:
    - Endpoints for subscribe/unsubscribe, list notifications, mark notifications read.
  - `backend/tests/test_forum_api.py`: Tests for likes, notifications, mentions, subscriptions (some currently fixture-limited).

- **Search / filters / pagination**
  - Forum:
    - `GET /api/v1/forum/search` in `forum_routes.py`: title-based thread search with simple pagination; no category/status/tag filters yet.
    - Category thread lists and post lists include `page`/`limit` with sane defaults, ordered by pinned + last_post_at.
  - News:
    - `GET /api/v1/news`: `q` (title/summary/content via translations), `category`, sort, direction, page, limit.
  - Wiki:
    - Public slug-based lookup; no explicit search API for wiki pages.
  - Frontend:
    - `administration-tool/static/forum.js`: forum list, thread view and notifications with stable pagination.
    - `administration-tool/static/news.js`: news list supports query, category, sort, direction, pagination.

- **Moderation / report / audit capabilities**
  - Model:
    - `ForumReport` with `status` in {open, reviewed, resolved, dismissed}, timestamps and handler.
  - Service:
    - `forum_service.list_reports`, `update_report_status`, `list_reports_for_target`.
  - API:
    - `backend/app/api/v1/forum_routes.py`: endpoints for creating reports, listing open and handled reports, updating status, moderation dashboard counters.
  - UI:
    - `administration-tool/static/forum.js`: report modal on thread page.
    - Management JS/templates (manage forum) provide report list and status updates (per 0.0.20 QA report).
  - Docs:
    - `docs/forum/ModerationWorkflow.md`: high-level moderation workflow including merge/split and report handling.
    - `docs/FORUM_QA_REPORT_0.0.20.md`: QA summary of moderation features and tests.

- **Current tests and Postman**
  - Tests:
    - `backend/tests/test_forum_api.py`: broad coverage of categories, threads, posts, likes, reports, moderation, search, subscriptions, notifications.
    - `backend/tests/test_news_api.py`: includes discussion link behavior.
    - `backend/tests/test_wiki_public.py`: includes wiki discussion link behavior.
  - Postman:
    - `postman/WorldOfShadows_API.postman_collection.json`: forum categories, threads, posts, merge/split, basic reports; news and wiki endpoints including discussion-thread link/unlink routes.

- **Docs / changelog**
  - `docs/FORUM_QA_REPORT_0.0.20.md`: describes forum QA pass and coverage.
  - `docs/FORUM_MERGE_SPLIT_DELTA_0.0.25.md`: details merge/split implementation and tests.
  - `docs/forum/ModerationWorkflow.md`: describes moderation flows including merge/split and current reports.
  - `CHANGELOG.md`:
    - v0.0.20: forum QA and API enrichment.
    - v0.0.25: forum merge/split wave, tests, docs, Postman.

### 2. Gaps for v0.0.26 Wave

- **Forum ↔ product integration**
  - News:
    - Public detail currently includes `discussion_thread_id`/`discussion_thread_slug` in the dict, but:
      - There is no public/UI “Discuss this article” entrypoint on the news detail page.
      - Admin/news management UI does not surface linked discussion state beyond raw ids.
      - There is no concept of “related threads” beyond the single linked discussion thread.
  - Wiki:
    - Public wiki UI already shows a “Discuss this page” link when a discussion thread is linked, but:
      - No related threads beyond the primary discussion thread.
      - Admin tooling is focused on link/unlink only; no overview of discussion activity.
  - Related threads:
    - No explicit related-thread model or API for NewsArticle or WikiPage.
    - No automatic suggestion logic based on categories/tags beyond the single `discussion_thread_id` link.

- **Community comfort**
  - Bookmarks / saved threads:
    - No bookmark or “saved threads” model.
    - No API or UI to mark threads as saved or to list user-specific saved threads.
  - Search and filters:
    - Forum search is limited to thread titles; does not currently search post content.
    - No category/status/tag filters on `/api/v1/forum/search`.
    - Pagination exists but search result ordering is solely by pin + last_post_at; no explicit stable key for tie-breaking.
  - Tags:
    - No tag model for forum threads.
    - No tagging API or UI.
  - Reactions:
    - Only simple like/unlike on posts via `ForumPostLike` and `like_count`.
    - No multi-reaction model or UI.

- **Moderation at operational level**
  - Bulk actions:
    - Forum moderation offers per-thread and per-post operations (lock, pin, hide, etc.) but no bulk endpoints (e.g. bulk hide/unhide or bulk archive).
  - Moderation log / audit log:
    - General `activity_log` model exists (log_activity used widely), but:
      - No dedicated moderation/audit view focused on forum operations.
      - No filtered API for moderation events only.
  - Report workflows:
    - Report status model exists (`open`, `reviewed`, `resolved`, `dismissed`).
    - Moderation UI allows viewing and updating statuses, but:
      - No explicit escalation indicator/state beyond the basic statuses.
      - No bulk resolve/dismiss for multiple reports at once.
      - Filtering is limited to basic status filters.

- **Performance and stability**
  - Query/index review:
    - Forum, news and wiki use straightforward SQLAlchemy queries with indexes from migrations, but:
      - No dedicated indexes yet for high-cardinality search fields (e.g. forum thread title for search, report status for dashboards, bookmark/tag tables that will be added).
  - Search hardening:
    - Forum search short-circuits on empty `q` by returning 0 items; behavior is acceptable but:
      - No limits or normalization for very short queries or extremely broad searches.
      - No validated combination of potential new filters (category/status/tag).
  - Pagination refinement:
    - Thread and post listings, notifications and news lists have simple `page`/`limit` handling, but:
      - No explicit guardrails against unreasonable `limit` values apart from existing caps.
      - No dedicated pagination on new lists (bookmarks, related threads, bulk moderation views) yet.
  - Tests:
    - Forum and discussion-link tests exist but:
      - No tests yet for bookmarks, tags, related threads, bulk moderation, or extended search filters (to be added in this wave).

### 3. Files Expected to Change in This Wave

- **Backend models / migrations**
  - `backend/app/models/forum.py` + new migrations:
    - Add bookmark/saved-thread model.
    - Add tag model and thread–tag association.
    - Optionally add simple related-thread mapping model if not modeled via existing relations.
  - Potentially `backend/app/models/activity_log.py` (if moderation/audit log fields need extension).

- **Backend services**
  - `backend/app/services/forum_service.py`:
    - Bookmark CRUD and listing helpers.
    - Tag creation/normalization, association, and search/filter helpers.
    - Related-thread lookup helpers for News/Wiki integration.
    - Bulk moderation helper functions wrapping existing per-thread/post operations.
    - Search enhancements (filters for category/status/tag, optional content search, safer ordering).
  - `backend/app/services/news_service.py`:
    - Expose related/linked thread information in public and editorial detail payloads in a stable way.
  - `backend/app/services/wiki_service.py`:
    - Expose related/linked thread information for wiki pages where appropriate.

- **Backend API routes**
  - `backend/app/api/v1/forum_routes.py`:
    - New endpoints for bookmarks (save/unsave/list).
    - Extended `/forum/search` query parameters (category/status/tag; optional content search).
    - Endpoints for tagging threads (add/remove tags, list thread tags) and tag-based filtering.
    - Bulk moderation endpoints for safe actions (e.g. bulk hide/unhide posts, bulk archive/unarchive/lock/unlock threads, bulk resolve/dismiss reports).
    - Moderation log / audit endpoints scoped for moderators/admins only.
  - `backend/app/api/v1/news_routes.py`:
    - Optional additions to detail/list responses for related threads and discussion state.
  - `backend/app/api/v1/wiki_routes.py` and `backend/app/api/v1/wiki_admin_routes.py`:
    - Optional additions for exposing related threads and discussion activity where useful to moderators.

- **Administration-tool templates and static assets**
  - Templates:
    - `administration-tool/templates/news_detail.html`:
      - Display “Discuss this article” entrypoint when a linked thread exists.
      - Potentially show related threads block.
    - `administration-tool/templates/wiki_public.html`:
      - Extend discussion UI if related threads are added.
    - Forum management templates (e.g. manage forum/report views):
      - Integrate bulk actions, improved report lists, escalation signals and moderation log views.
  - Static JS:
    - `administration-tool/static/news.js`:
      - Render discussion entrypoint and related threads for news detail.
    - `administration-tool/static/forum.js`:
      - Implement bookmarks UI, improved search filters, tags rendering and filtering, and bulk moderation behaviors.
    - Management JS for moderation dashboard (e.g. `manage_forum.js` or similar) for bulk actions and audit log views.

- **Tests**
  - `backend/tests/test_forum_api.py`:
    - New tests for bookmarks, tags, extended search filters, bulk moderation actions, moderation log, and report workflows.
  - `backend/tests/test_news_api.py`:
    - Tests for improved discussion integration and related threads on news detail.
  - `backend/tests/test_wiki_public.py`:
    - Tests for wiki discussion integration and related threads (where implemented).

- **Postman / docs / changelog**
  - `postman/WorldOfShadows_API.postman_collection.json`:
    - New requests for bookmarks, tags, related threads, bulk moderation endpoints, moderation log, and enhanced News/Wiki discussion APIs.
  - Docs:
    - New or updated docs under `docs/` and `docs/forum/` describing:
      - News/Wiki discussion usage.
      - Related threads semantics.
      - Bookmarks/tags/search/filter usage.
      - Moderation workflows and escalation rules.
  - `CHANGELOG.md`:
    - v0.0.26 entry describing this integration/moderation/performance wave.

### 4. Guardrails – Areas Not to Broadly Refactor

- **Architecture**
  - Preserve split architecture:
    - Backend: Flask API, DB, auth, business logic only.
    - `administration-tool`: Flask-based admin/public UI with Jinja templates and progressive enhancement JS.
  - Do **not** introduce SPA frameworks (React, Vue, Next.js, etc.) or client-side routers.
  - Keep remote-first + PythonAnywhere deployment defaults intact (no localhost-only defaults in config or docs).

- **Auth and permissions**
  - Do not weaken existing role checks (user vs moderator vs admin).
  - Reuse existing helpers (`get_current_user`, `current_user_is_moderator`, `current_user_is_admin`, `require_jwt_moderator_or_admin`) for new endpoints.
  - All new moderation and related-thread endpoints must be permission-checked consistently with existing patterns.

- **Existing forum flows**
  - Avoid broad refactors of core forum models, merge/split logic, notification mechanics, or existing moderation actions.
  - Do not change semantics of `ForumReport.status` values; any escalation state must either reuse existing values or be an additive layer that remains backward compatible.
  - Keep existing notification/event creation logic intact; any extension must be additive and minimal.

- **News/Wiki editorial flows**
  - Do not redesign news or wiki editorial workflows or translation systems.
  - Changes should be strictly additive for discussion integration and related threads exposure.

### 5. High-Risk Integrity and Performance Areas

- **Data integrity**
  - **Bookmarks / tags / related threads:**
    - New models and associations must:
      - Enforce uniqueness where appropriate (e.g. one bookmark per user+thread, normalized tag names, unique thread–tag pairs).
      - Respect thread visibility and deletion status in all list/search endpoints.
  - **Moderation bulk actions:**
    - Bulk operations must:
      - Use the same business rules as per-item operations (e.g. lock, hide, archive) to avoid divergence.
      - Avoid partial updates or inconsistent counters by using transactions and existing helper functions where possible.
  - **Report workflows and escalation:**
    - Any new status or escalation flag must:
      - Be consistent with existing `ForumReport.status` behavior.
      - Not silently reinterpret or break current status values.

- **Performance**
  - **Forum search and filters:**
    - Extending search to include post content or tag filters risks heavier queries on large datasets.
    - Must:
      - Keep queries index-friendly.
      - Avoid unbounded `JOIN` + `LIKE` scans without reasonable constraints.
  - **Moderation dashboards and logs:**
    - Listing many reports or moderation log entries requires stable pagination and appropriate indexes (e.g. on `status`, `created_at`, `handled_at`).
  - **Bookmarks/tags/related threads:**
    - New tables must have indexes on foreign keys and commonly filtered columns (user_id, thread_id, tag name).
    - Queries for user-specific bookmarks and tag-based searches must respect index usage.

