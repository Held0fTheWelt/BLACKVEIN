# API Reference — World of Shadows Backend

Complete reference for all REST API endpoints in the World of Shadows backend. For authentication details, see `docs/security.md`.

---

## Base Configuration

### URL Format
```
{{baseUrl}}/api/v1/{{endpoint}}
```

### Authentication
- All endpoints require JWT Bearer token in `Authorization` header (except where noted as optional)
- Format: `Authorization: Bearer {{jwt_token}}`
- Obtain token via `POST /api/v1/auth/login`

### Pagination
All list endpoints support:
- `page` (default: 1) — Page number (1-based)
- `limit` (default: 20, max: 100) — Items per page

Response format:
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

### Rate Limiting
- Default: 100 requests per minute
- Specific endpoints: 60 per minute (public reads), 30 per minute (writes)
- Headers in response:
  - `RateLimit-Limit`: Maximum requests
  - `RateLimit-Remaining`: Requests remaining
  - `RateLimit-Reset`: Unix timestamp of reset

---

## Authentication Endpoints

### POST /api/v1/auth/login
Login with username and password; get JWT token.

**Request:**
```json
{
  "username": "demo",
  "password": "YourPassword1"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Response 401:**
```json
{"error": "Invalid credentials"}
```

---

### GET /api/v1/auth/me
Get current authenticated user.

**Auth:** Required
**Response 200:**
```json
{
  "id": 1,
  "username": "demo",
  "email": "demo@example.com",
  "role_id": 1,
  "role_name": "admin",
  "role_level": 100,
  "is_banned": false,
  "created_at": "2026-03-01T10:00:00+00:00",
  "last_seen_at": "2026-03-14T15:30:00+00:00",
  "allowed_features": ["manage.news", "manage.forum", ...]
}
```

---

## Forum Endpoints

### Categories

#### GET /api/v1/forum/categories
List visible forum categories.

**Auth:** Optional
**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "slug": "general",
      "title": "General Discussion",
      "description": "Off-topic conversations",
      "thread_count": 42,
      "is_archived": false
    }
  ],
  "total": 5
}
```

---

#### GET /api/v1/forum/categories/<slug>
Get one category by slug.

**Auth:** Optional
**Response 200:**
```json
{
  "id": 1,
  "slug": "general",
  "title": "General Discussion",
  "description": "Off-topic conversations",
  "thread_count": 42,
  "post_count": 156,
  "is_archived": false,
  "is_private": false
}
```

---

### Threads

#### GET /api/v1/forum/categories/<slug>/threads
List threads in a category.

**Auth:** Optional
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "slug": "welcome-thread",
      "title": "Welcome to the forum!",
      "status": "open",
      "is_pinned": true,
      "is_locked": false,
      "is_featured": false,
      "is_archived": false,
      "view_count": 256,
      "reply_count": 12,
      "author_username": "admin",
      "category": {
        "id": 1,
        "slug": "general",
        "title": "General Discussion"
      },
      "created_at": "2026-03-01T10:00:00+00:00",
      "last_post_at": "2026-03-14T15:30:00+00:00",
      "tags": [
        {"slug": "welcome", "label": "welcome"}
      ],
      "bookmarked_by_me": false
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

#### GET /api/v1/forum/threads/<slug>
Get thread detail with posts.

**Auth:** Optional
**Response 200:**
```json
{
  "id": 1,
  "slug": "welcome-thread",
  "title": "Welcome to the forum!",
  "status": "open",
  "is_pinned": true,
  "is_locked": false,
  "is_featured": false,
  "is_archived": false,
  "view_count": 256,
  "reply_count": 12,
  "author_username": "admin",
  "author_id": 1,
  "category": {
    "id": 1,
    "slug": "general",
    "title": "General Discussion"
  },
  "created_at": "2026-03-01T10:00:00+00:00",
  "last_post_at": "2026-03-14T15:30:00+00:00",
  "tags": [
    {"slug": "welcome", "label": "welcome"}
  ],
  "subscribed_by_me": false,
  "bookmarked_by_me": false,
  "posts": [
    {
      "id": 1,
      "thread_id": 1,
      "content": "Welcome to our community!",
      "author_username": "admin",
      "author_id": 1,
      "status": "visible",
      "is_hidden": false,
      "like_count": 3,
      "liked_by_me": false,
      "created_at": "2026-03-01T10:00:00+00:00",
      "updated_at": "2026-03-01T10:00:00+00:00"
    }
  ]
}
```

---

#### POST /api/v1/forum/categories/<slug>/threads
Create a new thread.

**Auth:** Required (user+)
**Request:**
```json
{
  "title": "My new discussion",
  "content": "Here's what I want to discuss..."
}
```

**Response 201:**
```json
{
  "id": 42,
  "slug": "my-new-discussion",
  "title": "My new discussion",
  "status": "open",
  "author_id": 5,
  "author_username": "shadow_runner",
  "created_at": "2026-03-14T16:00:00+00:00"
}
```

**Response 403:**
```json
{"error": "You cannot create threads in this category"}
```

---

#### PUT /api/v1/forum/threads/<int:thread_id>
Update thread (title/content).

**Auth:** Required (author/mod/admin)
**Request:**
```json
{
  "title": "Updated title",
  "content": "Updated content"
}
```

**Response 200:**
```json
{
  "id": 1,
  "slug": "updated-title",
  "title": "Updated title",
  "updated_at": "2026-03-14T16:00:00+00:00"
}
```

---

#### DELETE /api/v1/forum/threads/<int:thread_id>
Soft-delete a thread (author/mod/admin only).

**Auth:** Required
**Response 204:** (no content)

---

### Posts

#### GET /api/v1/forum/threads/<int:thread_id>/posts
Get posts in a thread.

**Auth:** Optional
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "thread_id": 1,
      "content": "This is a reply.",
      "author_username": "user",
      "author_id": 2,
      "status": "visible",
      "is_hidden": false,
      "like_count": 2,
      "liked_by_me": false,
      "created_at": "2026-03-01T10:00:00+00:00"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20
}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/posts
Post a reply.

**Auth:** Required
**Request:**
```json
{
  "content": "Great discussion!",
  "parent_post_id": null
}
```

**Response 201:**
```json
{
  "id": 42,
  "thread_id": 1,
  "content": "Great discussion!",
  "author_id": 5,
  "author_username": "shadow_runner",
  "created_at": "2026-03-14T16:00:00+00:00"
}
```

---

#### PUT /api/v1/forum/posts/<int:post_id>
Edit own post.

**Auth:** Required (author/mod/admin)
**Request:**
```json
{
  "content": "Edited content"
}
```

**Response 200:**
```json
{
  "id": 42,
  "content": "Edited content",
  "updated_at": "2026-03-14T16:00:00+00:00"
}
```

---

#### DELETE /api/v1/forum/posts/<int:post_id>
Soft-delete own post.

**Auth:** Required
**Response 204:** (no content)

---

### Likes & Reactions

#### POST /api/v1/forum/posts/<int:post_id>/like
Like a post (user only; idempotent).

**Auth:** Required
**Response 200:**
```json
{"message": "Liked"}
```

---

#### DELETE /api/v1/forum/posts/<int:post_id>/like
Unlike a post (idempotent).

**Auth:** Required
**Response 200:**
```json
{"message": "Unliked"}
```

---

### Bookmarks

#### POST /api/v1/forum/threads/<int:thread_id>/bookmark
Bookmark a thread (idempotent).

**Auth:** Required
**Response 200:**
```json
{"message": "Bookmarked"}
```

---

#### DELETE /api/v1/forum/threads/<int:thread_id>/bookmark
Remove bookmark (idempotent).

**Auth:** Required
**Response 200:**
```json
{"message": "Unbookmarked"}
```

---

#### GET /api/v1/forum/bookmarks
List user's bookmarked threads.

**Auth:** Required
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 42,
      "slug": "interesting-discussion",
      "title": "Interesting Discussion",
      "reply_count": 8,
      "author_username": "admin",
      "category": {"id": 1, "slug": "general", "title": "General"},
      "tags": [{"slug": "lore", "label": "lore"}],
      "last_post_at": "2026-03-14T15:30:00+00:00"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

### Tags

#### GET /api/v1/forum/tags
List all tags (paginated, searchable).

**Auth:** Required (moderator+)
**Params:**
- `q` — Search query (optional)
- `page` (default: 1)
- `limit` (default: 50, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "slug": "lore",
      "label": "lore",
      "thread_count": 12,
      "created_at": "2026-03-01T10:00:00+00:00"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 50
}
```

---

#### GET /api/v1/forum/tags/popular
Get popular tags by usage.

**Auth:** Optional
**Params:**
- `limit` (default: 10, max: 50)

**Response 200:**
```json
{
  "items": [
    {
      "slug": "lore",
      "label": "lore",
      "thread_count": 42
    },
    {
      "slug": "spoilers",
      "label": "spoilers",
      "thread_count": 28
    }
  ]
}
```

---

#### GET /api/v1/forum/tags/<slug>
Get tag detail with threads.

**Auth:** Optional
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "id": 1,
  "slug": "lore",
  "label": "lore",
  "thread_count": 12,
  "threads": [
    {
      "id": 1,
      "slug": "world-history",
      "title": "World History",
      "reply_count": 5,
      "author_username": "admin"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20
}
```

---

#### PUT /api/v1/forum/threads/<int:thread_id>/tags
Set tags on a thread.

**Auth:** Required (author/mod/admin)
**Request:**
```json
{
  "tags": ["lore", "main-quest", "spoilers"]
}
```

**Response 200:**
```json
{
  "tags": [
    {"slug": "lore", "label": "lore"},
    {"slug": "main-quest", "label": "main-quest"},
    {"slug": "spoilers", "label": "spoilers"}
  ]
}
```

---

#### DELETE /api/v1/forum/tags/<int:tag_id>
Delete a tag (admin only; returns 409 if in use).

**Auth:** Required (admin)
**Response 204:** (no content)

**Response 409:**
```json
{"error": "Tag is currently in use by 12 threads"}
```

---

### Search

#### GET /api/v1/forum/search
Full-text forum search with filters.

**Auth:** Optional
**Params:**
- `q` — Search term (optional, max 200 chars)
- `category` — Filter by category slug (optional)
- `status` — Filter by status: open, locked, archived, hidden (optional)
- `tag` — Filter by tag slug (optional)
- `include_content` — Include post content in search (0 or 1, optional)
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "slug": "first-thread",
      "title": "First thread",
      "status": "open",
      "is_pinned": true,
      "reply_count": 8,
      "author_username": "admin"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

---

### Reports

#### POST /api/v1/forum/reports
Create a report for a thread or post.

**Auth:** Required
**Request:**
```json
{
  "target_type": "post",
  "target_id": 123,
  "reason": "inappropriate content"
}
```

**Response 201:**
```json
{
  "id": 1,
  "target_type": "post",
  "target_id": 123,
  "status": "open",
  "reported_by": 5,
  "reason": "inappropriate content",
  "created_at": "2026-03-14T16:00:00+00:00"
}
```

---

#### GET /api/v1/forum/reports
List reports (mod/admin).

**Auth:** Required (moderator+)
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)
- `status` (optional: open, reviewed, escalated, resolved, dismissed)
- `target_type` (optional: thread, post)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "target_type": "post",
      "target_id": 123,
      "target_title": "Inappropriate post content",
      "status": "open",
      "reported_by_username": "concerned_user",
      "reason": "inappropriate content",
      "created_at": "2026-03-14T16:00:00+00:00",
      "handled_by_username": null,
      "handled_at": null,
      "resolution_note": null
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 20
}
```

---

#### GET /api/v1/forum/reports/<int:report_id>
Get report detail (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{
  "id": 1,
  "target_type": "post",
  "target_id": 123,
  "target_title": "Post content",
  "status": "open",
  "reported_by_id": 5,
  "reported_by_username": "concerned_user",
  "reason": "inappropriate content",
  "created_at": "2026-03-14T16:00:00+00:00",
  "handled_by_id": null,
  "handled_by_username": null,
  "handled_at": null,
  "resolution_note": null
}
```

---

#### PUT /api/v1/forum/reports/<int:report_id>
Update report status (mod/admin).

**Auth:** Required (moderator+)
**Request:**
```json
{
  "status": "resolved",
  "resolution_note": "Post has been hidden"
}
```

**Response 200:**
```json
{
  "id": 1,
  "status": "resolved",
  "handled_by": 1,
  "handled_at": "2026-03-14T16:00:00+00:00",
  "resolution_note": "Post has been hidden"
}
```

---

#### POST /api/v1/forum/reports/bulk-status
Update multiple reports at once (mod/admin).

**Auth:** Required (moderator+)
**Request:**
```json
{
  "report_ids": [1, 2, 3],
  "status": "resolved",
  "resolution_note": "Spam removed"
}
```

**Response 200:**
```json
{
  "updated": 3,
  "message": "3 reports updated"
}
```

---

### Moderation Queues

#### GET /api/v1/forum/moderation/escalation-queue
Get escalated reports by priority.

**Auth:** Required (moderator+)
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "target_type": "post",
      "target_title": "Serious violation",
      "reason": "threatening behavior",
      "reported_by_username": "user1",
      "created_at": "2026-03-14T10:00:00+00:00",
      "status": "escalated",
      "priority": 1
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 20
}
```

---

#### GET /api/v1/forum/moderation/review-queue
Get open and recent reports for review.

**Auth:** Required (moderator+)
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 2,
      "target_type": "thread",
      "target_title": "Questionable discussion",
      "reason": "rule violation",
      "reported_by_username": "user2",
      "created_at": "2026-03-13T14:00:00+00:00",
      "status": "open"
    }
  ],
  "total": 8,
  "page": 1,
  "per_page": 20
}
```

---

#### GET /api/v1/forum/moderation/moderator-assigned
Get reports assigned to the calling moderator.

**Auth:** Required (moderator+)
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 5,
      "target_type": "post",
      "target_title": "Questionable content",
      "reason": "potential spam",
      "reported_by_username": "user3",
      "created_at": "2026-03-12T09:00:00+00:00",
      "status": "open",
      "assigned_to_id": 2,
      "assigned_to_username": "moderator"
    }
  ],
  "total": 2,
  "page": 1,
  "per_page": 20
}
```

---

#### GET /api/v1/forum/moderation/handled-reports
Get resolved and dismissed reports.

**Auth:** Required (moderator+)
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 10,
      "target_type": "post",
      "target_title": "Removed post",
      "status": "resolved",
      "handled_by_username": "admin",
      "handled_at": "2026-03-10T15:00:00+00:00",
      "resolution_note": "Post violated guidelines"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 20
}
```

---

#### POST /api/v1/forum/moderation/reports/<int:report_id>/assign
Assign report to a moderator.

**Auth:** Required (moderator+)
**Request:**
```json
{
  "moderator_id": 2,
  "note": "This needs urgent review"
}
```

**Response 200:**
```json
{
  "id": 1,
  "assigned_to_id": 2,
  "assigned_to_username": "moderator",
  "assigned_at": "2026-03-14T16:00:00+00:00"
}
```

---

### Moderation Actions

#### POST /api/v1/forum/threads/<int:thread_id>/lock
Lock a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread locked"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/unlock
Unlock a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread unlocked"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/pin
Pin a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread pinned"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/unpin
Unpin a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread unpinned"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/feature
Feature a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread featured"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/unfeature
Unfeature a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread unfeatured"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/archive
Archive a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread archived"}
```

---

#### POST /api/v1/forum/threads/<int:thread_id>/unarchive
Unarchive a thread (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Thread unarchived"}
```

---

#### POST /api/v1/forum/posts/<int:post_id>/hide
Hide a post (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Post hidden"}
```

---

#### POST /api/v1/forum/posts/<int:post_id>/unhide
Unhide a post (mod/admin).

**Auth:** Required (moderator+)
**Response 200:**
```json
{"message": "Post unhidden"}
```

---

## User Endpoints

### GET /api/v1/users/<int:user_id>/profile
Get user profile with activity.

**Auth:** Optional
**Response 200:**
```json
{
  "id": 5,
  "username": "shadow_runner",
  "email": "user@example.com",
  "role_id": 1,
  "role_name": "user",
  "role_level": 0,
  "is_banned": false,
  "created_at": "2026-03-01T10:00:00+00:00",
  "last_seen_at": "2026-03-14T15:30:00+00:00",
  "thread_count": 8,
  "post_count": 42,
  "recent_threads": [
    {
      "id": 1,
      "slug": "my-thread",
      "title": "My thread",
      "created_at": "2026-03-14T10:00:00+00:00"
    }
  ],
  "recent_posts": [
    {
      "id": 100,
      "content": "Great reply!",
      "thread_id": 1,
      "created_at": "2026-03-14T11:00:00+00:00"
    }
  ]
}
```

---

### GET /api/v1/users/<int:user_id>/bookmarks
Get user's bookmarked threads.

**Auth:** Optional
**Params:**
- `page` (default: 1)
- `limit` (default: 20, max: 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 42,
      "slug": "interesting-discussion",
      "title": "Interesting Discussion",
      "reply_count": 8,
      "author_username": "admin",
      "category": {"id": 1, "slug": "general", "title": "General"},
      "last_post_at": "2026-03-14T15:30:00+00:00"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

## News Endpoints

### GET /api/v1/news/<id_or_slug>
Get a single news article by ID (integer) or slug (string).

**Auth:** Optional (requires JWT for draft articles)
**Params:**
- `lang` (optional) — Language code for translation

**Response 200:**
```json
{
  "id": 1,
  "title": "New Game Announcement",
  "slug": "new-game-announcement",
  "summary": "An exciting new game is coming",
  "content": "Full article content...",
  "author_id": 5,
  "author_name": "Editor",
  "is_published": true,
  "published_at": "2026-03-14T10:00:00+00:00",
  "created_at": "2026-03-14T09:00:00+00:00",
  "discussion": {
    "type": "primary",
    "thread_id": 42,
    "thread_slug": "game-announcement-discussion",
    "thread_title": "Let's discuss the new game",
    "category": "general"
  },
  "related_threads": [
    {
      "id": 43,
      "slug": "similar-game-thread",
      "title": "Similar Game Discussion",
      "reply_count": 8,
      "author_username": "user1",
      "category": {"id": 1, "slug": "general", "title": "General"},
      "type": "related"
    }
  ],
  "suggested_threads": [
    {
      "id": 44,
      "slug": "game-lore-discussion",
      "title": "Game Lore Thread",
      "reply_count": 5,
      "author_username": "user2",
      "category": {"id": 1, "slug": "general", "title": "General"},
      "type": "suggested",
      (removed - not supported by current implementation)
    }
  ]
}
```

**Response 404:** (Article not found or draft without authorization)
```json
{"error": "Not found"}
```

---

### GET /api/v1/news/<id>/suggested-threads
Get suggested related threads for an article (separate endpoint).

**Auth:** Optional
**Params:**
- `limit` (default: 5, max: 10)

**Response 200:**
```json
{
  "items": [
    {
      "id": 44,
      "slug": "game-lore-discussion",
      "title": "Game Lore Thread",
      "reply_count": 5,
      "author_username": "user2",
      "category": {"id": 1, "slug": "general", "title": "General"}
    }
  ]
}
```

---

## Wiki Endpoints

### GET /api/v1/wiki/<slug>
Get a wiki page by slug with integrated discussion context.

**Auth:** Optional
**Params:**
- `lang` (optional) — Language code for translation

**Response 200:**
```json
{
  "title": "World Lore Guide",
  "slug": "world-lore-guide",
  "content_markdown": "# Lore\n\nDetailed lore content...",
  "html": "<h1>Lore</h1>\n<p>Detailed lore content...</p>",
  "language_code": "en",
  "discussion": {
    "type": "primary",
    "thread_id": 50,
    "thread_slug": "lore-discussion",
    "thread_title": "Let's discuss the world lore",
    "category": "general"
  },
  "related_threads": [
    {
      "id": 51,
      "slug": "related-lore-thread",
      "title": "Related Lore Discussion",
      "reply_count": 12,
      "author_username": "user3",
      "category": {"id": 1, "slug": "general", "title": "General"},
      "type": "related"
    }
  ],
  "suggested_threads": [
    {
      "id": 52,
      "slug": "category-discussion",
      "title": "General Discussion",
      "reply_count": 20,
      "author_username": "user4",
      "category": {"id": 1, "slug": "general", "title": "General"},
      "type": "suggested",
      (removed - not supported by current implementation)
    }
  ]
}
```

**Response 404:** (Page not found)
```json
{"error": "Not found"}
```

---

### GET /api/v1/wiki/<int:page_id>/suggested-threads
Get suggested related threads for a wiki page (separate endpoint).

**Auth:** Optional
**Params:**
- `limit` (default: 5, max: 10)

**Response 200:**
```json
{
  "items": [
    {
      "id": 52,
      "slug": "category-discussion",
      "title": "General Discussion",
      "reply_count": 20,
      "author_username": "user4",
      "category": {"id": 1, "slug": "general", "title": "General"}
    }
  ]
}
```

---

## Discussion Context Overview

### Types of Thread Links in News/Wiki

When retrieving a news article or wiki page, you can see three distinct types of forum thread links:

#### 1. Primary Discussion (`type: "primary"`)
- One discussion thread per article/page, representing the main discussion space
- Set by editors via `POST /api/v1/news/<id>/discussion-thread` or `POST /api/v1/wiki/<slug>/discussion-thread`
- Included in the response as a single `discussion` object (or `null`)
- Represents the canonical conversation space for that content

#### 2. Related Threads (`type: "related"`)
- Multiple manually-curated threads linked by editors
- Set via `POST /api/v1/news/<id>/related-threads` or `POST /api/v1/wiki/<slug>/related-threads`
- Included in the response as an array `related_threads`
- Represent topically-connected discussions chosen explicitly by editors
- Can be removed by editors via DELETE endpoints

#### 3. Suggested Threads (`type: "suggested"`)
- Automatically generated suggestions based on category matching
- Computed deterministically without manual curation
- Included in the response as an array `suggested_threads`
- Each suggestion includes a `reason` field explaining the match
- Excludes duplicates with primary discussion and manually-linked related threads
- Limits to 5 per content item by default (max 10)

### Auto-Suggestion Strategy

Automatic suggestions use these signals:
- **Primary ranking:** Shared category with the content
- **Secondary ranking:** Recent activity (post/reply count, last activity timestamp)
- **Visibility:** Only public (non-deleted, non-hidden, non-archived) threads
- **Deduplication:** Excludes primary discussion and manually linked related threads

---

## Error Responses

### Common Error Codes

**400 Bad Request**
```json
{
  "error": "Invalid request",
  "details": "Missing required field: title"
}
```

**401 Unauthorized**
```json
{
  "error": "Authentication required"
}
```

**403 Forbidden**
```json
{
  "error": "You do not have permission to perform this action"
}
```

**404 Not Found**
```json
{
  "error": "Resource not found"
}
```

**409 Conflict**
```json
{
  "error": "Conflict",
  "details": "Tag is currently in use by 12 threads"
}
```

**429 Too Many Requests**
```json
{
  "error": "Rate limit exceeded"
}
```

**500 Internal Server Error**
```json
{
  "error": "Internal server error"
}
```

---

## Development Configuration

### Local Development
```bash
# Backend (default port 5000)
BACKEND_API_URL=http://127.0.0.1:5000

# Frontend (default port 5001)
BACKEND_API_URL=http://127.0.0.1:5000
```

### Remote (Production)
```bash
# Backend (PythonAnywhere default)
BACKEND_API_URL=https://yourusername.pythonanywhere.com

# Frontend
BACKEND_API_URL=https://yourusername.pythonanywhere.com
```

---

## Postman Collection

Import the Postman collection at `postman/WorldOfShadows_API.postman_collection.json` to test all endpoints.

**Collection Features:**
- Pre-configured base URL variable (`baseUrl`)
- JWT token variable (`jwt_token`) — populate after login
- Example requests for all endpoints
- Common error cases documented

---

## Rate Limiting

All endpoints are rate-limited by default:

| Endpoint Type | Limit |
|---------------|-------|
| Public read (GET) | 60 per minute |
| Authenticated read (GET) | 100 per minute |
| Write operations (POST/PUT/DELETE) | 30 per minute |

Rate limit info available in response headers:
- `RateLimit-Limit`
- `RateLimit-Remaining`
- `RateLimit-Reset`

---

## See Also

- [Security Documentation](docs/security.md)
- [Phase Summary](docs/PHASE_SUMMARY.md)
- [Community Features](docs/FORUM_COMMUNITY_FEATURES.md)
- [Moderation Workflow](docs/forum/ModerationWorkflow.md)
- [Development Setup](docs/development/LocalDevelopment.md)

---

*Last updated: 2026-03-14*
*Version: 0.0.32+*
