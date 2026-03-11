# Postman – World of Shadows API

## Files

- **WorldOfShadows_API.postman_collection.json** – Collection with all API requests and **test scripts** (status codes and response assertions).
- **WorldOfShadows_Local.postman_environment.json** – Local test environment (localhost:5000, admin credentials).
- **WorldOfShadows_Test.postman_environment.json** – Additional test environment (e.g. for testuser or different base URL).

## Setup

1. In Postman: **Import** → import the collection and both environment files.
2. Select **Environment** in the top right (e.g. "World of Shadows – Local").
3. Start the backend: `cd Backend && flask run` (or `python run.py`), default port 5000.

## Environment variables (full test environment)

| Variable | Description | Example |
|----------|-------------|---------|
| `baseUrl` | Backend base URL | `http://localhost:5000` |
| `apiPath` | API prefix (optional) | `/api/v1` |
| `username` | Login username | `admin` |
| `password` | Login password | (secret) |
| `email` | User email | `admin@example.com` |
| `access_token` | JWT (set by "Login") | – |
| `user_id` | Current user ID (from Login/Me/Register) | – |
| `target_user_id` | User ID for Users Delete (set by "Users List", different user) | – |
| `news_id` | A news ID (set by "News List") | – |
| `register_username` | Username for registration | `postman_user` |
| `register_email` | Email for registration | `postman@example.com` |
| `register_password` | Password for registration | (secret) |

## Flow

1. Run **Login (saves token)** → `access_token` and `user_id` are set.
2. Protected requests (Me, Test Protected, **Users**, **Roles**, **Admin Logs**, News Write) automatically use **Authorization: Bearer {{access_token}}**.
3. **Users List** (admin only): sets `target_user_id` to another user for **Users Delete**.
4. **Roles** (admin only): List, Get, Create, Update, Delete. Roles List/Create set `role_id` for Get/Update/Delete.
5. **Admin Logs List** and **Admin Logs Export** (admin only): activity logs API; 403 if not admin.
6. **News:** List (public) and **News List (editor, include drafts)** set `news_id`; **News Create** sets `news_id` on 201. Use editor/admin token for Create, Update, Delete, Publish, Unpublish.

## Collection Runner

- Select **Collection** → **Run**.
- Choose environment → **Run World of Shadows API**.
- All requests run in sequence; **test scripts** run for each (green/red).

Note: **Users**, **Roles**, and **Admin Logs** require a user with **admin** role (in the DB `role='admin'`). "Register" creates a new user; on repeated runs you may get 409 (username/email already taken) unless `register_username`/`register_email` are changed. For a clean run, execute only **Login** and **System/News/Users/Roles/Admin Logs** first, or use a one-off new registration user.
