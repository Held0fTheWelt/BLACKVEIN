# Forum Community Features

This document covers community-facing forum features: bookmarks, tags, and search/filter parameters. All endpoints are under `/api/v1/`.

---

## Bookmarks

Authenticated users can save threads to their personal bookmark list.

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/forum/threads/<id>/bookmark` | User (JWT) | Bookmark a thread |
| `DELETE` | `/forum/threads/<id>/bookmark` | User (JWT) | Remove a bookmark |
| `GET` | `/forum/bookmarks` | User (JWT) | List own bookmarks |

### Bookmark list response

`GET /forum/bookmarks?page=1&limit=20`

```json
{
  "items": [
    {
      "id": 1,
      "slug": "welcome-to-general",
      "title": "Welcome to General",
      "status": "open",
      "category_id": 1,
      "category_slug": "general",
      "author_id": 3,
      "author_username": "admin",
      "tags": ["announcement"],
      "bookmarked_at": "2026-03-10T09:00:00+00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 20
}
```

### Thread list bookmark state

When a thread list is fetched with a valid JWT, each thread object includes:

```json
{
  "bookmarked_by_me": true
}
```

For anonymous requests, `bookmarked_by_me` is always `false`.

---

## Tags

Tags are normalized labels attached to forum threads. Tag slugs are derived from labels (lowercase, hyphenated). The same tag object is reused across threads.

### How tags work

- Tags are created implicitly when a thread author or moderator/admin calls `PUT /forum/threads/<id>/tags`.
- Tag labels are normalized to slug form on write (e.g. `"Game Lore"` → slug `"game-lore"`, label `"game-lore"`).
- If a tag with the same slug already exists it is reused; no duplicate slugs.
- Tags appear in thread detail responses (`GET /forum/threads/<slug>`), thread list responses (`GET /forum/categories/<slug>/threads`), and bookmark list responses.

### Setting tags on a thread

`PUT /api/v1/forum/threads/<id>/tags` — requires thread author or moderator/admin.

Request body:

```json
{
  "tags": ["lore", "announcement"]
}
```

Response: thread object with updated `tags` array.

### Tag management (moderator/admin)

`GET /api/v1/forum/tags` — list all tags with thread counts. Requires moderator or admin.

Query params:
- `q` — optional text filter (matches label or slug)
- `page` — page number (default 1)
- `limit` — results per page (default 50, max 100)

Response:

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
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

`DELETE /api/v1/forum/tags/<id>` — delete a tag. Requires admin. Returns 409 if the tag is currently associated with any threads.

---

## Search and Filters

### Thread search

`GET /api/v1/forum/search`

Searches thread titles and optionally post content.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | — | Search query. Required (empty queries with no filters return empty results). |
| `category` | string | — | Filter by category slug. |
| `status` | string | — | Filter by thread status (`open`, `locked`, `archived`). |
| `tag` | string | — | Filter by tag slug. |
| `include_content` | `1`/`0` | `0` | If `1`, also searches post content (query must be ≥ 3 characters). |
| `page` | int | 1 | Page number. |
| `limit` | int | 20 | Results per page (max 100). |

Notes:
- Empty or whitespace-only queries with no filters return an empty result set.
- Post-content search is only performed when `include_content=1` and the query is at least 3 characters.
- Overly long queries are truncated before executing.

### Thread list filters

`GET /api/v1/forum/categories/<slug>/threads?page=1&limit=20`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number. |
| `limit` | int | 20 | Results per page (max 100). |

The response includes `total` (count of all visible threads), `page`, `per_page`, and `items`. Each item includes `bookmarked_by_me` (bool) and `tags` (array of label strings).

**Known limitation:** Per-user visibility filtering is applied in Python after loading up to 1000 threads from the database. Categories with more than 1000 non-deleted threads may not surface all threads at higher page offsets.

### Report list filters (moderator/admin)

`GET /api/v1/forum/reports?status=open`

| Param | Type | Description |
|-------|------|-------------|
| `status` | string | Filter: `open`, `reviewed`, `escalated`, `resolved`, `dismissed`. Omit for all. |

Returns all matching reports in a single list (no server-side pagination). The response shape is `{"items": [...]}`.
