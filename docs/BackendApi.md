# Backend API – Overview

The backend API is served under the prefix **`/api/v1`**. All responses are JSON. Protected endpoints expect the header **`Authorization: Bearer <JWT>`**.

---

## Overview

| Area     | Endpoints                                                                 |
|----------|---------------------------------------------------------------------------|
| **Auth** | Register, Login, Me                                                       |
| **System** | Health, Test Protected                                                   |
| **Users** | List (GET, Admin), Get (GET), Update (PUT), Delete (DELETE, Admin), Assign role (PATCH, Admin), Ban (POST, Admin), Unban (POST, Admin) |
| **News** | List (GET), Detail (GET), Create (POST), Update (PUT), Delete, Publish, Unpublish |

---

## 1. Auth

### 1.1 Register – Create user

**`POST /api/v1/auth/register`**

Creates a new user. When `REGISTRATION_REQUIRE_EMAIL` is **False** (default), email is optional; users without email can log in immediately. When **True**, email is required and a verification email is sent after registration; the user can log in only after clicking the activation link (or when MAIL_ENABLED is off, the link is logged in dev).

- **Rate limit:** 10 per minute  
- **Auth:** None  

**Request body (JSON):**

| Field      | Type   | Required | Description                          |
|------------|--------|----------|--------------------------------------|
| `username` | string | yes      | Unique, 2–80 chars, `a-zA-Z0-9_-`     |
| `email`    | string | no*      | Unique, valid format; *required when REGISTRATION_REQUIRE_EMAIL=1 |
| `password` | string | yes      | Min. 8 chars, upper/lowercase, digit |

**Response:**

- **201 Created:** `{ "id": <number>, "username": "<string>" }`
- **400 Bad Request:** `{ "error": "<message>" }` (e.g. invalid password, missing fields)
- **409 Conflict:** `{ "error": "Username already taken" }` or `"Email already registered"`

---

### 1.2 Login – Get JWT

**`POST /api/v1/auth/login`**

Authenticates with username and password and returns a JWT and user data. If the user has an email and it is not yet verified, login returns 403 (email verification required). Users without email can log in immediately.

- **Rate limit:** 20 per minute  
- **Auth:** None  

**Request body (JSON):**

| Field      | Type   | Required | Description |
|------------|--------|----------|-------------|
| `username` | string | yes      | Username    |
| `password` | string | yes      | Password    |

**Response:**

- **200 OK:**  
  `{ "access_token": "<JWT>", "user": { "id": <number>, "username": "<string>", "role": "<string>" } }`
- **400 Bad Request:** `{ "error": "Invalid or missing JSON body" }` or `"Username and password are required"`
- **401 Unauthorized:** `{ "error": "Invalid username or password" }`
- **403 Forbidden:** `{ "error": "Email not verified." }` – email not yet confirmed; or `{ "error": "Account is restricted." }` – user is banned

---

### 1.3 Me – Current user

**`GET /api/v1/auth/me`**

Returns the user identified by the JWT.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT (required)  

**Response:**

- **200 OK:** `{ "id": <number>, "username": "<string>", "role": "<string>" }`  
  Possible roles: `user`, `moderator`, `admin`.
- **401 Unauthorized:** Missing or invalid token: `{ "error": "Authorization required. Missing or invalid token." }` or `"Invalid or expired token."`
- **403 Forbidden:** `{ "error": "Account is restricted." }` – user is banned
- **404 Not Found:** `{ "error": "User not found" }` (token valid but user no longer in DB)

---

## 2. System

### 2.1 Health – API status

**`GET /api/v1/health`**

Simple API health check.

- **Rate limit:** 100 per minute  
- **Auth:** None  

**Response:**

- **200 OK:** `{ "status": "ok" }`

---

### 2.2 Test Protected – Protected route (example)

**`GET /api/v1/test/protected`**

Example of a protected route. Callable only with a valid JWT.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT (required)  

**Response:**

- **200 OK:**  
  `{ "message": "ok", "user_id": <number>, "username": "<string>" }`
- **401:** Same as Me (missing/invalid token)

---

## 3. News (CRUD)

Public read (list, detail): no auth; only **published** articles. With **optional** JWT (moderator/admin): list can include drafts via `published_only=0` or `include_drafts=1`; detail returns draft articles too (full CRUD read). Write and status changes (Create, Update, Delete, Publish, Unpublish) require JWT and role **moderator** or **admin**; otherwise 401 (no token) or 403 (Forbidden).

---

### 3.1 News List – List articles

**`GET /api/v1/news`**

Returns a paginated list of articles. **Default:** published only. With **Bearer JWT** (moderator or admin) and `published_only=0` or `include_drafts=1`, returns all articles including drafts (for CRUD workflows).

- **Rate limit:** 60 per minute  
- **Auth:** None (public). Optional JWT for moderator/admin to include drafts.  

**Query parameters:**

| Parameter       | Type   | Default        | Description                                      |
|-----------------|--------|----------------|--------------------------------------------------|
| `q`             | string | –              | Search term (searches title/content)            |
| `sort`          | string | `published_at` | Sort: `published_at`, `created_at`, `updated_at`, `title` |
| `direction`     | string | `desc`         | `asc` or `desc`                                 |
| `page`          | int    | 1              | Page number (≥ 1)                                |
| `limit`         | int    | 20             | Items per page (1–100)                           |
| `category`      | string | –              | Filter by category                               |
| `published_only`| string | (effective 1)   | `0` or `false` with moderator/admin JWT: include drafts |
| `include_drafts` | string | –              | `1` or `true` with moderator/admin JWT: include drafts |

**Response:**

- **200 OK:**  
  `{ "items": [ <news object>, ... ], "total": <number>, "page": <number>, "per_page": <number> }`

**News object (excerpt):**  
`id`, `title`, `slug`, `summary`, `content`, `author_id`, `author_name`, `is_published`, `published_at` (ISO-8601), `created_at`, `updated_at`, `cover_image`, `category`

---

### 3.2 News Detail – Get single article (Read)

**`GET /api/v1/news/<id>`**

Returns an article by numeric ID. **Without auth:** only published articles; unpublished or scheduled return 404. **With Bearer JWT (moderator/admin):** returns the article even if draft (so moderators can view/edit drafts).

- **Rate limit:** 60 per minute  
- **Auth:** None (public). Optional JWT for moderator/admin to read drafts.  

**Response:**

- **200 OK:** A single news object (same fields as in list).
- **404 Not Found:** `{ "error": "Not found" }` (not found, or draft without moderator/admin token)

---

### 3.3 News Create – Create article

**`POST /api/v1/news`**

Creates a new news article. Author is taken from the JWT identity.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **moderator** or **admin**  

**Request body (JSON):**

| Field          | Type   | Required | Description           |
|----------------|--------|----------|-----------------------|
| `title`        | string | yes      | Title                 |
| `slug`         | string | yes      | Unique URL slug       |
| `content`      | string | yes      | Content (text)        |
| `summary`      | string | no       | Short summary         |
| `is_published` | bool   | no       | Default: false        |
| `cover_image`  | string | no       | URL or path           |
| `category`     | string | no       | Category              |

**Response:**

- **201 Created:** The created news object.
- **400 Bad Request:** `{ "error": "title, slug, and content are required" }` or other validation errors.
- **401/403:** No token or role not moderator/admin.
- **409 Conflict:** `{ "error": "Slug already in use" }`

---

### 3.4 News Update – Edit article

**`PUT /api/v1/news/<id>`**

Updates an existing article. Only provided fields are changed.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **moderator** or **admin**  

**Request body (JSON):** All fields optional: `title`, `slug`, `summary`, `content`, `cover_image`, `category`.

**Response:**

- **200 OK:** The updated news object.
- **400/401/403:** Same as Create.
- **404 Not Found:** `{ "error": "News not found" }`
- **409 Conflict:** `{ "error": "Slug already in use" }`

---

### 3.5 News Delete – Delete article

**`DELETE /api/v1/news/<id>`**

Deletes an article.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **moderator** or **admin**  

**Response:**

- **200 OK:** `{ "message": "Deleted" }`
- **404 Not Found:** `{ "error": "<message>" }`
- **401/403:** Same as above.

---

### 3.6 News Publish – Publish article

**`POST /api/v1/news/<id>/publish`**

Sets the article to "published" (and `published_at` to now).

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **moderator** or **admin**  

**Response:**

- **200 OK:** The updated news object (with `is_published: true`, `published_at` set).
- **404:** Article not found.
- **401/403:** Same as above.

---

### 3.7 News Unpublish – Unpublish article

**`POST /api/v1/news/<id>/unpublish`**

Sets the article to "not published" (`is_published: false`, `published_at` optionally cleared).

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **moderator** or **admin**  

**Response:**

- **200 OK:** The updated news object.
- **404/401/403:** Same as Publish.

---

## 4. Users (CRUD)

All user endpoints require **Bearer JWT**. **List** and **Delete** are for **admin** role only; **Get** and **Update** for Admin (any user) or for the current user (Self).

### 4.1 Users List – List users (Admin)

**`GET /api/v1/users`**

Paginated list of all users. **Admin** only.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Query parameters:**

| Parameter | Type   | Default | Description                |
|-----------|--------|---------|----------------------------|
| `page`    | int    | 1       | Page number (≥ 1)          |
| `limit`   | int    | 20      | Items per page (1–100)     |
| `q`       | string | –       | Search in username/email   |

**Response:**

- **200 OK:** `{ "items": [ { "id", "username", "role", "email" }, ... ], "total", "page", "per_page" }`
- **403:** Not admin

---

### 4.2 Users Get – Get one user

**`GET /api/v1/users/<id>`**

Single user: **Admin** may fetch any user; otherwise only the **current** user's profile (`id` = JWT user). For self and for admin, the response includes `email`.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT (Admin or Self)  

**Response:**

- **200 OK:** `{ "id", "username", "role" }` or including `"email"` (see above)
- **403:** Other user, not admin
- **404:** User not found

---

### 4.3 Users Update – Edit user

**`PUT /api/v1/users/<id>`**

Update user: **Admin** may update any user and may set `role`; otherwise only **own** profile (no `role`). Body: all fields optional.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT (Admin or Self)  

**Request body (JSON):**

| Field               | Type   | Description                                              |
|---------------------|--------|----------------------------------------------------------|
| `username`          | string | New username (unique, 2–80 chars, `a-zA-Z0-9_-`)         |
| `email`             | string | New email (unique, valid format)                         |
| `password`          | string | New password (same rules as registration)                |
| `current_password`  | string | Required when changing **own** password                  |
| `role`              | string | **Admin** only: `user`, `moderator`, `admin`   |

**Response:**

- **200 OK:** Updated user object (same as Get, including `email` when Admin/Self)
- **400:** Validation error, e.g. "Current password is incorrect"
- **403:** No permission for this user
- **404:** User not found
- **409:** "Username already taken" or "Email already registered"

---

### 4.4 Users Delete – Delete user (Admin)

**`DELETE /api/v1/users/<id>`**

Permanently delete a user. **Admin** only. The user's news entries are kept; `author_id` is set to `null`.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Response:**

- **200 OK:** `{ "message": "Deleted" }`
- **403:** Not admin
- **404:** User not found

---

### 4.5 Users Assign role – Set user role (Admin)

**`PATCH /api/v1/users/<id>/role`**

Set a user's role. **Admin** only. Allowed values: `user`, `moderator`, `admin`.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Request body (JSON):**

| Field  | Type   | Required | Description                    |
|--------|--------|----------|--------------------------------|
| `role` | string | yes      | One of: `user`, `moderator`, `admin` |

**Response:**

- **200 OK:** Updated user object including `email` and ban fields (`is_banned`, `banned_at`, `ban_reason`)
- **400:** Invalid or missing body, or "Invalid role; allowed: user, moderator, admin"
- **403:** Not admin
- **404:** User not found

---

### 4.6 Users Ban – Ban user (Admin)

**`POST /api/v1/users/<id>/ban`**

Ban a user. **Admin** only. Banned users cannot log in (web and API) and are shown the blocked-user page. Admins cannot ban themselves.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Request body (JSON):**

| Field    | Type   | Required | Description        |
|----------|--------|----------|--------------------|
| `reason` | string | no       | Optional ban reason |

**Response:**

- **200 OK:** User object including `email` and ban fields (`is_banned`, `banned_at`, `ban_reason`)
- **400:** "Cannot ban yourself" or invalid body
- **403:** Not admin
- **404:** User not found

---

### 4.7 Users Unban – Unban user (Admin)

**`POST /api/v1/users/<id>/unban`**

Remove ban from a user. **Admin** only.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Request body:** None required (JSON body ignored).

**Response:**

- **200 OK:** User object including `email` and ban fields (`is_banned`, `banned_at`, `ban_reason`)
- **403:** Not admin
- **404:** User not found

---

## 5. Roles (CRUD)

All role endpoints require **Bearer JWT** and **admin** role. Role names: lowercase letters, digits, underscore; 1–20 characters. Default seeded roles: `user`, `moderator`, `admin`. User update and assign-role accept only these role names.

### 5.1 Roles List

**`GET /api/v1/roles`**

Paginated list of roles.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Query parameters:**

| Parameter | Type   | Default | Description           |
|-----------|--------|--------|-----------------------|
| `page`    | int    | 1      | Page number (≥ 1)     |
| `limit`   | int    | 50     | Items per page (1–100)|
| `q`       | string | –      | Search in role name   |

**Response:**

- **200 OK:** `{ "items": [ { "id", "name" }, ... ], "total", "page", "per_page" }`
- **403:** Not admin

### 5.2 Roles Get

**`GET /api/v1/roles/<id>`**

Single role by id.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Response:**

- **200 OK:** `{ "id", "name" }`
- **403:** Not admin
- **404:** Role not found

### 5.3 Roles Create

**`POST /api/v1/roles`**

Create a new role.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Request body (JSON):**

| Field  | Type   | Required | Description                                  |
|--------|--------|----------|----------------------------------------------|
| `name` | string | yes      | Unique name (lowercase, digits, underscore)  |

**Response:**

- **201 Created:** `{ "id", "name" }`
- **400:** Validation error (e.g. invalid name format)
- **403:** Not admin
- **409:** Role name already exists

### 5.4 Roles Update

**`PUT /api/v1/roles/<id>`**

Update a role's name.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Request body (JSON):**

| Field  | Type   | Required | Description                                  |
|--------|--------|----------|----------------------------------------------|
| `name` | string | yes      | New unique name (same format as create)     |

**Response:**

- **200 OK:** `{ "id", "name" }`
- **400/403/404/409:** Same as create

### 5.5 Roles Delete

**`DELETE /api/v1/roles/<id>`**

Delete a role. Fails if any user has this role.

- **Rate limit:** 30 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Response:**

- **200 OK:** `{ "message": "Deleted" }`
- **400:** Cannot delete: users have this role
- **403:** Not admin
- **404:** Role not found

---

## 6. Admin logs

Activity logs are structured entries (auth, news, admin actions) for the admin dashboard. **Admin** role only.

### 6.1 Admin logs list

**`GET /api/v1/admin/logs`**

Paginated list of activity log entries. Newest first.

- **Rate limit:** 60 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Query parameters:**

| Parameter   | Type   | Description                              |
|------------|--------|------------------------------------------|
| `q`        | string | Search in message, action, actor username |
| `category` | string | Filter by category (e.g. auth, news, admin) |
| `status`   | string | Filter by status (success, error, warning, info) |
| `date_from`| string | From date (YYYY-MM-DD)                    |
| `date_to`  | string | To date (YYYY-MM-DD)                     |
| `page`     | int    | Page number (default 1)                  |
| `limit`    | int    | Items per page (default 50, max 100)     |

**Response:**

- **200 OK:** `{ "items": [ { "id", "created_at", "actor_user_id", "actor_username_snapshot", "actor_role_snapshot", "category", "action", "status", "message", "route", "method", "tags", "metadata", "target_type", "target_id" }, ... ], "total", "page", "limit" }`
- **403:** Not admin  
- **401:** Missing or invalid token  

### 6.2 Admin logs export (CSV)

**`GET /api/v1/admin/logs/export`**

Export filtered activity logs as CSV. Same query parameters as list; `limit` max 5000.

- **Rate limit:** 10 per minute  
- **Auth:** Bearer JWT, role **admin**  

**Response:** CSV file (attachment); **403** if not admin.

---

## 7. General

### 7.1 Authentication

- Protected endpoints expect the header: **`Authorization: Bearer <access_token>`**  
  The token is obtained from **`POST /api/v1/auth/login`**.
- Invalid or expired token: **401** with JSON `error`.
- Valid token but insufficient rights (e.g. role `user` for news write): **403 Forbidden**.

### 7.2 Error responses

- API errors are JSON: `{ "error": "<message>" }`.
- Missing or invalid JSON body: **400** with corresponding `error` message.

### 7.3 CORS

- When frontend and backend use different origins, **CORS_ORIGINS** must be set in the backend so the browser allows API requests. Comma-separated list of origins; no spaces around commas, no trailing slashes. Examples: local frontend → `http://127.0.0.1:5001,http://localhost:5001`; frontend on another subdomain (e.g. PythonAnywhere) → `https://deine-frontend-app.pythonanywhere.com`. See `.env.example` and `docs/development/LocalDevelopment.md`.

### 7.4 Rate limits

- Per-endpoint limits are as stated above (e.g. 10/min Register, 20/min Login, 60/min Health/News List). Exceeding them typically returns **429 Too Many Requests** (depending on config).
