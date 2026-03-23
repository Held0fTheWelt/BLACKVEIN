# World of Shadows – Wiki

Welcome to the **World of Shadows** (Blackveign) wiki.

## About the project

World of Shadows is a Flask-based backend with API, authentication, news system, and email verification. The frontend consumes the API; login, registration, and dashboard are provided by the backend.

## Contents

- **News:** Published articles at `/news` (or via the frontend) and via the API `GET /api/v1/news`.
- **Registration & login:** Email verification (activation link) is required; login is blocked until verification.
- **Users & roles:** Roles `user`, `moderator`, `admin`. Moderators and admins can create and edit news; admins have access to user management (CRUD, assign role, ban/unban via the API).

## Technical stack

- **Backend:** Flask, SQLAlchemy, Flask-Migrate, JWT (API), session (web), Flask-Mail.
- **API documentation:** See `docs/BackendApi.md`.
- **Runbook:** See `docs/runbook.md` for local commands (PowerShell and Bash, `flask` and `python -m flask`).

---

*This wiki is generated from the Markdown file `Backend/content/wiki.md`.*
