# Phase 1 Audit – Roles, Permissions, News Access, User Admin, Blocked-User

Audit-only document for the role and access-control upgrade. No feature implementation.

## 1. User and role models

- **User:** `Backend/app/models/user.py` – `role_id` (FK to `roles`), property `role` returns role name. No ban-related fields.
- **Role:** `Backend/app/models/role.py` – table `roles` (id, name). Constants: NAME_USER, NAME_MODERATOR, NAME_EDITOR, NAME_ADMIN. Seed: user, moderator, editor, admin.
- **User constants:** user.py defines ROLE_USER, ROLE_MODERATOR, ROLE_EDITOR, ROLE_ADMIN.
- **Migrations:** 004 adds users.role (string, server_default "editor"); 007 adds roles table, users.role_id, backfill, drops role string.

## 2. Auth and permissions

- **Web session:** `web/routes.py` – /login (verify_user, then email-verification check, then session). `web/auth.py`: require_web_login, require_web_admin (session + is_admin).
- **API JWT:** `api/v1/auth_routes.py` – POST login (verify_user, email check, then JWT). GET /auth/me with jwt_required.
- **Permission helpers:** `auth/permissions.py` – get_current_user(), current_user_is_admin(), current_user_can_write_news(). can_write_news() in User model: editor or admin.

## 3. News write access

- **File:** `api/v1/news_routes.py`. All write endpoints: @jwt_required(), then current_user_can_write_news() or 403.
- **User.can_write_news():** returns True for role in (ROLE_EDITOR, ROLE_ADMIN). No moderator in write path today.

## 4. User API and admin

- **User API:** GET list, GET one, PUT update, DELETE – list/delete admin-only; get/update admin or self. PUT allows admin to set role.
- **Dashboard:** require_web_login; logs/export use require_web_admin.
- **Admin API:** admin_routes (logs, export) and role_routes: all require current_user_is_admin().

## 5. Banned/blocked user

- **None.** No is_banned, banned_at, ban_reason. verify_user and login flows do not check ban. No blocked-user template or view.

## 6. Templates

- Login, register, register_pending, dashboard, forgot_password, reset_password, resend_verification. No blocked/banned page.

## 7. Postman

- Collection: Auth, System, News (includes "editor, include drafts", Create/Update/Publish/Unpublish/Delete), Users, Roles, Admin Logs.
- Descriptions and variables reference editor role; no ban/unban or assign-role requests; no moderator-specific flow.

## 8. Editor references (to replace with moderator)

| Location | Usage |
|----------|--------|
| app/models/user.py | ROLE_EDITOR, can_write_news uses editor |
| app/models/role.py | NAME_EDITOR, seed editor |
| app/auth/permissions.py | Docstring "editor or admin" |
| app/api/v1/news_routes.py | Docstrings "editor/admin" |
| run.py | seed-dev-user uses editor_role, NAME_EDITOR |
| migrations 004, 007 | server_default editor, seed editor |
| tests/conftest.py | editor_user, editor_headers, NAME_EDITOR |
| tests/test_news_api.py | editor_headers, "editor" in tests |
| tests/test_admin_logs.py | editor in role helpers |

## 9. Gaps

- **Editor → moderator:** All editor usage must become moderator; migration for existing editor → moderator.
- **Ban state:** Add is_banned, banned_at, ban_reason; enforce in login (web + API) and in session/JWT use; add blocked-user view.
- **Admin-only role/ban API:** Today PUT user can set role; need dedicated assign-role and ban/unban endpoints and enforcement.
- **News write:** Change from editor-or-admin to moderator-or-admin using centralized helper.
