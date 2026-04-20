# Management frontend – script order and verification

## Script load order (required)

The management area uses a shared auth layer (`manage_auth.js`) that must be available before any page-specific script runs. **Page scripts must be loaded after the shared bootstrap.**

### Template structure

In `administration-tool/templates/manage/base.html`:

1. Inline script: `window.__FRONTEND_CONFIG__` (backend API URL and i18n).
2. `main.js` – public frontend helpers (getApiBaseUrl, apiFetch).
3. `manage_auth.js` – defines `window.ManageAuth` (apiFetchWithAuth, ensureAuth, logout, etc.).
4. `{% block extra_scripts %}` – **page-specific scripts only** (e.g. `manage_users.js`, `manage_news.js`).

**Rule:** Page-specific scripts must be placed in `{% block extra_scripts %}`, not inside `{% block content %}`. If a page script is put in the content block, it runs before `manage_auth.js` and `ManageAuth` is undefined, so the page will not work.

### Page modules

Each page module (users, news, wiki, slogans) does the following:

- Uses an `apiRef` (or equivalent) set at **initialization time**, not at script parse time.
- Registers a `DOMContentLoaded` listener (or runs immediately if the document is already loaded) and then resolves `ManageAuth.apiFetchWithAuth`. If it is missing, the module logs to the console and shows an inline error instead of failing silently.
- Does not rely on top-level `if (!api) return;` as the only guard, because that can run before `ManageAuth` exists if script order were ever wrong.

## Manual verification pass

After any change to manage templates or script order, run through this checklist:

1. **Login** (`/manage/login`)
   - Page loads; form submits to backend; on success, redirect to `next` or `/manage`; JWT stored.
   - On invalid credentials, error message shown.
   - If already logged in, redirect to `/manage`.

2. **Dashboard** (`/manage`)
   - Loads without redirect when logged in; user/role shown in header; nav links visible (Users only for admin).
   - Cards link to News, Users (if admin), Wiki, Slogans.

3. **Users** (`/manage/users`, admin only)
   - List loads (or “No users” / error).
   - Search input + Apply and Enter key trigger list reload with query.
   - Clicking a row selects the user and loads the edit form; Save, Ban, Unban, Delete work against the existing API.

4. **News** (`/manage/news`)
   - List loads with filters; Apply and pagination work.
   - New article, select article, edit DE/EN tabs, Save, Publish/Unpublish, Delete work where the backend supports them.

5. **Wiki** (`/manage/wiki`)
   - Page list loads; selecting a page loads translations; editor and preview work; Save works.

6. **Slogans** (`/manage/slogans`)
   - List loads; filters work; New slogan, Edit, Save, Activate/Deactivate, Delete work.

7. **Logout**
   - Log out clears token and redirects to `/manage/login`.

8. **Unauthorized**
   - Accessing a manage page without a token redirects to login. Invalid/expired token on an API call redirects to login after 401.

If any of the above fail (e.g. “Auth not loaded”, empty list that should have data, or buttons doing nothing), check the browser console for errors and confirm that script order in the HTML is as above and that page scripts are in `extra_scripts`.
