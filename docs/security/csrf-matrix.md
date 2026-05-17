# CSRF Matrix

This matrix is the explicit contract for browser-originated, mutating flows that can involve cookies. JSON API endpoints remain intentionally CSRF-exempt when they require `Authorization: Bearer ...`; browser services must not forward inbound `Cookie` headers to backend APIs.

## Security Governance

The operator surface for this matrix is [Security governance administration](../admin/security-governance.md). The normative architecture records are [ADR-0050: Security governance for browser mutation boundaries](../ADR/adr-0050-security-governance-browser-mutation-boundaries.md) and [ADR-0052: Security governance admin control plane](../ADR/adr-0052-security-governance-admin-control-plane.md). The administration page at `/manage/security-governance` exposes the matrix, target cookie policy, effective backend cookie posture, proxy boundaries, secret-store policy, Redis governance evidence, storage-layer encryption evidence, and the full `security_governance.v1` JSON payload.

Security governance settings are policy and release evidence. They do not directly toggle the `/api/v1` CSRF exemption, route auth, proxy cookie stripping, or deployment secret/Redis materialization.

## Policy Summary

| Flow family | Credential sent by browser | Mutating methods | CSRF stance | Regression coverage |
| --- | --- | --- | --- | --- |
| Backend legacy web routes | Backend `session` cookie | `POST` | Protected by global Flask-WTF CSRF when `WTF_CSRF_ENABLED=True`; `api_v1` is exempt. | `backend/tests/test_csrf_protection.py` |
| Backend JSON API `/api/v1/*` | Bearer token in `Authorization` header | `POST`, `PUT`, `PATCH`, `DELETE` | CSRF-exempt by design; do not rely on browser cookies for API auth. | `backend/tests/test_csrf_protection.py` |
| Frontend player forms | Frontend `session` cookie stores server-side tokens | `POST` | Same-origin forms, `SESSION_COOKIE_SAMESITE=Lax`, `HttpOnly`; no upstream cookies are sent. | `frontend/tests/test_csrf_matrix.py`, `frontend/tests/test_api_client.py` |
| Frontend same-origin API proxy `/api/v1/<path>` | Frontend `session` cookie only to look up server-side token | `POST`, `PUT`, `PATCH`, `DELETE` | Server forwards Bearer token to backend and omits inbound cookies. | `frontend/tests/test_csrf_matrix.py`, `frontend/tests/test_api_client.py` |
| Administration tool proxy `/_proxy/api/*` | Admin tool `session` cookie is not forwarded | `POST`, `PUT`, `PATCH`, `DELETE` | Same-origin proxy allowlist; forwards approved headers only, strips `Cookie`/`Set-Cookie`/host spoofing headers. | `administration-tool/tests/test_proxy_contract.py` |

## Route Matrix

| Surface | Route or pattern | Methods | Mutation | Cookie relevance | Required CSRF behavior |
| --- | --- | --- | --- | --- | --- |
| Backend web compatibility | `/logout` | `POST` | Clears legacy backend session and redirects. | Uses backend `session` cookie. | Requires valid Flask-WTF CSRF token when CSRF is enabled. |
| Backend web compatibility | `/login`, `/register`, `/resend-verification`, `/forgot-password`, `/reset-password/<token>` | `POST` | Compatibility redirect to frontend; no backend account mutation happens in these web handlers. | Browser may send backend `session` cookie. | Covered by global web CSRF when CSRF is enabled. |
| Backend web compatibility | `/play/start`, `/play/<session_id>/execute` | `POST` | Compatibility redirect to frontend play routes. | Browser may send backend `session` cookie. | Covered by global web CSRF when CSRF is enabled. |
| Backend API | `/api/v1/auth/register`, `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/refresh`, and other `/api/v1/*` JSON mutations | `POST`, `PUT`, `PATCH`, `DELETE` | Account, content, forum, game, and governance mutations. | API auth is Bearer-token based; no browser cookie should authenticate the API. | Remains CSRF-exempt; requires route auth, role checks, and/or public endpoint policy. |
| Frontend auth forms | `/login`, `/logout`, `/register`, `/resend-verification`, `/forgot-password`, `/reset-password/<token>` | `POST` | Mutates frontend Flask session and/or calls backend API with Bearer token. | Uses frontend `session` cookie. | SameSite=Lax + same-origin form action; backend call uses Bearer, not inbound cookies. |
| Frontend play forms/API | `/play/start`, `/play/<session_id>/execute` | `POST` | Creates or advances a play run via backend API. | Uses frontend `session` cookie for the access token; per-run `wos_backend_session_<run_id>` cookie is `SameSite=Strict` and `HttpOnly`. | SameSite=Lax/Strict cookies; backend call uses Bearer, not inbound cookies. |
| Frontend API proxy | `/api/v1/<path>` | `POST`, `PUT`, `PATCH`, `DELETE` | Same-origin JSON proxy to backend. | Frontend `session` cookie only unlocks server-side Bearer token lookup. | Do not forward inbound `Cookie`; send `Authorization: Bearer ...` only when logged in. |
| Admin proxy | `/_proxy/api/*` | `POST`, `PUT`, `PATCH`, `DELETE` | Same-origin proxy to backend APIs for admin UI. | Admin `session` cookie may be present on the proxy request. | Do not forward inbound `Cookie` or `Set-Cookie`; allowlist API paths and approved headers only. |

## Test Expectations

- Backend CSRF-enabled tests must reject mutating legacy web posts without a token.
- Backend API tests must prove `/api/v1/*` remains callable without CSRF tokens when endpoint auth requirements are otherwise satisfied.
- Frontend tests must pin session cookie flags and prove server-side backend calls send Bearer headers without copying inbound cookies.
- Admin proxy tests must prove mutating proxy calls strip browser cookies and preserve only approved headers.
