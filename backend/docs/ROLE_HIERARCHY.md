# Role hierarchy (0.0.16)

> **Area-based access (0.0.17):** Admin/dashboard feature visibility also depends on **RoleAreas**. See [AREA_ACCESS_CONTROL.md](AREA_ACCESS_CONTROL.md).

## Overview

- **Roles:** user, qa, moderator, admin (stored in `roles` table; name unique). The role says *what* you can do (e.g. admin = access to admin APIs); it does not imply a numeric authority.
- **RoleLevel:** Integer on each user (`users.role_level`). Pure **authority rank**: who has higher authority in the system. Not “level 50 = moderator”; it only defines hierarchy for who may edit whom.
- **All users start with role_level 0.** Only the initially seeded SuperAdmin (e.g. via `flask seed-dev-user --username admin --password Admin123 --superadmin` or `flask seed-admin-user`) gets role_level 100.
- **SuperAdmin:** An admin user with `role_level >= 100`. Only they may raise their own role_level (self-elevation). The label “SuperAdmin” is semantic only; the rule is “admin with level 100+”.

## Rules (enforced server-side)

1. Only admins may manage roles and perform admin actions on users.
2. QA is a normal assignable role, not an admin role.
3. An admin may only **edit** (PUT, PATCH role, ban, unban, delete) users whose **role_level is strictly lower** than their own.
4. Assigning a role (PATCH role or PUT role) only changes the user’s role; it does **not** change their role_level. So assigning “admin” does not set level to 50; everyone stays at 0 unless explicitly set or seeded.
5. **Self-elevation:** No user may increase their own role_level, except a **SuperAdmin** may set their own role_level to any value >= 100.
6. Non-SuperAdmin may not set their own role_level at all via API (403).

## API

- **User list/detail:** Include `role_id`, `role_level`.
- **PUT /api/v1/users/<id>:** Optional body `role`, `role_level`. Hierarchy checked before apply.
- **PATCH /api/v1/users/<id>/role:** Body `role`. Target must have lower role_level. RoleLevel is not changed when role is assigned.
- **POST ban/unban, DELETE user:** Target must have lower role_level than actor.

## Frontend

- **Manage → Roles:** List, create, edit (name, description, default_role_level), delete. Admin only.
- **Manage → Users:** Table shows Role and Level. Form: role dropdown (from API), role_level number. Buttons disabled when target has equal or higher level; message explains.

## Migration

- **017:** Adds `roles.description`, `roles.default_role_level`; adds `users.role_level` (NOT NULL, default 0); backfills from role defaults; inserts role `qa`.
- **018:** Sets all `users.role_level = 0`. Authority is per-user; only seed commands create a SuperAdmin (100). Use `flask seed-dev-user --username admin --password Admin123 --superadmin` or `flask seed-admin-user` to create the initial SuperAdmin.
