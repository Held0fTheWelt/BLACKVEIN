# Phase 1 Inspection — Role hierarchy 0.0.16

## Current state

### Role model
- `roles` table: id, name (unique, max 20). No description, no default_role_level, no timestamps.
- `ensure_roles_seeded()`: user, moderator, admin only (no QA). Editor was removed in migration 009.
- Role CRUD API exists; admin-only; no hierarchy.

### User model
- `role_id` FK to roles; `role_rel`; no `role_level`.
- `to_dict()`: exposes `role` (name), not `role_id` or `role_level`.
- `is_admin` = has_role(admin). No SuperAdmin, no level checks.

### Auth
- `require_jwt_admin`: any admin role; no RoleLevel.
- `require_web_admin`: session + `user.is_admin`.
- No centralized hierarchy checks.

### User service
- `ALLOWED_ROLE_NAMES`: user, moderator, admin (no QA).
- `assign_role`, `update_user`, `ban_user`, `unban_user`, `delete_user`: no hierarchy; any admin can act on any user.

### Frontend
- Manage nav: News, Users, Wiki, Slogans. No "Roles" page.
- users.html: Role dropdown hardcoded (user, moderator, admin). No RoleLevel, no roles management.

### Migrations
- 004: users.role string; 007: roles table, users.role_id, seed user/moderator/editor/admin; 009: editor→moderator, ban fields.
- No role_level on users; no description/default_role_level on roles.

### Drift
- ALLOWED_ROLES (permissions) and ALLOWED_ROLE_NAMES (user_service) must add QA.
- Frontend role list must eventually come from API and include QA; RoleLevel must be shown and edited with hierarchy rules.
