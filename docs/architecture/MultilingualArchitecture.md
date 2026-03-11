# Multilingual Content Architecture

Internal reference for language support across Backend, Frontend, and n8n. Keep concise.

## Language configuration

- **Supported language codes:** `de`, `en`
- **Default language:** `de`
- **Validation:** Backend accepts only supported codes; invalid codes are rejected.

## Fallback order

For content (news, wiki):

1. Requested language (e.g. `?lang=en`)
2. Content default/original language (article/page `default_language` or source translation)
3. Global default language (`de`)

For UI strings: same order (user preference → session/route → browser if used → default).

## Translation statuses

Used for content translations (news, wiki). Machine translations must not be auto-published.

| Status | Meaning |
|--------|---------|
| `missing` | No translation row for that language |
| `machine_draft` | Machine-generated, not yet reviewed |
| `review_required` | Submitted for review |
| `approved` | Approved, not yet published |
| `published` | Live for that language |
| `outdated` | Source changed; translation should be updated |

Transitions (e.g. submit-review, approve, publish) are backend-enforced; role checks apply.

## Roles and permissions

- **Public:** Read published content only; language via `lang` query or route.
- **Moderator / Admin:** Create/edit articles and wiki pages; manage translations; submit for review; approve; publish. No password or hash access in admin UI.
- **Admin only:** User administration (username, email, role, preferred_language, ban); no password editing or hash exposure.
- All permission checks are enforced in the backend; frontend only reflects backend reality.

## Backend ↔ n8n event contract

- **Backend triggers n8n** via signed webhook (or equivalent). Payload must identify entity (news article id or wiki page id), target language, and optionally source language/version.
- **Events:**
  - `news.translation.requested` – create or refresh machine translation for a news article
  - `wiki.translation.requested` – create or refresh machine translation for a wiki page
  - `news.source.updated` – source content changed; mark derived translations outdated (and optionally trigger re-translation)
  - `wiki.source.updated` – same for wiki
- **n8n → Backend:** n8n calls backend APIs with a dedicated service credential/token. Writes go in as `machine_draft` only. No direct DB access from n8n.
- **Idempotency:** Repeated triggers for the same entity+language should not create duplicate translations; backend upserts or overwrites machine_draft for that language.

## Public vs editorial/admin routes

- **Public:** `GET /api/v1/news?lang=`, `GET /api/v1/news/<slug>?lang=`, `GET /api/v1/wiki/<slug>?lang=` (and existing public pages). No auth required; return content in requested or fallback language.
- **Editorial/Admin:** All create/update/translation/review/publish endpoints require JWT and moderator or admin role. User admin (list, get, update, ban, role) requires admin. Frontend manage area (`/manage/...`) uses token-based API access and must not expose passwords or hashes.

## UI vs content translations

- **UI translations:** Frontend-only (e.g. JSON files per language). Labels, buttons, nav, messages. Not stored in backend.
- **Content translations:** Backend-owned. News and wiki content per language in DB; status and workflow in backend. n8n only produces machine_draft content; humans approve/publish.
