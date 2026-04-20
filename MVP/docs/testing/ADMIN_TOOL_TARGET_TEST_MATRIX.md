# Administration Tool Target Test Matrix

**Version**: 0.1.10
**Date**: 2026-03-25
**Purpose**: Define comprehensive test coverage structure for the Flask-based public frontend.

---

## Executive Summary

The Administration Tool (`administration-tool/`) is a lightweight Flask public frontend that:
- Serves static HTML/templates only (no database)
- Proxies API requests to the backend (`/_proxy` endpoints)
- Enforces security headers and session management
- Provides multilingual UI (DE, EN)
- Implements role-based management UI (news, users, roles, areas, wiki, slogans, forum, analytics)

**Current test count**: ~20 tests across config, routing, security, and proxy layers.

**Target coverage by phase**:
- **Phase 1 (WAVE 0)**: 30 new tests (structure definition)
- **Phase 2**: 50 additional tests (full security coverage)
- **Phase 3**: 25 additional tests (edge cases and performance)
- **Total target**: ~95 tests

---

## Layer Architecture

### Layer 1: Config & Initialization
**Scope**: App factory, configuration validation, environment handling
**Type**: Unit + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| App Factory | 12 | 12 | unit, contract | test_app_creation_is_deterministic, test_app_accepts_custom_secret_key |
| Secret Key Validation | 8 | 8 | unit, contract | test_secret_key_auto_generated_when_none, test_secret_key_min_length_production |
| Backend URL Config | 8 | 10 | unit, contract, integration | test_backend_url_with_https_scheme, test_backend_url_with_port |
| Session Security | 2 | 4 | unit, security, contract | test_session_cookie_secure_flag_set, test_session_cookie_httponly_flag_set |
| **Layer 1 Total** | **30** | **34** | | |

**Security Guarantees**:
- Secret key is cryptographically random (32+ bytes) in production
- Session cookies use Secure, HttpOnly, SameSite flags
- Backend URL validation prevents open redirects
- No hardcoded secrets in code

**Negative Tests**:
- Empty secret key rejected
- Secret key < 32 bytes rejected in production
- Invalid backend URL schemes (ftp://, etc.) rejected
- Whitespace-only backend URL rejected

---

### Layer 2: Routing & Template Resolution
**Scope**: All public and management routes, template rendering, redirect logic
**Type**: Integration + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Public Routes (/) | 2 | 3 | integration, contract | test_index_returns_200, test_index_renders_html |
| News Routes (/news, /news/<id>) | 2 | 4 | integration, contract | test_news_list_renders, test_news_detail_loads_from_api |
| Wiki Routes (/wiki, /wiki/<slug>) | 2 | 4 | integration, contract | test_wiki_index_renders, test_wiki_slug_preserves_case |
| Forum Routes (/forum/*) | 4 | 8 | integration, contract | test_forum_index_lists_categories, test_forum_category_renders |
| Forum Notifications (/forum/notifications) | 1 | 2 | integration, contract | test_forum_notifications_requires_login |
| Forum Saved Threads (/forum/saved) | 1 | 2 | integration, contract | test_forum_saved_threads_requires_login |
| User Profile (/users/<id>/profile) | 1 | 2 | integration, contract | test_user_profile_renders, test_user_profile_invalid_id_returns_404 |
| Management Routes (/manage/*) | 5 | 8 | integration, contract | test_manage_index_renders, test_manage_news_renders |
| Language Resolution | 2 | 4 | integration, contract | test_language_from_query_param, test_language_from_accept_header |
| **Layer 2 Total** | **20** | **37** | | |

**Expected Status Codes**:
- 200: Valid route, template renders
- 302/307: Redirects (if any implemented)
- 404: Invalid route or missing resource
- 500: Template rendering error

**State Transitions**:
- Query param ?lang=de → session["lang"] persists
- Accept-Language header fallback when session undefined
- Default language used when all detection fails

**Negative Tests**:
- Invalid language codes ignored
- Missing route returns 404
- Template rendering error returns 500
- SQL injection attempts in route params blocked

---

### Layer 3: Proxy & Backend Integration (ALLOWLIST-BASED)
**Scope**: `/_proxy/*` endpoint, request forwarding, header manipulation, error mapping
**Type**: Integration + Security + Contract
**Security Model**: ALLOWLIST-based (deny-by-default, explicitly allow `api/`, explicitly deny `admin/`)

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Proxy Allowed Paths (Allowlist) | 3 | 4 | contract, integration | test_proxy_forwards_api_paths, test_proxy_allows_various_api_paths |
| Proxy Denied Paths (Denylist + Allowlist) | 2 | 3 | security, contract | test_proxy_blocks_admin_paths, test_proxy_blocks_admin_with_post |
| HTTP Methods (GET, POST, PUT, DELETE) | 2 | 5 | contract, integration | test_proxy_forwards_all_http_methods, test_proxy_POST_with_body |
| Request Headers (Allowlist) | 2 | 4 | security, contract | test_proxy_forwards_authorization_header, test_proxy_strips_cookie_header |
| Response Headers Preservation | 1 | 3 | contract, integration | test_proxy_preserves_content_type, test_proxy_preserves_empty_response_body |
| Error Response Mapping | 2 | 4 | contract, integration | test_proxy_backend_404_forwarded, test_proxy_urlerror_returns_502 |
| Proxy OPTIONS/Preflight | 1 | 2 | contract, integration | test_proxy_options_returns_204, test_proxy_options_no_call_to_backend |
| Upstream Network Errors | 1 | 3 | integration | test_proxy_timeout_returns_502, test_proxy_urlerror_connection_refused_returns_502 |
| **Layer 3 Total** | **14** | **28** | | |

**Security Guarantees** (ALLOWLIST-BASED):
1. **Path Allowlist**: Only paths starting with `api/` are forwarded (explicit allow)
2. **Path Denylist**: Paths starting with `admin` are blocked even if they somehow match allowlist (defense-in-depth)
3. **Unmapped Paths**: All other paths (e.g., `_admin/*`, `system/*`, custom prefixes) return 403 Forbidden
4. **Header Allowlist**: Only `Authorization`, `Content-Type`, `Accept`, `Accept-Language`, `User-Agent` are forwarded
5. **Header Dangerous List**: `Cookie`, `Set-Cookie`, `Host`, `X-Forwarded-For`, `X-Real-IP` are explicitly blocked (defense-in-depth)
6. **Request Bodies**: Preserved for POST/PUT/PATCH; stripped for GET/DELETE
7. **Response Integrity**: Status codes, bodies, Content-Type headers forwarded as-is from backend
8. **Upstream Errors**: HTTP errors (4xx/5xx) forwarded transparently; network errors mapped to 502

**Negative Tests** (Comprehensive Coverage):
- Non-allowlist paths (`_admin/*`, `system/*`, `internal/*`) → 403 Forbidden
- Path traversal attempts (`/../../../admin`) → 403 Forbidden
- Admin paths with various HTTP methods (POST, PUT, DELETE) → 403 Forbidden
- Admin paths with URL encoding (`%61dmin`) → 403 Forbidden
- Dangerous headers stripped (Cookie, Set-Cookie, Host, X-Forwarded-For, X-Real-IP)
- Custom headers not in allowlist → not forwarded
- Missing backend URL configured → 500 Internal Server Error
- Timeout on slow backend → 502 Bad Gateway
- Network errors (connection refused, DNS resolution failure) → 502 Bad Gateway
- Invalid upstream response → graceful error mapping
- Malformed JSON body → forwarded as-is (backend validates)

**Expected Response Codes**:
- 200-299: Successful upstream response
- 3xx: Upstream redirect (forwarded)
- 4xx: Client error from upstream
- 500: Template/config error
- 502: Upstream network error
- 503: Upstream unavailable
- 504: Upstream timeout

---

### Layer 4: Security Headers & CSP
**Scope**: Security headers, Content Security Policy, HSTS, clickjacking protection
**Type**: Security + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| X-Content-Type-Options | 1 | 1 | security, contract | test_header_x_content_type_options_nosniff |
| X-Frame-Options | 1 | 1 | security, contract | test_header_x_frame_options_deny |
| Referrer-Policy | 1 | 1 | security, contract | test_header_referrer_policy_strict_origin |
| Permissions-Policy | 1 | 1 | security, contract | test_header_permissions_policy_disables_geolocation |
| CSP default-src | 1 | 2 | security, contract | test_csp_default_src_self, test_csp_blocks_inline_scripts |
| CSP script-src | 1 | 2 | security, contract | test_csp_script_src_allows_self, test_csp_script_src_allows_cdn |
| CSP style-src | 1 | 1 | security, contract | test_csp_style_src_self_and_unsafe_inline |
| CSP connect-src | 1 | 2 | security, contract | test_csp_connect_src_includes_backend_origin, test_csp_connect_src_https_only |
| CSP object-src/frame-ancestors | 1 | 1 | security, contract | test_csp_object_src_none, test_csp_frame_ancestors_none |
| CSP form-action | 1 | 1 | security, contract | test_csp_form_action_self |
| **Layer 4 Total** | **10** | **13** | | |

**Security Guarantees**:
- All security headers present on every response
- CSP prevents inline scripts, eval(), external scripts (except CDN)
- CSP connect-src allows only HTTPS backend origin
- Clickjacking (X-Frame-Options) always DENY
- MIME type sniffing prevented
- Geolocation/microphone/camera permissions disabled

**Negative Tests**:
- Missing security header → FAIL
- CSP violation on blocked resource → browser blocks (not app's fault)
- Inline script in CSP header → violation warning in console

---

### Layer 5: Session & Cookie Security
**Scope**: Session configuration, cookie flags, session persistence
**Type**: Security + Integration + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Cookie Secure Flag | 1 | 1 | security, contract | test_session_cookie_secure_true |
| Cookie HttpOnly Flag | 1 | 1 | security, contract | test_session_cookie_httponly_true |
| Cookie SameSite Flag | 1 | 1 | security, contract | test_session_cookie_samesite_lax |
| Session Lifetime | 1 | 2 | security, contract | test_session_lifetime_3600_seconds, test_session_expires_after_timeout |
| Language Persistence in Session | 1 | 2 | integration, contract | test_language_persists_in_session, test_session_lang_survives_multiple_requests |
| **Layer 5 Total** | **5** | **8** | | |

**Security Guarantees**:
- Cookies transmitted only over HTTPS
- JavaScript cannot access session cookie
- CSRF protected (SameSite=Lax)
- Session expires after 1 hour of inactivity
- Session data is server-side only (Flask signed cookies)

**Negative Tests**:
- Session cookie sent over HTTP → NOT sent (HTTPS enforced in production)
- JavaScript attempts to read session cookie → blocked by HttpOnly
- CSRF token missing on POST → (not implemented in this app)

---

### Layer 6: Internationalization (i18n)
**Scope**: Language detection, translation loading, locale resolution
**Type**: Integration + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Translation File Loading | 2 | 3 | integration, contract | test_translations_load_for_supported_languages, test_missing_translation_falls_back_to_default |
| Language Resolution Priority | 2 | 4 | integration, contract | test_query_param_overrides_session, test_session_overrides_accept_language |
| Default Language Fallback | 1 | 2 | contract, integration | test_unsupported_lang_uses_default, test_missing_translation_file_uses_default |
| Translation Context in Templates | 1 | 2 | integration, contract | test_template_receives_translation_dict, test_template_renders_translated_strings |
| **Layer 6 Total** | **6** | **11** | | |

**Expected Behavior**:
1. Query param ?lang=de → session["lang"] = "de"
2. Next request uses session lang (unless overridden)
3. Accept-Language header: en-US → use "en"
4. No lang specified → DEFAULT_LANGUAGE ("de")
5. Missing translation file → fallback to DEFAULT_LANGUAGE

**Negative Tests**:
- Unsupported language code (fr, es) → ignored, use default
- Malformed Accept-Language header → safely parsed, fallback on error
- Missing translation key → key name returned as fallback

---

### Layer 7: Context Processor & Template Globals
**Scope**: Context injection, template variable availability, dynamic config in templates
**Type**: Integration + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| Backend URL Injection | 1 | 2 | integration, contract | test_backend_url_available_in_templates, test_backend_url_stripped_of_trailing_slash |
| Frontend Config Injection | 0 | 2 | integration, contract | test_frontend_config_dict_in_template_context, test_frontend_config_has_required_fields |
| Language Info Injection | 0 | 2 | integration, contract | test_current_lang_available_in_templates, test_supported_languages_list_available |
| Translation Dict Injection | 0 | 2 | integration, contract | test_translation_dict_available_as_t, test_translation_dict_matches_current_lang |
| **Layer 7 Total** | **1** | **8** | | |

**Expected Template Context**:
- backend_api_url: BACKEND_API_URL string
- frontend_config: dict with backendApiUrl, apiProxyBase, supportedLanguages, defaultLanguage, currentLanguage
- current_lang: current language code
- supported_languages: list of language codes
- t: translation dictionary

**Negative Tests**:
- Context processor fails → request fails with 500
- Missing translation dict → templates fail to render
- Null backend_url → proxy requests fail

---

### Layer 8: Error Handling & Edge Cases
**Scope**: 4xx/5xx responses, malformed requests, upstream failures
**Type**: Integration + Contract

| Component | Current Tests | Target Tests | Markers | Test Examples |
|-----------|---------------|--------------|---------|---------------|
| 404 Not Found | 1 | 2 | contract, integration | test_invalid_route_returns_404, test_404_page_renders |
| 500 Internal Error | 0 | 2 | contract, integration | test_template_error_returns_500, test_500_page_renders |
| Malformed JSON Body | 1 | 2 | contract, integration | test_proxy_forwards_malformed_json, test_proxy_invalid_json_forwarded_to_backend |
| Missing Required Query Params | 0 | 2 | contract, integration | test_proxy_missing_api_key_forwarded, test_route_with_required_slug_missing_returns_404 |
| **Layer 8 Total** | **2** | **8** | | |

**Expected Behaviors**:
- Invalid route → 404 from Flask router
- Template rendering error → 500
- Proxy upstream error → mapped response code
- Malformed query string → forwarded as-is (backend validates)

---

## Test Classification Summary

| Layer | Type | Current | Target | Gap |
|-------|------|---------|--------|-----|
| Config & Init | unit, contract | 30 | 34 | +4 |
| Routing & Templates | integration, contract | 20 | 37 | +17 |
| Proxy & Backend | integration, security, contract | 14 | 28 | +14 |
| Security Headers | security, contract | 10 | 13 | +3 |
| Session & Cookies | security, integration, contract | 5 | 8 | +3 |
| i18n | integration, contract | 6 | 11 | +5 |
| Context Processor | integration, contract | 1 | 8 | +7 |
| Error Handling | integration, contract | 2 | 8 | +6 |
| **TOTAL** | | **88** | **147** | **+59** |

---

## Marker Breakdown

**Currently Configured**:
```ini
[pytest]
markers =
    unit: Unit tests (fast, isolated, no external dependencies)
    integration: Integration tests (external deps like DB, API, auth)
    security: Security validation tests (OWASP, authZ/authN, input validation)
    contract: API contract and interface stability tests
    browser: Browser integration tests
    slow: Slow running tests that should be skipped in fast mode
```

**Test Distribution by Marker**:
- @pytest.mark.unit: ~34 tests (app factory, config validation)
- @pytest.mark.integration: ~85 tests (routing, proxy, i18n, templates)
- @pytest.mark.security: ~22 tests (headers, auth, proxy blocking)
- @pytest.mark.contract: ~120 tests (all response schemas, API contracts)
- @pytest.mark.slow: ~5 tests (timeout tests, network errors)
- @pytest.mark.browser: 0 tests (admin tool is server-side only)

---

## Test Execution Profiles

### Fast Profile (Unit Only)
```bash
pytest -m unit --durations=10
# Expected: ~34 tests, <5 seconds
```

### Standard Profile (Unit + Integration)
```bash
pytest -m "unit or integration" --durations=10
# Expected: ~119 tests, <30 seconds
```

### Full Profile (All Markers)
```bash
pytest --durations=20
# Expected: ~147 tests, <60 seconds
```

### Security Focus
```bash
pytest -m "security or contract" --durations=10
# Expected: ~142 tests, <40 seconds
```

---

## Implementation Phases

### WAVE 0 (Current)
- Define test matrix structure (this document)
- Update pytest.ini with all markers
- Verify current ~88 tests are properly marked
- Document security guarantees and negative tests

### WAVE 1 (Phase 1)
- Implement Layer 1 & 2 gaps (~21 new tests)
- Config validation edge cases
- Route coverage completeness

### WAVE 2 (Phase 2)
- Implement Layer 3-5 gaps (~20 new tests)
- Proxy security hardening
- Session/cookie compliance

### WAVE 3 (Phase 3)
- Implement Layer 6-8 gaps (~18 new tests)
- i18n edge cases
- Error handling completeness

---

## File Structure

```
administration-tool/
├── tests/
│   ├── conftest.py                    # Fixtures: app, client, monkeypatch
│   ├── test_config.py                 # Layer 1: Config validation (unit)
│   ├── test_config_contract.py        # Layer 1: Config contract (contract)
│   ├── test_app_factory.py            # Layer 1: App factory (unit, contract)
│   ├── test_routes.py                 # Layer 2: Routing (integration, contract)
│   ├── test_proxy.py                  # Layer 3: Proxy basics (integration)
│   ├── test_proxy_contract.py         # Layer 3: Proxy contract (contract)
│   ├── test_proxy_security.py         # Layer 3: Proxy security (security)
│   ├── test_proxy_error_mapping.py    # Layer 3: Error mapping (integration)
│   ├── test_security_headers.py       # Layer 4: Security headers (security, contract)
│   ├── test_session_security.py       # Layer 5: Session config (security, contract)
│   ├── test_i18n.py                   # Layer 6: Translation loading (integration)
│   ├── test_language_resolution.py    # Layer 6: Language detection (integration, contract)
│   ├── test_context_processor.py      # Layer 7: Template context (integration, contract)
│   └── test_error_responses.py        # Layer 8: Error handling (contract, integration)
└── pytest.ini                         # Markers configuration
```

---

## Success Criteria

By end of WAVE 0:
- pytest.ini has all 7 markers defined
- pytest --collect-only works and shows proper marker assignments
- All current tests are marked with appropriate layer markers
- No marker warnings on test collection
- Matrix document is complete and actionable

By end of WAVE 1:
- 147 total tests in suite
- Layer 1 & 2 at 100% target coverage
- Security marker on all security-critical tests
- Contract marker on all public API contracts
- Unit marker on all isolated unit tests

---

## Notes for Implementation

1. **Proxy Security**: The `/_proxy` endpoint is critical. Test ALL path patterns comprehensively.
2. **Header Testing**: Use response inspection to verify all security headers present.
3. **Backend Isolation**: Mock/stub backend URL; never make real HTTP calls in unit tests.
4. **Template Rendering**: Test with actual Flask context; verify all injected variables are present.
5. **i18n Fallback**: Test ALL fallback chains: query → session → header → default.
6. **Session Persistence**: Verify language choice persists across requests via session.
7. **CSP Strictness**: CSP should block most inline content; test browser violations if possible.
