# Forum Module - Postman Collection Update Guide

**Status:** Forum endpoints identified and documented for Postman integration
**File to Update:** `postman/WorldOfShadows_API.postman_collection.json`
**Collection Name:** WorldOfShadows_API

## Implementation Note

The following endpoints should be added as a new folder "Forum" in the existing Postman collection, maintaining the current folder structure and auth pattern used for other API endpoints.

---

## Forum Endpoints to Add

### 1. PUBLIC FORUM - Categories

**GET /api/v1/forum/categories**
- **Auth:** Optional (Public)
- **Description:** List all accessible forum categories
- **Query Parameters:** None
- **Example Response:**
  ```json
  {
    "items": [
      {
        "id": 1,
        "slug": "general",
        "title": "General Discussion",
        "description": "General forum discussions",
        "is_active": true,
        "is_private": false,
        "sort_order": 0
      }
    ],
    "total": 1
  }
  ```

**GET /api/v1/forum/categories/:slug**
- **Auth:** Optional (Public)
- **Description:** Get single category by slug
- **URL Parameter:** `slug` (string)
- **Example:** `/api/v1/forum/categories/general`

---

### 2. FORUM THREADS - Public Operations

**GET /api/v1/forum/categories/:categorySlug/threads**
- **Auth:** Optional (Public)
- **Description:** List threads in a category (paginated)
- **URL Parameter:** `categorySlug` (string)
- **Query Parameters:**
  - `page` (integer, default: 1)
  - `limit` (integer, default: 20, max: 100)
- **Example:** `/api/v1/forum/categories/general/threads?page=1&limit=20`

**GET /api/v1/forum/threads/:slug**
- **Auth:** Optional (Public - returns author_username and category info)
- **Description:** Get thread detail by slug
- **URL Parameter:** `slug` (string)
- **Example Response:**
  ```json
  {
    "id": 1,
    "slug": "welcome-to-forum",
    "title": "Welcome to our Forum",
    "author_username": "admin",
    "status": "open",
    "is_locked": false,
    "is_pinned": true,
    "view_count": 150,
    "reply_count": 5,
    "created_at": "2026-03-12T10:00:00Z",
    "category": { "id": 1, "slug": "general", "title": "General" }
  }
  ```

**GET /api/v1/forum/threads/:threadId/posts**
- **Auth:** Optional (JWT supported for `include_hidden` flag)
- **Description:** List posts in a thread (paginated)
- **URL Parameter:** `threadId` (integer)
- **Query Parameters:**
  - `page` (integer, default: 1)
  - `limit` (integer, default: 20, max: 100)
  - `include_hidden` (boolean, moderator+ only)
  - `include_deleted` (boolean, moderator+ only)
- **Example:** `/api/v1/forum/threads/1/posts?page=1&limit=20`
- **Example Post Response:**
  ```json
  {
    "id": 10,
    "thread_id": 1,
    "author_id": 5,
    "author_username": "john_doe",
    "content": "Great discussion!",
    "status": "visible",
    "like_count": 3,
    "liked_by_me": false,
    "created_at": "2026-03-12T10:30:00Z",
    "edited_at": null
  }
  ```

**POST /api/v1/forum/categories/:categorySlug/threads**
- **Auth:** Required (JWT)
- **Description:** Create a new thread in a category
- **URL Parameter:** `categorySlug` (string)
- **Request Body:**
  ```json
  {
    "title": "My Discussion Topic",
    "content": "This is the initial post content..."
  }
  ```
- **Response:** 201 Created with thread object including `author_username` and `category` info

---

### 3. FORUM POSTS - Public Operations

**POST /api/v1/forum/threads/:threadId/posts**
- **Auth:** Required (JWT)
- **Description:** Create a reply post in a thread
- **URL Parameter:** `threadId` (integer)
- **Request Body:**
  ```json
  {
    "content": "This is my reply...",
    "parent_post_id": null
  }
  ```
- **Response:** 201 Created with post object including `author_username` and `liked_by_me`

**PUT /api/v1/forum/posts/:postId**
- **Auth:** Required (JWT) - Authors or moderators/admins
- **Description:** Edit a post (must be author, moderator, or admin)
- **URL Parameter:** `postId` (integer)
- **Request Body:**
  ```json
  {
    "content": "Edited post content..."
  }
  ```
- **Response:** 200 OK with updated post object

**DELETE /api/v1/forum/posts/:postId**
- **Auth:** Required (JWT) - Authors or moderators/admins
- **Description:** Soft-delete a post
- **URL Parameter:** `postId` (integer)
- **Response:** 200 OK

---

### 4. LIKES & INTERACTIONS

**POST /api/v1/forum/posts/:postId/like**
- **Auth:** Required (JWT)
- **Description:** Like a post
- **URL Parameter:** `postId` (integer)
- **Request Body:** `{}` (empty)
- **Response:**
  ```json
  {
    "message": "Liked",
    "like_count": 4,
    "liked_by_me": true
  }
  ```

**DELETE /api/v1/forum/posts/:postId/like**
- **Auth:** Required (JWT)
- **Description:** Unlike a post
- **URL Parameter:** `postId` (integer)
- **Response:**
  ```json
  {
    "message": "Unliked",
    "like_count": 3,
    "liked_by_me": false
  }
  ```

---

### 5. REPORTS & MODERATION

**POST /api/v1/forum/reports**
- **Auth:** Required (JWT)
- **Description:** Submit a report on a post or thread
- **Request Body:**
  ```json
  {
    "target_type": "post",
    "target_id": 10,
    "reason": "Spam or abuse content"
  }
  ```
- **Response:** 201 Created

**GET /api/v1/forum/reports**
- **Auth:** Required (JWT) - Moderator+
- **Description:** List reports (moderators see own + all; admins see all)
- **Query Parameters:**
  - `status` (string: open, reviewed, resolved, dismissed)
  - `page` (integer, default: 1)
  - `limit` (integer, default: 20)

**PUT /api/v1/forum/reports/:reportId**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Update report status
- **URL Parameter:** `reportId` (integer)
- **Request Body:**
  ```json
  {
    "status": "resolved"
  }
  ```
- **Response:** 200 OK with updated report

---

### 6. MODERATION ACTIONS (Public Thread View)

**POST /api/v1/forum/threads/:threadId/lock**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Lock a thread (prevent new replies)
- **Response:** 200 OK with thread object (`is_locked: true`)

**POST /api/v1/forum/threads/:threadId/unlock**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Unlock a thread
- **Response:** 200 OK with thread object (`is_locked: false`)

**POST /api/v1/forum/threads/:threadId/pin**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Pin thread to top
- **Response:** 200 OK with thread object (`is_pinned: true`)

**POST /api/v1/forum/threads/:threadId/unpin**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Unpin thread
- **Response:** 200 OK with thread object (`is_pinned: false`)

**POST /api/v1/forum/posts/:postId/hide**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Hide a post from view
- **Response:** 200 OK with post object (`status: "hidden"`)

**POST /api/v1/forum/posts/:postId/unhide**
- **Auth:** Required (JWT) - Moderator+
- **Description:** Unhide a post
- **Response:** 200 OK with post object (`status: "visible"`)

---

### 7. SEARCH

**GET /api/v1/forum/search**
- **Auth:** Optional (Public)
- **Description:** Search forum threads by title
- **Query Parameters:**
  - `q` (string, required) - Search query
  - `page` (integer, default: 1)
  - `limit` (integer, default: 20, max: 100)
- **Example:** `/api/v1/forum/search?q=security&page=1&limit=20`
- **Response:** Returns visible threads matching query with `author_username` included

---

### 8. ADMIN OPERATIONS - Category Management

**POST /api/v1/forum/admin/categories**
- **Auth:** Required (JWT) - Admin only
- **Description:** Create a new forum category
- **Request Body:**
  ```json
  {
    "slug": "announcements",
    "title": "Announcements",
    "description": "Important announcements from staff",
    "sort_order": 0,
    "is_active": true,
    "is_private": false,
    "required_role": null
  }
  ```
- **Response:** 201 Created

**PUT /api/v1/forum/admin/categories/:categoryId**
- **Auth:** Required (JWT) - Admin only
- **Description:** Update category settings
- **URL Parameter:** `categoryId` (integer)
- **Request Body:** Same as POST (slug cannot be changed)
- **Response:** 200 OK

**DELETE /api/v1/forum/admin/categories/:categoryId**
- **Auth:** Required (JWT) - Admin only
- **Description:** Delete a forum category
- **Response:** 200 OK or error if threads exist

---

## Postman Collection Folder Structure Recommendation

```
Forum (NEW FOLDER)
├── Categories
│   ├── Get all categories
│   ├── Get category detail
├── Threads - Public
│   ├── List threads in category
│   ├── Get thread detail
│   ├── Create new thread
├── Posts - Public
│   ├── List posts in thread
│   ├── Create reply post
│   ├── Edit own post
│   ├── Delete own post
├── Likes
│   ├── Like a post
│   ├── Unlike a post
├── Reports
│   ├── Submit report
│   ├── List reports (mod)
│   ├── Update report status
├── Moderation
│   ├── Lock thread
│   ├── Unlock thread
│   ├── Pin thread
│   ├── Unpin thread
│   ├── Hide post
│   ├── Unhide post
├── Search
│   ├── Search threads
└── Admin
    ├── Create category
    ├── Update category
    └── Delete category
```

---

## Authentication Pattern

All JWT-authenticated endpoints should use the existing Postman pattern:

**Headers:**
```
Authorization: Bearer {{jwt_token}}
Content-Type: application/json
```

**Environment Variables Used:**
- `{{base_url}}` - Backend base URL
- `{{jwt_token}}` - JWT token from login response

---

## Example Test Workflow

1. **Login** to get JWT token
2. **Get Categories** - Public request
3. **Create Thread** - Requires JWT (post `/categories/general/threads`)
4. **Create Post** - Requires JWT (post `/threads/1/posts`)
5. **Like Post** - Requires JWT (post `/posts/10/like`)
6. **Submit Report** - Requires JWT (post `/reports`)
7. **Moderate** - Requires JWT + Moderator role (post `/threads/1/lock`)

---

## Implementation Notes

- All forum endpoints follow REST conventions
- Consistency with existing API collection structure
- Auth patterns match other API collections in project
- Response includes pagination metadata where applicable
- All timestamps in ISO 8601 format
- Safe user fields (author_username) exposed without sensitive data
- Forum endpoints ready for integration testing

**Status:** Guide complete. Ready for manual import or automated integration into Postman collection.
