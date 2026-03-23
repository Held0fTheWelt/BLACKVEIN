# n8n Integration (World of Shadows)

Backend triggers translation jobs via webhook; n8n calls the backend API with a service token to write `machine_draft` translations.

## Environment (Backend)

| Variable | Description |
|----------|-------------|
| `N8N_WEBHOOK_URL` | Full URL of the n8n webhook that receives translation requests (e.g. `https://n8n.example.com/webhook/...`). If unset, auto-translate in the UI does not call n8n. |
| `N8N_WEBHOOK_SECRET` | Optional. Shared secret for signing webhook payloads (HMAC-SHA256). n8n can verify `X-Webhook-Signature: sha256=<hex>`. |
| `N8N_SERVICE_TOKEN` | Secret token n8n sends in `X-Service-Key` when calling the backend. Required if n8n should write translations. Do not commit; use env or secrets manager. |

## Events (Backend → n8n)

POST to `N8N_WEBHOOK_URL` with JSON body. If `N8N_WEBHOOK_SECRET` is set, the backend sends `X-Webhook-Signature: sha256=<hmac_hex>` (HMAC-SHA256 over the raw JSON body).

### news.translation.requested

```json
{
  "event": "news.translation.requested",
  "article_id": 123,
  "target_language": "en",
  "source_language": "de"
}
```

- **article_id:** News article ID.
- **target_language:** Language to translate into (`de` or `en`).
- **source_language:** Language to use as source (article default). n8n can GET `.../news/<article_id>/translations/<source_language>` with `X-Service-Key`, then translate and PUT `.../translations/<target_language>`.

### wiki.translation.requested

```json
{
  "event": "wiki.translation.requested",
  "page_id": 1,
  "target_language": "en",
  "source_language": "de"
}
```

- **page_id:** Wiki page ID.
- **target_language:** Target language.
- **source_language:** Source language (e.g. config default). n8n can GET `.../wiki-admin/pages/<page_id>/translations/<source_language>` with `X-Service-Key`, then translate and PUT back.

## n8n → Backend (service auth)

All write requests from n8n must use the same backend base URL and send:

- **Header:** `X-Service-Key: <N8N_SERVICE_TOKEN>`
- No JWT. The backend accepts `X-Service-Key` only for PUT translation endpoints and forces `translation_status` to `machine_draft`.

### Endpoints n8n may call (with `X-Service-Key`)

- **GET /api/v1/news/<article_id>/translations/<lang>**  
  Returns one translation (title, slug, summary, content, etc.). Use `source_language` from the webhook payload to read the source, then PUT the new translation for `target_language`.
- **PUT /api/v1/news/<article_id>/translations/<lang>**  
  Body: `title`, `slug`, `summary`, `content`, optional `seo_title`, `seo_description`. Status is forced to `machine_draft`.
- **GET /api/v1/wiki-admin/pages/<page_id>/translations/<lang>**  
  Returns one wiki translation (title, slug, content_markdown, etc.).
- **PUT /api/v1/wiki-admin/pages/<page_id>/translations/<lang>**  
  Body: `title`, `slug`, `content_markdown`. Status is forced to `machine_draft`.

## Webhook signature verification (n8n)

If `N8N_WEBHOOK_SECRET` is set:

1. Read raw request body (UTF-8).
2. Compute `HMAC-SHA256(secret, body)` and compare with `X-Webhook-Signature` (strip `sha256=` prefix, then compare hex).
3. Reject request if mismatch.

## Idempotency

The backend upserts translations per article/page + language. Repeated PUTs for the same entity and language overwrite the existing row (or create it). n8n can safely retry; no duplicate rows. Triggering the same `news.translation.requested` / `wiki.translation.requested` multiple times for the same entity and language is safe.

## Workflow outline (n8n)

1. **Webhook** node: receives POST from backend; verify signature if secret is set.
2. **Switch** on `body.event`: `news.translation.requested` vs `wiki.translation.requested`.
3. **News branch:** GET `/api/v1/news/<article_id>/translations/<source_language>` with `X-Service-Key`; translate (e.g. DeepL/OpenAI); PUT `/api/v1/news/<article_id>/translations/<target_language>` with `X-Service-Key`, body `title`, `slug`, `summary`, `content`.
4. **Wiki branch:** GET `/api/v1/wiki-admin/pages/<page_id>/translations/<source_language>` with `X-Service-Key`; translate; PUT `/api/v1/wiki-admin/pages/<page_id>/translations/<target_language>` with `X-Service-Key`.
5. Error handling: log and optionally retry; do not publish. Only `machine_draft` is written by n8n; humans approve/publish.

Credentials (DeepL, OpenAI, backend `N8N_SERVICE_TOKEN`) must be stored in n8n or env, never in the repo.
