# Role hierarchy (0.0.16)

## Overview

- **Roles:** user, qa, moderator, admin (stored in `roles` table; name unique).
- **RoleLevel:** Integer on each user (`users.role_level`). Determines administrative power.
- **SuperAdmin:** An admin user with `role_level >= 100` (constant `SUPERADMIN_THRESHOLD`).

## Rules (enforced server-side)

1. Only admins may manage roles and perform admin actions on users.
2. QA is a normal assignable role, not an admin role.
3. An admin may only **edit** (PUT, PATCH role, ban, unban, delete) users whose **role_level is strictly lower** than their own.
4. An admin may **not** assign a role whose `default_role_level` is >= their own (prevents elevating someone to or above your level).
5. **Self-elevation:** No user may increase their own role_level, except a **SuperAdmin** may set their own role_level to any value >= 100.
6. Non-SuperAdmin may not set their own role_level at all via API (403).

## API

- **User list/detail:** Include `role_id`, `role_level`.
- **PUT /api/v1/users/<id>:** Optional body `role`, `role_level`. Hierarchy checked before apply.
- **PATCH /api/v1/users/<id>/role:** Body `role`. Target must have lower role_level; new role’s default_level must be < actor’s level.
- **POST ban/unban, DELETE user:** Target must have lower role_level than actor.

## Frontend

- **Manage → Roles:** List, create, edit (name, description, default_role_level), delete. Admin only.
- **Manage → Users:** Table shows Role and Level. Form: role dropdown (from API), role_level number. Buttons disabled when target has equal or higher level; message explains.

## Migration

- **017:** Adds `roles.description`, `roles.default_role_level`; adds `users.role_level` (NOT NULL, default 0); backfills from role defaults; inserts role `qa` with default_level 5.
