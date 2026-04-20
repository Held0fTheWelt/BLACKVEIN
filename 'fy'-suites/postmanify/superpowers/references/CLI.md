# Postmanify CLI

## Install

From the repository root:

```bash
pip install -e .
```

This installs the **`postmanify`** console script and the **`postmanify`** Python package (under `'fy'-suites/postmanify/`).

## Commands

### `plan`

Prints JSON with tag folder count, total generated requests, and number of per-tag sub-suites (no writes).

```bash
python -m postmanify.tools plan
python -m postmanify.tools plan --openapi docs/api/openapi.yaml
```

### `generate`

Writes:

- `postman/WorldOfShadows_Complete_OpenAPI.postman_collection.json` — one folder per OpenAPI **tag**, one request per operation (method + path); default **`generate`** target.
- `postman/suites/WorldOfShadows_Suite_<TagSlug>.postman_collection.json` — **sub-suite** per tag (single folder).
- `postman/postmanify-manifest.json` — source path, sha256 of the OpenAPI file, and list of suite files.

```bash
python -m postmanify.tools generate
python -m postmanify.tools generate --openapi docs/api/openapi.yaml --backend-api-prefix /api/v1
```

### Direct script (no `-m`)

```bash
python "./'fy'-suites/postmanify/tools/cli.py" plan
```

## Environment variables in URLs

Generated requests use **`{{backendBaseUrl}}{{backendApiPrefix}}/…`** for paths under the configured `--backend-api-prefix` (default `/api/v1`). Use existing **`WorldOfShadows_Local`** or **`WorldOfShadows_Docker`** environments from `postman/`.
