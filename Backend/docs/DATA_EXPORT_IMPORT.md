# Data export/import and data-tool (0.0.18)

## Export format

Exports use a JSON structure:

- `metadata` – versioning and scope
- `data` – application data

Example:

```json
{
  "metadata": {
    "format_version": 1,
    "application_version": "0.0.18",
    "schema_revision": "xxxx", // Alembic version_num when available
    "exported_at": "2026-03-12T09:55:56.098974+00:00",
    "scope": { "type": "full" | "table" | "rows", "table": "users", "primary_keys": [1,2,3] },
    "tables": [
      { "name": "users", "row_count": 10 },
      { "name": "roles", "row_count": 4 }
    ],
    "generator": { "name": "WorldOfShadows Backend", "host": "hostname" },
    "checksum": { "algorithm": "sha256", "value": "<hex-of-data-section>" }
  },
  "data": {
    "tables": {
      "users": [
        { "id": 1, "username": "adminuser", "created_at": "..." }
      ],
      "roles": [
        { "id": 1, "name": "user" }
      ]
    }
  }
}
```

Notes:

- `schema_revision` is taken from Alembic's `alembic_version.version_num` when present, otherwise empty (e.g. in tests).
- `format_version` is independent from the DB schema and is currently `1`.
- `checksum` covers only the `data` section using a stable JSON encoding.

## Export scopes

Backend service: `app.services.data_export_service`.

- **Full database:** `export_full()` – exports all application tables in `db.metadata` except `alembic_version`.
- **Single table:** `export_table(table_name)` – all rows from the given table.
- **Selected rows:** `export_table_rows(table_name, primary_keys)` – only rows with the given primary key values (single-column PK only).

## API endpoints

Routes in `app/api/v1/data_routes.py`:

- `POST /api/v1/data/export`
  - Body:
    - `{ "scope": "full" }`
    - `{ "scope": "table", "table": "users" }`
    - `{ "scope": "rows", "table": "users", "primary_keys": [1,2,3] }`
  - Auth: JWT required, admin role, feature `manage.data_export`.
  - Response: full JSON payload as above.

- `POST /api/v1/data/import/preflight`
  - Body: full export JSON.
  - Auth: JWT required, admin role, feature `manage.data_import`.
  - Behavior: runs validation only, no writes.
  - Response: `{ ok: bool, metadata: {...}, issues: [{code, message, table?}, ...] }`.

- `POST /api/v1/data/import/execute`
  - Body: full export JSON.
  - Auth: JWT required, **SuperAdmin** (`role=admin` and `role_level >= 100`), feature `manage.data_import`.
  - Behavior:
    - Runs the same preflight validation.
    - On success and no critical issues, inserts rows in a single transaction (`execute_import`).
    - On failure, returns 400 with issues and no changes applied.

## Validation and collision strategy

Validation (`app.services.data_import_service`):

- **Metadata:**
  - `metadata.format_version` must equal `EXPORT_FORMAT_VERSION` (1).
  - `metadata.schema_revision` must be present; if it differs from the current schema revision (when available), issue `SCHEMA_MISMATCH`.
- **Data structure:**
  - `data.tables` must be a mapping `{ table_name: [rows...] }`.
  - Unknown or forbidden tables (e.g. `alembic_version`) produce `UNKNOWN_TABLE`.
  - Rows must be objects; non-object rows produce `INVALID_ROW`.
  - Required columns (non-nullable without default/server_default, excluding autoincrement PKs) must be present; otherwise `MISSING_REQUIRED_FIELDS`.
- **Primary key collisions:**
  - For single-column PK tables, existing rows with the same PK values are detected.
  - Policy: **fail on conflict** – issues contain `PRIMARY_KEY_CONFLICT`, and execute endpoint returns 400 without partial writes.

Import execution:

- All inserts are executed inside `db.session.begin()` and rolled back on any `SQLAlchemyError`.
- DateTime strings are parsed from ISO-8601 when column type is `DateTime`, otherwise values are passed through.

## Security and permissions

- Export and import endpoints require JWT and feature-based access:
  - `manage.data_export` (admin-role users) for export.
  - `manage.data_import` (admin-role users) for preflight.
- Import execution additionally requires **SuperAdmin** (`current_user_is_super_admin()`).
- Endpoints use the same role/role_level/area-based permission model as other admin features.
- No frontend-only protection: the backend enforces roles, feature access, and SuperAdmin requirement.

## Frontend admin UI

Located in the public frontend:

- Template: `administration-tool/templates/manage/data.html`.
- Script: `administration-tool/static/manage_data.js`.

Features:

- **Export:**
  - Scope selector: full, table, rows.
  - Table dropdown pre-populated from a `scope=full` export's `metadata.tables`.
  - Rows scope accepts comma-separated primary key values.
  - Result JSON is shown in a `<pre>` block and can be saved manually.

- **Import:**
  - Textarea to paste JSON payload.
  - "Preflight only" button calls `/data/import/preflight` and displays result JSON.
  - "Execute import" button calls `/data/import/execute` and shows result JSON (SuperAdmin-only; backend enforces).

The sidebar nav entry "Data" is only visible for users who have `manage.data_export` in `allowed_features` from `/api/v1/auth/me`.

## data-tool CLI

Path: `data-tool/data_tool.py`.

Usage:

- Help: `python data-tool/data_tool.py --help`
- Inspect: `python data-tool/data_tool.py [--current-schema REV] inspect export.json`
- Validate: `python data-tool/data_tool.py [--current-schema REV] validate export.json`
- Transform (currently structural no-op for supported payloads):  
  `python data-tool/data_tool.py [--current-schema REV] transform export.json cleaned.json`

Behavior:

- Reads payload JSON and runs basic validation (same expectations on `metadata` and `data.tables`).
- Optional `--current-schema` lets the tool flag `SCHEMA_MISMATCH` before hitting the backend.
- `transform` refuses to process unsupported `format_version`; for supported payloads it writes a sanitized copy.

## Version compatibility model

- Export format version: `format_version = 1`.
- Application version: `application_version = "0.0.18"` (from `app.version.APP_VERSION`).
- Schema version: `schema_revision` from Alembic when available; empty string when not.
- Currently, imports are accepted only for `format_version == 1`. Older/other versions must be transformed by the data-tool once transformation rules exist.

