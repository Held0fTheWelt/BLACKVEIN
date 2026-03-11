# Phase 1 Audit – Admin Logs & Role System

Audit of the current codebase to implement production admin logging, real dashboard logs, and an extensible User/Moderator/Admin role system.

---

## 1. Dashboard logs UI and demo data

### Template: `Backend/app/web/templates/dashboard.html`
- **Logs area:** View `#view-logs` (hidden by default; shown when "Logs" nav item is clicked).
- **Structure:** Table with columns: Date, User, Category, Action, Status, Tags.
- **Filters:** `#filter-search`, `#filter-category` (auth/api/admin), `#filter-status` (success/error/warning), `#filter-date-from`, `#filter-date-to`, Clear button.
- **Actions:** `#export-csv` button.
- **Footer:** `#table-count` shows "X entries".
- **No server-side data:** Table body `#table-body` is empty in HTML; filled by JavaScript.

### JavaScript: `Backend/app/static/dashboard.js`
- **DEMO_ROWS:** Hardcoded array of ~30 fake log entries (lines 9–38). Fields: `date`, `user`, `category`, `action`, `status`, `tags`.
- **filterRows():** Filters DEMO_ROWS client-side by category, status, date range, and search (user + action + tags).
- **filterAndRender():** Clears `#table-body`, appends one `<tr>` per filtered row, updates `#table-count`.
- **exportCsv():** Builds CSV from filtered DEMO_ROWS (Date,User,Category,Action,Status,Tags), triggers download.
- **Initialization:** `init()` calls `filterAndRender()` so the table shows demo data on load.
- **Where fake logs come from:** Exclusively from the `DEMO_ROWS` array in `dashboard.js`. No API call, no server data.

**Conclusion:** Remove reliance on DEMO_ROWS; add API fetch for logs, loading/empty/error states, and wire filters + CSV export to real data (or server-side export).

---

## 2. User model and role

### Model: `Backend/app/models/user.py`
- **Columns:** id, username, email, password_hash, **role** (String(20), nullable=False, default="user"), email_verified_at.
- **Constants:** `ROLE_USER`, `ROLE_EDITOR`, `ROLE_ADMIN`. **No ROLE_MODERATOR.**
- **Methods:** `to_dict(include_email=False)` (includes role), `can_write_news()` → True for editor or admin only.
- **Default role:** New instances use `default="user"` in Python. `user_service.create_user()` explicitly sets `role=User.ROLE_USER`.

### Migration: `Backend/migrations/versions/004_add_user_role.py`
- Adds column `role` with `server_default="editor"`. **Discrepancy:** DB default is "editor", application default for new users is "user". Existing DBs created by this migration have editor as default for rows inserted without role; new code uses User.ROLE_USER. For a clean role foundation, consider a follow-up migration to set server_default to "user" and introduce a proper Role table.

**Conclusion:** Introduce Role model/table; add moderator; default new users to user; centralize role names and add helpers (has_role, is_admin, is_moderator_or_admin). Align migration default with "user" for new registrations.

---

## 3. Auth and session / JWT

### Web auth: `Backend/app/web/auth.py`
- **require_web_login:** Checks `session.get("user_id")`; loads User; redirects to login if missing or if user has email but no email_verified_at. **No role check.** Any verified logged-in user can access dashboard (and thus currently sees Admin section and fake logs).
- **is_safe_redirect:** Used for login `next` parameter.

### Web routes: `Backend/app/web/routes.py`
- **/dashboard:** Decorated with `@require_web_login`. No admin-only check; any logged-in user can open dashboard and see Metrics, Overview, Logs, User Settings.
- **Login/logout/register/activate/reset:** Standard flows; no activity logging yet.

### API auth: `Backend/app/auth/permissions.py`
- **get_current_user():** Resolves JWT identity to User (for use after @jwt_required()).
- **current_user_is_admin():** True iff user.role == User.ROLE_ADMIN.
- **current_user_can_write_news():** True for editor or admin (uses user.can_write_news()).
- No moderator-specific helper; no shared "require admin" decorator used on web routes.

### API auth routes: `Backend/app/api/v1/auth_routes.py`
- Register, login, me. Login returns user dict including role. No activity logging.

**Conclusion:** Keep existing auth flow. Add centralized role helpers (including moderator) and reuse them for: (1) admin-only logs API, (2) optional admin-only dashboard or admin-only Logs section in the UI.

---

## 4. Current role checks and admin-only behavior

- **API user routes:** `GET /api/v1/users` and `DELETE /api/v1/users/<id>` use `current_user_is_admin()`; non-admin get 403.
- **API news write:** All write endpoints use `current_user_can_write_news()` (editor or admin).
- **Dashboard:** No role check. Any logged-in user sees full dashboard including Logs. Admin-only behavior should be enforced for: (1) GET /api/v1/admin/logs (and export), (2) visibility of Logs tab (or entire admin section) for non-admin users.

**Conclusion:** Enforce admin-only on the logs API. In the dashboard, either hide admin section (Overview, Metrics, Logs) from non-admins or at least hide/disable Logs for non-admin and rely on API as source of truth (403 for non-admin).

---

## 5. Logger usage (technical vs activity logs)

- **app/__init__.py:** Configures app.logger and "app" package logger (level, handlers). No activity/audit log.
- **user_service.py:** logger.info/warning for user created, login failure, password reset, email verification.
- **auth_routes.py:** logger.warning for API login 401.
- **mail_service.py:** logger.warning/exception for mail send (dev URL log, failures).
- **news_service.py:** logger.info for news created/updated/deleted/published/unpublished.
- **user_routes.py:** logger = getLogger(__name__) but no log calls in the excerpt.

All of these are **technical/system logs** (stdout/file). There is **no** persisted **activity/audit log** table or service for dashboard visibility. No raw Python logs are piped to the dashboard.

**Conclusion:** Introduce a dedicated ActivityLog model and a central `log_activity(...)` service. Use it for auth, account, news, and admin actions. Keep technical logging as-is; do not pipe it into the dashboard.

---

## 6. CSV / export

- **Current:** Only in `Backend/app/static/dashboard.js`: client-side CSV export from filtered DEMO_ROWS. No server-side export endpoint.
- **Desired:** Export real logs; either server-side endpoint (e.g. GET /api/v1/admin/logs/export?...) honoring filters, or client-side export from real fetched data (with clear scope: current page vs current filter set).

---

## 7. Tests relevant to dashboard, auth, admin

- **test_web.py:** test_dashboard_anonymous_redirects_to_login, test_dashboard_logged_in_returns_200. No test that non-admin cannot access logs API; no test for role assignment on registration.
- **test_api.py:** test_register_success, test_login_success_returns_token, test_me_with_token_returns_user; no assertion on role in register/login/me. test_user fixture does not set role (model default or DB default used).
- **conftest.py:** test_user (no email, no role set → role from column default or model default); test_user_with_email (has email_verified_at); editor_user (role=User.ROLE_EDITOR). No admin_user fixture; no moderator fixture.
- **test_news_api.py:** Uses editor_user/editor_headers for write tests; no admin-only API tests.
- **test_user_routes:** Not seen in list; user API tests may be in test_api or separate file. No admin logs API tests (endpoint does not exist yet).

**Conclusion:** Add tests for: default role on registration (user); role helpers; admin-only guards (logs API 403 for non-admin); moderator recognized; activity log creation for key events; admin logs API returns real data and respects filters; CSV export; dashboard logs not using demo data.

---

## 8. Best candidates for activity logging

- **Auth/account:** web login success/failure, login blocked (unverified); API login success/failure; logout; registration success; verification email sent; email verification success; resend verification; password reset requested; password reset completed.
- **News/admin:** news created/updated/published/unpublished/deleted; user updated; user role changed; user deleted; any existing admin-only action (e.g. user list/delete already exist; logs API access can be logged when we add it).

---

## 9. Summary

| Area | Current state | Direction |
|------|----------------|-----------|
| Dashboard logs | DEMO_ROWS in dashboard.js; no API | Real API, loading/empty/error; filters + CSV from real data |
| User role | role column (user/editor/admin); no moderator; no Role table | Role table + user→role; user, moderator, admin; default user |
| Role checks | permissions.current_user_is_admin, can_write_news; no web guard | Centralized has_role, is_admin, is_moderator_or_admin; admin-only logs API and UI |
| Activity logs | None (only technical logging) | ActivityLog model + log_activity() service; instrument auth, account, news, admin |
| CSV export | Client-side from DEMO_ROWS | Server-side or client-side from real logs |
| Tests | No role/registration role test; no logs API; no activity log tests | Add coverage for roles, guards, logging, logs API, export |

No behavior change in this phase except optional minimal correctness fixes. Implementation in Phases 2–12.
