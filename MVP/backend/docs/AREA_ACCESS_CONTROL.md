# Area-based access control (0.0.17)

## Overview

Access to admin/dashboard and management features is controlled by **Role**, **RoleLevel**, and **RoleAreas**. A user may use a feature only if:

1. **Role** permits it (e.g. admin for user management).
2. **RoleLevel** hierarchy permits it (e.g. admin may only edit users with lower level).
3. **Area** access permits it: the user has the "all" area or at least one of the areas assigned to that feature.

## Area model

- **Areas** are stored in the `areas` table (id, name, slug, description, is_system, created_at, updated_at).
- **Default areas** (seeded by migration 019 and `ensure_areas_seeded()`): `all`, `community`, `website content`, `rules and system`, `ai integration`, `game`, `wiki`.
- **`all`** is the special wildcard: users assigned to "all" can access every area-scoped feature. Slug: `all`, `is_system=True`.
- **User–area relation:** Many-to-many via `user_areas` (user_id, area_id). A user can have zero, one, or many areas. **No user area rows** = feature_areas are **not** applied for that user (full feature access allowed by role only). To restrict someone to a subset, assign them specific areas (not `all`). Empty **feature** mapping (`feature_areas` has no rows for that feature) = that feature is global for all allowed roles.

## Feature / view assignment

- **feature_areas** table: (feature_id, area_id). Each feature (e.g. `manage.news`, `manage.users`) can be assigned zero or more areas.
- **If a feature has no rows** in feature_areas: it is **global** (any user with the required role can access).
- **If a feature has area rows:** only users who have the "all" area or one of those area IDs can access (in addition to role/level).

## Feature identifiers (stable)

Used in API and permission checks:

- `manage.news`, `manage.users`, `manage.roles`, `manage.wiki`, `manage.slogans`
- `manage.areas`, `manage.feature_areas`
- `manage.system_diagnosis` (aggregated operator diagnosis API and `/manage/diagnosis` UI; moderator+ by default)
- `manage.play_service_control` (Play-Service **desired** state, test/apply admin APIs, `/manage/play-service-control` UI; **admin-only** by default)
- `dashboard.metrics`, `dashboard.logs`, `dashboard.settings`, `dashboard.user_settings`

## API

- **Areas:** `GET/POST /api/v1/areas`, `GET/PUT/DELETE /api/v1/areas/<id>`. Admin only; requires feature `manage.areas`.
- **User areas:** `GET /api/v1/users/<id>/areas`, `PUT /api/v1/users/<id>/areas` (body: `{ "area_ids": [...] }`). Admin only; hierarchy: target must have lower role_level.
- **Feature areas:** `GET /api/v1/feature-areas`, `GET/PUT /api/v1/feature-areas/<feature_id>` (body: `{ "area_ids": [...] }`). Admin only; requires feature `manage.feature_areas`.
- **Auth/me:** Response includes `allowed_features` (list of feature_ids the user can access) and `area_ids` / `areas`.

## Frontend

- **Manage → Areas:** List, create, edit, delete areas. Admin only; nav visible only if user has `manage.areas` in `allowed_features`.
- **Manage → Feature access:** List features and their area_ids; edit area assignment per feature. Admin only; requires `manage.feature_areas`.
- **Manage → Users:** User form includes "Areas" multi-select and "Save areas" (PUT user areas). Shown only when admin may edit that user.
- **Nav visibility:** All manage nav links (News, Users, Roles, Areas, Feature access, Wiki, Slogans) are shown or hidden based on `allowed_features` from `/api/v1/auth/me`.

## Hierarchy and areas

- Existing **role/role_level** rules are unchanged. An admin may only edit/ban/delete users with strictly lower role_level.
- Assigning **areas** to a user or to a feature is an **admin** action; user-area PUT and feature-area PUT enforce admin and, for user areas, hierarchy (target user must have lower level).
- System area "all" cannot be deleted or have its slug changed.

## Migrations

- **019:** Creates `areas` and `user_areas`; seeds default areas.
- **020:** Creates `feature_areas`.

## Future extension

- The schema and permission helpers support restricting **public** or **non-admin** features by area later (e.g. "this wiki section is only for users with area X") without redesigning the data model.
