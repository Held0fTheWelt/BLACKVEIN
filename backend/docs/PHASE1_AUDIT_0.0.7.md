# Phase 1 Audit – Email verification (0.0.7)

## Findings

### User model (`app/models/user.py`)
- **email_verified_at:** Does NOT exist. Need to add: nullable DateTime, default None.
- Columns today: id, username, email, password_hash, role.

### PasswordResetToken (`app/models/password_reset_token.py`) – reference for token pattern
- **Table:** `password_reset_tokens`
- **Fields:** id, user_id (FK users.id), token_hash (String 128, unique), created_at (DateTime timezone), used (Boolean)
- **No** expires_at column; expiry = created_at + TOKEN_EXPIRY_MINUTES (60).
- **is_expired:** `now > created + timedelta(minutes=...)`; handles naive datetime (replace tzinfo=utc).
- **Token creation (user_service):** `raw = secrets.token_urlsafe(32)`, `token_hash = hashlib.sha256(raw.encode()).hexdigest()`.
- **Relationship:** `user = db.relationship("User", backref="reset_tokens")`.
- EmailVerificationToken will mirror: token_hash, user_id, created_at; add expires_at, used_at, invalidated_at, purpose, sent_to_email.

### user_service.py
- **create_user:** Creates user; no email_verified_at (will default to None once column exists). No change to signature; new users stay unverified.
- **Password reset:** create_password_reset_token, get_valid_reset_token, reset_password_with_token – must remain unchanged.
- **To add:** create_email_verification_token, invalidate_existing_verification_tokens, verify_email_token, resend_verification_email.

### app/web/routes.py
- **/register:** Exists (GET + POST). POST creates user, flashes "Account created. Please log in.", redirects to login. Must change to: create verification token, send verification email, redirect to `/register/pending`.
- **/login:** After verify_user success, sets session. Must add: if user.email_verified_at is None and user.email, do not set session; flash and redirect.
- **To add:** `/register/pending` (GET), `/activate/<token>` (GET), `/resend-verification` (GET + POST).

### app/web/auth.py – require_web_login
- **Current:** Only checks `session.get("user_id")`; redirects to login if missing.
- **Enforcement point:** After confirming user_id in session, load user and check `user.email_verified_at is not None` (or user has no email). If unverified: clear session, flash, redirect to login with hint to resend verification.

### app/api/v1/auth_routes.py – /auth/login
- **Current:** On verify_user success, issues JWT and returns 200.
- **Enforcement point:** Before issuing JWT, check `user.email_verified_at` (or user has no email). If unverified: return 403 JSON `{"error": "Email not verified."}`.

### app/config.py
- **Mail already:** MAIL_SERVER, MAIL_PORT, MAIL_USE_TLS, MAIL_USERNAME, MAIL_PASSWORD, MAIL_DEFAULT_SENDER.
- **To add:** MAIL_ENABLED (bool), MAIL_USE_SSL (bool), APP_PUBLIC_BASE_URL, EMAIL_VERIFICATION_TTL_HOURS (default 24).

### app/extensions.py
- **Flask-Mail:** Already imported and registered (`mail = Mail()`, `mail.init_app(app)`). **Do not modify** (protected).

### requirements.txt
- **flask-mail:** Already present (`flask-mail>=0.10,<1`). No change.

### app/web/templates/register.html
- Exists: username, email, password, password_confirm, CSRF, form-hint, link to login. Extend only if needed; no redesign.

### app/web/templates/base.html
- Blocks: title, content, flash_messages, site_header, site_main, site_footer, extra_scripts. Uses `url_for('static', filename='style.css')`, btn, etc.

### mail_service.py
- **Exists.** send_password_reset_email uses url_for(..., _external=True); dev fallback: if TESTING or (MAIL_SERVER==localhost and not MAIL_USERNAME), log URL and return True. **To add:** send_verification_email(user, raw_token); use MAIL_ENABLED for dev log vs send.

### Tests
- **test_user:** No email, no email_verified_at. After adding column, will have None. Treat “no email” as verified so existing login tests pass.
- **test_user_with_email:** Has email; after schema change will have email_verified_at=None → would be unverified and block login. Must set email_verified_at in this fixture (or in app logic treat test config differently). Conftest: “extend with new fixtures only, do not modify existing ones” – we will add unverified_user; for existing fixtures we set email_verified_at where user has email so password-reset and login tests still pass.
- **editor_user:** Same: set email_verified_at so news write tests pass.
- **New fixture:** unverified_user (email set, email_verified_at=None) for verification/login-block tests.

### Migrations
- Latest: 004_add_user_role. Next: 005_add_email_verified_at (User), then 006_email_verification_tokens (new table).

---

No preparatory code changes in Phase 1. Proceeding to Phase 2 (User model + migration).
